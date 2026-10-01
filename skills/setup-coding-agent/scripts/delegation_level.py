#!/usr/bin/env python3
"""
delegation_level.py - per-project setting for how much edit work Claude hands to the coding agent, plus the
two Claude Code hooks that enforce the strictest level. Standard library only. A copy of this file is placed in
the project (.claude/bombot-forge-hook.py) so a hook command does not depend on the plugin's versioned folder.

Levels (names, not numbers):
  always      every delegable edit goes to agent_run.py; a PreToolUse hook blocks Claude's Edit/Write in the project
  medium      hand over most well-scoped, testable edits; Claude keeps the small or ambiguous ones
  low         hand over only large repetitive jobs with a clear test
  on-request  never on its own; only when the user says so          <- default when nothing is set

Everything it writes is PERSONAL (not meant to be committed): CLAUDE.local.md (one marked block - the rest of the
file is never touched), .claude/settings.local.json (only our hook entries), .claude/bombot-forge.local.json (the
choice), .claude/bombot-forge-hook.py, .claude/bombot-forge-override.json; and it adds them to .git/info/exclude.

  python3 delegation_level.py show   [--project DIR]
  python3 delegation_level.py set    --level LEVEL [--hook] [--project DIR] [--dry-run]
  python3 delegation_level.py remove [--project DIR] [--dry-run]
  python3 delegation_level.py hook pretool|userprompt          (called by Claude Code; reads JSON on stdin)

Exit codes: 0 ok - 2 refused (bad level, not a directory). Hooks always exit 0 and FAIL OPEN: a broken hook must not
stop Claude from editing (the failure is printed to stderr).
"""
import argparse, datetime, fnmatch, json, os, re, shutil, subprocess, sys, tempfile

HOOK_VERSION = 1
LEVELS = ("always", "medium", "low", "on-request")
DEFAULT_LEVEL = "on-request"
CONFIG_REL = ".claude/bombot-forge.local.json"
MD_REL = "CLAUDE.local.md"
SETTINGS_REL = ".claude/settings.local.json"
HOOK_REL = ".claude/bombot-forge-hook.py"
OVERRIDE_REL = ".claude/bombot-forge-override.json"
MARK_BEGIN = "<!-- bombot-forge:delegation:begin -->"
MARK_END = "<!-- bombot-forge:delegation:end -->"
HOOK_TAG = "bombot-forge-hook.py"
OVERRIDE_PHRASES = ["!self", "ให้ claude ทำเองรอบนี้", "claude ทำเองรอบนี้"]
RELEASE_PHRASES = ["!agent", "กลับไปส่ง agent"]
# files Claude may always edit itself under `always`: our own settings/notes and things that must never be delegated
ALLOW_GLOBS = [".claude/**", "CLAUDE.md", "CLAUDE.local.md", ".gitignore", "deploy.xml", "manifest.xml", ".env*"]
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
LEVEL_TITLE = {"always": "บังคับทุกกรณี (always)", "medium": "กลาง (medium)", "low": "น้อย (low)",
               "on-request": "เมื่อเรียกใช้ (on-request)"}
LEVEL_RULES = {
    "always": [
        "งานแก้/เขียนไฟล์ในโปรเจกต์นี้ทุกงานที่ส่งได้ → เขียน brief ลงไฟล์ แล้วรัน `agent_run.py --repo . --task-file <brief>` "
        "**ห้ามแก้ไฟล์เอง** · หน้าที่ของ Claude: brief, review ทุกบรรทัด, apply (`git apply`), ปิดด้วย `--log-outcome`",
    ],
    "medium": [
        "ส่งงานที่ขอบเขตชัดและมี acceptance test (คำสั่งที่ต้องผ่าน) ให้ agent เกือบทั้งหมด · "
        "งานเล็กมาก (ไม่กี่บรรทัด), งานกำกวม, หรืองานที่ต้องตัดสินใจเชิงออกแบบ Claude ทำเอง",
    ],
    "low": [
        "ส่งเฉพาะงานซ้ำๆ จำนวนมาก (หลายไฟล์/หลายจุดแบบเดียวกัน, rote) ที่มี test ชัดเจน — นอกนั้น Claude ทำเอง",
    ],
    "on-request": [
        "ไม่ส่งงานให้ agent เอง · ส่งเฉพาะเมื่อผู้ใช้สั่งชัด (เช่น \"ส่ง agent\", \"ใช้ teibto-agent\")",
    ],
}


# ---------------------------------------------------------------- files
def _p(project, rel):
    return os.path.join(project, *rel.split("/"))


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".bf-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _backup(path):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def read_config(project):
    try:
        d = json.loads(_read(_p(project, CONFIG_REL)) or "{}")
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def current_level(project):
    lv = read_config(project).get("level")
    return lv if lv in LEVELS else DEFAULT_LEVEL


