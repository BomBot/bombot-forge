#!/usr/bin/env python3
"""
build_nondev.py - assemble the NON-DEV global CLAUDE.md text.

It does not keep a second copy of the shared sections. It takes the dev snapshot that ships in this plugin
(../../setup-global-instructions/reference/global-CLAUDE.snapshot.md), keeps five of its sections verbatim
(Accuracy, Communication style, Slack, Session memory, Browser automation), drops the developer-only ones
(Code conventions, Editing existing code, SDF Deploy, graphify, project-folder move, Coding agent), and adds the
sections in ../reference/nondev-sections.md (Role, the SDF / deploy / upload ban, the UI scope A/B/C, way of working, Git).

  python3 build_nondev.py                 # print the assembled text
  python3 build_nondev.py --out FILE      # write it to FILE
  python3 build_nondev.py --deny-rules    # print the permissions.deny entries as JSON

Exit codes: 0 ok - 2 refused (a section the recipe needs is missing from the dev snapshot or the overrides)
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEV_SNAPSHOT = os.path.join(HERE, "..", "..", "setup-global-instructions", "reference", "global-CLAUDE.snapshot.md")
OVERRIDES = os.path.join(HERE, "..", "reference", "nondev-sections.md")

# (source, heading prefix) in output order. "dev" = kept verbatim from the dev snapshot, "non" = from nondev-sections.md
RECIPE = [("non", "Role"), ("dev", "Accuracy"), ("dev", "Communication style"), ("dev", "Slack"),
          ("non", "ห้ามใช้ SDF"), ("non", "ขอบเขตงานผ่าน UI"), ("non", "วิธีทำงาน"), ("non", "Git"),
          ("dev", "Session memory"), ("dev", "Browser automation")]

HEADER = """> **Reference for a NON-DEV machine** (someone who reads and verifies NetSuite but does not write or deploy code),
> assembled by the `setup-global-instructions-nondev` skill from the dev snapshot plus its own sections.
> Customer/personal identifiers are placeholders - fill them from your own values, never invent:
> `<Your Name>` · `<work-email>` · `<personal-gmail>` · `<PROJECT>` · `<qa-project>`.
> Do NOT paste real customer names or account ids back into the repo - it is public and the redaction CI blocks them.
"""

# Entries for ~/.claude/settings.json -> permissions.deny. Command-text patterns: measured to block a direct call,
# `bash -c '...'` and an absolute/`$(which ...)` path; NOT a call whose name is built from a variable.
DENY_RULES = ["Bash(suitecloud:*)", "Bash(npx suitecloud:*)", "Bash(*suitecloud*)"]


def split_h1(text):
    """[(heading, body_text_including_the_heading_line)], ignoring '# ' lines inside ``` fences. Text before the
    first heading is returned under heading None."""
    out, cur, head, fenced = [], [], None, False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("# "):
            if cur or head is not None:
                out.append((head, "".join(cur)))
            head, cur = line[2:].strip(), [line]
        else:
            cur.append(line)
    out.append((head, "".join(cur)))
    return out


def pick(sections, prefix):
    hits = [body for h, body in sections if h and h.startswith(prefix)]
    if len(hits) != 1:
        raise ValueError("expected exactly one section starting with %r, found %d" % (prefix, len(hits)))
    return hits[0].rstrip("\n") + "\n"


def build(dev_text=None, nondev_text=None):
    dev = split_h1(dev_text if dev_text is not None else open(DEV_SNAPSHOT, encoding="utf-8").read())
    non = split_h1(nondev_text if nondev_text is not None else open(OVERRIDES, encoding="utf-8").read())
    parts = [HEADER]
    for src, prefix in RECIPE:
        parts.append(pick(dev if src == "dev" else non, prefix))
    return "\n".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out")
    ap.add_argument("--deny-rules", action="store_true")
    a = ap.parse_args(argv)
    if a.deny_rules:
        print(json.dumps(DENY_RULES, indent=2)); return 0
    try:
        text = build()
    except (ValueError, OSError) as e:
        print("REFUSED:", e); return 2
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote", a.out, "(%d lines)" % text.count("\n"))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
