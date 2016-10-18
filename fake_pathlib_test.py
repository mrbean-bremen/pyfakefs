"""Tests for fake_pathlib."""

import unittest

import sys

from pyfakefs import fake_filesystem
from pyfakefs import fake_pathlib


class FakePathlibModuleTest(unittest.TestCase):
    def setUp(self):
        self.filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        self.filesystem.supports_drive_letter = False
        self.pathlib = fake_pathlib.FakePathlibModule(self.filesystem)
        self.path = self.pathlib.Path
        self.is_windows = sys.platform == 'win32'

    def test_initialization_type(self):
        """Make sure tests for class type will work"""
        path = self.path('/test')
        if self.is_windows:
            self.assertTrue(isinstance(path, self.pathlib.WindowsPath))
            self.assertTrue(isinstance(path, self.pathlib.PureWindowsPath))
            self.assertTrue(self.pathlib.PurePosixPath())
            self.assertRaises(NotImplementedError, self.pathlib.PosixPath)
        else:
            self.assertTrue(isinstance(path, self.pathlib.PosixPath))
            self.assertTrue(isinstance(path, self.pathlib.PurePosixPath))
            self.assertTrue(self.pathlib.PureWindowsPath())
            self.assertRaises(NotImplementedError, self.pathlib.WindowsPath)

    def test_init_with_segments(self):
        """Basic initialization tests - taken from pathlib.Path documentation"""
        self.assertEqual(self.path('/', 'foo', 'bar', 'baz'), self.pathlib.Path('/foo/bar/baz'))
        self.assertEqual(self.path(), self.pathlib.Path('.'))
        self.assertEqual(self.path(self.path('foo'), self.path('bar')), self.path('foo/bar'))
        self.assertEqual(self.path('/etc') / 'init.d' / 'reboot', self.path('/etc/init.d/reboot'))

    def test_init_collapse(self):
        """Tests for collapsing path during initialization - taken from pathlib.PurePath documentation"""
        self.filesystem.supports_drive_letter = False
        self.assertEqual(self.path('foo//bar'), self.path('foo/bar'))
        self.assertEqual(self.path('foo/./bar'), self.path('foo/bar'))
        self.assertNotEqual(self.path('foo/../bar'), self.path('foo/bar'))
        self.assertEqual(self.path('/etc', '/usr', 'lib64'), self.path('/usr/lib64'))

        self.filesystem.supports_drive_letter = True
        self.assertEqual(self.path('c:/Windows', 'd:bar'), self.path('d:bar'))
        self.assertEqual(self.path('c:/Windows', '/Program Files'), self.path('c:/Program Files'))

    def test_path_parts(self):
        self.filesystem.supports_drive_letter = False
        path = self.path('/foo/bar/setup.py')
        self.assertEqual(path.parts, ('/', 'foo', 'bar', 'setup.py'))
        self.assertEqual(path.drive, '')
        self.assertEqual(path.root, '/')
        self.assertEqual(path.anchor, '/')
        self.assertEqual(path.name, 'setup.py')
        self.assertEqual(path.stem, 'setup')
        self.assertEqual(path.suffix, '.py')
        self.assertEqual(path.parent, self.path('/foo/bar'))
        self.assertEqual(path.parents[0], self.path('/foo/bar'))
        self.assertEqual(path.parents[1], self.path('/foo'))
        self.assertEqual(path.parents[2], self.path('/'))

    def test_path_parts_with_drive(self):
        self.filesystem.supports_drive_letter = True
        path = self.path('d:/python scripts/setup.py')
        self.assertEqual(path.parts, ('d:/', 'python scripts', 'setup.py'))
        self.assertEqual(path.drive, 'd:')
        self.assertEqual(path.root, '/')
        self.assertEqual(path.anchor, 'd:/')
        self.assertEqual(path.name, 'setup.py')
        self.assertEqual(path.stem, 'setup')
        self.assertEqual(path.suffix, '.py')
        self.assertEqual(path.parent, self.path('d:/python scripts'))
        self.assertEqual(path.parents[0], self.path('d:/python scripts'))
        self.assertEqual(path.parents[1], self.path('d:/'))

    def test_is_absolute(self):
        self.assertTrue(self.path('/a/b').is_absolute())
        self.assertFalse(self.path('a/b').is_absolute())
        self.filesystem.supports_drive_letter = True

    def test_is_reserved(self):
        self.assertFalse(self.path('/dev').is_reserved())
        self.assertFalse(self.path('/').is_reserved())
        if self.is_windows:
            self.assertTrue(self.path('COM1').is_reserved())
            self.assertTrue(self.path('nul.txt').is_reserved())
        else:
            self.assertFalse(self.path('COM1').is_reserved())
            self.assertFalse(self.path('nul.txt').is_reserved())


class FakePathlibModuleWithDriveTest(unittest.TestCase):
    def setUp(self):
        self.filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        self.filesystem.supports_drive_letter = True
        self.pathlib = fake_pathlib.FakePathlibModule(self.filesystem)
        self.path = self.pathlib.Path

    def test_init_with_segments(self):
        """Basic initialization tests - taken from pathlib.Path documentation"""
        self.assertEqual(self.path('c:/', 'foo', 'bar', 'baz'), self.pathlib.Path('c:/foo/bar/baz'))
        self.assertEqual(self.path(), self.pathlib.Path('.'))
        self.assertEqual(self.path(self.path('foo'), self.path('bar')), self.path('foo/bar'))
        self.assertEqual(self.path('c:/Users') / 'john' / 'data', self.path('c:/Users/john/data'))

    def test_init_collapse(self):
        """Tests for collapsing path during initialization - taken from pathlib.PurePath documentation"""
        self.assertEqual(self.path('c:/Windows', 'd:bar'), self.path('d:bar'))
        self.assertEqual(self.path('c:/Windows', '/Program Files'), self.path('c:/Program Files'))

    def test_path_parts(self):
        path = self.path('d:/python scripts/setup.py')
        self.assertEqual(path.parts, ('d:/', 'python scripts', 'setup.py'))
        self.assertEqual(path.drive, 'd:')
        self.assertEqual(path.root, '/')
        self.assertEqual(path.anchor, 'd:/')
        self.assertEqual(path.name, 'setup.py')
        self.assertEqual(path.stem, 'setup')
        self.assertEqual(path.suffix, '.py')
        self.assertEqual(path.parent, self.path('d:/python scripts'))
        self.assertEqual(path.parents[0], self.path('d:/python scripts'))
        self.assertEqual(path.parents[1], self.path('d:/'))

    def test_is_absolute(self):
        self.assertTrue(self.path('c:/a/b').is_absolute())
        self.assertFalse(self.path('/a/b').is_absolute())
        self.assertFalse(self.path('c:').is_absolute())
        self.assertTrue(self.path('//some/share').is_absolute())
