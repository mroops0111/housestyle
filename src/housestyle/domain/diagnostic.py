import dataclasses
import enum

from .position import SourceRange
from .text import TextEdit


class Severity(enum.IntEnum):
    SUGGESTION = 1
    WARNING = 2
    ERROR = 3


class FixKind(enum.Enum):
    TARGETED = 'targeted'
    REFLOW = 'reflow'
    REWRITE = 'rewrite'

    @property
    def is_mechanical(self) -> bool:
        return self is not FixKind.REWRITE


@dataclasses.dataclass(frozen=True, slots=True)
class Fix:
    kind: FixKind
    edits: tuple[TextEdit, ...] = ()

    def __post_init__(self) -> None:
        if self.kind is FixKind.REWRITE and self.edits:
            raise ValueError('A REWRITE fix carries no edits, only the author can resolve it')
        if self.kind.is_mechanical and not self.edits:
            raise ValueError(f'A {self.kind.name} fix must carry at least one edit')

    @classmethod
    def targeted(cls, *edits: TextEdit) -> 'Fix':
        return cls(FixKind.TARGETED, edits)

    @classmethod
    def reflow(cls, *edits: TextEdit) -> 'Fix':
        return cls(FixKind.REFLOW, edits)

    @classmethod
    def rewrite(cls) -> 'Fix':
        return cls(FixKind.REWRITE)


@dataclasses.dataclass(frozen=True, slots=True)
class RuleMeta:
    rule_id: str
    summary: str
    fix_kind: FixKind
    default_severity: Severity = Severity.ERROR
    source: str = 'housestyle'

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError('A rule needs an id')


@dataclasses.dataclass(frozen=True, slots=True)
class Diagnostic:
    rule_id: str
    range: SourceRange
    message: str
    severity: Severity = Severity.ERROR
    fix: Fix | None = None
    source: str = 'housestyle'

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError(f'Rule {self.rule_id} produced an empty message')

    @property
    def is_mechanical(self) -> bool:
        return self.fix is not None and self.fix.kind.is_mechanical

    @property
    def needs_author(self) -> bool:
        return not self.is_mechanical


@dataclasses.dataclass(frozen=True, slots=True)
class Report:
    diagnostics: tuple[Diagnostic, ...] = ()
    unavailable_sources: tuple[str, ...] = ()

    @property
    def mechanical(self) -> tuple[Diagnostic, ...]:
        return tuple(diagnostic for diagnostic in self.diagnostics if diagnostic.is_mechanical)

    @property
    def needing_author(self) -> tuple[Diagnostic, ...]:
        return tuple(diagnostic for diagnostic in self.diagnostics if diagnostic.needs_author)

    @property
    def is_clean(self) -> bool:
        return not self.diagnostics

    def by_kind(self, kind: FixKind) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic for diagnostic in self.diagnostics if diagnostic.fix is not None and diagnostic.fix.kind is kind
        )

    def merged_with(self, other: 'Report') -> 'Report':
        seen: set[tuple[str, int, int]] = set()
        merged_diagnostics: list[Diagnostic] = []
        for diagnostic in (*self.diagnostics, *other.diagnostics):
            key = (diagnostic.rule_id, diagnostic.range.start, diagnostic.range.end)
            if key in seen:
                continue
            seen.add(key)
            merged_diagnostics.append(diagnostic)
        merged_diagnostics.sort(key=lambda diagnostic: (diagnostic.range.start, diagnostic.rule_id))
        return Report(
            tuple(merged_diagnostics),
            tuple(dict.fromkeys((*self.unavailable_sources, *other.unavailable_sources))),
        )
