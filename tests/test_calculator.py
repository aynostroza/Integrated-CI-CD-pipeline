import unittest

from app.calculator import add, divide, multiply, subtract


class CalculatorTests(unittest.TestCase):
    def test_add_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        self.assertEqual(add(-2, -3), -5)

    def test_add_zero(self):
        self.assertEqual(add(7, 0), 7)

    def test_add_decimals(self):
        self.assertAlmostEqual(add(0.1, 0.2), 0.3)

    def test_subtract_positive(self):
        self.assertEqual(subtract(10, 4), 6)

    def test_subtract_negative_result(self):
        self.assertEqual(subtract(4, 10), -6)

    def test_subtract_equal(self):
        self.assertEqual(subtract(8, 8), 0)

    def test_multiply_positive(self):
        self.assertEqual(multiply(6, 7), 42)

    def test_multiply_negative(self):
        self.assertEqual(multiply(-3, 4), -12)

    def test_multiply_zero(self):
        self.assertEqual(multiply(10, 0), 0)

    def test_divide_exact(self):
        self.assertEqual(divide(12, 3), 4)

    def test_divide_fraction(self):
        self.assertAlmostEqual(divide(1, 4), 0.25)

    def test_divide_negative(self):
        self.assertEqual(divide(-10, 2), -5)

    def test_divide_zero_numerator(self):
        self.assertEqual(divide(0, 5), 0)

    def test_divide_by_zero(self):
        with self.assertRaisesRegex(ValueError, "Cannot divide by zero"):
            divide(10, 0)


if __name__ == "__main__":
    unittest.main()
