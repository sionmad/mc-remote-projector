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
Minecraft screen uses a 48 x 27 pixel sample and sends one frame per second.
`src/xperiment/minecraft_screen.py` is a helper module, so run `main.py` for the
actual transfer demo.

Run an existing pygame file without changing that file:

```bash
python main.py --dot --minecraft path/to/your_game.py
```

In dot mode, `main.py` runs the target pygame file and captures frames whenever
the target calls `pygame.display.flip()` or `pygame.display.update()`.

***
### ToDolist
- [x] Set up the Python environment and install required dependencies
- [x] Create a basic pygame window for the game screen source
- [x] Capture and process screen pixels from the pygame window
- [x] Design the mapping between pygame screen coordinates and Minecraft coordinates
- [x] Connect to Minecraft using the minecraft-remote-api
- [ ] Send pixel-based frame data to Minecraft in a working prototype
- [ ] Improve performance and reduce lag for real-time display
- [ ] Add error handling and fallback behavior for connection or rendering issues
- [ ] Test the prototype with simple visual content and refine the output
