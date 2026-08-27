import dataclasses
import typing

from ...domain.comment import CommentForm, Visibility


@dataclasses.dataclass(frozen=True, slots=True)
class MarkerSplit:
    indent: str
    marker: str
    payload: str
    suffix: str = ''


class LanguageProfile(typing.Protocol):
    @property
    def language_id(self) -> str: ...

    @property
    def extensions(self) -> frozenset[str]: ...

    @property
    def doc_form_marker(self) -> str: ...

    @property
    def signature_tags(self) -> tuple[str, ...]: ...

    @property
    def comment_node(self) -> str: ...

    @property
    def root_nodes(self) -> frozenset[str]: ...

    @property
    def definition_nodes(self) -> frozenset[str]: ...

    def query(self) -> str: ...

    def symbol_kind(self, node_type: str) -> str: ...

    def visibility_of(self, name: str) -> Visibility: ...

    def split_marker(self, line: str, form: CommentForm) -> MarkerSplit: ...
