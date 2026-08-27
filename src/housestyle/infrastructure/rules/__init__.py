from .layout import LineWidthRule, WrapPointRule
from .rewrite import StubFragmentRule, UnbreakableSentenceRule


LAYOUT_RULES = (WrapPointRule(), LineWidthRule())
REWRITE_RULES = (StubFragmentRule(), UnbreakableSentenceRule())
ALL_RULES = LAYOUT_RULES + REWRITE_RULES

__all__ = [
    'ALL_RULES',
    'LAYOUT_RULES',
    'REWRITE_RULES',
    'LineWidthRule',
    'StubFragmentRule',
    'UnbreakableSentenceRule',
    'WrapPointRule',
]
