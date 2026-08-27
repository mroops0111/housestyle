import dataclasses
import enum
import typing

from ...domain.comment import CommentForm, SymbolKind, Visibility


class NodeRole(enum.Enum):
    ROOT = 'root'
    DEFINITION = 'definition'
    COMMENT = 'comment'
    OTHER = 'other'


@dataclasses.dataclass(frozen=True, slots=True)
class MarkerSplit:
    indent: str
    marker: str
    payload: str
    suffix: str = ''


class LanguageConventions(typing.Protocol):
    @property
    def language_id(self) -> str: ...

    @property
    def extensions(self) -> frozenset[str]: ...

    @property
    def doc_form_marker(self) -> str: ...

    @property
    def signature_tags(self) -> tuple[str, ...]: ...

    def visibility_of(self, name: str) -> Visibility: ...

    def split_marker(self, line: str, form: CommentForm) -> MarkerSplit: ...


class GrammarAdapter(typing.Protocol):
    def query(self) -> str: ...

    def role_of(self, node_type: str) -> NodeRole: ...

    def symbol_kind(self, node_type: str) -> SymbolKind: ...


class LanguageProfile(LanguageConventions, GrammarAdapter, typing.Protocol): ...
