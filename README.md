# Mouse Mover & Browser Automator

A small Python utility that moves the pointer within the detected screen bounds
and can occasionally scroll or refresh the active browser tab.

## Setup

Use Python 3.10 or newer, then install the dependency:

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python mouse_mover.py
```

The default run continues until stopped. Use `Ctrl+C` to exit. You can also set
a finite run time and adjust movement, hover, and browser-action timing:

```powershell
python mouse_mover.py --duration 600 --min-step 8 --max-step 24 `
  --hover-chance 0.12 --min-action-interval 90 --max-action-interval 180
```

Browser actions affect whichever application is currently active. Switch to the
intended browser tab before starting if you want scroll or refresh actions to
apply there.

## Options

| Option | Default | Description |
| --- | ---: | --- |
| `--min-step` | `8` | Minimum movement distance in pixels |
| `--max-step` | `24` | Maximum movement distance in pixels |
| `--min-interval` | `0.5` | Minimum movement duration in seconds |
| `--max-interval` | `1.5` | Maximum movement duration in seconds |
| `--min-hover-duration` | `0.4` | Minimum duration of a hover pause in seconds |
| `--max-hover-duration` | `1.8` | Maximum duration of a hover pause in seconds |
| `--hover-chance` | `0.12` | Chance of a hover pause after each move, from `0` to `1` |
| `--min-action-interval` | `90` | Minimum delay between browser actions in seconds |
| `--max-action-interval` | `180` | Maximum delay between browser actions in seconds |
| `--scroll-amount` | `300` | Scroll distance in pixels |
| `--duration` | `0` | Run time in seconds; `0` means until stopped |

Movement reflects at the pixel boundaries (`0` through screen size minus one),
including when a step crosses an edge. Each movement follows a short, curved
series of bounded waypoints with randomized durations and easing. Hover pauses
are randomized and may include small, bounded cursor jitters. PyAutoGUI's
failsafe is enabled: moving the pointer to a screen corner stops the program.

## Tests

Run the standard-library tests with:

```powershell
python -m unittest
```
