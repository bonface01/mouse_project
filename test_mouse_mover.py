import unittest

from mouse_mover import advance_axis


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


if __name__ == "__main__":
    unittest.main()
