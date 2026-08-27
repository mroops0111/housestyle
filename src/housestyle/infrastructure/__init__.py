from .languages import PYTHON
from .parser import TreeSitterParser
from .rules import LAYOUT_RULES


DEFAULT_PARSER = TreeSitterParser((PYTHON,))

__all__ = ['DEFAULT_PARSER', 'LAYOUT_RULES', 'PYTHON', 'TreeSitterParser']
