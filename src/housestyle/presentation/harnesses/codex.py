import pathlib
import re
import typing

from .base import Payload, existing_source_files


EDIT_TOOLS = frozenset({'apply_patch'})

# Codex carries no path field.
# The patch body names each file in its header, so the path is read back out of the diff.
_PATCH_HEADER = re.compile(r'^(?:\*\*\*\s+(?:Update|Add|Delete) File:|---|\+\+\+)\s+(.+?)\s*$', re.MULTILINE)
_STRIP_PREFIX = re.compile(r'^[ab]/')


class CodexHarness:
    name = 'codex'

    def __init__(self, extensions: frozenset[str]) -> None:
        self._extensions = extensions

    def handles(self, payload: Payload) -> bool:
        tool_name = payload.get('tool_name')
        return isinstance(tool_name, str) and tool_name in EDIT_TOOLS

    def targets(self, payload: Payload) -> tuple[pathlib.Path, ...]:
        command = self._tool_input(payload).get('command')
        if not isinstance(command, str):
            return ()
        named = [_STRIP_PREFIX.sub('', match.group(1)) for match in _PATCH_HEADER.finditer(command)]
        return existing_source_files([name for name in named if name != '/dev/null'], self._extensions)

    def _tool_input(self, payload: Payload) -> typing.Mapping[str, object]:
        tool_input = payload.get('tool_input')
        return tool_input if isinstance(tool_input, dict) else {}