# ---------------------------------------------------------------- the CLAUDE.local.md block
def render_block(level, hook, phrases=None, release=None, allow=None):
    if level not in LEVELS:
        raise ValueError("level must be one of %s" % ", ".join(LEVELS))
    lines = [MARK_BEGIN,
             "## การส่งงานแก้ไฟล์ให้ coding agent (ตั้งโดย skill `setup-coding-agent` — เฉพาะเครื่องนี้ ไม่ commit)",
             "ระดับของ project นี้: **%s**" % LEVEL_TITLE[level]]
    lines += ["- " + r for r in LEVEL_RULES[level]]
    if level == "always" and hook:
        lines.append("- hook บล็อกเครื่องมือ Edit/Write ในโปรเจกต์ (ยกเว้น: %s) · ถ้าผู้ใช้พิมพ์ %s ในข้อความ = "
                     "**รอบสนทนานี้** Claude แก้เองได้ · %s = กลับไปส่ง agent · **Claude ห้ามเปิดโหมดนี้เอง**" % (
                         ", ".join("`%s`" % g for g in (allow or ALLOW_GLOBS)),
                         " หรือ ".join("`%s`" % x for x in (phrases or OVERRIDE_PHRASES)),
                         " หรือ ".join("`%s`" % x for x in (release or RELEASE_PHRASES))))
    lines += ["- ไม่ส่ง agent เด็ดขาด: งาน browser, production, deploy, secrets, ข้อมูลลูกค้า · ผลจาก agent เป็นแค่คำอ้าง "
              "ต้อง review ทุกบรรทัดก่อน apply",
              MARK_END]
    return "\n".join(lines) + "\n"


