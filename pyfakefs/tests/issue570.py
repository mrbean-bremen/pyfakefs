import time
import unittest

import tqdm

from pyfakefs.fake_filesystem_unittest import TestCase


class TestClass(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def test_tqdm(self):
        with tqdm.tqdm(total=100, ascii=False) as pbar:
            for i in range(10):
                time.sleep(0.1)
                pbar.update(10)


if __name__ == "__main__":
    unittest.main()
