import asyncio
from pathlib import Path


def longest_common_prefix(strings: list[str]) -> str:
    """
    Find the longest common prefix among a list of strings.

    Arguments:
        strings: List of strings

    Returns:
        The longest common prefix string
    """
    if not strings:
        return ""

    # Start with the first string as reference
    prefix: str = strings[0]

    # Compare with each subsequent string
    for current_string in strings[1:]:
        # Reduce prefix until it matches the start of current string
        while not current_string.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""

    return prefix


class DirectoryReadTask:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.done_event = asyncio.Event()
        self.directory_listing: list[Path] = []
        self._task: asyncio.Task | None = None

    def read(self) -> None:
        # TODO: Should this be cancellable, or have a maximum number of paths for the case of very large directories?
        for path in self.path.iterdir():
            self.directory_listing.append(path)

    def start(self) -> None:
        asyncio.create_task(self.run(), name=f"DirectoryReadTask({str(self.path)!r})")

    async def run(self):
        await asyncio.to_thread(self.read)
        self.done_event.set()

    async def wait(self) -> list[Path]:
        await self.done_event.wait()
        return self.directory_listing


class PathComplete:
    def __init__(self) -> None:
        self.read_tasks: dict[Path, DirectoryReadTask] = {}
        self.directory_listings: dict[Path, list[Path]] = {}

    async def __call__(self, current_working_directory: Path, path: str) -> str | None:
        directory_path = (
            current_working_directory.expanduser().resolve().absolute()
            / Path(path).expanduser()
        )

        node: str = path
        if not directory_path.is_dir():
            node = directory_path.name
            directory_path = directory_path.parent

        if (listing := self.directory_listings.get(directory_path)) is None:
            read_task = DirectoryReadTask(directory_path)
            self.read_tasks[directory_path] = read_task
            read_task.start()
            listing = await read_task.wait()

        if not (
            matching_nodes := [
                path.name for path in listing if path.name.startswith(node)
            ]
        ):
            # Nothing matches
            return None

        if not (prefix := longest_common_prefix(matching_nodes)):
            return None

        return prefix[len(path) :]


if __name__ == "__main__":

    async def run():
        path_complete = PathComplete()
        cwd = Path("~/sandbox")

        print(await path_complete(cwd, "cl"))

    asyncio.run(run())
