#!/usr/bin/env bash
# validate-setup.sh — confirm THIS machine is set up to use ns_write.py the same
# way as the others. Run from a project root:  bash <skill>/scripts/validate-setup.sh
# Exit 0 = all required checks PASS; exit 1 = at least one FAIL.

set -u
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CANON="$SKILL_DIR/scripts/ns_write.py"
PROJ_SCRIPT="scripts/qa/ns_write.py"
SETTINGS=".claude/settings.local.json"
ALLOW_RULE='Bash(python3 scripts/qa/ns_write.py:*)'

fail=0
pass() { printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; fail=1; }
info() { printf '  \033[33mINFO\033[0m  %s\n' "$1"; }

echo "ns-record-write setup check — project: $(pwd)"

# 1. project script present + matches canonical (no drift across machines)
if [ -f "$PROJ_SCRIPT" ]; then
  if [ -f "$CANON" ] && cmp -s "$PROJ_SCRIPT" "$CANON"; then
    pass "$PROJ_SCRIPT present and matches skill canonical"
  else
    bad "$PROJ_SCRIPT present but DIFFERS from skill canonical ($CANON) — re-copy to sync"
  fi
else
  bad "$PROJ_SCRIPT missing — copy it: mkdir -p scripts/qa && cp \"$CANON\" $PROJ_SCRIPT"
fi

# 2. allow rule present in settings.local.json (the per-machine bit)
if [ -f "$SETTINGS" ]; then
  if python3 - "$SETTINGS" "$ALLOW_RULE" <<'PY'
import json, sys
path, rule = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
except Exception as e:
    print("   (settings.local.json not valid JSON: %s)" % e); sys.exit(2)
allow = (d.get("permissions") or {}).get("allow") or []
sys.exit(0 if rule in allow else 1)
PY
  then
    pass "allow rule present in $SETTINGS"
  else
    bad "allow rule NOT in $SETTINGS — add:  \"$ALLOW_RULE\"  to permissions.allow"
  fi
else
  bad "$SETTINGS missing — create it with permissions.allow containing \"$ALLOW_RULE\""
fi

# 3. bsk: installed, daemon answering, a browser connected, extension not behind the CLI
if command -v bsk >/dev/null 2>&1; then
  st="$(BSK_AUTO_START=0 bsk status --json 2>/dev/null)"
  if [ -z "$st" ]; then
    bad "bsk installed ($(bsk --version 2>/dev/null)) but the daemon is not answering (bsk daemon start; bsk doctor)"
  else
    msg="$(printf '%s' "$st" | python3 -c '
import json, sys
b = (json.load(sys.stdin).get("browsers") or [])
if not b: print("NOBROWSER"); sys.exit()
skew = [x for x in b if x.get("version_skew")]
print(("SKEW extension %s" % skew[0].get("extension_version")) if skew else "OK")' 2>/dev/null)"
    case "$msg" in
      OK)        pass "bsk lane: $(bsk --version 2>/dev/null), browser connected, no version skew" ;;
      NOBROWSER) bad "bsk daemon up but no browser connected (open Chrome, turn the BrowserSkill extension on)" ;;
      SKEW*)     bad "bsk $(bsk --version 2>/dev/null) but the Chrome ${msg#SKEW } is behind — update the extension (chrome://extensions)" ;;
      *)         bad "could not read bsk status" ;;
    esac
  fi
else
  bad "bsk not installed (run the setup-browser skill)"
fi

echo
if [ "$fail" -eq 0 ]; then echo "RESULT: all required checks PASS"; else echo "RESULT: setup INCOMPLETE — fix the FAIL lines above"; fi
exit "$fail"
