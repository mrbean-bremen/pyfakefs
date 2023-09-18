import io
import os
import pathlib
import platform
import zipfile

import pytest

import pyfakefs
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut


class MyTest(pyfakefs_ut.TestCase):
    @classmethod
    def setUpClass(cls):
        print("")
        print(f"{platform.python_version()=}")
        print(f"{pyfakefs.__version__=}")
        print(f"{pytest.__version__=}")

        print(f"before setUpClassPyfakefs() :: {os.getcwd()=}")
        cls.setUpClassPyfakefs(allow_root_user=False)

        zip_filepath = pathlib.Path.cwd() / "foo.zip"
        print(f"{str(zip_filepath)=}")
        print(f"after setUpClassPyfakefs() :: {os.getcwd()=}")

        with zipfile.ZipFile(zip_filepath, "w") as zip_handle:
            with zip_handle.open("nice.txt", "w") as entry_handle:
                entry_handle.write(b"foobar")

        print(zip_filepath)
        print(zip_filepath.exists())
        print("\n===== end setUpClass() ===")

    def test_foobar(self):
        zip_filepath = pathlib.Path.cwd() / "foo.zip"
        print(zip_filepath)
        print(zip_filepath.exists())

        self.assertTrue(zip_filepath.exists())

        # read
        # with zip_filepath.open('rb') as handle:
        print("X" * 55)
        with open(str(zip_filepath), "rb") as handle:
            print("T" * 55)
            stream = io.BytesIO(handle.read())
        print("U" * 55)

        with zipfile.ZipFile(stream, "r") as zip_handle:
            with zip_handle.open("nice.txt", "r") as entry_handle:
                content = entry_handle.read()

        print(f"{content=}")
