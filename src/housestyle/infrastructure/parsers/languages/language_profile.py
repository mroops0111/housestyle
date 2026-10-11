import enum
import typing

from ....domain.models.comment import SymbolKind
from ....domain.ports.language_conventions import LanguageConventions


class NodeRole(enum.Enum):
    ROOT = 'root'
    DEFINITION = 'definition'
    COMMENT = 'comment'
    OTHER = 'other'


class GrammarAdapter(typing.Protocol):
    def query(self) -> str: ...

    def role_of(self, node_type: str) -> NodeRole: ...

    def symbol_kind(self, node_type: str) -> SymbolKind: ...


class LanguageProfile(LanguageConventions, GrammarAdapter, typing.Protocol): ...
