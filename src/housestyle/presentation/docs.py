from ..domain.diagnostic import RuleMetadata
from ..domain.rules import Rule


HEADING = '# Rules'
PREAMBLE = (
    'Generated from `RuleMetadata`. Edit the rule, not this file.\n\n'
    'The fix kind states who resolves a finding. A mechanical kind is repaired without telling the author, '
    'so only a rewrite reaches an agent.'
)


def render(rules: tuple[Rule, ...]) -> str:
    sorted_rules = sorted(rules, key=lambda rule: (rule.metadata.fix_kind.value, rule.metadata.rule_id))
    lines = [HEADING, '', PREAMBLE, '', '| Rule | Fix kind | Summary |', '| --- | --- | --- |']
    lines.extend(_row(rule.metadata) for rule in sorted_rules)
    return '\n'.join(lines) + '\n'


def _row(metadata: RuleMetadata) -> str:
    return f'| `{metadata.rule_id}` | {metadata.fix_kind.value} | {metadata.summary} |'
