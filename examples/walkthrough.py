import sys

from housestyle.application import LintDocument, RuleEngine
from housestyle.domain import Document, RuleSet
from housestyle.infrastructure import ALL_RULES, DEFAULT_PARSER


SOURCE = """def build(value):
    # cap the size to the shared limit so the mmap does not
    # blow past it, an unbounded value faults the runner.
    return value
"""

WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def show(n, title, body):
    print(f'\n{"─" * 62}\n{n}. {title}\n{"─" * 62}')
    print(body)


show(1, '原始碼 (就是一串字)', SOURCE.rstrip())

doc = Document(uri='file:///demo.py', text=SOURCE, language_id='python')
block = DEFAULT_PARSER.parse(doc)[0]

show(
    2,
    'Parser 把它變成物件 CommentGroup',
    f"""form       = {block.form.value}          註解的外形
placement  = {block.placement.value}   它站在哪
attachment = {block.attachment}      它在說誰
line_count = {block.line_count}
widest     = {block.longest_line} 字元""",
)

show(
    3,
    '每一行被拆成三塊 (這是量寬度的關鍵)',
    '\n'.join(
        f'  indent={line.indent!r:6s} delimiter={line.delimiter!r:5s} text={line.text!r}' for line in block.lines
    ),
)

show(
    4,
    'Prose 是剝掉標記後的純文字',
    f"""physical_lines = {block.prose().physical_lines}

flattened      = {block.prose().flattened!r}

sentences      = {[s.text for s in block.prose().sentences()]}""",
)

show(5, f'reflow 算出正確排版 (一句一行, 寬度 {WIDTH})', block.reflow(WIDTH).render())

report = LintDocument(DEFAULT_PARSER, RuleEngine(ALL_RULES)).run(
    doc, RuleSet(enabled=frozenset(r.meta.rule_id for r in ALL_RULES), line_width=WIDTH)
)

show(
    6,
    '8 條規則各問一個問題，這些有意見',
    '\n'.join(f'  {d.rule_id:22s} 誰修? {"工具" if d.is_mechanical else "作者"}' for d in report.diagnostics),
)

print(f'\n  → 機械可修 {len(report.mechanical)} 條，工具靜默處理')
print(f'  → 需要作者 {len(report.needing_author)} 條，只有這些會給 AI 看')
