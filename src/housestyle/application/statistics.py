import dataclasses
import statistics

from ..domain.comment import CommentBlock, CommentForm, CommentPlacement, Visibility
from ..domain.document import Document
from ..domain.ports import SourceParser


@dataclasses.dataclass(frozen=True, slots=True)
class Distribution:
    label: str
    values: tuple[int, ...]

    @property
    def count(self) -> int:
        return len(self.values)

    def percentile(self, fraction: float) -> int:
        if not self.values:
            return 0
        ordered = sorted(self.values)
        index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
        return ordered[index]

    @property
    def maximum(self) -> int:
        return max(self.values, default=0)

    @property
    def median(self) -> int:
        return round(statistics.median(self.values)) if self.values else 0


@dataclasses.dataclass(frozen=True, slots=True)
class CorpusStatistics:
    documents: int
    blocks: int
    line_counts: tuple[Distribution, ...]
    physical_widths: Distribution
    sentence_lengths: Distribution
    unbreakable_at: tuple[tuple[int, int], ...]

    def line_counts_for(self, label: str) -> Distribution:
        for distribution in self.line_counts:
            if distribution.label == label:
                return distribution
        return Distribution(label, ())


class MeasureCorpus:
    def __init__(self, parser: SourceParser, widths: tuple[int, ...] = (72, 80, 88, 100, 120)) -> None:
        self._parser = parser
        self._widths = widths

    def run(self, documents: tuple[Document, ...]) -> CorpusStatistics:
        grouped: dict[str, list[int]] = {}
        widths: list[int] = []
        lengths: list[int] = []
        unbreakable = dict.fromkeys(self._widths, 0)
        blocks = 0

        for document in documents:
            for block in self._parser.parse(document):
                blocks += 1
                grouped.setdefault(self._label(block), []).append(block.line_count)
                widths.extend(line.physical_width for line in block.lines)
                for sentence in block.prose().sentences():
                    lengths.append(len(sentence.text))
                    for width in self._widths:
                        if self._is_unbreakable(sentence.text, width):
                            unbreakable[width] += 1

        return CorpusStatistics(
            documents=len(documents),
            blocks=blocks,
            line_counts=tuple(Distribution(label, tuple(values)) for label, values in sorted(grouped.items())),
            physical_widths=Distribution('physical-width', tuple(widths)),
            sentence_lengths=Distribution('sentence-length', tuple(lengths)),
            unbreakable_at=tuple(sorted(unbreakable.items())),
        )

    def _label(self, block: CommentBlock) -> str:
        if block.form is CommentForm.DOC:
            visibility = Visibility.PUBLIC if block.attaches_to_public_symbol else Visibility.INTERNAL
            return f'doc/{visibility.value}'
        if block.placement is CommentPlacement.FILE_HEADER:
            return 'line/file-header'
        return f'line/{block.placement.value}'

    def _is_unbreakable(self, sentence: str, width: int) -> bool:
        return len(sentence) > width and ',' not in sentence
