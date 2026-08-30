from ..languages import PYTHON
from .layout import LineWidthRule, WrapPointRule
from .rewrite import StubFragmentRule, UnbreakableSentenceRule
from .structural import BlockTooLongRule, DocCommentFormRule, NoFileHeaderRule, NoSignatureRestatingRule


LAYOUT_RULES = (WrapPointRule(), LineWidthRule())
REWRITE_RULES = (StubFragmentRule(), UnbreakableSentenceRule())
STRUCTURAL_RULES = (
    NoFileHeaderRule(),
    DocCommentFormRule(PYTHON),
    NoSignatureRestatingRule(PYTHON),
    BlockTooLongRule(),
)
ALL_RULES = LAYOUT_RULES + REWRITE_RULES + STRUCTURAL_RULES

__all__ = [
    'ALL_RULES',
    'LAYOUT_RULES',
    'REWRITE_RULES',
    'STRUCTURAL_RULES',
    'BlockTooLongRule',
    'DocCommentFormRule',
    'LineWidthRule',
    'NoFileHeaderRule',
    'NoSignatureRestatingRule',
    'StubFragmentRule',
    'UnbreakableSentenceRule',
    'WrapPointRule',
]
