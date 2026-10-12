#!/usr/bin/env bash
# The plugin cannot install subedit, so a missing command has to say so
# rather than failing in a way that reads as a clean run.
set -uo pipefail

if command -v subedit-hook >/dev/null 2>&1; then
    exec subedit-hook
fi

if command -v uvx >/dev/null 2>&1; then
    exec uvx --from git+https://github.com/mroops0111/subedit subedit-hook
fi

cat >&2 <<'MESSAGE'
subedit-hook is not installed, so comment checks are not running.

    uv tool install git+https://github.com/mroops0111/subedit

Install it, or remove the subedit plugin.
MESSAGE
exit 1
