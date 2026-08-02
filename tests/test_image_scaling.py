import os
import tempfile
import unittest
from pathlib import Path

import pygame

from xperiment.pygame_pixels import capture_window_pixels


class ImageScalingTests(unittest.TestCase):
    def test_aspect_ratio_is_preserved_when_scaling(self) -> None:
        pygame.init()
        try:
            surface = pygame.Surface((400, 100))
            surface.fill((255, 0, 0))

            frame = capture_window_pixels(surface, sample_size=(128, 72))

            self.assertEqual(frame.width, 128)
            self.assertEqual(frame.height, 72)
            self.assertEqual(frame.source_size, (400, 100))
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
