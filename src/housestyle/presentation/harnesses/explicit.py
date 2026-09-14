import pathlib

from .base import Payload, existing_source_files


class ExplicitPathsHarness:
    """The fallback, for a caller with no harness of its own.

    A pre-commit hook or a CI step sends {"paths": [...]} rather than a tool payload,
    so anything that can write JSON reaches the same loop without a harness being written for it.
    """

    name = 'explicit'

    def __init__(self, extensions: frozenset[str]) -> None:
        self._extensions = extensions

    def handles(self, payload: Payload) -> bool:
        return isinstance(payload.get('paths'), list)

    def targets(self, payload: Payload) -> tuple[pathlib.Path, ...]:
        named = payload.get('paths')
        if not isinstance(named, list):
            return ()
        return existing_source_files([value for value in named if isinstance(value, str)], self._extensions)
