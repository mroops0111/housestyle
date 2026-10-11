import dataclasses
import typing

from ..models.comment import CommentForm, Visibility


@dataclasses.dataclass(frozen=True, slots=True)
class DelimiterSplit:
    indent: str
    delimiter: str
    text: str
    suffix: str = ''


class LanguageConventions(typing.Protocol):
    @property
    def language_id(self) -> str: ...

    @property
    def extensions(self) -> frozenset[str]: ...

    @property
    def doc_delimiter(self) -> str: ...

    @property
    def signature_tags(self) -> tuple[str, ...]: ...

    def visibility_of(self, name: str) -> Visibility: ...

    def split_delimiter(self, line: str, form: CommentForm) -> DelimiterSplit: ...
