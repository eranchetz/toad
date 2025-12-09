from typing import Iterable

from toad.menus import MenuItem
from toad.widgets.terminal import Terminal


class ShellTerminal(Terminal):
    """Subclass of Terminal used in the Shell view."""

    def get_block_menu(self) -> Iterable[MenuItem]:
        return
        yield

    def get_block_content(self, destination: str) -> str | None:
        return "\n".join(line.content.plain for line in self.state.buffer.lines)
