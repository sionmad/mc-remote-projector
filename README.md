# xperiment


## What are you doing now?

I'm making a new API that uses pygame and minecraft-remote-api.
***
## Goal of this project
To make an engine to convert the screen of a game window created with pygame into pixels and display it within the Minecraft game using the minecraft-remote-api
***
## Current progress
- Python 3.11 environment set up in the workspace
- pygame sample window confirmed to run
- Minecraft Remote API import confirmed
- Starter script added: main.py
- Reusable pygame pixel capture helpers added in `src/xperiment/pygame_pixels.py`

## Pygame pixel capture

Run the demo:

```bash
python main.py
```

The demo draws into a pygame window, captures that window as RGB pixels, applies
simple color processing, and shows a processed preview. Use the helper directly
from your own pygame loop:

```python
from xperiment.pygame_pixels import capture_window_pixels, posterize

frame = capture_window_pixels(
    screen,
    sample_size=(64, 36),
    processor=lambda frame: posterize(frame, levels=5),
)

for x, y, (red, green, blue) in frame.iter_pixels():
    # Convert this pixel to a Minecraft block or any other output.
    pass
```

`frame.pixels` is a row-major RGB byte string. Use `frame.color_at(x, y)`,
`frame.iter_pixels()`, or `frame.rows()` when plain Python values are easier.

Send the pygame frame to Minecraft as a flat block screen:

```bash
python main.py --minecraft
```

Add `--reset-world` if you want to clear the nearby area first. By default the
Minecraft screen uses a 64 x 36 pixel sample and sends one frame per second.
`src/xperiment/minecraft_screen.py` is a helper module, so run `main.py` for the
actual transfer demo.

Run an existing pygame file without changing that file:

```bash
python main.py --dot --minecraft path/to/your_game.py
```

In dot mode, `main.py` runs the target pygame file and captures frames whenever
the target calls `pygame.display.flip()` or `pygame.display.update()`.

Send an image file to Minecraft as a block screen:

```bash
python main.py --image path/to/image.png --minecraft
```

Use `--palette mixed` to try a wider set of Minecraft blocks beyond concrete.

## Minecraft connection with param_mc_remote

The Minecraft transfer path uses `param_mc_remote.py` and `axis_flat.py` from the project root.
Before running `--minecraft`, make sure the project can import those modules and that your
Minecraft server details are configured in `param_mc_remote.py`.

Typical setup:

- edit `param_mc_remote.py` to point at your Minecraft server address / port
- confirm the player name and origin coordinates are correct for your world
- run the demo from the project root so the local modules resolve correctly

Example:

```bash
python main.py --minecraft
```

If you want to clear the target area first, add `--reset-world`.

***