def upsert_block(text, block):
    """Replace our marked block, or append it. Every other character of `text` is kept as it was."""
    text = text or ""
    i, j = text.find(MARK_BEGIN), text.find(MARK_END)
    if i != -1 and j != -1 and j > i:
        end = j + len(MARK_END)
        if text[end:end + 1] == "\n":
            end += 1
        return text[:i] + block + text[end:]
    sep = "" if not text else ("\n" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n"))
    return text + sep + block


def remove_block(text):
    i, j = (text or "").find(MARK_BEGIN), (text or "").find(MARK_END)
    if i == -1 or j == -1 or j < i:
        return text
    end = j + len(MARK_END)
    if text[end:end + 1] == "\n":
        end += 1
    out = text[:i].rstrip("\n") + ("\n" if text[:i].strip() else "") + text[end:].lstrip("\n")
    return out


# ---------------------------------------------------------------- settings.local.json (hooks)
def hook_commands(python):
    base = '"%s" "$CLAUDE_PROJECT_DIR/%s" hook ' % (python, HOOK_REL)
    return base + "pretool", base + "userprompt"


def merge_hooks(settings, python, enable):
    """Remove every hook entry of ours, then (if enable) add the two. Other keys and other hooks are kept."""
    s = json.loads(json.dumps(settings or {}))
    hooks = s.setdefault("hooks", {})
    for event in list(hooks):
        kept = []
        for entry in hooks[event]:
            inner = [h for h in entry.get("hooks", []) if HOOK_TAG not in str(h.get("command", ""))]
            if inner:
                kept.append(dict(entry, hooks=inner))
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if enable:
        pre, prompt = hook_commands(python)
        hooks.setdefault("PreToolUse", []).append(
            {"matcher": "|".join(EDIT_TOOLS), "hooks": [{"type": "command", "command": pre}]})
        hooks.setdefault("UserPromptSubmit", []).append({"hooks": [{"type": "command", "command": prompt}]})
    if not hooks:
        del s["hooks"]
    return s


def ensure_excluded(project, rels):
    """Add paths to .git/info/exclude (per clone, never committed) unless git already ignores them."""
    notes = []
    try:
        top = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=project, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ["git not available - make sure %s are not committed" % ", ".join(rels)]
    if top.returncode != 0:
        return ["not a git repo - nothing to exclude"]
    gitdir = os.path.join(project, top.stdout.strip()) if not os.path.isabs(top.stdout.strip()) else top.stdout.strip()
    excl = os.path.join(gitdir, "info", "exclude")
    have = (_read(excl) or "")
    add = []
    for rel in rels:
        ign = subprocess.run(["git", "check-ignore", "-q", rel], cwd=project, capture_output=True, timeout=20)
        if ign.returncode != 0 and rel not in have.split("\n"):
            add.append(rel)
    if add:
        os.makedirs(os.path.dirname(excl), exist_ok=True)
        _write_atomic(excl, have + ("" if have.endswith("\n") or not have else "\n") + "\n".join(add) + "\n")
        notes.append("added to .git/info/exclude: " + ", ".join(add))
    return notes or ["all personal files are already git-ignored"]


# ---------------------------------------------------------------- install / remove
def install(project, level, hook=False, python=None, phrases=None, release=None, allow=None, dry_run=False):
    if level not in LEVELS:
        raise ValueError("level must be one of %s" % ", ".join(LEVELS))
    if not os.path.isdir(project):
        raise ValueError("not a directory: %s" % project)
    python = python or sys.executable
    hook = bool(hook) and level == "always"
    actions = []
    cfg = {"schema": 1, "level": level, "hook": hook, "override_phrases": phrases or OVERRIDE_PHRASES,
           "release_phrases": release or RELEASE_PHRASES, "allow_globs": allow or ALLOW_GLOBS,
           "set_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    md_old = _read(_p(project, MD_REL))
    md_new = upsert_block(md_old, render_block(level, hook, cfg["override_phrases"], cfg["release_phrases"], cfg["allow_globs"]))
    st_old = _read(_p(project, SETTINGS_REL))
    st_new = json.dumps(merge_hooks(json.loads(st_old) if st_old else {}, python, hook), ensure_ascii=False, indent=2) + "\n"
    if (st_old is None and not hook):
        st_new = None                                      # nothing to write: no file, no hook wanted
    actions.append("%s: level=%s hook=%s" % (CONFIG_REL, level, hook))
    actions.append("%s: %s the delegation block (rest of the file untouched)" % (MD_REL, "update" if md_old and MARK_BEGIN in md_old else "add"))
    if st_new is not None and st_new != st_old:
        actions.append("%s: %s our hook entries" % (SETTINGS_REL, "add" if hook else "remove"))
    if hook:
        actions.append("%s: copy of this script (hook version %d)" % (HOOK_REL, HOOK_VERSION))
    if dry_run:
        return ["DRY RUN - " + a for a in actions]
    _write_atomic(_p(project, CONFIG_REL), json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    if md_new != md_old:
        _backup(_p(project, MD_REL)) if md_old is not None else None
        _write_atomic(_p(project, MD_REL), md_new)
    if st_new is not None and st_new != st_old:
        _backup(_p(project, SETTINGS_REL)) if st_old is not None else None
        _write_atomic(_p(project, SETTINGS_REL), st_new)
    if hook:
        shutil.copy2(os.path.abspath(__file__), _p(project, HOOK_REL))
    elif os.path.exists(_p(project, HOOK_REL)):
        os.remove(_p(project, HOOK_REL))                    # level changed away from `always`: drop the unused copy
        actions.append("%s: removed (no hook at this level)" % HOOK_REL)
    actions += ensure_excluded(project, [CONFIG_REL, MD_REL, SETTINGS_REL, HOOK_REL, OVERRIDE_REL])
    return actions


def remove(project, dry_run=False):
    actions = []
    md_old = _read(_p(project, MD_REL))
    if md_old and MARK_BEGIN in md_old:
        actions.append("%s: remove our block" % MD_REL)
    st_old = _read(_p(project, SETTINGS_REL))
    if st_old and HOOK_TAG in st_old:
        actions.append("%s: remove our hook entries" % SETTINGS_REL)
    for rel in (CONFIG_REL, HOOK_REL, OVERRIDE_REL):
        if os.path.exists(_p(project, rel)):
            actions.append("delete " + rel)
    if dry_run:
        return ["DRY RUN - " + a for a in actions] or ["DRY RUN - nothing to remove"]
    if md_old and MARK_BEGIN in md_old:
        _backup(_p(project, MD_REL))
        new = remove_block(md_old)
        if new.strip():
            _write_atomic(_p(project, MD_REL), new)
        else:
            os.remove(_p(project, MD_REL))
    if st_old and HOOK_TAG in st_old:
        _backup(_p(project, SETTINGS_REL))
        _write_atomic(_p(project, SETTINGS_REL), json.dumps(merge_hooks(json.loads(st_old), sys.executable, False), ensure_ascii=False, indent=2) + "\n")
    for rel in (CONFIG_REL, HOOK_REL, OVERRIDE_REL):
        if os.path.exists(_p(project, rel)):
            os.remove(_p(project, rel))
    return actions or ["nothing to remove"]


# ---------------------------------------------------------------- hooks
def _matches(rel, pat):
    rel = rel.replace(os.sep, "/")
    if pat.endswith("/**"):
        return rel == pat[:-3] or rel.startswith(pat[:-2])
    if "/" not in pat:
        return fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], pat)
    return fnmatch.fnmatchcase(rel, pat)


def _overrides(project):
    try:
        d = json.loads(_read(_p(project, OVERRIDE_REL)) or "{}")
        return d if isinstance(d, dict) and isinstance(d.get("sessions"), list) else {"sessions": []}
    except ValueError:
        return {"sessions": []}


def decide_pretool(payload, project=None):
    """Return the hook's JSON answer (deny) or None (allow). Pure apart from reading the project's files."""
    if payload.get("tool_name") not in EDIT_TOOLS:
        return None
    project = project or os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ""
    cfg = read_config(project)
    if cfg.get("level") != "always" or not cfg.get("hook"):
        return None
    ti = payload.get("tool_input") or {}
    target = ti.get("file_path") or ti.get("notebook_path")
    if not target:
        return None
    root, path = os.path.realpath(project), os.path.realpath(os.path.join(project, target) if not os.path.isabs(target) else target)
    if path != root and not path.startswith(root + os.sep):
        return None                                        # outside the project: not ours to police
    rel = os.path.relpath(path, root)
    if any(_matches(rel, g) for g in cfg.get("allow_globs") or ALLOW_GLOBS):
        return None
    sid = payload.get("session_id")
    if sid and any(s.get("session_id") == sid for s in _overrides(project)["sessions"]):
        return None
    phrases = cfg.get("override_phrases") or OVERRIDE_PHRASES
    reason = ("DELEGATION LEVEL = always (this project): do not edit %s yourself. Write a brief to a file and run "
              "agent_run.py (skill setup-coding-agent), then review and apply the patch. Only the user can lift this for "
              "the current conversation, by typing one of: %s. Do not ask the user to type it and do not work around "
              "this block." % (rel, ", ".join(phrases)))
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}


