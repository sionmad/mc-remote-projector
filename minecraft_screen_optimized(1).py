"""Render captured pygame frames as Minecraft block screens."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Protocol

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pygame_pixels import PixelFrame, RGBColor
else:
    from .pygame_pixels import PixelFrame, RGBColor


class MinecraftLike(Protocol):
    def setBlock(self, *args) -> None:
        ...

    def setBlocks(self, *args) -> None:
        ...


@dataclass(frozen=True)
class BlockColor:
    block_id: str
    rgb: RGBColor


@dataclass
class MinecraftPixelScreen:
    """A flat X/Y block wall for displaying RGB pixel frames."""

    mc: MinecraftLike
    width: int
    height: int
    origin_x: int
    origin_y: int
    z: int
    palette: Sequence[BlockColor]
    air_block: str
    _last_blocks: list[str] | None = field(default=None, init=False, repr=False)

    @property
    def bounds(self) -> tuple[int, int, int, int, int, int]:
        return (
            self.origin_x,
            self.origin_y,
            self.z,
            self.origin_x + self.width - 1,
            self.origin_y + self.height - 1,
            self.z,
        )

    def clear(self) -> int:
        """Clear the whole screen wall."""

        self.mc.setBlocks(*self.bounds, self.air_block)
        self._last_blocks = None
        return 1

    def draw_frame(self, frame: PixelFrame, only_changed: bool = True) -> int:
        """Draw a captured frame and return the number of Minecraft commands."""

        if frame.sample_size != (self.width, self.height):
            raise ValueError(
                "frame size must match MinecraftPixelScreen size: "
                f"{frame.sample_size} != {(self.width, self.height)}"
            )

        blocks = frame_to_blocks(frame, self.palette)
        if self._last_blocks is None or not only_changed:
            command_count = self._draw_full_rows(blocks)
        else:
            command_count = self._draw_changed_rows(blocks, self._last_blocks)

        self._last_blocks = blocks
        return command_count


    def _draw_full_rows(self, blocks: Sequence[str]) -> int:
        return self._draw_rectangles(blocks)

    def _draw_changed_rows(self, blocks: Sequence[str], last_blocks: Sequence[str]) -> int:
        return self._draw_rectangles(blocks, last_blocks)

    def _draw_rectangles(
        self,
        blocks: Sequence[str],
        last_blocks: Sequence[str] | None = None,
    ) -> int:
        """
        Draw using rectangle compression + difference rendering.

        Adjacent horizontal runs are merged vertically into a single setBlocks call.
        When last_blocks is provided, only changed pixels are rendered.
        """
        command_count = 0
        active: dict[tuple[int, int, str], tuple[int, int]] = {}

        for y in range(self.height):
            row_start = y * self.width
            runs: list[tuple[int, int, str]] = []

            x = 0
            while x < self.width:
                index = row_start + x

                if last_blocks is not None and blocks[index] == last_blocks[index]:
                    x += 1
                    continue

                block_id = blocks[index]
                run_start = x
                x += 1

                while x < self.width:
                    index = row_start + x
                    if blocks[index] != block_id:
                        break
                    if last_blocks is not None and blocks[index] == last_blocks[index]:
                        break
                    x += 1

                runs.append((run_start, x - 1, block_id))

            new_active: dict[tuple[int, int, str], tuple[int, int]] = {}

            for x1, x2, block_id in runs:
                key = (x1, x2, block_id)
                if key in active:
                    start_y, _ = active[key]
                    new_active[key] = (start_y, y)
                else:
                    new_active[key] = (y, y)

            for key, (start_y, end_y) in active.items():
                if key not in new_active:
                    x1, x2, block_id = key
                    self._emit_rectangle(x1, x2, start_y, end_y, block_id)
                    command_count += 1

            active = new_active

        for key, (start_y, end_y) in active.items():
            x1, x2, block_id = key
            self._emit_rectangle(x1, x2, start_y, end_y, block_id)
            command_count += 1

        return command_count

    def _emit_rectangle(
        self,
        x1: int,
        x2: int,
        y1: int,
        y2: int,
        block_id: str,
    ) -> None:
        """Emit one compressed rectangle."""
        mc_y_top = self.origin_y + (self.height - 1 - y1)
        mc_y_bottom = self.origin_y + (self.height - 1 - y2)

        self.mc.setBlocks(
            self.origin_x + x1,
            mc_y_bottom,
            self.z,
            self.origin_x + x2,
            mc_y_top,
            self.z,
            block_id,
        )


def frame_to_blocks(frame: PixelFrame, palette: Sequence[BlockColor]) -> list[str]:
    """Convert RGB pixels to nearest Minecraft block IDs."""

    if not palette:
        raise ValueError("palette must contain at least one block color")

    cache: dict[RGBColor, str] = {}
    blocks: list[str] = []

    for offset in range(0, len(frame.pixels), 3):
        color = (
            frame.pixels[offset],
            frame.pixels[offset + 1],
            frame.pixels[offset + 2],
        )
        block_id = cache.get(color)
        if block_id is None:
            block_id = nearest_block(color, palette)
            cache[color] = block_id
        blocks.append(block_id)

    return blocks


def nearest_block(color: RGBColor, palette: Sequence[BlockColor]) -> str:
    """Return the palette block with the closest RGB color."""

    return min(
        palette,
        key=lambda candidate: color_distance_squared(color, candidate.rgb),
    ).block_id


def color_distance_squared(left: RGBColor, right: RGBColor) -> int:
    return sum((left[index] - right[index]) ** 2 for index in range(3))


def make_concrete_palette(block) -> tuple[BlockColor, ...]:
    """Create a solid-color palette from Minecraft concrete blocks."""

    return (
        BlockColor(block.BLACK_CONCRETE, (8, 10, 15)),
        BlockColor(block.BLUE_CONCRETE, (44, 46, 143)),
        BlockColor(block.BROWN_CONCRETE, (96, 59, 31)),
        BlockColor(block.CYAN_CONCRETE, (21, 119, 136)),
        BlockColor(block.GRAY_CONCRETE, (54, 57, 61)),
        BlockColor(block.GREEN_CONCRETE, (73, 91, 36)),
        BlockColor(block.LIGHT_BLUE_CONCRETE, (36, 137, 199)),
        BlockColor(block.LIGHT_GRAY_CONCRETE, (125, 125, 115)),
        BlockColor(block.LIME_CONCRETE, (94, 168, 24)),
        BlockColor(block.MAGENTA_CONCRETE, (170, 48, 160)),
        BlockColor(block.ORANGE_CONCRETE, (224, 97, 0)),
        BlockColor(block.PINK_CONCRETE, (214, 101, 143)),
        BlockColor(block.PURPLE_CONCRETE, (100, 32, 156)),
        BlockColor(block.RED_CONCRETE, (142, 32, 32)),
        BlockColor(block.WHITE_CONCRETE, (207, 213, 214)),
        BlockColor(block.YELLOW_CONCRETE, (240, 175, 21)),
    )


def _print_direct_run_help() -> None:
    print("minecraft_screen.py is a helper module for drawing pixel frames.")
    print("Run the pygame-to-Minecraft demo from the project root instead:")
    print(r"  .\.venv\Scripts\python.exe main.py --minecraft")
    print("Add --reset-world if you want to clear the display area first.")


if __name__ == "__main__":
    _print_direct_run_help()
