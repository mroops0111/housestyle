import pathlib
import re
import typing

from .base import HarnessMeta, Payload, existing_source_files


EDIT_TOOLS = frozenset({'apply_patch'})

# Codex carries no path field.
# The patch body names each file in its header, so the path is read back out of the diff.
_PATCH_HEADER = re.compile(r'^(?:\*\*\*\s+(?:Update|Add|Delete) File:|---|\+\+\+)\s+(.+?)\s*$', re.MULTILINE)
_STRIP_PREFIX = re.compile(r'^[ab]/')

CODEX = HarnessMeta(
    name='codex',
    summary='Codex sends a patch, and the path is read from its header.',
    example={'tool_name': 'apply_patch', 'tool_input': {'command': '*** Update File: src/module.py'}},
)


class CodexHarness:
    meta = CODEX

    def __init__(self, extensions: frozenset[str]) -> None:
        self._extensions = extensions

    def edited_files(self, payload: Payload) -> tuple[pathlib.Path, ...] | None:
        tool_name = payload.get('tool_name')
        if not isinstance(tool_name, str) or tool_name not in EDIT_TOOLS:
            return None
        command = self._tool_input(payload).get('command')
        if not isinstance(command, str):
            return None
        named = [_STRIP_PREFIX.sub('', match.group(1)) for match in _PATCH_HEADER.finditer(command)]
        return existing_source_files([name for name in named if name != '/dev/null'], self._extensions)

    def _tool_input(self, payload: Payload) -> typing.Mapping[str, object]:
        tool_input = payload.get('tool_input')
        return tool_input if isinstance(tool_input, dict) else {}
