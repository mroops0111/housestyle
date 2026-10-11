from ..domain.rules import (
    BlockTooLongRule,
    FileHeaderCommentRule,
    LineTooLongRule,
    MidClauseBreakRule,
    PlainCommentOnPublicRule,
    SignatureRestatingTagRule,
    StubFragmentRule,
    UnbreakableSentenceRule,
)
from .config_sources import CONFIG_NAME, TomlConfigSource
from .linters import AutoCorrectLinter, ValeLinter
from .parsers import PYTHON, LanguageProfile, NodeRole, TreeSitterParser


LAYOUT_RULES = (MidClauseBreakRule(), LineTooLongRule())
REWRITE_RULES = (StubFragmentRule(), UnbreakableSentenceRule())
STRUCTURAL_RULES = (
    FileHeaderCommentRule(),
    PlainCommentOnPublicRule(PYTHON),
    SignatureRestatingTagRule(PYTHON),
    BlockTooLongRule(),
)
ALL_RULES = LAYOUT_RULES + REWRITE_RULES + STRUCTURAL_RULES

DEFAULT_PARSER = TreeSitterParser((PYTHON,))
DEFAULT_CONFIG_SOURCE = TomlConfigSource(tuple(rule.metadata.rule_id for rule in ALL_RULES))

EXTERNAL_LINTERS = (ValeLinter(), AutoCorrectLinter())

__all__ = [
    'ALL_RULES',
    'CONFIG_NAME',
    'DEFAULT_CONFIG_SOURCE',
    'DEFAULT_PARSER',
    'EXTERNAL_LINTERS',
    'LAYOUT_RULES',
    'PYTHON',
    'REWRITE_RULES',
    'STRUCTURAL_RULES',
    'AutoCorrectLinter',
    'LanguageProfile',
    'NodeRole',
    'TomlConfigSource',
    'TreeSitterParser',
    'ValeLinter',
]
