"""Run existing pygame files while capturing their display output."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path
import runpy
import sys
import time
from typing import Any

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from .minecraft_screen import MinecraftPixelScreen
from .pygame_pixels import PixelFrame, capture_window_pixels, posterize


@dataclass
class DotCaptureBridge:
    """Capture pygame display frames without changing the pygame source file."""

    sample_size: tuple[int, int]
    minecraft_screen: MinecraftPixelScreen | None = None
    fps: float = 1.0
    posterize_levels: int = 5
    log_status: bool = True
    _next_capture_at: float = field(default=0.0, init=False, repr=False)
    _last_log_at: float = field(default=0.0, init=False, repr=False)

    def capture_display(self, force: bool = False) -> PixelFrame | None:
        """Capture the current pygame display surface if it is time to send."""

        surface = pygame.display.get_surface()
        if surface is None:
            return None
        return self.capture_surface(surface, force=force)

    def capture_surface(
        self, surface: pygame.Surface, force: bool = False
    ) -> PixelFrame | None:
        """Capture a pygame surface and optionally send it to Minecraft."""

        now = time.monotonic()
        if not force and now < self._next_capture_at:
            return None

        frame = capture_window_pixels(
            surface,
            sample_size=self.sample_size,
            processor=self._process_frame,
        )

        command_count = 0
        if self.minecraft_screen is not None:
            command_count = self.minecraft_screen.draw_frame(frame, only_changed=True)

        self._next_capture_at = now + (1.0 / self.fps)
        self._log_frame(frame, command_count, now)
        return frame

    def _process_frame(self, frame: PixelFrame) -> PixelFrame:
        if self.posterize_levels <= 0:
            return frame
        return posterize(frame, levels=self.posterize_levels)

    def _log_frame(self, frame: PixelFrame, command_count: int, now: float) -> None:
        if not self.log_status or now < self._last_log_at + 1.0:
            return

        if self.minecraft_screen is None:
            print(f"dot captured {frame.width}x{frame.height} frame")
        else:
            print(
                f"dot sent {frame.width}x{frame.height} frame to Minecraft "
                f"with {command_count} command(s)"
            )
        self._last_log_at = now


@contextmanager
def capture_pygame_display_updates(bridge: DotCaptureBridge) -> Iterator[None]:
    """Patch pygame display updates so an unmodified pygame file can be captured."""

    original_flip = pygame.display.flip
    original_update = pygame.display.update

    def flip_with_capture(*args: Any, **kwargs: Any) -> Any:
        bridge.capture_display()
        return original_flip(*args, **kwargs)

    def update_with_capture(*args: Any, **kwargs: Any) -> Any:
        bridge.capture_display()
        return original_update(*args, **kwargs)

    pygame.display.flip = flip_with_capture
    pygame.display.update = update_with_capture
    try:
        yield
    finally:
        pygame.display.flip = original_flip
        pygame.display.update = original_update


def run_pygame_file(
    script_path: str | Path,
    script_args: Sequence[str],
    bridge: DotCaptureBridge,
) -> None:
    """Run a pygame script and capture display frames from the outside."""

    path = Path(script_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"pygame file not found: {path}")
    if not path.is_file():
        raise ValueError(f"pygame path is not a file: {path}")

    original_argv = sys.argv[:]
    original_path = sys.path[:]

    sys.argv = [str(path), *script_args]
    sys.path.insert(0, str(path.parent))

    try:
        with capture_pygame_display_updates(bridge):
            runpy.run_path(str(path), run_name="__main__")
    finally:
        sys.argv = original_argv
        sys.path[:] = original_path
