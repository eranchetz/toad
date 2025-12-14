from pathlib import Path
from typing import Iterable

import pathspec.patterns
from pathspec import PathSpec

from textual import work
from textual.widgets import DirectoryTree


class ProjectDirectoryTree(DirectoryTree):
    def __init__(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(path, name=name, id=id, classes=classes, disabled=disabled)
        self._path_spec: PathSpec | None = None

    @work(thread=True)
    async def load_path_spec(self, git_ignore_path: Path) -> PathSpec | None:
        """Get a path spec instance if there is a .gitignore file present.

        Args:
            git_ignore_path): Path to .gitignore.

        Returns:
            A `PathSpec` instance.
        """
        try:
            if git_ignore_path.is_file():
                spec_text = git_ignore_path.read_text()
                spec = PathSpec.from_lines(
                    pathspec.patterns.GitWildMatchPattern, spec_text.splitlines()
                )
                return spec
        except OSError:
            return None
        return None

    async def get_path_spec(self) -> PathSpec | None:
        if self._path_spec is None:
            path = (
                Path(self.path) if isinstance(self.path, str) else self.path
            ) / ".gitignore"
            self._path_spec = await self.load_path_spec(path).wait()
        return self._path_spec

    async def on_mount(self) -> None:
        await self.get_path_spec()

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter the paths before adding them to the tree.

        Args:
            paths: The paths to be filtered.

        Returns:
            The filtered paths.

        By default this method returns all of the paths provided. To create
        a filtered `DirectoryTree` inherit from it and implement your own
        version of this method.
        """

        if path_spec := self._path_spec:
            for path in paths:
                if not path_spec.match_file(path):
                    yield path
        yield from paths
