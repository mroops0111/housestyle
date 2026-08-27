import dataclasses
import enum

from .position import SourceRange
from .prose import Prose, reflow_sentence
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
        filled = [line for line in self.lines if line.payload.strip()]
        base = min((len(line.indent) for line in filled), default=0)
        rendered = [
            ' ' * max(0, len(line.indent) - base) + line.payload.rstrip() if line.payload.strip() else ''
            for line in self.lines
        ]
        return Prose('\n'.join(rendered))

    def reflow(self, width: int) -> 'CommentBlock':
        payloads = self._reflowed_payloads(width)
        if not payloads:
            return self
        return self._rebuild(payloads)

    def _reflowed_payloads(self, width: int) -> tuple[str, ...]:
        budget = max(20, width - self.lines[0].prefix_width)
        out: list[str] = []
        for paragraph, is_literal in self._paragraphs():
            if out:
                out.append('')
            if is_literal:
                out.extend(paragraph)
                continue
            joined = ' '.join(line.strip() for line in paragraph if line.strip())
            sentences = Prose(joined).sentences()
            if any(len(item.text) > budget and ',' not in item.text for item in sentences):
                out.extend(paragraph)
                continue
            for sentence in sentences:
                out.extend(reflow_sentence(sentence.text, budget))
        return tuple(out)

    def fits(self, width: int) -> bool:
        return self.widest_line <= width

    def _paragraphs(self) -> tuple[tuple[tuple[str, ...], bool], ...]:
        found: list[tuple[tuple[str, ...], bool]] = []
        for segment in self.prose().segments():
            current: list[str] = []
            for line in segment.lines:
                if line.strip():
                    current.append(line)
                elif current:
                    found.append((tuple(current), segment.is_literal))
                    current = []
            if current:
                found.append((tuple(current), segment.is_literal))
        return tuple(found)

    def _rebuild(self, payloads: tuple[str, ...]) -> 'CommentBlock':
        if self.form is not CommentForm.DOC:
            return self.with_payloads(payloads)
        opening, closing = self.lines[0], self.lines[-1]
        closes_alone = len(self.lines) > 1 and not closing.payload.strip()
        body = [
            dataclasses.replace(opening, marker='', suffix='', payload=payload, range=opening.range)
            for payload in payloads
        ]
        body[0] = dataclasses.replace(body[0], marker=opening.marker)
        if closes_alone or len(payloads) > 1:
            body.append(dataclasses.replace(closing, marker=closing.marker or opening.marker, payload='', suffix=''))
            if not closes_alone:
                body[-1] = dataclasses.replace(body[-1], marker=opening.marker.strip())
        else:
            body[0] = dataclasses.replace(body[0], suffix=closing.suffix or opening.marker.strip())
        return dataclasses.replace(self, lines=tuple(body))

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
