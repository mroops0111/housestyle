import dataclasses
import itertools

from .position import SourceRange


@dataclasses.dataclass(frozen=True, slots=True)
class TextEdit:
    range: SourceRange
    new_text: str

    @property
    def is_insertion(self) -> bool:
        return self.range.is_empty

    @property
    def is_deletion(self) -> bool:
        return not self.range.is_empty and not self.new_text


def apply_edits(text: str, edits: tuple[TextEdit, ...]) -> str:
    if not edits:
        return text
    ordered = sorted(edits, key=lambda edit: (edit.range.start, edit.range.end))
    for earlier, later in itertools.pairwise(ordered):
        if earlier.range.overlaps(later.range):
            raise ValueError(f'Overlapping edits at bytes {earlier.range.start} and {later.range.start}')
    data = bytearray(text.encode('utf-8'))
    for edit in reversed(ordered):
        data[edit.range.start : edit.range.end] = edit.new_text.encode('utf-8')
    return data.decode('utf-8')
