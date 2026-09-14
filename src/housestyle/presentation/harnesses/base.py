import pathlib
import typing


# Both Claude Code and Codex block by exiting two and writing the reason to stderr,
# so the exit contract is shared and only the payload shape differs.
BLOCK_EXIT = 2

Payload = typing.Mapping[str, object]


class AgentHarness(typing.Protocol):
    name: str

    def handles(self, payload: Payload) -> bool: ...

    def targets(self, payload: Payload) -> tuple[pathlib.Path, ...]: ...


def existing_source_files(
    candidates: typing.Iterable[str | pathlib.Path], extensions: frozenset[str]
) -> tuple[pathlib.Path, ...]:
    paths = [pathlib.Path(candidate) for candidate in candidates]
    return tuple(dict.fromkeys(path for path in paths if path.suffix in extensions and path.is_file()))
