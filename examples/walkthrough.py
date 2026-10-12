import sys

from subedit.application import Linter, RuleEngine
from subedit.domain import Document, RuleSet
from subedit.infrastructure import ALL_RULES, DEFAULT_PARSER


SOURCE = """def build(value):
    # cap the size to the shared limit so the mmap does not
    # blow past it, an unbounded value faults the runner.
    return value
"""

WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def show(step_number, title, body):
    print(f'\n{"─" * 62}\n{step_number}. {title}\n{"─" * 62}')
    print(body)


show(1, 'Source (just a string)', SOURCE.rstrip())

document = Document(uri='file:///demo.py', text=SOURCE, language_id='python')
group = DEFAULT_PARSER.parse(document)[0]

show(
    2,
    'The parser turns it into a CommentGroup',
    f"""form       = {group.form.value}          shape of the comment
placement  = {group.placement.value}   where it sits
attachment = {group.attachment}      what it documents
line_count = {group.line_count}
widest     = {group.longest_line} characters""",
)

show(
    3,
    'Each line splits into three parts (the key to measuring width)',
    '\n'.join(
        f'  indent={line.indent!r:6s} delimiter={line.delimiter!r:5s} text={line.text!r}' for line in group.lines
    ),
)

show(
    4,
    'Prose is the plain text left once the markers are stripped',
    f"""physical_lines = {group.prose().physical_lines}

flattened      = {group.prose().flattened!r}

sentences      = {[sentence.text for sentence in group.prose().sentences()]}""",
)

show(5, f'reflow computes the right layout (one sentence per line, width {WIDTH})', group.reflow(WIDTH).render())

report = Linter(DEFAULT_PARSER, RuleEngine(ALL_RULES)).run(
    document, RuleSet(enabled_rule_ids=frozenset(rule.metadata.rule_id for rule in ALL_RULES), line_width=WIDTH)
)

show(
    6,
    'Each of the 8 rules asks one question, and these answered',
    '\n'.join(
        f'  {diagnostic.rule_id:22s} fixed by {"the tool" if diagnostic.is_mechanical else "the author"}'
        for diagnostic in report.diagnostics
    ),
)

print(f'\n  → {len(report.mechanical)} mechanical, repaired silently by the tool')
print(f'  → {len(report.needing_author)} need the author, and only these reach an agent')
