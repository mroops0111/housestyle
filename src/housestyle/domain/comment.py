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
    delimiter: str
    text: str
    suffix: str = ''

    @property
    def physical_width(self) -> int:
        return len(self.indent) + len(self.delimiter) + len(self.text) + len(self.suffix)

    @property
    def prefix_width(self) -> int:
        return len(self.indent) + len(self.delimiter)

    def rendered_lines(self) -> str:
        if not self.text and not self.suffix:
            return (self.indent + self.delimiter).rstrip()
        return self.indent + self.delimiter + self.text + self.suffix


@dataclasses.dataclass(frozen=True, slots=True)
class CommentGroup:
    range: SourceRange
    lines: tuple[CommentLine, ...]
    form: CommentForm
    placement: CommentPlacement
    attachment: SymbolRef | None = None

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError('A comment group needs at least one line')
        if self.attachment is not None and self.placement is not CommentPlacement.LEADING_DECLARATION:
            raise ValueError(
                f'Only a leading declaration comment documents a symbol, '
                f'but a {self.placement.value} comment carries {self.attachment.name!r}'
            )

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def longest_line(self) -> int:
        return max(line.physical_width for line in self.lines)

    @property
    def attaches_to_public_symbol(self) -> bool:
        return self.attachment is not None and self.attachment.visibility is Visibility.PUBLIC

    def prose(self) -> Prose:
        filled_lines = [line for line in self.lines if line.text.strip()]
        base = min((len(line.indent) for line in filled_lines), default=0)
        rendered_lines = [
            ' ' * max(0, len(line.indent) - base) + line.text.rstrip() if line.text.strip() else ''
            for line in self.lines
        ]
        return Prose('\n'.join(rendered_lines))

    def reflow(self, width: int) -> 'CommentGroup':
        texts = self._reflowed_payloads(width)
        if not texts:
            return self
        return self._rebuild(texts)

    def _reflowed_payloads(self, width: int) -> tuple[str, ...]:
        budget = max(20, width - self.lines[0].prefix_width)
        out: list[str] = []
        for paragraph, is_literal in self._paragraphs():
            if out:
                out.append('')
            if is_literal:
                out.extend(paragraph)
                continue
            joined_text = ' '.join(line.strip() for line in paragraph if line.strip())
            for sentence in Prose(joined_text).sentences():
                out.extend(reflow_sentence(sentence.text, budget))
        return tuple(out)

    def _paragraphs(self) -> tuple[tuple[tuple[str, ...], bool], ...]:
        paragraphs: list[tuple[tuple[str, ...], bool]] = []
        for segment in self.prose().segments():
            current_lines: list[str] = []
            for line in segment.lines:
                if line.strip():
                    current_lines.append(line)
                elif current_lines:
                    paragraphs.append((tuple(current_lines), segment.is_literal))
                    current_lines = []
            if current_lines:
                paragraphs.append((tuple(current_lines), segment.is_literal))
        return tuple(paragraphs)

    def _rebuild(self, texts: tuple[str, ...]) -> 'CommentGroup':
        if self.form is not CommentForm.DOC:
            return self.with_texts(texts)
        opening, closing = self.lines[0], self.lines[-1]
        closes_alone = len(self.lines) > 1 and not closing.text.strip()
        body = [dataclasses.replace(opening, delimiter='', suffix='', text=text, range=opening.range) for text in texts]
        body[0] = dataclasses.replace(body[0], delimiter=opening.delimiter)
        if closes_alone or len(texts) > 1:
            body.append(
                dataclasses.replace(closing, delimiter=closing.delimiter or opening.delimiter, text='', suffix='')
            )
            if not closes_alone:
                body[-1] = dataclasses.replace(body[-1], delimiter=opening.delimiter.strip())
        else:
            body[0] = dataclasses.replace(body[0], suffix=closing.suffix or opening.delimiter.strip())
        return dataclasses.replace(self, lines=tuple(body))

    def with_texts(self, texts: tuple[str, ...]) -> 'CommentGroup':
        if not texts:
            raise ValueError('A comment block needs at least one line')
        template = self.lines[0]
        rebuilt = tuple(
            dataclasses.replace(
                self.lines[index] if index < len(self.lines) else template,
                text=text,
            )
            for index, text in enumerate(texts)
        )
        return dataclasses.replace(self, lines=rebuilt)

    def render(self) -> str:
        return '\n'.join(line.rendered_lines() for line in self.lines)

    def as_edit(self) -> TextEdit:
        return TextEdit(self.range, self.render())
