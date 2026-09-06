from ..languages import PYTHON
from .layout import LineTooLongRule, MidClauseBreakRule
from .rewrite import StubFragmentRule, UnbreakableSentenceRule
from .structural import BlockTooLongRule, FileHeaderCommentRule, PlainCommentOnPublicRule, SignatureRestatingTagRule


LAYOUT_RULES = (MidClauseBreakRule(), LineTooLongRule())
REWRITE_RULES = (StubFragmentRule(), UnbreakableSentenceRule())
STRUCTURAL_RULES = (
    FileHeaderCommentRule(),
    PlainCommentOnPublicRule(PYTHON),
    SignatureRestatingTagRule(PYTHON),
    BlockTooLongRule(),
)
ALL_RULES = LAYOUT_RULES + REWRITE_RULES + STRUCTURAL_RULES

__all__ = [
    'ALL_RULES',
    'LAYOUT_RULES',
    'REWRITE_RULES',
    'STRUCTURAL_RULES',
    'BlockTooLongRule',
    'FileHeaderCommentRule',
    'LineTooLongRule',
    'MidClauseBreakRule',
    'PlainCommentOnPublicRule',
    'SignatureRestatingTagRule',
    'StubFragmentRule',
    'UnbreakableSentenceRule',
]
