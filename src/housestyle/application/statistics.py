import dataclasses
import statistics

from ..domain.comment import CommentForm, CommentGroup, CommentPlacement, Visibility
from ..domain.document import Document
from ..domain.ports import SourceParser


@dataclasses.dataclass(frozen=True, slots=True)
class Distribution:
    label: str
    measurements: tuple[int, ...]

    @property
    def count(self) -> int:
        return len(self.measurements)

    def percentile(self, fraction: float) -> int:
        if not self.measurements:
            return 0
        sorted_values = sorted(self.measurements)
        index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
        return sorted_values[index]

    @property
    def maximum(self) -> int:
        return max(self.measurements, default=0)

    @property
    def median(self) -> int:
        return round(statistics.median(self.measurements)) if self.measurements else 0


@dataclasses.dataclass(frozen=True, slots=True)
class CorpusStatistics:
    documents: int
    blocks: int
    line_counts: tuple[Distribution, ...]
    physical_widths: Distribution
    sentence_lengths: Distribution
    unbreakable_at: tuple[tuple[int, int], ...]


class MeasureCorpus:
    def __init__(self, parser: SourceParser, physical_widths: tuple[int, ...] = (72, 80, 88, 100, 120)) -> None:
        self._parser = parser
        self._widths = physical_widths

    def run(self, documents: tuple[Document, ...]) -> CorpusStatistics:
        grouped_line_counts: dict[str, list[int]] = {}
        physical_widths: list[int] = []
        sentence_lengths: list[int] = []
        unbreakable_counts = dict.fromkeys(self._widths, 0)
        group_count = 0

        for document in documents:
            for group in self._parser.parse(document):
                group_count += 1
                grouped_line_counts.setdefault(self._label(group), []).append(group.line_count)
                physical_widths.extend(line.physical_width for line in group.lines)
                for sentence in group.prose().sentences():
                    sentence_lengths.append(len(sentence.text))
                    for width in self._widths:
                        if self._is_unbreakable(sentence.text, width):
                            unbreakable_counts[width] += 1

        return CorpusStatistics(
            documents=len(documents),
            blocks=group_count,
            line_counts=tuple(
                Distribution(label, tuple(measurements)) for label, measurements in sorted(grouped_line_counts.items())
            ),
            physical_widths=Distribution('physical-width', tuple(physical_widths)),
            sentence_lengths=Distribution('sentence-length', tuple(sentence_lengths)),
            unbreakable_at=tuple(sorted(unbreakable_counts.items())),
        )

    def _label(self, group: CommentGroup) -> str:
        if group.form is CommentForm.DOC:
            visibility = Visibility.PUBLIC if group.attaches_to_public_symbol else Visibility.INTERNAL
            return f'doc/{visibility.value}'
        if group.placement is CommentPlacement.FILE_HEADER:
            return 'line/file-header'
        return f'line/{group.placement.value}'

    def _is_unbreakable(self, sentence: str, width: int) -> bool:
        return len(sentence) > width and ',' not in sentence
