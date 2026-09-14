import pathlib
import typing

from .base import Payload, existing_source_files


EDIT_TOOLS = frozenset({'Edit', 'Write', 'MultiEdit', 'NotebookEdit'})
PATH_FIELDS = ('file_path', 'notebook_path')


class ClaudeCodeHarness:
    name = 'claude-code'
    summary = 'Claude Code names the edited file in tool_input.'
    example = '{"tool_name": "Edit", "tool_input": {"file_path": "src/module.py"}}'

    def __init__(self, extensions: frozenset[str]) -> None:
        self._extensions = extensions

    def handles(self, payload: Payload) -> bool:
        """Claude Code names the edited file outright, under one of two keys."""
        tool_name = payload.get('tool_name')
        if not isinstance(tool_name, str) or tool_name not in EDIT_TOOLS:
            return False
        return any(field in self._tool_input(payload) for field in PATH_FIELDS)

    def targets(self, payload: Payload) -> tuple[pathlib.Path, ...]:
        tool_input = self._tool_input(payload)
        named = [tool_input.get(field) for field in PATH_FIELDS]
        return existing_source_files([value for value in named if isinstance(value, str) and value], self._extensions)

    def _tool_input(self, payload: Payload) -> typing.Mapping[str, object]:
        tool_input = payload.get('tool_input')
        return tool_input if isinstance(tool_input, dict) else {}
