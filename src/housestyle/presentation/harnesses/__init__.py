from ...infrastructure import PYTHON
from .base import BLOCK_EXIT, AgentHarness, Payload
from .claude_code import ClaudeCodeHarness
from .codex import CodexHarness


EXTENSIONS = frozenset(PYTHON.extensions)

# Each agent names its edit tools differently, so a payload identifies its own sender.
# One project can run both agents at once, and neither needs to know the other exists.
ALL_HARNESSES: tuple[AgentHarness, ...] = (
    ClaudeCodeHarness(EXTENSIONS),
    CodexHarness(EXTENSIONS),
)


def harness_for(payload: Payload) -> AgentHarness | None:
    return next((harness for harness in ALL_HARNESSES if harness.handles(payload)), None)


__all__ = [
    'ALL_HARNESSES',
    'BLOCK_EXIT',
    'AgentHarness',
    'ClaudeCodeHarness',
    'CodexHarness',
    'Payload',
    'harness_for',
]
