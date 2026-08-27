import dataclasses
import enum

from .position import SourceRange
from .prose import Prose
from .text import TextEdit


class CommentForm(enum.Enum):
    LINE = 'line'
    BLOCK = 'block'
    DOC = 'doc'


class CommentPlacement(enum.Enum):
    FILE_HEADER = 'file-header'
    LEADING_DECLARATION = 'leading-declaration'
    INLINE_BODY = 'inline-body'
    TRAILING = 'trailing'


class Visibility(enum.Enum):
    PUBLIC = 'public'
    INTERNAL = 'internal'


class SymbolKind(enum.Enum):
    MODULE = 'module'
    CLASS = 'class'
    FUNCTION = 'function'


@dataclasses.dataclass(frozen=True, slots=True)
class SymbolRef:
    name: str
    kind: SymbolKind
    visibility: Visibility


@dataclasses.dataclass(frozen=True, slots=True)
class CommentLine:
    range: SourceRange
    indent: str
    marker: str
    payload: str
    suffix: str = ''

    @property
    def physical_width(self) -> int:
        return len(self.indent) + len(self.marker) + len(self.payload) + len(self.suffix)

    @property
    def prefix_width(self) -> int:
        return len(self.indent) + len(self.marker)

    def rendered(self) -> str:
        if not self.payload and not self.suffix:
            return (self.indent + self.marker).rstrip()
        return self.indent + self.marker + self.payload + self.suffix


@dataclasses.dataclass(frozen=True, slots=True)
class CommentBlock:
    range: SourceRange
    lines: tuple[CommentLine, ...]
    form: CommentForm
    placement: CommentPlacement
    attachment: SymbolRef | None = None

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError('A comment block needs at least one line')

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def is_multiline(self) -> bool:
        return len(self.lines) > 1

    @property
    def widest_line(self) -> int:
        return max(line.physical_width for line in self.lines)

    @property
    def attaches_to_public_symbol(self) -> bool:
        return self.attachment is not None and self.attachment.visibility is Visibility.PUBLIC

    def prose(self) -> Prose:
        return Prose('\n'.join(line.payload.strip() for line in self.lines))

    def with_payloads(self, payloads: tuple[str, ...]) -> 'CommentBlock':
        if not payloads:
            raise ValueError('A comment block needs at least one line')
        template = self.lines[0]
        rebuilt = tuple(
            dataclasses.replace(
                self.lines[index] if index < len(self.lines) else template,
                payload=payload,
            )
            for index, payload in enumerate(payloads)
        )
        return dataclasses.replace(self, lines=rebuilt)

    def render(self) -> str:
        return '\n'.join(line.rendered() for line in self.lines)

    def as_edit(self) -> TextEdit:
        return TextEdit(self.range, self.render())
