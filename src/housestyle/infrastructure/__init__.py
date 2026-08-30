from .adapters import AutoCorrectAdapter, ValeAdapter
from .config import CONFIG_NAME, TomlConfigSource
from .languages import PYTHON
from .parser import TreeSitterParser
from .rules import ALL_RULES, LAYOUT_RULES, REWRITE_RULES


DEFAULT_PARSER = TreeSitterParser((PYTHON,))
DEFAULT_CONFIG = TomlConfigSource(tuple(rule.meta.rule_id for rule in ALL_RULES))

EXTERNAL_LINTERS = (ValeAdapter(), AutoCorrectAdapter())

__all__ = [
    'ALL_RULES',
    'CONFIG_NAME',
    'DEFAULT_CONFIG',
    'DEFAULT_PARSER',
    'EXTERNAL_LINTERS',
    'LAYOUT_RULES',
    'PYTHON',
    'REWRITE_RULES',
    'AutoCorrectAdapter',
    'TomlConfigSource',
    'TreeSitterParser',
    'ValeAdapter',
]
