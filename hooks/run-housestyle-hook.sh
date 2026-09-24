#!/usr/bin/env bash
# The plugin cannot install housestyle, so a missing command has to say so
# rather than failing in a way that reads as a clean run.
set -uo pipefail

if command -v housestyle-hook >/dev/null 2>&1; then
    exec housestyle-hook
fi

if command -v uvx >/dev/null 2>&1; then
    exec uvx --from git+https://github.com/mroops0111/housestyle housestyle-hook
fi

cat >&2 <<'MESSAGE'
housestyle-hook is not installed, so comment checks are not running.

    uv tool install git+https://github.com/mroops0111/housestyle

Install it, or remove the housestyle plugin.
MESSAGE
exit 1
