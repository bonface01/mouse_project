"""Move the mouse within the screen and optionally perform browser actions."""

from __future__ import annotations

import argparse
import platform
import random
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class AutomationConfig:
    min_step: int = 8
    max_step: int = 24
    min_interval: float = 0.5
    max_interval: float = 1.5
    min_action_interval: float = 90.0
    max_action_interval: float = 180.0
    scroll_amount: int = 300
    duration: float = 0.0

    def __post_init__(self) -> None:
        if self.min_step < 1 or self.max_step < self.min_step:
            raise ValueError("Step sizes must satisfy 1 <= min_step <= max_step.")
        if self.min_interval <= 0 or self.max_interval < self.min_interval:
            raise ValueError("Intervals must satisfy 0 < min_interval <= max_interval.")
        if (
            self.min_action_interval <= 0
            or self.max_action_interval < self.min_action_interval
        ):
            raise ValueError(
                "Browser action intervals must satisfy "
                "0 < min_action_interval <= max_action_interval."
            )
        if self.scroll_amount < 1:
            raise ValueError("scroll_amount must be at least 1.")
        if self.duration < 0:
            raise ValueError("duration cannot be negative.")


def advance_axis(
    position: int,
    direction: int,
    distance: int,
    maximum: int,
) -> tuple[int, int]:
    """Advance one coordinate and reflect it at either screen edge."""
    if maximum < 1:
        raise ValueError("maximum must be at least 1.")
    if not 0 <= position <= maximum:
        raise ValueError("position must be within the axis bounds.")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1.")
    if distance < 0:
        raise ValueError("distance cannot be negative.")

    # Unfold the reflected path into a repeating line of length 2 * maximum.
    # Folding the phase back across the far edge handles both normal bounces
    # and steps large enough to cross an edge more than once.
    period = 2 * maximum
    phase = position if direction > 0 else period - position
    phase = (phase + distance) % period
    if phase <= maximum:
        return phase, 1 if phase < maximum else -1
    return period - phase, -1


class MouseBrowserAutomator:
    def __init__(self, config: AutomationConfig) -> None:
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError(
                "PyAutoGUI is required. Install dependencies with "
                "`python -m pip install -r requirements.txt`."
            ) from exc

        self._pyautogui = pyautogui
        self._pyautogui.FAILSAFE = True
        self._config = config
        self._screen_width, self._screen_height = self._pyautogui.size()
        if self._screen_width < 2 or self._screen_height < 2:
            raise RuntimeError("The detected screen must be at least 2 by 2 pixels.")

        x, y = self._pyautogui.position()
        self._x = min(max(int(x), 0), self._screen_width - 1)
        self._y = min(max(int(y), 0), self._screen_height - 1)
        self._dx = random.choice((-1, 1))
        self._dy = random.choice((-1, 1))

    def _move(self) -> None:
        distance = random.randint(self._config.min_step, self._config.max_step)
        self._x, self._dx = advance_axis(
            self._x, self._dx, distance, self._screen_width - 1
        )
        self._y, self._dy = advance_axis(
            self._y, self._dy, distance, self._screen_height - 1
        )
        interval = random.uniform(
            self._config.min_interval, self._config.max_interval
        )
        self._pyautogui.moveTo(
            self._x,
            self._y,
            duration=interval,
            tween=self._pyautogui.easeInOutQuad,
        )

    def _browser_action(self) -> None:
        action = random.choice(("scroll_up", "scroll_down", "refresh"))
        if action == "scroll_up":
            self._pyautogui.scroll(self._config.scroll_amount)
        elif action == "scroll_down":
            self._pyautogui.scroll(-self._config.scroll_amount)
        else:
            modifier = "command" if platform.system() == "Darwin" else "ctrl"
            self._pyautogui.hotkey(modifier, "r")

    def run(self) -> None:
        """Run until the duration expires or the user stops the automation."""
        started_at = time.monotonic()
        next_action_at = started_at + random.uniform(
            self._config.min_action_interval,
            self._config.max_action_interval,
        )
        print("Automation running. Move the cursor to a screen corner to stop.")

        try:
            while (
                self._config.duration == 0
                or time.monotonic() - started_at < self._config.duration
            ):
                self._move()
                now = time.monotonic()
                if now >= next_action_at:
                    self._browser_action()
                    next_action_at = now + random.uniform(
                        self._config.min_action_interval,
                        self._config.max_action_interval,
                    )
                time.sleep(random.uniform(0.1, 0.4))
        except self._pyautogui.FailSafeException:
            print("Stopped by PyAutoGUI failsafe.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move the mouse within screen bounds and perform occasional "
        "browser scroll or refresh actions."
    )
    parser.add_argument("--min-step", type=int, default=8, help="Minimum move in pixels.")
    parser.add_argument("--max-step", type=int, default=24, help="Maximum move in pixels.")
    parser.add_argument(
        "--min-interval",
        type=float,
        default=0.5,
        help="Minimum movement duration in seconds.",
    )
    parser.add_argument(
        "--max-interval",
        type=float,
        default=1.5,
        help="Maximum movement duration in seconds.",
    )
    parser.add_argument(
        "--min-action-interval",
        type=float,
        default=90.0,
        help="Minimum time between browser actions in seconds.",
    )
    parser.add_argument(
        "--max-action-interval",
        type=float,
        default=180.0,
        help="Maximum time between browser actions in seconds.",
    )
    parser.add_argument(
        "--scroll-amount",
        type=int,
        default=300,
        help="Scroll distance in pixels when a scroll action is selected.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Run duration in seconds; 0 runs until stopped.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AutomationConfig(
        min_step=args.min_step,
        max_step=args.max_step,
        min_interval=args.min_interval,
        max_interval=args.max_interval,
        min_action_interval=args.min_action_interval,
        max_action_interval=args.max_action_interval,
        scroll_amount=args.scroll_amount,
        duration=args.duration,
    )
    try:
        MouseBrowserAutomator(config).run()
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
