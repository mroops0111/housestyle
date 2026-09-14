from ...infrastructure import PYTHON
from .base import BLOCK_EXIT, AgentHarness, Payload
from .claude_code import ClaudeCodeHarness
from .codex import CodexHarness
from .explicit import ExplicitPathsHarness


EXTENSIONS = frozenset(PYTHON.extensions)

# Order decides which harness claims an ambiguous payload, and the fallback must come last.
ALL_HARNESSES: tuple[AgentHarness, ...] = (
    ClaudeCodeHarness(EXTENSIONS),
    CodexHarness(EXTENSIONS),
    ExplicitPathsHarness(EXTENSIONS),
)


def harness_for(payload: Payload) -> AgentHarness | None:
    return next((harness for harness in ALL_HARNESSES if harness.handles(payload)), None)


__all__ = [
    'ALL_HARNESSES',
    'BLOCK_EXIT',
    'AgentHarness',
    'ClaudeCodeHarness',
    'CodexHarness',
    'ExplicitPathsHarness',
    'Payload',
    'harness_for',
]
