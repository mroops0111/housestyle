import abc
import enum

from ....domain.models.comment import SymbolKind
from ....domain.ports.language_conventions import LanguageConventions


class NodeRole(enum.Enum):
    ROOT = 'root'
    DEFINITION = 'definition'
    COMMENT = 'comment'
    OTHER = 'other'


class GrammarAdapter(abc.ABC):
    @abc.abstractmethod
    def query(self) -> str: ...

    @abc.abstractmethod
    def role_of(self, node_type: str) -> NodeRole: ...

    @abc.abstractmethod
    def symbol_kind(self, node_type: str) -> SymbolKind: ...


class LanguageProfile(LanguageConventions, GrammarAdapter): ...
