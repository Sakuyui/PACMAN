import unittest
from pacman.utilities.progress_bar import ProgressBar


class MyTestCase(unittest.TestCase):

    @unittest.skip("demonstrating skipping")
    def test_something(self):
        self.assertEqual(True, False, "Test not implemented yet")


if __name__ == '__main__':
    unittest.main()
