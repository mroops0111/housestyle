# Examples

A runnable tour of what happens to a comment, for anyone reading this codebase for the first time.

## The Walkthrough

```bash
uv run python examples/walkthrough.py 60
uv run python examples/walkthrough.py 120
```

It prints one comment at each stage of the pipeline, so the transformation is visible rather than described.

| Stage | What it shows |
| --- | --- |
| 1 | the source, which is only a string |
| 2 | `CommentBlock`, the string as an object with form, placement, and attachment |
| 3 | each line split into indent, marker, and payload, which is how width gets measured |
| 4 | `Prose`, the marker-stripped text, and the sentences found in it |
| 5 | `reflow`, the layout the rules want |
| 6 | the findings, each labelled with who can resolve it |

Passing a different width changes where the sentence has to break, which is the quickest way to see the layout rules react.

## The Probe

```bash
uv run housestyle check examples/probe.py --output=full
uv run housestyle check examples/probe.py --output=actionable
```

`examples/probe.py` carries one finding of each kind, under the narrow width in `examples/housestyle.toml`.

- **full** lists both, one repairable and one not.
- **actionable** lists only the sentence with no comma, because a tool cannot decide where its meaning divides.

That contrast is the whole design. Anything a deterministic process can fix is fixed without saying so, and only what needs rewriting reaches whoever is writing.

## Reading Order

Three files, smallest first. Together they are about two hundred lines, and the rest of the codebase repeats their shapes.

| File | Lines | What it teaches |
| --- | --- | --- |
| `src/housestyle/domain/text.py` | 31 | what a value object looks like here |
| `src/housestyle/infrastructure/rules/layout.py` | 57 | what a rule looks like |
| `src/housestyle/domain/diagnostic.py` | 116 | why `FixKind` is the centre of the design |
