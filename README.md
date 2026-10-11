# housestyle

Your house style, enforced in the places prose hides inside a codebase.

Linters check your code. Almost nothing checks the sentences you write around it. `housestyle` reads the comments and docstrings in your source, lays them out one sentence per line, and only tells you about the sentences a tool cannot fix for you.

## Example

An editor wraps a comment at whatever column it reaches, so sentences break mid clause.

```python
    # Cap the buffer at the runner limit, because an unbounded
    # read faults the job. Retry once, then give up.
```

`housestyle fix --write` repairs the layout and says nothing.

```python
    # Cap the buffer at the runner limit, because an unbounded read faults the job.
    # Retry once, then give up.
```

A sentence that runs past the width with no comma has nowhere legal to break, and only its author knows where the meaning divides. That one comes back to you, or to the agent that wrote it.

```text
1 comment finding needs rewriting in src/cache.py.
Each states the fix. Apply it in place, do not add a suppression comment.

line 2  [unbreakable-sentence]
  This sentence runs to 116 characters against a budget of 114 characters and contains no comma, so there is no legal place to break it. Add a comma at a clause boundary, or split it into two sentences.
```

## Installation

Install the command line tool with uv.

```bash
uv tool install git+https://github.com/mroops0111/housestyle@v0.1.0
```

## Commands

Every command takes files or directories.

| Command | Result |
| --- | --- |
| `housestyle check src/` | every finding |
| `housestyle check src/ --output=actionable` | only the sentences that need rewriting |
| `housestyle fix src/` | the repairs, as a diff |
| `housestyle fix src/ --write` | the repairs, applied |
| `housestyle stats src/` | comment shapes across the codebase, for setting thresholds from data |
| `housestyle rules` | every rule and who resolves it |

`check` and `fix` exit 1 while anything needs an author, so they drop into pre-commit or CI as they are.

## Fix Kinds

Every finding says who can resolve it, and the whole design turns on that answer.

| Kind | Resolved by | Reaches you |
| --- | --- | --- |
| `TARGETED` | the tool, silently | no |
| `REFLOW` | the tool, silently | no |
| `REWRITE` | only the author | yes |

Rewriting a sentence needs its meaning, which a deterministic process cannot supply. Everything else is repaired without a word, because each message costs the reader attention.

## Agent Hook

`housestyle-hook` runs after every file an agent edits. It repairs the mechanical findings in place, and exits 2 only when a sentence needs rewriting, which hands the message back to the model.

### Claude Code

The plugin registers the hook. It cannot install the tool, so install that first.

```text
/plugin marketplace add mroops0111/housestyle
/plugin install housestyle@mroops
```

To register it by hand instead, add this to `.claude/settings.json`.

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

Add this to `~/.codex/hooks.json`.

```json
{
  "hooks": {
    "PostToolUse": [{ "command": "housestyle-hook" }]
  }
}
```

### Several Agents

Registering the hook with both agents is the normal case. Each agent names its edit tools differently, so every payload identifies its sender, and a payload from anything else exits 0 untouched. `housestyle-hook --help` prints the payload shapes it accepts.

## Configuration

Settings come from `housestyle.toml`, or from `[tool.housestyle]` in `pyproject.toml`, whichever sits closest above the file being checked.

```toml
[housestyle]
line-width = 120
exclude = ["tests/fixtures/**"]

[rules]
mid-clause-break = "error"
block-too-long = { severity = "warning", line = 3, doc-public = 20 }
```

Rule names describe the problem they report. `docs/rules.md` lists every rule, generated from the rules themselves.

## Delegated Tools

`housestyle check` also runs two tools where they are installed, and folds their findings into its own report.

- **Vale**: punctuation, banned phrasing, and anything a markup aware prose linter already handles
- **AutoCorrect**: spacing and punctuation width between CJK and Latin text

`--no-delegate` skips both. `fix` and the agent hook do not run them.

## Surfaces

Code comments are the first surface, and Markdown comes next.

| Surface | Status | Mostly enforces |
| --- | --- | --- |
| Code comments and docstrings | working | layout, since comments sit inside a column limit |
| Markdown | planned | structure, since soft wrapped text barely needs layout |
| Markdown slides | planned | Markdown, with front matter left as it is |

## Related Tools

`housestyle` covers the one thing the usual Python tools leave alone.

| Tool | Checks |
| --- | --- |
| ruff | code structure |
| basedpyright | types |
| **housestyle** | **the natural language inside source** |

## License

MIT
