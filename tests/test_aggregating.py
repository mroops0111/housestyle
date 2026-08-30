import pathlib
import shutil

import pytest

from housestyle.application import Aggregator, LintDocument, RuleEngine
from housestyle.domain import Diagnostic, Document, Fix, FixKind, RuleSet, SourceRange
from housestyle.infrastructure import ALL_RULES, DEFAULT_PARSER, AutoCorrectAdapter, ValeAdapter


ENABLED = frozenset(rule.meta.rule_id for rule in ALL_RULES)
MIS_WRAPPED = (
    'def f():\n    # cap the size so the mmap does not\n    # blow past it, an unbounded value faults.\n    pass\n'
)


class StubLinter:
    def __init__(self, name: str, available: bool = True, diagnostics: tuple[Diagnostic, ...] = ()) -> None:
        self.name = name
        self._available = available
        self._diagnostics = diagnostics
        self.calls = 0

    def is_available(self) -> bool:
        return self._available

    def run(self, document: Document) -> tuple[Diagnostic, ...]:
        self.calls += 1
        return self._diagnostics


def finding(rule_id: str, start: int = 0, source: str = 'stub') -> Diagnostic:
    return Diagnostic(
        rule_id=rule_id,
        range=SourceRange(start, start + 1),
        message='from an external tool',
        fix=Fix.rewrite(),
        source=source,
    )


def document(text: str = MIS_WRAPPED) -> Document:
    return Document(uri='file:///a.py', text=text, language_id='python')


def aggregate(linters, text: str = MIS_WRAPPED, width: int = 60):
    core = LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES))
    return Aggregator(core, linters).run(document(text), RuleSet(enabled=ENABLED, line_width=width))


def test_native_findings_survive_with_no_linters() -> None:
    report = aggregate(())
    assert report.diagnostics
    assert all(item.source == 'housestyle' for item in report.diagnostics)


def test_external_findings_are_merged_in() -> None:
    report = aggregate((StubLinter('stub', diagnostics=(finding('stub.Rule'),)),))
    assert 'stub.Rule' in [item.rule_id for item in report.diagnostics]


def test_an_unavailable_linter_is_recorded_rather_than_fatal() -> None:
    linter = StubLinter('absent', available=False, diagnostics=(finding('never'),))
    report = aggregate((linter,))
    assert report.unavailable_sources == ('absent',)
    assert linter.calls == 0
    assert report.diagnostics


def test_identical_findings_from_two_sources_are_deduplicated() -> None:
    shared = finding('same.Rule', start=0)
    report = aggregate((StubLinter('a', diagnostics=(shared,)), StubLinter('b', diagnostics=(shared,))))
    assert [item.rule_id for item in report.diagnostics].count('same.Rule') == 1


def test_findings_differing_by_position_are_both_kept() -> None:
    linter = StubLinter('a', diagnostics=(finding('same.Rule', 0), finding('same.Rule', 40)))
    report = aggregate((linter,))
    assert [item.rule_id for item in report.diagnostics].count('same.Rule') == 2


def test_external_rewrite_findings_reach_the_author_partition() -> None:
    report = aggregate((StubLinter('a', diagnostics=(finding('stub.Rule'),)),))
    assert 'stub.Rule' in [item.rule_id for item in report.needing_author]


def test_mechanical_and_authored_findings_stay_separated() -> None:
    report = aggregate((StubLinter('a', diagnostics=(finding('stub.Rule'),)),))
    assert all(item.fix and item.fix.kind is FixKind.REFLOW for item in report.mechanical)
    assert all(item.needs_author for item in report.needing_author)


def test_a_clean_document_with_a_silent_linter_is_clean() -> None:
    report = aggregate((StubLinter('a'),), text='def f():\n    # short and fine.\n    pass\n')
    assert report.is_clean


@pytest.mark.skipif(shutil.which('vale') is None, reason='vale is not installed')
def test_the_vale_adapter_normalises_real_output(tmp_path: pathlib.Path) -> None:
    repo_config = pathlib.Path(__file__).resolve().parent.parent / '.vale.ini'
    shutil.copy(repo_config, tmp_path / '.vale.ini')
    shutil.copytree(repo_config.parent / 'styles', tmp_path / 'styles')
    target = tmp_path / 'probe.py'
    target.write_text('def f():\n    # a semicolon; which is forbidden here.\n    pass\n', encoding='utf-8')

    found = ValeAdapter().run(
        Document(uri=target.resolve().as_uri(), text=target.read_text(encoding='utf-8'), language_id='python')
    )
    assert any('Semicolon' in item.rule_id for item in found)
    assert all(item.source == 'vale' for item in found)
    assert all(item.fix and item.fix.kind is FixKind.REWRITE for item in found)


def test_adapters_report_absence_without_raising() -> None:
    assert ValeAdapter(executable='definitely-not-installed').is_available() is False
    assert AutoCorrectAdapter(executable='definitely-not-installed').is_available() is False
    missing = Document(uri='file:///nowhere/gone.py', text='# note\n', language_id='python')
    assert ValeAdapter(executable='definitely-not-installed').run(missing) == ()
    assert AutoCorrectAdapter(executable='definitely-not-installed').run(missing) == ()
