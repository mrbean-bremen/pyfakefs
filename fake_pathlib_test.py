"""Tests for fake_pathlib."""
import os
import stat
import unittest

import sys

from pyfakefs import fake_filesystem
from pyfakefs import fake_pathlib

is_windows = sys.platform == 'win32'


class FakePathlibInitializationTest(unittest.TestCase):
    def setUp(self):
        filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        filesystem.supports_drive_letter = False
        self.pathlib = fake_pathlib.FakePathlibModule(filesystem)
        self.path = self.pathlib.Path

    def test_initialization_type(self):
        """Make sure tests for class type will work"""
        path = self.path('/test')
        if is_windows:
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
        self.assertEqual(self.path('/', 'foo', 'bar', 'baz'),
                         self.path('/foo/bar/baz'))
        self.assertEqual(self.path(), self.path('.'))
        self.assertEqual(self.path(self.path('foo'), self.path('bar')),
                         self.path('foo/bar'))
        self.assertEqual(self.path('/etc') / 'init.d' / 'reboot',
                         self.path('/etc/init.d/reboot'))

    def test_init_collapse(self):
        """Tests for collapsing path during initialization - taken from pathlib.PurePath documentation"""
        self.assertEqual(self.path('foo//bar'), self.path('foo/bar'))
        self.assertEqual(self.path('foo/./bar'), self.path('foo/bar'))
        self.assertNotEqual(self.path('foo/../bar'), self.path('foo/bar'))
        self.assertEqual(self.path('/etc', '/usr', 'lib64'), self.path('/usr/lib64'))

    def test_path_parts(self):
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

    def test_is_absolute(self):
        self.assertTrue(self.path('/a/b').is_absolute())
        self.assertFalse(self.path('a/b').is_absolute())


class FakePathlibInitializationWithDriveTest(unittest.TestCase):
    def setUp(self):
        filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        filesystem.supports_drive_letter = True
        pathlib = fake_pathlib.FakePathlibModule(filesystem)
        self.path = pathlib.Path

    def test_init_with_segments(self):
        """Basic initialization tests - taken from pathlib.Path documentation"""
        self.assertEqual(self.path('c:/', 'foo', 'bar', 'baz'), self.path('c:/foo/bar/baz'))
        self.assertEqual(self.path(), self.path('.'))
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


class FakePathlibPurePathTest(unittest.TestCase):
    def setUp(self):
        filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        filesystem.supports_drive_letter = True
        pathlib = fake_pathlib.FakePathlibModule(filesystem)
        self.path = pathlib.Path

    def test_is_reserved(self):
        self.assertFalse(self.path('/dev').is_reserved())
        self.assertFalse(self.path('/').is_reserved())
        if is_windows:
            self.assertTrue(self.path('COM1').is_reserved())
            self.assertTrue(self.path('nul.txt').is_reserved())
        else:
            self.assertFalse(self.path('COM1').is_reserved())
            self.assertFalse(self.path('nul.txt').is_reserved())

    def test_joinpath(self):
        self.assertEqual(self.path('/etc').joinpath('passwd'),
                         self.path('/etc/passwd'))
        self.assertEqual(self.path('/etc').joinpath(self.path('passwd')),
                         self.path('/etc/passwd'))
        self.assertEqual(self.path('/foo').joinpath('bar', 'baz'),
                         self.path('/foo/bar/baz'))
        self.assertEqual(self.path('c:').joinpath('/Program Files'),
                         self.path('c:/Program Files'))

    def test_match(self):
        self.assertTrue(self.path('a/b.py').match('*.py'))
        self.assertTrue(self.path('/a/b/c.py').match('b/*.py'))
        self.assertFalse(self.path('/a/b/c.py').match('a/*.py'))
        self.assertTrue(self.path('/a.py').match('/*.py'))
        self.assertFalse(self.path('a/b.py').match('/*.py'))

    def test_relative_to(self):
        self.assertEqual(self.path('/etc/passwd').relative_to('/'), self.path('etc/passwd'))
        self.assertEqual(self.path('/etc/passwd').relative_to('/'), self.path('etc/passwd'))
        self.assertRaises(ValueError, self.path('passwd').relative_to, '/usr')

    def test_with_name(self):
        self.assertEqual(self.path('c:/Downloads/pathlib.tar.gz').with_name('setup.py'),
                         self.path('c:/Downloads/setup.py'))
        self.assertRaises(ValueError, self.path('c:/').with_name, 'setup.py')

    def test_with_suffix(self):
        self.assertEqual(self.path('c:/Downloads/pathlib.tar.gz').with_suffix('.bz2'),
                         self.path('c:/Downloads/pathlib.tar.bz2'))
        self.assertEqual(self.path('README').with_suffix('.txt'),
                         self.path('README.txt'))


