import pathlib

from ...infrastructure import PYTHON
from .base import BLOCK_EXIT, AgentHarness, HarnessMeta, Payload
from .claude_code import ClaudeCodeHarness
from .codex import CodexHarness


EXTENSIONS = frozenset(PYTHON.extensions)

# Each agent names its edit tools differently, so a payload identifies its own sender.
# One project can run both agents at once, and neither needs to know the other exists.
ALL_HARNESSES: tuple[AgentHarness, ...] = (
    ClaudeCodeHarness(EXTENSIONS),
    CodexHarness(EXTENSIONS),
)


def resolve(payload: Payload) -> tuple[AgentHarness, tuple[pathlib.Path, ...]] | None:
    """Hand the payload to each harness until one recognises it.

    A harness that declines returns None, so declining and finding nothing stay distinct.
    """
    for harness in ALL_HARNESSES:
        found = harness.edited_files(payload)
        if found is not None:
            return harness, found
    return None


__all__ = [
    'ALL_HARNESSES',
    'BLOCK_EXIT',
    'AgentHarness',
    'ClaudeCodeHarness',
    'CodexHarness',
    'HarnessMeta',
    'Payload',
    'resolve',
]
