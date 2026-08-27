import dataclasses
import enum
import re


ABBREVIATIONS = frozenset(
    {
        'e.g',
        'i.e',
        'etc',
        'vs',
        'cf',
        'al',
        'approx',
        'no',
        'fig',
        'ca',
        'resp',
    }
)

_SENTENCE_END = re.compile(r'[.!?]')
_TRAILING_WORD = re.compile(r'([A-Za-z][A-Za-z.]*)$')
_URL = re.compile(r'\b(?:https?://|www\.)\S+')
_CODE_SPAN = re.compile(r'`[^`]*`')
_FENCE = re.compile(r'^\s*(```|~~~)')
_LITERAL_MARKER = '\\b'


class BreakStrength(enum.IntEnum):
    COMMA = 1
    SENTENCE = 2


@dataclasses.dataclass(frozen=True, slots=True)
class BreakPoint:
    offset: int
    strength: BreakStrength


@dataclasses.dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    offset: int

    @property
    def end(self) -> int:
        return self.offset + len(self.text)


@dataclasses.dataclass(frozen=True, slots=True)
class Segment:
    lines: tuple[str, ...]
    is_literal: bool

    @property
    def text(self) -> str:
        return '\n'.join(self.lines)


@dataclasses.dataclass(frozen=True, slots=True)
class Prose:
    text: str

    @property
    def physical_lines(self) -> tuple[str, ...]:
        return tuple(self.text.split('\n'))

    def segments(self) -> tuple[Segment, ...]:
        found: list[Segment] = []
        current: list[str] = []
        literal = False
        fenced = False
        held = False

        def flush(next_literal: bool) -> None:
            nonlocal current, literal
            if current and next_literal != literal:
                found.append(Segment(tuple(current), literal))
                current = []
            literal = next_literal

        for line in self.physical_lines:
            stripped = line.strip()
            if _FENCE.match(line):
                fenced = not fenced
                flush(next_literal=True)
                current.append(line)
                continue
            if stripped.startswith(_LITERAL_MARKER):
                held = stripped == _LITERAL_MARKER
                flush(next_literal=True)
                current.append(line)
                continue
            if not stripped:
                held = False
                flush(next_literal=fenced)
                current.append(line)
                continue
            flush(next_literal=fenced or held or self._is_indented(line))
            current.append(line)

        if current:
            found.append(Segment(tuple(current), literal))
        return tuple(found)

    def _is_indented(self, line: str) -> bool:
        return line.startswith(('    ', '\t'))

    @property
    def flattened(self) -> str:
        return ' '.join(
            line.strip()
            for segment in self.segments()
            if not segment.is_literal
            for line in segment.lines
            if line.strip()
        )

    def sentences(self) -> tuple[Sentence, ...]:
        text = self.flattened
        if not text:
            return ()
        protected = self._protected_spans(text)
        found: list[Sentence] = []
        start = 0
        for match in _SENTENCE_END.finditer(text):
            end = match.end()
            if self._is_protected(match.start(), protected):
                continue
            if not self._terminates_a_sentence(text, match.start()):
                continue
            found.append(Sentence(text[start:end].strip(), start))
            start = end
            while start < len(text) and text[start] == ' ':
                start += 1
        if start < len(text):
            found.append(Sentence(text[start:].strip(), start))
        return tuple(item for item in found if item.text)

    def break_candidates(self) -> tuple[BreakPoint, ...]:
        text = self.flattened
        protected = self._protected_spans(text)
        points: list[BreakPoint] = []
        for match in re.finditer(r'[.!?,]', text):
            if self._is_protected(match.start(), protected):
                continue
            if match.group() == ',':
                points.append(BreakPoint(match.end(), BreakStrength.COMMA))
            elif self._terminates_a_sentence(text, match.start()):
                points.append(BreakPoint(match.end(), BreakStrength.SENTENCE))
        return tuple(points)

    def is_break_legal(self, offset: int) -> bool:
        return any(point.offset == offset for point in self.break_candidates())

    def _protected_spans(self, text: str) -> tuple[tuple[int, int], ...]:
        spans = [(match.start(), match.end()) for match in _URL.finditer(text)]
        spans.extend((match.start(), match.end()) for match in _CODE_SPAN.finditer(text))
        return tuple(spans)

    def _is_protected(self, offset: int, spans: tuple[tuple[int, int], ...]) -> bool:
        return any(start <= offset < end for start, end in spans)

    def _terminates_a_sentence(self, text: str, offset: int) -> bool:
        if text[offset] != '.':
            return self._followed_by_break(text, offset)
        if offset + 1 < len(text) and text[offset + 1].isdigit():
            return False
        if offset > 0 and text[offset - 1].isdigit() and offset + 1 < len(text) and text[offset + 1].isdigit():
            return False
        match = _TRAILING_WORD.search(text[:offset])
        if match and match.group(1).lower().rstrip('.') in ABBREVIATIONS:
            return False
        if match and len(match.group(1).replace('.', '')) == 1:
            return False
        return self._followed_by_break(text, offset)

    def _followed_by_break(self, text: str, offset: int) -> bool:
        rest = text[offset + 1 :]
        if not rest:
            return True
        if rest[0] in '"\')]}':
            rest = rest[1:]
        return not rest or rest[0] == ' '