def handle_userprompt(payload, project=None):
    """Record/clear the per-conversation override from what the USER typed. Returns text for Claude's context or None."""
    project = project or os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ""
    cfg = read_config(project)
    if cfg.get("level") != "always" or not cfg.get("hook"):
        return None
    sid, prompt = payload.get("session_id"), (payload.get("prompt") or "").casefold()
    if not sid or not prompt:
        return None
    ov = _overrides(project)
    have = any(s.get("session_id") == sid for s in ov["sessions"])
    rel_hit = any(x.casefold() in prompt for x in cfg.get("release_phrases") or RELEASE_PHRASES)
    set_hit = any(x.casefold() in prompt for x in cfg.get("override_phrases") or OVERRIDE_PHRASES)
    if rel_hit and have:
        ov["sessions"] = [s for s in ov["sessions"] if s.get("session_id") != sid]
        _write_atomic(_p(project, OVERRIDE_REL), json.dumps(ov, indent=2) + "\n")
        return "Delegation override ended by the user: back to `always` (do not edit project files yourself; use agent_run.py)."
    if set_hit and not rel_hit and not have:
        ov["sessions"] = (ov["sessions"] + [{"session_id": sid, "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}])[-50:]
        _write_atomic(_p(project, OVERRIDE_REL), json.dumps(ov, indent=2) + "\n")
        return "The user lifted the delegation block for THIS conversation (they typed it): you may edit project files yourself now."
    return None


def run_hook(kind, stdin_text):
    try:
        payload = json.loads(stdin_text or "{}")
        if kind == "pretool":
            out = decide_pretool(payload)
            if out:
                sys.stdout.write(json.dumps(out, ensure_ascii=False))
        elif kind == "userprompt":
            msg = handle_userprompt(payload)
            if msg:
                sys.stdout.write(msg)
    except Exception as e:                                 # fail open: never stop Claude because the hook broke
        sys.stderr.write("bombot-forge hook error (ignored, edits allowed): %s\n" % e)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("show", "set", "remove"):
        sp = sub.add_parser(name)
        sp.add_argument("--project", default=os.getcwd())
        if name != "show":
            sp.add_argument("--dry-run", action="store_true")
        if name == "set":
            sp.add_argument("--level", required=True)
            sp.add_argument("--hook", action="store_true", help="with level always: also install the blocking hooks")
    hp = sub.add_parser("hook"); hp.add_argument("kind", choices=["pretool", "userprompt"])
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        return run_hook(a.kind, sys.stdin.read())
    project = os.path.abspath(a.project)
    try:
        if a.cmd == "show":
            cfg = read_config(project)
            print("project : %s\nlevel   : %s%s\nhook    : %s\nblock   : %s" % (
                project, current_level(project), "" if cfg.get("level") in LEVELS else " (default - nothing set)",
                bool(cfg.get("hook")), "present" if MARK_BEGIN in (_read(_p(project, MD_REL)) or "") else "absent"))
        elif a.cmd == "set":
            print("\n".join(install(project, a.level, a.hook, dry_run=a.dry_run)))
        else:
            print("\n".join(remove(project, dry_run=a.dry_run)))
    except ValueError as e:
        print("REFUSED:", e); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
