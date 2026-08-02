"""Pixel capture helpers for pygame display surfaces."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
import os
from pathlib import Path
from typing import TypeAlias

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

RGBColor: TypeAlias = tuple[int, int, int]
PixelBytes: TypeAlias = bytes | bytearray
FrameProcessor: TypeAlias = Callable[["PixelFrame"], "PixelFrame | PixelBytes | None"]


@dataclass(frozen=True)
class PixelFrame:
    """A captured pygame frame stored as row-major RGB bytes."""

    width: int
    height: int
    pixels: bytes
    source_size: tuple[int, int]

    @property
    def sample_size(self) -> tuple[int, int]:
        return self.width, self.height

    def color_at(self, x: int, y: int) -> RGBColor:
        """Return the RGB color at a captured pixel coordinate."""

        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise IndexError(f"pixel coordinate outside frame: ({x}, {y})")

        offset = self._offset(x, y)
        return self.pixels[offset], self.pixels[offset + 1], self.pixels[offset + 2]

    def iter_pixels(
        self, stride: int = 1
    ) -> Iterator[tuple[int, int, RGBColor]]:
        """Yield captured pixels as ``(x, y, (red, green, blue))``."""

        if stride < 1:
            raise ValueError("stride must be at least 1")

        for y in range(0, self.height, stride):
            for x in range(0, self.width, stride):
                yield x, y, self.color_at(x, y)

    def rows(self) -> list[list[tuple[int, int, int]]]:
        """Return pixels as plain Python RGB rows."""

        return [
            [self.color_at(x, y) for x in range(self.width)]
            for y in range(self.height)
        ]

    def with_pixels(self, pixels: PixelBytes) -> "PixelFrame":
        """Return a copy of this frame with processed RGB bytes."""

        normalized = _normalize_rgb_bytes(pixels, self.width, self.height)
        return PixelFrame(
            width=self.width,
            height=self.height,
            pixels=normalized,
            source_size=self.source_size,
        )

    def _offset(self, x: int, y: int) -> int:
        return (y * self.width + x) * 3


def capture_window_pixels(
    surface: pygame.Surface,
    sample_size: tuple[int, int] | None = None,
    processor: FrameProcessor | None = None,
) -> PixelFrame:
    """Capture RGB pixels from a pygame window or surface.

    The returned frame stores pixels as row-major RGB bytes. Use ``sample_size``
    to downscale before processing.
    """

    source_size = surface.get_size()
    capture_surface = _scaled_surface(surface, sample_size)
    width, height = capture_surface.get_size()
    frame = PixelFrame(
        width=width,
        height=height,
        pixels=pygame.image.tostring(capture_surface, "RGB"),
        source_size=source_size,
    )

    if processor is not None:
        processed = processor(frame)
        if isinstance(processed, PixelFrame):
            frame = processed
        elif processed is not None:
            frame = frame.with_pixels(processed)

    return frame


def posterize(frame: PixelFrame, levels: int = 4) -> PixelFrame:
    """Reduce each RGB channel to a smaller number of color levels."""

    if not 2 <= levels <= 256:
        raise ValueError("levels must be between 2 and 256")

    output = bytearray(frame.pixels)
    for index, value in enumerate(output):
        output[index] = round(round((value / 255) * (levels - 1)) * 255 / (levels - 1))
    return frame.with_pixels(output)


def to_grayscale(frame: PixelFrame) -> PixelFrame:
    """Convert RGB pixels to grayscale while keeping three channels."""

    output = bytearray(len(frame.pixels))
    for offset in range(0, len(frame.pixels), 3):
        red = frame.pixels[offset]
        green = frame.pixels[offset + 1]
        blue = frame.pixels[offset + 2]
        luma = round(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        output[offset : offset + 3] = bytes((luma, luma, luma))
    return frame.with_pixels(output)


def threshold_brightness(
    frame: PixelFrame,
    threshold: int = 128,
    dark: RGBColor = (0, 0, 0),
    light: RGBColor = (255, 255, 255),
) -> PixelFrame:
    """Map pixels to two colors based on brightness."""

    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")

    output = bytearray(len(frame.pixels))
    for offset in range(0, len(frame.pixels), 3):
        red = frame.pixels[offset]
        green = frame.pixels[offset + 1]
        blue = frame.pixels[offset + 2]
        luma = round(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        color = light if luma >= threshold else dark
        output[offset : offset + 3] = bytes(color)
    return frame.with_pixels(output)


def frame_to_surface(frame: PixelFrame) -> pygame.Surface:
    """Convert a captured frame back into a pygame surface for previews."""

    return pygame.image.fromstring(frame.pixels, frame.sample_size, "RGB")


def load_image_frame(
    image_path: str | Path,
    sample_size: tuple[int, int] | None = None,
    processor: FrameProcessor | None = None,
) -> PixelFrame:
    """Load an image file and capture it as a pixel frame."""

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"image file not found: {path}")
    if not path.is_file():
        raise ValueError(f"image path is not a file: {path}")

    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))

    surface = pygame.image.load(str(path)).convert()
    return capture_window_pixels(surface, sample_size=sample_size, processor=processor)


def _scaled_surface(
    surface: pygame.Surface, sample_size: tuple[int, int] | None
) -> pygame.Surface:
    if sample_size is None or sample_size == surface.get_size():
        return surface

    width, height = sample_size
    if width < 1 or height < 1:
        raise ValueError("sample_size must contain positive width and height")

    source_width, source_height = surface.get_size()
    if source_width <= 0 or source_height <= 0:
        return surface

    scale = min(width / source_width, height / source_height)
    target_width = max(1, int(round(source_width * scale)))
    target_height = max(1, int(round(source_height * scale)))

    scaled = pygame.transform.smoothscale(surface, (target_width, target_height))
    if target_width == width and target_height == height:
        return scaled

    crop_rect = pygame.Rect(0, 0, width, height)
    if target_width > width:
        crop_rect.width = width
        crop_rect.x = (target_width - width) // 2
    elif target_height > height:
        crop_rect.height = height
        crop_rect.y = (target_height - height) // 2

    cropped = pygame.Surface((width, height), flags=pygame.SRCALPHA)
    cropped.fill((0, 0, 0, 0))
    cropped.blit(scaled, (0, 0), area=crop_rect)
    return cropped


def _normalize_rgb_bytes(pixels: PixelBytes, width: int, height: int) -> bytes:
    expected_length = width * height * 3
    normalized = bytes(pixels)
    if len(normalized) != expected_length:
        raise ValueError(
            f"pixel data must contain {expected_length} RGB bytes, "
            f"got {len(normalized)}"
        )

    return normalized
