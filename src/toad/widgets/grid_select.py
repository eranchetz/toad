from textual import containers

from textual.binding import Binding
from textual.reactive import reactive
from textual.layouts.grid import GridLayout


class GridSelect(containers.ItemGrid, can_focus=True):
    DEFAULT_CSS = """
    GridSelect {
        width: 1fr;
        height: auto;
        border: red;
        layout: grid;
    }
    """

    highlighted = reactive(0)

    CURSOR_GROUP = Binding.Group("Cursor", compact=True)
    BINDINGS = [
        Binding("up", "cursor_up", "Cursor Up", group=CURSOR_GROUP),
        Binding("down", "cursor_down", "Cursor Down", group=CURSOR_GROUP),
        Binding("left", "cursor_left", "Cursor Left", group=CURSOR_GROUP),
        Binding("right", "cursor_right", "Cursor Right", group=CURSOR_GROUP),
    ]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes, min_column_width=30)

    @property
    def grid_size(self) -> tuple[int, int] | None:
        assert isinstance(self.layout, GridLayout)
        return self.layout.grid_size

    def watch_highlighted(self, old_highlighted: int, highlighted: int) -> None:
        try:
            self.children[old_highlighted].remove_class("-highlight")
        except IndexError:
            pass
        try:
            highlighted_widget = self.children[highlighted]
            highlighted_widget.add_class("-highlight")
            if not self.screen.can_view_entire(highlighted_widget):
                self.screen.scroll_to_center(highlighted_widget, origin_visible=True)
        except IndexError:
            pass

    def validate_highlighted(self, highlighted: int) -> int:
        if highlighted < 0:
            return 0
        if highlighted >= len(self.children):
            return len(self.children) - 1
        return highlighted

    def action_cursor_up(self):
        if (grid_size := self.grid_size) is None:
            return
        width, height = grid_size
        if self.highlighted >= width:
            self.highlighted -= width

    def action_cursor_down(self):
        if (grid_size := self.grid_size) is None:
            return
        width, height = grid_size
        if self.highlighted + width < len(self.children):
            self.highlighted += width

    def action_cursor_left(self):
        self.highlighted -= 1

    def action_cursor_right(self):
        self.highlighted += 1


if __name__ == "__main__":
    from textual.app import App, ComposeResult
    from textual import widgets

    class GridApp(App):
        CSS = """
        .grid-item {
            width: 1fr;
            padding: 1 1;
            # background: blue 20%;        
            border: blank;


            &.-highlight {
                border: tall $primary;
                background: $panel;
            }
        }
        """

        def compose(self) -> ComposeResult:
            with GridSelect():
                for n in range(50):
                    yield widgets.Label(
                        f"#{n} Where there is a Will, there is a Way!",
                        classes="grid-item",
                    )

    GridApp().run()
