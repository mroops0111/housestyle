from ..domain.diagnostic import RuleMeta
from ..domain.rules import Rule


HEADING = '# Rules'
PREAMBLE = (
    'Generated from `RuleMeta`. Edit the rule, not this file.\n\n'
    'The fix kind states who resolves a finding. A mechanical kind is repaired without telling the author, '
    'so only a rewrite reaches an agent.'
)


def render(rules: tuple[Rule, ...]) -> str:
    sorted_rules = sorted(rules, key=lambda rule: (rule.meta.fix_kind.value, rule.meta.rule_id))
    lines = [HEADING, '', PREAMBLE, '', '| Rule | Fix kind | Summary |', '| --- | --- | --- |']
    lines.extend(_row(rule.meta) for rule in sorted_rules)
    return '\n'.join(lines) + '\n'


def _row(meta: RuleMeta) -> str:
    return f'| `{meta.rule_id}` | {meta.fix_kind.value} | {meta.summary} |'
