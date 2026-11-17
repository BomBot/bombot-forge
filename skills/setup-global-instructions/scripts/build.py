#!/usr/bin/env python3
"""
build.py - assemble the global CLAUDE.md text for a dev or a NON-DEV machine.

--role dev returns the dev snapshot (../reference/global-CLAUDE.snapshot.md) as is. --role nondev (the default):

it does not keep a second copy of the shared sections. It takes the dev snapshot, keeps six of its sections
verbatim (the machine section, Accuracy, Communication style, Slack, Session memory, Browser automation), drops the
developer-only ones (Code conventions, Editing existing code, SDF Deploy, codegraph, Coding agent), and adds the
sections in ../reference/nondev-sections.md (Role, the SDF / deploy / upload ban, the UI scope A/B/C, the narrow JS hotfix lane, way of working, Git).

  python3 build.py [--role dev|nondev]          # print the text
  python3 build.py --role dev --out FILE        # write it to FILE
  python3 build.py --deny-rules                 # print the non-dev permissions.deny entries as JSON

Exit codes: 0 ok - 2 refused (a section the recipe needs is missing from the dev snapshot or the overrides)
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEV_SNAPSHOT = os.path.join(HERE, "..", "reference", "global-CLAUDE.snapshot.md")
OVERRIDES = os.path.join(HERE, "..", "reference", "nondev-sections.md")

# (source, heading prefix) in output order. "dev" = kept verbatim from the dev snapshot, "non" = from nondev-sections.md
RECIPE = [("non", "Role"), ("dev", "เครื่องนี้"), ("dev", "Accuracy"), ("dev", "Communication style"), ("dev", "Slack"),
          ("non", "ห้ามใช้ SDF"), ("non", "ขอบเขตงานผ่าน UI"), ("non", "Hotfix JS"), ("non", "วิธีทำงาน"), ("non", "Git"),
          ("dev", "Session memory"), ("dev", "Browser automation")]

HEADER = """> **Reference for a NON-DEV machine** (someone who reads and verifies NetSuite but does not write or deploy code),
> assembled by the `setup-global-instructions` skill (role non-dev) from the dev snapshot plus its own sections.
> Placeholders are filled per machine, never invented: `<Your Name>` · `<work-email>` (asked) · `<OS>` (detected).
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
    ap.add_argument("--role", choices=("dev", "nondev"), default="nondev")
    ap.add_argument("--out")
    ap.add_argument("--deny-rules", action="store_true")
    a = ap.parse_args(argv)
    if a.deny_rules:
        print(json.dumps(DENY_RULES, indent=2)); return 0
    try:
        text = open(DEV_SNAPSHOT, encoding="utf-8").read() if a.role == "dev" else build()
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
