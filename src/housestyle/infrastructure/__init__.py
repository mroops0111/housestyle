from .languages import PYTHON
from .parser import TreeSitterParser


DEFAULT_PARSER = TreeSitterParser((PYTHON,))

__all__ = ['DEFAULT_PARSER', 'PYTHON', 'TreeSitterParser']
