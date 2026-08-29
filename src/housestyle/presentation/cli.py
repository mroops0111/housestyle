import difflib
import pathlib
import sys
import typing

import typer

from .. import __version__
from ..application import Aggregator, CorpusStatistics, FixDocument, LintDocument, MeasureCorpus, RuleEngine
from ..domain.document import Document
from ..infrastructure import ALL_RULES, DEFAULT_CONFIG, DEFAULT_PARSER, EXTERNAL_LINTERS, PYTHON
from . import report as reporters


app = typer.Typer(add_completion=False, help='A linter and formatter for the prose inside code comments.')

PERCENTILES = (0.5, 0.75, 0.9, 0.95, 0.99)
FORMATTERS = {'human': reporters.human, 'agent': reporters.agent, 'json': reporters.as_json}


def _load(paths: tuple[pathlib.Path, ...]) -> tuple[Document, ...]:
    files: list[pathlib.Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(candidate for candidate in path.rglob('*') if candidate.suffix in PYTHON.extensions))
        elif path.suffix in PYTHON.extensions:
            files.append(path)
    documents: list[Document] = []
    for file in files:
        try:
            text = file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        documents.append(Document(uri=file.resolve().as_uri(), text=text, language_id=PYTHON.language_id))
    return tuple(documents)


def _lint() -> LintDocument:
    return LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES))


def _aggregator(delegate: bool) -> Aggregator:
    return Aggregator(_lint(), EXTERNAL_LINTERS if delegate else ())


def _require(documents: tuple[Document, ...]) -> None:
    if not documents:
        typer.echo('No readable source files found.', err=True)
        raise typer.Exit(1)


@app.command()
def check(
    paths: list[pathlib.Path] = typer.Argument(..., help='Files or directories to check.'),
    output: str = typer.Option('human', '--output', help='human, agent, or json.'),
    delegate: bool = typer.Option(True, '--delegate/--no-delegate', help='Also run Vale and AutoCorrect.'),
) -> None:
    documents = _load(tuple(paths))
    _require(documents)
    formatter = FORMATTERS.get(output)
    if formatter is None:
        typer.echo(f'Unknown output format {output!r}. Choose human, agent, or json.', err=True)
        raise typer.Exit(2)

    aggregator = _aggregator(delegate)
    findings = 0
    for document in documents:
        result = aggregator.run(document, DEFAULT_CONFIG.resolve(_fspath(document)))
        findings += len(result.diagnostics)
        rendered = formatter(document, result)
        if rendered:
            typer.echo(rendered)
    raise typer.Exit(1 if findings else 0)


@app.command()
def fix(
    paths: list[pathlib.Path] = typer.Argument(..., help='Files or directories to fix.'),
    write: bool = typer.Option(False, '--write', help='Write changes instead of printing a diff.'),
) -> None:
    documents = _load(tuple(paths))
    _require(documents)

    fixer = FixDocument(_lint())
    changed = 0
    remaining = 0
    for document in documents:
        outcome = fixer.run(document, DEFAULT_CONFIG.resolve(_fspath(document)))
        remaining += len(outcome.remaining)
        if outcome.changed:
            changed += 1
            if write:
                pathlib.Path(_fspath(document)).write_text(outcome.document.text, encoding='utf-8')
            else:
                typer.echo(_diff(document, outcome.document))
        if outcome.remaining:
            typer.echo(reporters.agent(outcome.document, outcome.report))

    verb = 'rewrote' if write else 'would rewrite'
    typer.echo(f'{verb} {changed} of {len(documents)} files, {remaining} findings need an author.', err=True)
    raise typer.Exit(1 if remaining else 0)


@app.command()
def stats(paths: list[pathlib.Path] = typer.Argument(..., help='Files or directories to measure.')) -> None:
    documents = _load(tuple(paths))
    _require(documents)
    typer.echo(_render(MeasureCorpus(DEFAULT_PARSER).run(documents)))


@app.command()
def version() -> None:
    typer.echo(f'housestyle {__version__}')


def _fspath(document: Document) -> str:
    return document.uri.removeprefix('file://')


def _diff(before: Document, after: Document) -> str:
    path = _fspath(before)
    return ''.join(
        difflib.unified_diff(
            before.text.splitlines(keepends=True),
            after.text.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    ).rstrip()


def _render(report: CorpusStatistics) -> str:
    heading = f'{"group":24s} {"n":>6s} {"med":>5s} ' + ' '.join(f'p{int(p * 100):<3d}' for p in PERCENTILES) + '  max'
    lines = [f'{report.documents} documents, {report.blocks} comment blocks', '', 'block line counts', heading]
    lines.extend(_row(distribution.label, distribution) for distribution in report.line_counts)
    for distribution in (report.physical_widths, report.sentence_lengths):
        lines.extend(['', distribution.label, _row('', distribution)])
    lines.extend(['', 'sentences over width with no comma to break at'])
    for width, count in report.unbreakable_at:
        share = count / report.sentence_lengths.count * 100 if report.sentence_lengths.count else 0.0
        lines.append(f'  width {width:3d}  {count:5d} sentences  {share:5.2f}%')
    return '\n'.join(lines)


def _row(label: str, distribution: typing.Any) -> str:
    cells = ' '.join(f'{distribution.percentile(p):<4d}' for p in PERCENTILES)
    return f'{label:24s} {distribution.count:6d} {distribution.median:5d} {cells} {distribution.maximum:4d}'


def main() -> int:
    app()
    return 0


if __name__ == '__main__':
    sys.exit(main())
