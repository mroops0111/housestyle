# commentstyle

A linter and formatter for the prose inside code comments, across languages.

Linters check your code. Almost nothing checks your comments. `commentstyle` extracts comment blocks with
tree-sitter and enforces prose rules on them, covering the layout and position rules that markup-aware prose
linters structurally cannot reach.

## Status

Planning. The name is reserved and the architecture is being designed. Nothing works yet.

## Scope

Rules fall into three tiers. Most of them are shared across every language.

- **Universal prose**: line wrap points, line width, fragment stacking, forbidden punctuation
- **Structural, per-language binding**: doc comment form, file header comments, signature-restating tags
- **Genuinely per-language**: module docstrings, framework-specific description fields

## Frontends

One pure core, `lint(text, path, config) -> Diagnostic[]`, behind several thin adapters.

- **CLI**: `commentstyle check` and `commentstyle fix`
- **LSP**: diagnostics and quick fixes for any editor
- **Agent hook**: blocking feedback for coding agents

## License

MIT
