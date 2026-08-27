import pathlib
import sys

import typer

from .. import __version__
from ..application import CorpusStatistics, MeasureCorpus
from ..domain.document import Document
from ..infrastructure import DEFAULT_PARSER, PYTHON


app = typer.Typer(add_completion=False, help='A linter and formatter for the prose inside code comments.')

PERCENTILES = (0.5, 0.75, 0.9, 0.95, 0.99)


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


def _render(report: CorpusStatistics) -> str:
    header = f'{report.documents} documents, {report.blocks} comment blocks'
    lines = [
        header,
        '',
        'block line counts',
        f'{"group":24s} {"n":>6s} {"med":>5s} ' + ' '.join(f'p{int(p * 100):<3d}' for p in PERCENTILES) + '  max',
    ]
    for distribution in report.line_counts:
        cells = ' '.join(f'{distribution.percentile(p):<4d}' for p in PERCENTILES)
        lines.append(
            f'{distribution.label:24s} {distribution.count:6d} {distribution.median:5d} {cells} {distribution.maximum:4d}'
        )

    for distribution in (report.physical_widths, report.sentence_lengths):
        cells = ' '.join(f'{distribution.percentile(p):<4d}' for p in PERCENTILES)
        lines.extend(
            [
                '',
                distribution.label,
                f'{"":24s} {distribution.count:6d} {distribution.median:5d} {cells} {distribution.maximum:4d}',
            ]
        )

    lines.extend(['', 'sentences over width with no comma to break at'])
    for width, count in report.unbreakable_at:
        share = count / report.sentence_lengths.count * 100 if report.sentence_lengths.count else 0.0
        lines.append(f'  width {width:3d}  {count:5d} sentences  {share:5.2f}%')
    return '\n'.join(lines)


@app.command()
def stats(paths: list[pathlib.Path] = typer.Argument(..., help='Files or directories to measure.')) -> None:
    documents = _load(tuple(paths))
    if not documents:
        typer.echo('No readable source files found.', err=True)
        raise typer.Exit(1)
    typer.echo(_render(MeasureCorpus(DEFAULT_PARSER).run(documents)))


@app.command()
def version() -> None:
    typer.echo(f'housestyle {__version__}')


def main() -> int:
    app()
    return 0


if __name__ == '__main__':
    sys.exit(main())
