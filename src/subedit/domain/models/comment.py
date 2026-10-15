import dataclasses
import enum
import itertools

from .position import SourceRange
from .prose import Prose, Sentence, break_cost, comma_breaks, reflow_sentence
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

    def render(self) -> str:
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

    def reflow(self, width: int, stub_floor: int = 0) -> 'CommentGroup':
        # A one line docstring that fits is the summary convention, not a block to lay out.
        if self.form is CommentForm.DOC and self.line_count == 1 and self.longest_line <= width:
            return self
        texts = self._reflow_into_texts(width, stub_floor)
        # Text that ends up on one line closes there too, so the closing quotes need room beside it.
        closing_width = len(self._closing_quotes())
        if len(texts) == 1 and len(texts[0]) > self.text_budget(width, first_line=True) - closing_width:
            texts = self._reflow_into_texts(width, stub_floor, closing_width)
        if not texts:
            return self
        return self._rebuild_lines(texts)

    def text_budget(self, width: int, *, first_line: bool) -> int:
        """The characters of text a line holds, which on a docstring's opening line also cede the quotes."""
        opening = self.lines[0]
        quoted = first_line or self.form is not CommentForm.DOC
        return max(20, width - (opening.prefix_width if quoted else len(opening.indent)))

    # A sentence takes as few lines as fit, and the author's layout stays when it breaks no worse than the best one.
    # A sentence whose new layout would strand a stub or still overflow needs its author,
    # so it keeps the layout they gave it rather than one its own check rejects.
    def _reflow_into_texts(self, width: int, stub_floor: int, reserve: int = 0) -> tuple[str, ...]:
        body_budget = self.text_budget(width, first_line=False)
        out: list[str] = []
        for paragraph_index, (paragraph, is_literal) in enumerate(self._split_into_paragraphs()):
            if out:
                out.append('')
            if is_literal:
                out.extend(paragraph)
                continue
            lines = tuple(line.strip() for line in paragraph if line.strip())
            for sentence_index, sentence in enumerate(Prose(' '.join(lines)).sentences()):
                if sentence_index == 1 and paragraph_index == 0 and self.form is CommentForm.DOC:
                    out.append('')
                first_budget = self.text_budget(width, first_line=not out) - (reserve if not out else 0)
                best_lines = reflow_sentence(sentence.text, body_budget, stub_floor, first_width=first_budget)
                given_lines = _given_lines(lines, sentence)
                if given_lines and _keeps_given(given_lines, best_lines, (first_budget, body_budget), stub_floor):
                    out.extend(given_lines)
                elif _is_legal(best_lines, (first_budget, body_budget), stub_floor):
                    out.extend(best_lines)
                elif given_lines:
                    out.extend(given_lines)
                elif _strands_stub(best_lines, stub_floor):
                    return ()
                else:
                    out.extend(best_lines)
        return tuple(out)

    def _split_into_paragraphs(self) -> tuple[tuple[tuple[str, ...], bool], ...]:
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

    def _rebuild_lines(self, texts: tuple[str, ...]) -> 'CommentGroup':
        if self.form is not CommentForm.DOC:
            return self.with_texts(texts)
        opening, closing = self.lines[0], self.lines[-1]
        closes_alone = len(self.lines) > 1 and not closing.text.strip()
        body = [dataclasses.replace(opening, delimiter='', suffix='', text=text, range=opening.range) for text in texts]
        body[0] = dataclasses.replace(body[0], delimiter=opening.delimiter)
        # Text that fits one line closes on that line, as ruff and black format it.
        if len(texts) > 1:
            body.append(
                dataclasses.replace(closing, delimiter=closing.delimiter or opening.delimiter, text='', suffix='')
            )
            if not closes_alone:
                body[-1] = dataclasses.replace(body[-1], delimiter=opening.delimiter.strip())
        else:
            body[0] = dataclasses.replace(body[0], suffix=self._closing_quotes())
        return dataclasses.replace(self, lines=tuple(body))

    def _closing_quotes(self) -> str:
        if self.form is not CommentForm.DOC:
            return ''
        return self.lines[-1].suffix or self.lines[0].delimiter.strip()

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
        return '\n'.join(line.render() for line in self.lines)

    def as_edit(self) -> TextEdit:
        return TextEdit(self.range, self.render())


# The lines a sentence already occupies, when it has them to itself.
def _given_lines(lines: tuple[str, ...], sentence: Sentence) -> tuple[str, ...] | None:
    covering: list[str] = []
    start = 0
    for line in lines:
        end = start + len(line)
        if start < sentence.end and end > sentence.offset:
            if not covering and start != sentence.offset:
                return None
            covering.append(line)
            if end == sentence.end:
                return tuple(covering)
            if end > sentence.end:
                return None
        start = end + 1
    return None


def _keeps_given(
    given_lines: tuple[str, ...], best_lines: tuple[str, ...], budgets: tuple[int, int], stub_floor: int
) -> bool:
    return (
        len(given_lines) == len(best_lines)
        and _is_legal(given_lines, budgets, stub_floor)
        and break_cost(given_lines) <= break_cost(best_lines)
    )


def _is_legal(lines: tuple[str, ...], budgets: tuple[int, int], stub_floor: int) -> bool:
    first_budget, body_budget = budgets
    if any(len(line) > (first_budget if index == 0 else body_budget) for index, line in enumerate(lines)):
        return False
    if len(lines) == 1:
        return True
    if _strands_stub(lines, stub_floor):
        return False
    breaks = set(comma_breaks(' '.join(lines)))
    line_ends = itertools.accumulate(len(line) + 1 for line in lines[:-1])
    return all(line_end - 1 in breaks for line_end in line_ends)


def _strands_stub(lines: tuple[str, ...], stub_floor: int) -> bool:
    return len(lines) > 1 and min(map(len, lines)) < stub_floor
