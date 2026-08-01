from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from xperiment.pygame_pixels import capture_window_pixels, frame_to_surface, posterize
from xperiment.dot_runner import DotCaptureBridge, run_pygame_file
from xperiment.minecraft_screen import MinecraftPixelScreen, make_concrete_palette

WINDOW_SIZE = (640, 360)
SAMPLE_SIZE = (48, 27)
FPS = 60
MINECRAFT_FPS = 1.0


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    sample_size = (args.sample_width, args.sample_height)
    minecraft_screen = None
    next_minecraft_update_at = 0.0

    if args.minecraft:
        minecraft_screen = connect_minecraft_screen(sample_size, args.reset_world)

    if args.dot_file is not None:
        run_dot_file(args, sample_size, minecraft_screen)
        return

    if args.dot:
        print("dot mode enabled without a pygame file; using the built-in demo")

    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("pygame pixel capture")
    clock = pygame.time.Clock()

    running = True
    next_log_at = 0.0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        elapsed = pygame.time.get_ticks() / 1000.0
        draw_scene(screen, elapsed)

        frame = capture_window_pixels(
            screen,
            sample_size=sample_size,
            processor=lambda frame: posterize(frame, levels=5),
        )

        draw_preview(screen, frame)

        if minecraft_screen is not None and elapsed >= next_minecraft_update_at:
            command_count = minecraft_screen.draw_frame(frame, only_changed=True)
            print(
                f"sent {frame.width}x{frame.height} frame to Minecraft "
                f"with {command_count} command(s)"
            )
            next_minecraft_update_at = elapsed + (1.0 / args.minecraft_fps)

        if elapsed >= next_log_at:
            center = frame.color_at(frame.width // 2, frame.height // 2)
            print(
                f"captured {frame.width}x{frame.height} pixels "
                f"from {frame.source_size[0]}x{frame.source_size[1]} window; "
                f"center={center}"
            )
            next_log_at = elapsed + 1.0

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="pygame pixel capture demo",
        epilog=(
            "dot example: python main.py --dot --minecraft path/to/game.py"
        ),
    )
    parser.add_argument(
        "--dot",
        action="store_true",
        help=(
            "capture an existing pygame file without editing it; place the file "
            "path after this command's options"
        ),
    )
    parser.add_argument(
        "--minecraft",
        action="store_true",
        help="send the captured pygame frame to Minecraft as a block screen",
    )
    parser.add_argument(
        "--reset-world",
        action="store_true",
        help="clear the nearby Minecraft area before drawing the block screen",
    )
    parser.add_argument(
        "--minecraft-fps",
        type=float,
        default=MINECRAFT_FPS,
        help="how many frames per second to send to Minecraft",
    )
    parser.add_argument(
        "--posterize-levels",
        type=int,
        default=5,
        help="color levels per RGB channel before Minecraft block matching; 0 disables it",
    )
    parser.add_argument("--sample-width", type=int, default=SAMPLE_SIZE[0])
    parser.add_argument("--sample-height", type=int, default=SAMPLE_SIZE[1])
    args, extra_args = parser.parse_known_args(argv)

    if args.sample_width < 1 or args.sample_height < 1:
        parser.error("--sample-width and --sample-height must be positive")
    if args.minecraft_fps <= 0:
        parser.error("--minecraft-fps must be greater than 0")
    if args.posterize_levels != 0 and not 2 <= args.posterize_levels <= 256:
        parser.error("--posterize-levels must be 0 or between 2 and 256")

    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]

    if args.dot:
        args.dot_file = extra_args[0] if extra_args else None
        args.dot_args = extra_args[1:] if len(extra_args) > 1 else []
    elif extra_args:
        parser.error("unrecognized arguments: " + " ".join(extra_args))
    else:
        args.dot_file = None
        args.dot_args = []

    return args


def run_dot_file(
    args: argparse.Namespace,
    sample_size: tuple[int, int],
    minecraft_screen: MinecraftPixelScreen | None,
) -> None:
    bridge = DotCaptureBridge(
        sample_size=sample_size,
        minecraft_screen=minecraft_screen,
        fps=args.minecraft_fps,
        posterize_levels=args.posterize_levels,
    )
    print(f"dot running pygame file without modifying it: {args.dot_file}")
    run_pygame_file(args.dot_file, args.dot_args, bridge)


def connect_minecraft_screen(
    sample_size: tuple[int, int], reset_world: bool
) -> MinecraftPixelScreen:
    from mc_remote.minecraft import Minecraft

    import param_mc_remote as param
    from axis_flat import AXIS_Y_V_ORG, reset_minecraft_world
    from param_mc_remote import PLAYER_ORIGIN as PO
    from param_mc_remote import block

    width, height = sample_size
    mc = Minecraft.create(address=param.ADRS_MCR, port=param.PORT_MCR)
    mc.setPlayer(param.PLAYER_NAME, PO.x, PO.y, PO.z)
    mc.postToChat("main.py pygame pixel screen")

    if reset_world:
        reset_minecraft_world(mc, width=max(48, width // 2 + 8))

    minecraft_screen = MinecraftPixelScreen(
        mc=mc,
        width=width,
        height=height,
        origin_x=-(width // 2),
        origin_y=AXIS_Y_V_ORG - (height // 2),
        z=24,
        palette=make_concrete_palette(block),
        air_block=block.AIR,
    )
    minecraft_screen.clear()
    return minecraft_screen


def draw_scene(screen: pygame.Surface, elapsed: float) -> None:
    width, height = screen.get_size()
    screen.fill((8, 10, 18))

    for x in range(0, width, 12):
        phase = elapsed * 1.8 + x * 0.025
        color = (
            int(128 + 88 * math.sin(phase)),
            int(128 + 88 * math.sin(phase + 2.1)),
            int(128 + 88 * math.sin(phase + 4.2)),
        )
        pygame.draw.rect(screen, color, (x, 0, 12, height))

    for index in range(10):
        angle = elapsed * (0.7 + index * 0.08) + index
        radius = 22 + index * 4
        cx = width // 2 + int(math.cos(angle) * (width * 0.28))
        cy = height // 2 + int(math.sin(angle * 1.3) * (height * 0.26))
        color = (
            230 - index * 9,
            90 + index * 13,
            70 + index * 15,
        )
        pygame.draw.circle(screen, color, (cx, cy), radius)

    wave_y = height // 2 + int(math.sin(elapsed * 2.4) * 50)
    pygame.draw.line(screen, (248, 248, 238), (0, wave_y), (width, height - wave_y), 4)


def draw_preview(screen: pygame.Surface, frame) -> None:
    preview = frame_to_surface(frame)
    preview_size = (192, 108)
    preview = pygame.transform.scale(preview, preview_size)
    preview_rect = preview.get_rect(topright=(WINDOW_SIZE[0] - 12, 12))

    screen.blit(preview, preview_rect)
    pygame.draw.rect(screen, (245, 245, 235), preview_rect, 1)


if __name__ == "__main__":
    main()
