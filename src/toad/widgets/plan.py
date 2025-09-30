from dataclasses import dataclass

from textual.app import ComposeResult
from textual.content import Content
from textual.reactive import reactive
from textual import containers
from textual.widgets import Static

from toad.widgets.strike_text import StrikeText


class NonSelectableStatic(Static):
    ALLOW_SELECT = False


class Plan(containers.Grid):
    # BORDER_TITLE = "Plan"
    DEFAULT_CSS = """
    Plan {
        background: black 20%;
        height: auto;
        padding: 0 1;
        margin: 0 1 1 1;
        border: tall transparent;
        
        grid-size: 3;
        grid-columns: auto auto 1fr;
        grid-rows: auto;
        height: auto;        
        

        .plan {
            # padding: 0 1;
            color: $text-secondary;
        }
        .status {
            padding: 0 0 0 0;
            color: $text-secondary;
        }
        .priority {
            padding: 0 0 0 0;
        }

        .plan {
            # color: $text-primary;
        }
        .status-completed {
            # text-style: strike;
            color: $text-success;
        }

        .status-in_progress {
            # color: $text-primary;
        }
        .status-pending {
            opacity: 0.8;
        }
  
    }

    """

    @dataclass(frozen=True)
    class Entry:
        content: Content
        priority: str
        status: str

    entries: reactive[list[Entry] | None] = reactive(None, recompose=True)

    LEFT = Content.styled("▌", "$error-muted on transparent r")

    PRIORITIES = {
        "high": Content.assemble(
            ("▌", "$error-muted on transparent r"),
            ("H", "$text-error on $error-muted"),
            ("▐", "$error-muted on transparent r"),
        ),
        "medium": Content.assemble(
            ("▌", "$warning-muted on transparent r"),
            ("M", "$text-warning on $warning-muted"),
            ("▐", "$warning-muted on transparent r"),
        ),
        "low": Content.assemble(
            ("▌", "$primary-muted on transparent r"),
            ("L", "$text-primary on $primary-muted"),
            ("▐", "$primary-muted on transparent r"),
        ),
    }

    def __init__(
        self,
        entries: list[Entry],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        self.newly_completed: set[Plan.Entry] = set()
        super().__init__(name=name, id=id, classes=classes)
        self.set_reactive(Plan.entries, entries)

    def watch_entries(self, old_entries: list[Entry], new_entries: list[Entry]) -> None:
        entry_map = {entry.content: entry for entry in old_entries}
        newly_completed: set[Plan.Entry] = set()
        for entry in new_entries:
            old_entry = entry_map.get(entry.content, None)
            if (
                old_entry is not None
                and entry.status == "completed"
                and entry.status != old_entry.status
            ):
                newly_completed.add(entry)
        self.newly_completed = newly_completed

    def compose(self) -> ComposeResult:
        if not self.entries:
            return
        for index, entry in enumerate(self.entries, 1):
            classes = f"priority-{entry.priority} status-{entry.status}"
            # yield Static(
            #     Content(f"{index}"),
            #     classes=f"numeral {classes}",
            # )

            yield NonSelectableStatic(
                self.PRIORITIES[entry.priority],
                classes=f"priority {classes}",
            ).with_tooltip(f"priority: {entry.priority}")
            yield NonSelectableStatic(
                self.render_status(entry.status),
                classes=f"status {classes}",
            )
            yield (
                strike_text := StrikeText(
                    entry.content,
                    classes=f"plan {classes}",
                )
            )
            if entry in self.newly_completed:
                self.call_after_refresh(strike_text.strike)

    def render_status(self, status: str) -> Content:
        if status == "completed":
            return Content.from_markup("✔ ")
        elif status == "pending":
            return Content.styled("⏲ ")
        elif status == "in_progress":
            return Content.from_markup("⮕")
        return Content()


if __name__ == "__main__":
    from textual.app import App

    entries = [
        Plan.Entry(
            Content.from_markup(
                "Build the best damn UI for agentic coding in the terminal"
            ),
            "high",
            "in_progress",
        ),
        Plan.Entry(Content.from_markup("???"), "medium", "in_progress"),
        Plan.Entry(
            Content.from_markup("[b]Profit[/b]. Retire to Costa Rica"),
            "low",
            "pending",
        ),
    ]

    new_entries = [
        Plan.Entry(
            Content.from_markup(
                "Build the best damn UI for agentic coding in the terminal"
            ),
            "high",
            "completed",
        ),
        Plan.Entry(Content.from_markup("???"), "medium", "in_progress"),
        Plan.Entry(
            Content.from_markup("[b]Profit[/b]. Retire to Costa Rica"),
            "low",
            "pending",
        ),
    ]

    class PlanApp(App):
        BINDINGS = [("space", "strike")]

        CSS = """
        Screen {
            align: center middle;
        }
        """

        def compose(self) -> ComposeResult:
            yield Plan(entries)

        def action_strike(self) -> None:
            self.query_one(Plan).entries = new_entries

    app = PlanApp()
    app.run()
