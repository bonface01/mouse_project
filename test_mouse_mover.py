import unittest
from unittest.mock import patch

from mouse_mover import (
    AutomationConfig,
    MouseBrowserAutomator,
    advance_axis,
    quadratic_waypoints,
)


class FakePyAutoGUI:
    @staticmethod
    def easeInOutQuad(progress):
        return 2 * progress**2 if progress < 0.5 else 1 - (-2 * progress + 2) ** 2 / 2

    @staticmethod
    def easeOutQuad(progress):
        return 1 - (1 - progress) ** 2

    @staticmethod
    def linear(progress):
        return progress

    def __init__(self) -> None:
        self.moves = []

    def moveTo(self, x, y, duration, tween) -> None:
        self.moves.append((x, y, duration, tween))


def make_automator(
    *,
    x: int = 5,
    y: int = 5,
    dx: int = 1,
    dy: int = 1,
    width: int = 11,
    height: int = 11,
) -> MouseBrowserAutomator:
    automator = MouseBrowserAutomator.__new__(MouseBrowserAutomator)
    automator._pyautogui = FakePyAutoGUI()
    automator._config = AutomationConfig()
    automator._screen_width = width
    automator._screen_height = height
    automator._x = x
    automator._y = y
    automator._dx = dx
    automator._dy = dy
    return automator


class AdvanceAxisTests(unittest.TestCase):
    def test_bounces_at_maximum(self) -> None:
        self.assertEqual(advance_axis(8, 1, 5, 10), (7, -1))

    def test_bounces_at_zero(self) -> None:
        self.assertEqual(advance_axis(2, -1, 5, 10), (3, 1))

    def test_handles_multiple_reflections(self) -> None:
        self.assertEqual(advance_axis(2, 1, 29, 10), (9, -1))

    def test_direction_points_inward_at_edges(self) -> None:
        self.assertEqual(advance_axis(7, 1, 3, 10), (10, -1))
        self.assertEqual(advance_axis(3, -1, 3, 10), (0, 1))

    def test_rejects_invalid_bounds_and_direction(self) -> None:
        with self.assertRaises(ValueError):
            advance_axis(0, 1, 1, 0)
        with self.assertRaises(ValueError):
            advance_axis(2, 0, 1, 10)


class CurvedMovementTests(unittest.TestCase):
    def test_quadratic_waypoints_follow_curve_and_end_at_target(self) -> None:
        points = quadratic_waypoints(
            (1, 1), (9, 9), (9, 1), 4, screen_width=10, screen_height=10
        )

        self.assertEqual(len(points), 4)
        self.assertEqual(points[-1], (9, 9))
        self.assertGreater(points[1][0], points[1][1])

    def test_quadratic_waypoints_stay_inside_screen_near_edges(self) -> None:
        points = quadratic_waypoints(
            (0, 1), (9, 8), (20, -20), 8, screen_width=10, screen_height=10
        )

        self.assertTrue(all(0 <= x < 10 and 0 <= y < 10 for x, y in points))
        self.assertEqual(points[-1], (9, 8))

    def test_movement_waypoints_end_at_reflected_boundary_target(self) -> None:
        automator = make_automator(x=8, y=8, width=11, height=11)
        with (
            patch("mouse_mover.random.randint", return_value=5),
            patch("mouse_mover.random.uniform", side_effect=[0.0, 1.0]),
            patch(
                "mouse_mover.random.choice",
                return_value=automator._pyautogui.easeOutQuad,
            ),
        ):
            automator._move()

        positions = [(x, y) for x, y, _, _ in automator._pyautogui.moves]
        self.assertEqual(positions[-1], (7, 7))
        self.assertTrue(all(0 <= x < 11 and 0 <= y < 11 for x, y in positions))
        self.assertEqual(len(positions), 5)

    def test_hover_jitter_is_bounded_and_returns_to_resting_position(self) -> None:
        automator = make_automator(x=9, y=5, width=10, height=10)
        with (
            patch("mouse_mover.random.uniform", side_effect=[1.2, 0.1, 0.1]),
            patch("mouse_mover.random.random", return_value=0.0),
            patch("mouse_mover.random.choice", side_effect=[1, -1]),
            patch("mouse_mover.random.randint", side_effect=[3, 2]),
            patch("mouse_mover.time.sleep") as sleep,
        ):
            automator.hover()

        self.assertEqual(
            [(x, y) for x, y, _, _ in automator._pyautogui.moves],
            [(9, 3), (9, 5)],
        )
        sleep.assert_called_once_with(1.2)

    def test_config_rejects_invalid_hover_settings(self) -> None:
        with self.assertRaises(ValueError):
            AutomationConfig(hover_chance=1.1)
        with self.assertRaises(ValueError):
            AutomationConfig(min_hover_duration=2, max_hover_duration=1)


if __name__ == "__main__":
    unittest.main()
