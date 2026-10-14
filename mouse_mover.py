"""Move the mouse within the screen and optionally perform browser actions."""

from __future__ import annotations

import argparse
import platform
import random
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class AutomationConfig:
    min_step: int = 8
    max_step: int = 24
    min_interval: float = 0.5
    max_interval: float = 1.5
    min_hover_duration: float = 0.4
    max_hover_duration: float = 1.8
    hover_chance: float = 0.12
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
            self.min_hover_duration < 0
            or self.max_hover_duration < self.min_hover_duration
        ):
            raise ValueError(
                "Hover durations must satisfy "
                "0 <= min_hover_duration <= max_hover_duration."
            )
        if not 0 <= self.hover_chance <= 1:
            raise ValueError("hover_chance must be between 0 and 1.")
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


def quadratic_waypoints(
    start: tuple[int, int],
    end: tuple[int, int],
    control: tuple[float, float],
    segments: int,
    screen_width: int,
    screen_height: int,
    easing: Callable[[float], float] | None = None,
) -> list[tuple[int, int]]:
    """Sample a quadratic Bezier curve and keep every point within the screen."""
    if segments < 1:
        raise ValueError("segments must be at least 1.")
    if screen_width < 1 or screen_height < 1:
        raise ValueError("Screen dimensions must be at least 1.")
    for x, y in (start, end):
        if not 0 <= x < screen_width or not 0 <= y < screen_height:
            raise ValueError("Path endpoints must be within the screen bounds.")

    points = []
    for index in range(1, segments + 1):
        t = index / segments
        if easing is not None:
            t = easing(t)
        inverse_t = 1 - t
        x = (
            inverse_t * inverse_t * start[0]
            + 2 * inverse_t * t * control[0]
            + t * t * end[0]
        )
        y = (
            inverse_t * inverse_t * start[1]
            + 2 * inverse_t * t * control[1]
            + t * t * end[1]
        )
        points.append(
            (
                min(max(round(x), 0), screen_width - 1),
                min(max(round(y), 0), screen_height - 1),
            )
        )
    points[-1] = end
    return points


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
        start = (self._x, self._y)
        distance = random.randint(self._config.min_step, self._config.max_step)
        self._x, self._dx = advance_axis(
            self._x, self._dx, distance, self._screen_width - 1
        )
        self._y, self._dy = advance_axis(
            self._y, self._dy, distance, self._screen_height - 1
        )
        end = (self._x, self._y)
        delta_x = end[0] - start[0]
        delta_y = end[1] - start[1]
        travel_distance = max(1, (delta_x**2 + delta_y**2) ** 0.5)
        max_curve_offset = min(10, travel_distance * 0.3)
        curve_offset = random.uniform(-max_curve_offset, max_curve_offset)
        control = (
            (start[0] + end[0]) / 2 - delta_y / travel_distance * curve_offset,
            (start[1] + end[1]) / 2 + delta_x / travel_distance * curve_offset,
        )
        easing = random.choice(
            (self._pyautogui.easeInOutQuad, self._pyautogui.easeOutQuad)
        )
        waypoints = quadratic_waypoints(
            start,
            end,
            control,
            segments=5,
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            easing=easing,
        )
        total_duration = random.uniform(
            self._config.min_interval, self._config.max_interval
        )
        for x, y in waypoints:
            self._pyautogui.moveTo(
                x,
                y,
                duration=total_duration / len(waypoints),
                tween=self._pyautogui.linear,
            )

    def hover(self) -> None:
        """Pause at the current position, sometimes adding small bounded jitters."""
        duration = random.uniform(
            self._config.min_hover_duration,
            self._config.max_hover_duration,
        )
        if random.random() < 0.35:
            jitter_x = random.choice((-1, 1)) * random.randint(1, 3)
            jitter_y = random.choice((-1, 1)) * random.randint(1, 3)
            jitter_position = (
                min(max(self._x + jitter_x, 0), self._screen_width - 1),
                min(max(self._y + jitter_y, 0), self._screen_height - 1),
            )
            tween = self._pyautogui.easeInOutQuad
            self._pyautogui.moveTo(
                *jitter_position,
                duration=random.uniform(0.08, 0.2),
                tween=tween,
            )
            self._pyautogui.moveTo(
                self._x,
                self._y,
                duration=random.uniform(0.08, 0.2),
                tween=tween,
            )
        time.sleep(duration)

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
                if random.random() < self._config.hover_chance:
                    self.hover()
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
        "--min-hover-duration",
        type=float,
        default=0.4,
        help="Minimum duration of a hover pause in seconds.",
    )
    parser.add_argument(
        "--max-hover-duration",
        type=float,
        default=1.8,
        help="Maximum duration of a hover pause in seconds.",
    )
    parser.add_argument(
        "--hover-chance",
        type=float,
        default=0.12,
        help="Chance of a hover pause after each move, from 0 to 1.",
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
        min_hover_duration=args.min_hover_duration,
        max_hover_duration=args.max_hover_duration,
        hover_chance=args.hover_chance,
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
