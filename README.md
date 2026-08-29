# housestyle

A linter and formatter for the prose inside code comments, across languages.

Linters check your code. Almost nothing checks your comments. `housestyle` extracts comment blocks with
tree-sitter and enforces prose rules on them, covering the layout and position rules that markup-aware prose
linters structurally cannot reach.

## Status

Planning. The name is reserved and the architecture is being designed. Nothing works yet.

## Scope

Rules fall into three tiers. Most of them are shared across every language.

- **Universal prose**: line wrap points, line width, fragment stacking, forbidden punctuation
- **Structural, per-language binding**: doc comment form, file header comments, signature-restating tags
- **Genuinely per-language**: module docstrings, framework-specific description fields

## Agent Hook

Wire it into Claude Code so mechanical findings are repaired on write and only the rest reach the model.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "housestyle-hook" }]
      }
    ]
  }
}
```

The hook reads the tool payload on stdin, repairs every mechanical finding in place without saying anything, and exits 2 only when a finding needs rewriting. Exit 2 sends the message back to the model, which is the one path by which anything reaches it.

Silence on repaired findings is deliberate. Each surfaced message costs agent attention, and attention is the scarce resource this tool exists to protect.

## Frontends

One pure core, `lint(text, path, config) -> Diagnostic[]`, behind several thin adapters.

- **CLI**: `housestyle check` and `housestyle fix`
- **LSP**: diagnostics and quick fixes for any editor
- **Agent hook**: blocking feedback for coding agents

## License

MIT