class FakePathlibPathTest(unittest.TestCase):
    def setUp(self):
        self.filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        self.filesystem.supports_drive_letter = False
        self.filesystem.is_case_sensitive = True
        pathlib = fake_pathlib.FakePathlibModule(self.filesystem)
        self.path = pathlib.Path

    def test_cwd(self):
        self.filesystem.cwd = '/home/jane'
        self.assertEqual(self.path.cwd(), '/home/jane')

    def test_stat(self):
        file_object = self.filesystem.CreateFile('/home/jane/test.py', st_size=20)

        stat_result = self.path('/home/jane/test.py').stat()
        self.assertFalse(stat_result[stat.ST_MODE] & stat.S_IFDIR)
        self.assertTrue(stat_result[stat.ST_MODE] & stat.S_IFREG)
        self.assertEqual(stat_result[stat.ST_INO], file_object.st_ino)
        self.assertEqual(stat_result[stat.ST_SIZE], 20)
        self.assertEqual(stat_result[stat.ST_MTIME], file_object.st_mtime)

    def test_chmod(self):
        file_object = self.filesystem.CreateFile('/home/jane/test.py', st_mode=stat.S_IFREG | 0o666)
        self.path('/home/jane/test.py').chmod(0o444)
        self.assertEqual(file_object.st_mode, stat.S_IFREG | 0o444)

    def test_exists(self):
        self.filesystem.CreateFile('/home/jane/test.py')
        self.filesystem.CreateDirectory('/home/john')
        self.filesystem.CreateLink('/john', '/home/john')
        self.filesystem.CreateLink('/none', '/home/none')

        self.assertTrue(self.path('/home/jane/test.py').exists())
        self.assertTrue(self.path('/home/jane').exists())
        self.assertTrue(self.path('/john').exists())
        self.assertFalse(self.path('/none').exists())
        self.assertFalse(self.path('/home/jane/test').exists())

    def test_expanduser(self):
        if is_windows:
            self.assertEqual(self.path('~').expanduser(),
                             self.path(os.environ['USERPROFILE'].replace('\\', '/')))
        else:
            self.assertEqual(self.path('~').expanduser(),
                             self.path(os.environ['HOME']))


class FakePathlibFileObjectProperrtyTest(unittest.TestCase):
    def setUp(self):
        filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        filesystem.supports_drive_letter = False
        pathlib = fake_pathlib.FakePathlibModule(filesystem)
        self.path = pathlib.Path
        filesystem.CreateFile('/home/jane/test.py')
        filesystem.CreateDirectory('/home/john')
        filesystem.CreateLink('/john', '/home/john')
        filesystem.CreateLink('/test.py', '/home/jane/test.py')
        filesystem.CreateLink('/broken_dir_link', '/home/none')
        filesystem.CreateLink('/broken_file_link', '/home/none/test.py')

    def test_exists(self):
        self.assertTrue(self.path('/home/jane/test.py').exists())
        self.assertTrue(self.path('/home/jane').exists())
        self.assertFalse(self.path('/home/jane/test').exists())
        self.assertTrue(self.path('/john').exists())
        self.assertTrue(self.path('/test.py').exists())
        self.assertFalse(self.path('/broken_dir_link').exists())
        self.assertFalse(self.path('/broken_file_link').exists())

    def test_is_dir(self):
        self.assertFalse(self.path('/home/jane/test.py').is_dir())
        self.assertTrue(self.path('/home/jane').is_dir())
        self.assertTrue(self.path('/john').is_dir())
        self.assertFalse(self.path('/test.py').is_dir())
        self.assertFalse(self.path('/broken_dir_link').is_dir())
        self.assertFalse(self.path('/broken_file_link').is_dir())

    def test_is_file(self):
        self.assertTrue(self.path('/home/jane/test.py').is_file())
        self.assertFalse(self.path('/home/jane').is_file())
        self.assertFalse(self.path('/john').is_file())
        self.assertTrue(self.path('/test.py').is_file())
        self.assertFalse(self.path('/broken_dir_link').is_file())
        self.assertFalse(self.path('/broken_file_link').is_file())

    def test_is_symlink(self):
        self.assertFalse(self.path('/home/jane/test.py').is_symlink())
        self.assertFalse(self.path('/home/jane').is_symlink())
        self.assertTrue(self.path('/john').is_symlink())
        self.assertTrue(self.path('/test.py').is_symlink())
        self.assertTrue(self.path('/broken_dir_link').is_symlink())
        self.assertTrue(self.path('/broken_file_link').is_symlink())
