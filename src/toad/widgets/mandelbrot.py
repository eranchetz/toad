from functools import lru_cache
from typing import NamedTuple

import math

from textual import events
from textual.color import Color
from textual.content import Content, Span
from textual.geometry import NULL_SIZE, Offset
from textual.reactive import reactive, var
from textual.style import Style
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.timer import Timer


COLORS = [
    Color.parse(color).rgb
    for color in [
        "#881177",
        "#aa3355",
        "#cc6666",
        "#ee9944",
        "#eedd00",
        "#99dd55",
        "#44dd88",
        "#22ccbb",
        "#00bbcc",
        "#0099cc",
        "#3366bb",
        "#663399",
    ]
]


class MandelbrotRegion(NamedTuple):
    """Defines the extents of the mandelbrot set."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def zoom(
        self, focal_x: float, focal_y: float, zoom_factor: float
    ) -> "MandelbrotRegion":
        """
        Return a new region zoomed in or out from a focal point.

        Args:
            focal_x: X coordinate of the point to zoom around (in complex plane coordinates)
            focal_y: Y coordinate of the point to zoom around (in complex plane coordinates)
            zoom_factor: Zoom factor (>1 to zoom in, <1 to zoom out, =1 for no change)

        Returns:
            A new MandelbrotRegion with the focal point at the same relative position
        """
        # Calculate current dimensions
        width = self.x_max - self.x_min
        height = self.y_max - self.y_min

        # Calculate new dimensions
        new_width = width / zoom_factor
        new_height = height / zoom_factor

        # Calculate focal point's relative position in current region
        fx = (focal_x - self.x_min) / width
        fy = (focal_y - self.y_min) / height

        # Calculate new bounds maintaining the focal point's relative position
        new_x_min = focal_x - fx * new_width
        new_x_max = focal_x + (1 - fx) * new_width
        new_y_min = focal_y - fy * new_height
        new_y_max = focal_y + (1 - fy) * new_height

        return MandelbrotRegion(new_x_min, new_x_max, new_y_min, new_y_max)


class Mandelbrot(Static):
    ALLOW_SELECT = False
    DEFAULT_CSS = """
    Mandelbrot {
        
        border: block black 20%;
        text-wrap: nowrap;
        text-overflow: clip;
        overflow: hidden;
    }
    """

    set_region = reactive(MandelbrotRegion(-2, 1.0, -1.0, 1.0), init=False)
    max_iterations = var(64)
    rendered_size = var(NULL_SIZE)
    rendered_set = var(Content(""))
    zoom_position = var(Offset(0, 0))
    zoom_timer: var[Timer | None] = var(None)
    zoom_scale = var(0.99)

    BRAILLE_CHARACTERS = [chr(0x2800 + i) for i in range(256)]

    # (BIT, X_OFFSET, Y_OFFSET)
    PATCH_COORDS = [
        (1, 0, 0),
        (2, 0, 1),
        (4, 0, 2),
        (8, 1, 0),
        (16, 1, 1),
        (32, 1, 2),
        (64, 0, 3),
        (128, 1, 3),
    ]

    @staticmethod
    def mandelbrot(c_real: float, c_imag: float, max_iterations: int):
        """
        Determine the smooth iteration count for a point in the Mandelbrot set.
        Uses continuous (smooth) iteration counting for better detail outside the set.

        Args:
            c_real: The real part of the complex number.
            c_imag: The imaginary part of the complex number.

        Returns:
            A float representing the smooth iteration count, or MAX_ITER for points in the set.
        """
        z_real = 0
        z_imag = 0
        for i in range(max_iterations):
            z_real_new = z_real * z_real - z_imag * z_imag + c_real
            z_imag_new = 2 * z_real * z_imag + c_imag
            z_real = z_real_new
            z_imag = z_imag_new
            if z_real * z_real + z_imag * z_imag > 4:
                return i
        return max_iterations

    def on_mount(self):
        self.call_after_refresh(self.update_mandelbrot)

    def update_mandelbrot(self) -> None:
        mandelbrot = self.generate()
        self.update(mandelbrot)

    def on_mouse_down(self, event: events.Click) -> None:
        if self.zoom_timer:
            self.zoom_timer.stop()

        self.zoom_position = event.offset
        self.zoom_scale = 0.95 if event.ctrl else 1.05
        self.zoom_timer = self.set_interval(1 / 30, self.zoom)
        self.capture_mouse()

    def on_mouse_up(self, event: events.Click) -> None:
        if self.zoom_timer:
            self.zoom_timer.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        self.zoom_position = event.offset

    def zoom(self) -> None:
        zoom_x, zoom_y = self.zoom_position
        width, height = self.content_size
        x_min, x_max, y_min, y_max = self.set_region

        set_width = (x_max - x_min) * 0.9
        set_height = (y_max - y_min) * 0.9

        x = x_min + (zoom_x / width) * set_width
        y = y_min + (zoom_y / height) * set_height

        self.set_region = self.set_region.zoom(x, y, self.zoom_scale)

    def watch_set_region(self) -> None:
        self.rendered_set = Content("")
        self.update_mandelbrot()

    def render(self) -> Content:
        return self.generate()

    def generate(self) -> Content:
        if self.rendered_set and self.size == self.rendered_size:
            return self.rendered_set
        lines: list[Content] = []
        width, height = self.content_size
        x_min, x_max, y_min, y_max = self.set_region
        mandelbrot_width = x_max - x_min
        mandelbrot_height = y_max - y_min

        mandelbrot = self.mandelbrot

        max_iterations = self.max_iterations
        set_width = width * 2
        set_height = height * 4
        BRAILLE_MAP = self.BRAILLE_CHARACTERS
        PATCH_COORDS = self.PATCH_COORDS
        max_color = len(COLORS) - 1

        for row in range(0, height * 4, 4):
            line: list[str] = []
            spans: list[Span] = []
            colors: list[tuple[int, int, int]] = []

            for column in range(0, width * 2, 2):
                colors.clear()
                braille_key = 0

                for bit, dot_x, dot_y in PATCH_COORDS:
                    x: int = column + dot_x
                    y: int = row + dot_y
                    c_real: float = x_min + mandelbrot_width * x / set_width
                    c_imag: float = y_min + mandelbrot_height * y / set_height
                    if (
                        iterations := mandelbrot(c_real, c_imag, max_iterations)
                    ) < max_iterations:
                        braille_key |= bit
                        colors.append(
                            COLORS[round((iterations / max_iterations) * max_color)]
                        )

                if colors:
                    patch_red = 0
                    patch_green = 0
                    patch_blue = 0
                    for red, green, blue in colors:
                        patch_red += red
                        patch_green += green
                        patch_blue += blue

                    color_count = len(colors)
                    patch_color = Color(
                        int(patch_red / color_count),
                        int(patch_green / color_count),
                        int(patch_blue / color_count),
                    )
                    line.append(BRAILLE_MAP[braille_key])
                    span_column = column // 2
                    spans.append(
                        Span(
                            span_column, span_column + 1, Style(foreground=patch_color)
                        )
                    )
                else:
                    line.append(" ")

            lines.append(Content("".join(line), spans=spans).simplify())

        self.rendered_set = Content("\n", cell_length=width).join(lines)
        self.rendered_size = self.size
        return self.rendered_set


if __name__ == "__main__":

    class MApp(App):
        CSS = """
        Screen {
            align: center middle;
            background: $panel;
            Mandelbrot {
                background: black 20%;                
                width: 40;
                height: 16;
            }
        }

        """

        def compose(self) -> ComposeResult:
            yield Mandelbrot()

    app = MApp()
    app.run()
