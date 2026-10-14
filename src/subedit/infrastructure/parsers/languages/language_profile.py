import abc
import enum

from tree_sitter import Language

from ....domain.models.comment import SymbolKind
from ....domain.ports.language_conventions import LanguageConventions


class NodeRole(enum.Enum):
    ROOT = 'root'
    DEFINITION = 'definition'
    IMPORT = 'import'
    COMMENT = 'comment'
    OTHER = 'other'


class GrammarAdapter(abc.ABC):
    # The grammar ships as a wheel, so a first run never reaches the network.
    @abc.abstractmethod
    def language(self) -> Language: ...

    @abc.abstractmethod
    def query(self) -> str: ...

    @abc.abstractmethod
    def role_of(self, node_type: str) -> NodeRole: ...

    @abc.abstractmethod
    def symbol_kind(self, node_type: str) -> SymbolKind: ...


class LanguageProfile(LanguageConventions, GrammarAdapter): ...
