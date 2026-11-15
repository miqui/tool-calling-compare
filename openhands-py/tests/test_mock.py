import unittest

from tcc_openhands import mock_get_weather


class MockTest(unittest.TestCase):
    def test_mock_weather_keyless(self) -> None:
        self.assertEqual(mock_get_weather("Paris")["temp_c"], 18)


if __name__ == "__main__":
    unittest.main()
