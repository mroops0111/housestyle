# housestyle

Your house style, enforced in the places prose hides inside a codebase.

Linters check your code. Almost nothing checks the sentences you write around it. `housestyle` extracts prose with tree-sitter and enforces layout and structure rules on it, delegating the rules other tools already do well.

## Surfaces

| Surface | Status | What it enforces here |
| --- | --- | --- |
| Code comments and docstrings | working | layout, mostly. One sentence per line, physical width, and the wrap faults neither Vale nor a formatter can reach |
| Markdown | planned | structure, mostly. Heading case and form, a lead sentence before a list, bold bullet labels |
| Markdown based slides | planned | Markdown plus front matter, which the extractor already treats as literal |

The two surfaces need opposite things. Code comments sit inside a column limit, so layout dominates and structure is incidental. Markdown is soft wrapped, so layout barely applies and structure is the whole point.

## What It Does Not Do

Delegated rather than reimplemented, verified by measurement rather than assumed:

- **Vale** for punctuation, banned phrasing, and anything a markup aware prose linter already handles
- **AutoCorrect** for spacing and punctuation width between CJK and Latin text

`housestyle` normalises their findings into its own report, so a mechanical fix is applied silently and only what needs rewriting is surfaced.

## Fix Kinds

Every finding says who can resolve it, which is the axis the whole design turns on.

| Kind | Resolved by | Reaches an agent |
| --- | --- | --- |
| `TARGETED` | the tool, silently | no |
| `REFLOW` | the tool, silently | no |
| `REWRITE` | only the author | yes |

Rewriting a sentence needs meaning, and a deterministic process cannot supply it. Everything else is repaired without saying so, because each surfaced message costs the reader attention.

## Usage

```bash
uv tool install git+https://github.com/mroops0111/housestyle

housestyle check src/                    # every finding
housestyle check src/ --output=actionable  # only what you must rewrite
housestyle fix src/ --write              # repair what can be repaired
housestyle stats src/                    # measure, to set thresholds from data
```

## Agent Hook

One entry point serves every agent. `housestyle-hook` reads a payload on stdin, repairs every mechanical finding in place without saying anything, and exits 2 only when a finding needs rewriting. Exit 2 returns the message to the model, which is the one path by which anything reaches it.

Register the same command with each agent you use. Nothing tells it which agent is running, because the payload already says.

### Claude Code

`.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [{ "type": "command", "command": "housestyle-hook" }]
      }
    ]
  }
}
```

### Codex

`~/.codex/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [{ "command": "housestyle-hook" }]
  }
}
```

### Both at once

Registering both is the normal case, and they do not interfere. The two agents name their edit tools differently, so every payload identifies its own sender.

| | Claude Code | Codex |
| --- | --- | --- |
| Tool names | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | `apply_patch` |
| Path | `tool_input.file_path` | parsed back out of the patch header |
| Blocking | exit 2 with stderr | exit 2 with stderr |

Each harness answers whether it recognises a payload and which files that payload names. A payload neither claims, such as a `Bash` call, exits 0 in silence, because an agent sends many that are none of our business.

Supporting a third agent is one file answering those two questions, with nothing else in the codebase changing. Run `housestyle-hook --help` to print the shapes it accepts. Each harness publishes its own example, and a test feeds every example back through the selector, so the printed contract cannot drift from the code.

### Outside an agent

Use the CLI. `housestyle fix --write` followed by `housestyle check --output=actionable` produces the same repairs and the same report, and a pre-commit hook or a CI step wants an ordinary exit code rather than the agent convention of 2.

## Configuration

Settings come from `housestyle.toml`, or from `[tool.housestyle]` in `pyproject.toml`, whichever is found first walking upward from the file being checked. A dedicated file wins over `pyproject.toml` in the same directory.

```toml
[housestyle]
line-width = 120
exclude = ["tests/fixtures/**"]

[rules]
mid-clause-break = "error"
block-too-long = { severity = "warning", line = 3, doc-public = 20 }
```

Rule names describe the problem they report, following the convention ruff uses. Every rule is listed in `docs/rules.md`, which is generated from the rules themselves.

## Where It Sits

`housestyle` is one tool among three, split by what each analyses rather than by language.

| Tool | Analyses | Knowledge it needs |
| --- | --- | --- |
| ruff | code structure | Python syntax and semantics |
| basedpyright | types | the type system |
| **housestyle** | **natural language inside source** | English prose and layout |

`ruff` cannot judge where a sentence should break, and `housestyle` cannot judge whether a variable is unused. Run both, through pre-commit or CI.

## License

MIT
