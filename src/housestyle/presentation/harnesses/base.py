import dataclasses
import pathlib
import typing


# Both Claude Code and Codex block by exiting two and writing the reason to stderr,
# so the exit contract is shared and only the payload shape differs.
BLOCK_EXIT = 2

Payload = typing.Mapping[str, object]


@dataclasses.dataclass(frozen=True, slots=True)
class HarnessMeta:
    name: str
    summary: str
    example: Payload

    def __post_init__(self) -> None:
        if not self.name or not self.summary:
            raise ValueError('A harness names itself and says what it recognises')


class AgentHarness(typing.Protocol):
    meta: HarnessMeta

    def edited_files(self, payload: Payload) -> tuple[pathlib.Path, ...] | None:
        """Return the files this payload edited, or None when it came from another agent.

        An empty tuple and None mean different things.
        Empty says the payload was ours and touched nothing we check.
        None says it was never ours to read.
        """
        ...


def existing_source_files(
    candidates: typing.Iterable[str | pathlib.Path], extensions: frozenset[str]
) -> tuple[pathlib.Path, ...]:
    paths = [pathlib.Path(candidate) for candidate in candidates]
    return tuple(dict.fromkeys(path for path in paths if path.suffix in extensions and path.is_file()))
