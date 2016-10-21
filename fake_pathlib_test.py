#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unittests for fake_pathlib."""

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
        self.filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        self.filesystem.supports_drive_letter = False
        pathlib = fake_pathlib.FakePathlibModule(self.filesystem)
        self.path = pathlib.Path
        self.filesystem.CreateFile('/home/jane/test.py', st_size=100, st_mode=stat.S_IFREG | 0o666)
        self.filesystem.CreateDirectory('/home/john')
        self.filesystem.CreateLink('/john', '/home/john')
        self.filesystem.CreateLink('/test.py', '/home/jane/test.py')
        self.filesystem.CreateLink('/broken_dir_link', '/home/none')
        self.filesystem.CreateLink('/broken_file_link', '/home/none/test.py')

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

    def test_stat(self):
        file_object = self.filesystem.ResolveObject('/home/jane/test.py')

        stat_result = self.path('/test.py').stat()
        self.assertFalse(stat_result[stat.ST_MODE] & stat.S_IFDIR)
        self.assertTrue(stat_result[stat.ST_MODE] & stat.S_IFREG)
        self.assertEqual(stat_result[stat.ST_INO], file_object.st_ino)
        self.assertEqual(stat_result[stat.ST_SIZE], 100)
        self.assertEqual(stat_result[stat.ST_MTIME], file_object.st_mtime)

    def test_lstat(self):
        link_object = self.filesystem.LResolveObject('/test.py')

        stat_result = self.path('/test.py').lstat()
        self.assertTrue(stat_result[stat.ST_MODE] & stat.S_IFREG)
        self.assertTrue(stat_result[stat.ST_MODE] & stat.S_IFLNK)
        self.assertEqual(stat_result[stat.ST_INO], link_object.st_ino)
        self.assertEqual(stat_result[stat.ST_SIZE], len('/home/jane/test.py'))
        self.assertEqual(stat_result[stat.ST_MTIME], link_object.st_mtime)

    def test_chmod(self):
        file_object = self.filesystem.ResolveObject('/home/jane/test.py')
        link_object = self.filesystem.LResolveObject('/test.py')
        self.path('/test.py').chmod(0o444)
        self.assertEqual(file_object.st_mode, stat.S_IFREG | 0o444)
        self.assertEqual(link_object.st_mode, stat.S_IFLNK | 0o777)

    def test_lchmod(self):
        file_object = self.filesystem.ResolveObject('/home/jane/test.py')
        link_object = self.filesystem.LResolveObject('/test.py')
        self.path('/test.py').lchmod(0o444)
        self.assertEqual(file_object.st_mode, stat.S_IFREG | 0o666)
        self.assertEqual(link_object.st_mode, stat.S_IFLNK | 0o444)


class FakePathlibPathFileOperationTest(unittest.TestCase):
    """Tests some basic file handling. Mostly we can rely on the existing tests
    for fake_filesystem methods, as most pathlib methods are just a wrapper around them.
    """

    def setUp(self):
        self.filesystem = fake_filesystem.FakeFilesystem(path_separator='/')
        self.filesystem.supports_drive_letter = False
        self.filesystem.is_case_sensitive = True
        pathlib = fake_pathlib.FakePathlibModule(self.filesystem)
        self.path = pathlib.Path

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

    def test_open(self):
        self.filesystem.CreateDirectory('/foo')
        self.assertRaises(OSError, self.path('/foo/bar.txt').open)
        self.path('/foo/bar.txt').open('w')
        self.assertTrue(self.filesystem.Exists('/foo/bar.txt'))

    @unittest.skipIf(sys.version_info < (3, 5), 'New in version 3.5')
    def test_read_text(self):
        self.filesystem.CreateFile('text_file', contents='ерунда', encoding='cyrillic')
        file_path = self.path('text_file')
        self.assertEqual(file_path.read_text(encoding='cyrillic'), 'ерунда')

    @unittest.skipIf(sys.version_info < (3, 5), 'New in version 3.5')
    def test_write_text(self):
        file_path = self.path('text_file')
        file_path.write_text('ανοησίες', encoding='greek')
        self.assertTrue(self.filesystem.Exists('text_file'))
        file_object = self.filesystem.ResolveObject('text_file')
        self.assertEqual(file_object.byte_contents.decode('greek'), 'ανοησίες')

    @unittest.skipIf(sys.version_info < (3, 5), 'New in version 3.5')
    def test_read_bytes(self):
        self.filesystem.CreateFile('binary_file', contents=b'Binary file contents')
        file_path = self.path('binary_file')
        self.assertEqual(file_path.read_bytes(), b'Binary file contents')

    @unittest.skipIf(sys.version_info < (3, 5), 'New in version 3.5')
    def test_write_bytes(self):
        file_path = self.path('binary_file')
        file_path.write_bytes(b'Binary file contents')
        self.assertTrue(self.filesystem.Exists('binary_file'))
        file_object = self.filesystem.ResolveObject('binary_file')
        self.assertEqual(file_object.byte_contents, b'Binary file contents')

    def test_rename(self):
        self.filesystem.CreateFile('/foo/bar.txt', contents='test')
        self.path('/foo/bar.txt').rename('foo/baz.txt')
        self.assertFalse(self.filesystem.Exists('/foo/bar.txt'))
        file_obj = self.filesystem.ResolveObject('foo/baz.txt')
        self.assertTrue(file_obj)
        self.assertEqual(file_obj.contents, 'test')

    def test_replace(self):
        self.filesystem.CreateFile('/foo/bar.txt', contents='test')
        self.filesystem.CreateFile('/bar/old.txt', contents='replaced')
        self.path('/bar/old.txt').replace('foo/bar.txt')
        self.assertFalse(self.filesystem.Exists('/bar/old.txt'))
        file_obj = self.filesystem.ResolveObject('foo/bar.txt')
        self.assertTrue(file_obj)
        self.assertEqual(file_obj.contents, 'replaced')

    def test_unlink(self):
        self.filesystem.CreateFile('/foo/bar.txt', contents='test')
        self.assertTrue(self.filesystem.Exists('/foo/bar.txt'))
        self.path('/foo/bar.txt').unlink()
        self.assertFalse(self.filesystem.Exists('/foo/bar.txt'))

    def test_touch_non_existing(self):
        self.filesystem.CreateDirectory('/foo')
        self.path('/foo/bar.txt').touch(mode=0o444)
        file_obj = self.filesystem.ResolveObject('/foo/bar.txt')
        self.assertTrue(file_obj)
        self.assertEqual(file_obj.contents, '')
        self.assertTrue(file_obj.st_mode, stat.S_IFREG | 0o444)

    def test_touch_existing(self):
        self.filesystem.CreateFile('/foo/bar.txt', contents='test')
        file_path = self.path('/foo/bar.txt')
        self.assertRaises(FileExistsError, file_path.touch, exist_ok=False)
        file_path.touch()
        file_obj = self.filesystem.ResolveObject('/foo/bar.txt')
        self.assertTrue(file_obj)
        self.assertEqual(file_obj.contents, 'test')

    def test_samefile(self):
        self.filesystem.CreateFile('/foo/bar.txt')
        self.filesystem.CreateFile('/foo/baz.txt')
        self.assertRaises(OSError, self.path('/foo/other').samefile, '/foo/other.txt')
        path = self.path('/foo/bar.txt')
        self.assertRaises(OSError, path.samefile, '/foo/other.txt')
        self.assertFalse(path.samefile('/foo/baz.txt'))
        self.assertTrue(path.samefile('/foo/../foo/bar.txt'))


if __name__ == '__main__':
    unittest.main()
