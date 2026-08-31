# Rules

Generated from `RuleMeta`. Edit the rule, not this file.

The fix kind states who resolves a finding. A mechanical kind is repaired without telling the author, so only a rewrite reaches an agent.

| Rule | Fix kind | Summary |
| --- | --- | --- |
| `line-width` | reflow | A physical comment line must fit the configured width, counting indent and delimiter. |
| `wrap-point` | reflow | A comment block must be laid out one sentence per line, splitting only at commas. |
| `block-too-long` | rewrite | A comment block long enough to restate the code has stopped earning its place. |
| `doc-comment-form` | rewrite | A public symbol must be documented in the doc comment form its language renders. |
| `no-file-header` | rewrite | A file must not open with a banner comment before its first declaration. |
| `no-signature-restating` | rewrite | A doc comment must not restate what the type signature already carries. |
| `stub-fragment` | rewrite | A sentence forced to break must not leave a stub of a line behind. |
| `unbreakable-sentence` | rewrite | A sentence over the width must carry a comma so it has somewhere legal to break. |
