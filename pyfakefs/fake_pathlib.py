import os
import pathlib
import stat
from urllib.parse import quote_from_bytes as urlquote_from_bytes

import sys

from pyfakefs.fake_filesystem import FakeFileOpen


def init_module(filesystem):
    FakePath.filesystem = filesystem
    FakePathlibModule.PureWindowsPath._flavour = _FakeWindowsFlavour(filesystem)
    FakePathlibModule.PurePosixPath._flavour = _FakePosixFlavour(filesystem)


class _FakeFlavour(pathlib._Flavour):
    filesystem = None
    sep = '/'
    altsep = None
    has_drv = False

    ext_namespace_prefix = '\\\\?\\'

    drive_letters = (
        set(chr(x) for x in range(ord('a'), ord('z') + 1)) |
        set(chr(x) for x in range(ord('A'), ord('Z') + 1))
    )

    def __init__(self, filesystem):
        self.filesystem = filesystem
        self.sep = filesystem.path_separator
        self.altsep = filesystem.alternative_path_separator
        self.has_drv = filesystem.supports_drive_letter
        super(_FakeFlavour, self).__init__()

    def _split_extended_path(self, s, ext_prefix=ext_namespace_prefix):
        prefix = ''
        if s.startswith(ext_prefix):
            prefix = s[:4]
            s = s[4:]
            if s.startswith('UNC\\'):
                prefix += s[:3]
                s = '\\' + s[3:]
        return prefix, s

    def _splitroot_with_drive(self, part, sep):
        first = part[0:1]
        second = part[1:2]
        if (second == sep and first == sep):
            # XXX extended paths should also disable the collapsing of "."
            # components (according to MSDN docs).
            prefix, part = self._split_extended_path(part)
            first = part[0:1]
            second = part[1:2]
        else:
            prefix = ''
        third = part[2:3]
        if (second == sep and first == sep and third != sep):
            # is a UNC path:
            # vvvvvvvvvvvvvvvvvvvvv root
            # \\machine\mountpoint\directory\etc\...
            #            directory ^^^^^^^^^^^^^^
            index = part.find(sep, 2)
            if index != -1:
                index2 = part.find(sep, index + 1)
                # a UNC path can't have two slashes in a row
                # (after the initial two)
                if index2 != index + 1:
                    if index2 == -1:
                        index2 = len(part)
                    if prefix:
                        return prefix + part[1:index2], sep, part[index2 + 1:]
                    else:
                        return part[:index2], sep, part[index2 + 1:]
        drv = root = ''
        if second == ':' and first in self.drive_letters:
            drv = part[:2]
            part = part[2:]
            first = third
        if first == sep:
            root = first
            part = part.lstrip(sep)
        return prefix + drv, root, part

    def _splitroot_posix(self, part, sep):
        if part and part[0] == sep:
            stripped_part = part.lstrip(sep)
            # According to POSIX path resolution:
            # http://pubs.opengroup.org/onlinepubs/009695399/basedefs/xbd_chap04.html#tag_04_11
            # "A pathname that begins with two successive slashes may be
            # interpreted in an implementation-defined manner, although more
            # than two leading slashes shall be treated as a single slash".
            if len(part) - len(stripped_part) == 2:
                return '', sep * 2, stripped_part
            else:
                return '', sep, stripped_part
        else:
            return '', '', part

    def splitroot(self, part, sep=None):
        if sep is None:
            sep = self.filesystem.path_separator
        if self.filesystem.supports_drive_letter:
            return self._splitroot_with_drive(part, sep)
        return self._splitroot_posix(part, sep)

    def casefold(self, s):
        if self.filesystem.is_case_sensitive:
            return s
        return s.lower()

    def casefold_parts(self, parts):
        if self.filesystem.is_case_sensitive:
            return parts
        return [p.lower() for p in parts]

    def resolve(self, path):
        # todo: adapt error handling
        return self.filesystem.ResolvePath(str(path))

    def gethomedir(self, username):
        if not username:
            try:
                return os.environ['HOME']
            except KeyError:
                import pwd
                return pwd.getpwuid(os.getuid()).pw_dir
        else:
            import pwd
            try:
                return pwd.getpwnam(username).pw_dir
            except KeyError:
                raise RuntimeError("Can't determine home directory "
                                   "for %r" % username)


class _FakeWindowsFlavour(_FakeFlavour):
    reserved_names = (
        {'CON', 'PRN', 'AUX', 'NUL'} |
        {'COM%d' % i for i in range(1, 10)} |
        {'LPT%d' % i for i in range(1, 10)}
    )

    def is_reserved(self, parts):
        # NOTE: the rules for reserved names seem somewhat complicated
        # (e.g. r"..\NUL" is reserved but not r"foo\NUL").
        # We err on the side of caution and return True for paths which are
        # not considered reserved by Windows.
        if not parts:
            return False
        if self.filesystem.supports_drive_letter and parts[0].startswith('\\\\'):
            # UNC paths are never reserved
            return False
        return parts[-1].partition('.')[0].upper() in self.reserved_names

    def make_uri(self, path):
        # Under Windows, file URIs use the UTF-8 encoding.
        # original version, not faked
        # todo: make this part dependent on drive support, add encoding as property
        drive = path.drive
        if len(drive) == 2 and drive[1] == ':':
            # It's a path on a local drive => 'file:///c:/a/b'
            rest = path.as_posix()[2:].lstrip('/')
            return 'file:///%s/%s' % (
                drive, urlquote_from_bytes(rest.encode('utf-8')))
        else:
            # It's a path on a network drive => 'file://host/share/a/b'
            return 'file:' + urlquote_from_bytes(path.as_posix().encode('utf-8'))

    def gethomedir(self, username):
        # original version, not faked
        if 'HOME' in os.environ:
            userhome = os.environ['HOME']
        elif 'USERPROFILE' in os.environ:
            userhome = os.environ['USERPROFILE']
        elif 'HOMEPATH' in os.environ:
            try:
                drv = os.environ['HOMEDRIVE']
            except KeyError:
                drv = ''
            userhome = drv + os.environ['HOMEPATH']
        else:
            raise RuntimeError("Can't determine home directory")

        if username:
            # Try to guess user home directory.  By default all users
            # directories are located in the same place and are named by
            # corresponding usernames.  If current user home directory points
            # to nonstandard place, this guess is likely wrong.
            if os.environ['USERNAME'] != username:
                drv, root, parts = self.parse_parts((userhome,))
                if parts[-1] != os.environ['USERNAME']:
                    raise RuntimeError("Can't determine home directory "
                                       "for %r" % username)
                parts[-1] = username
                if drv or root:
                    userhome = drv + root + self.join(parts[1:])
                else:
                    userhome = self.join(parts)
        return userhome


class _FakePosixFlavour(_FakeFlavour):
    def is_reserved(self, parts):
        return False

    def make_uri(self, path):
        # We represent the path using the local filesystem encoding,
        # for portability to other applications.
        bpath = bytes(path)
        return 'file://' + urlquote_from_bytes(bpath)

    def gethomedir(self, username):
        # original version, not faked
        if not username:
            try:
                return os.environ['HOME']
            except KeyError:
                import pwd
                return pwd.getpwuid(os.getuid()).pw_dir
        else:
            import pwd
            try:
                return pwd.getpwnam(username).pw_dir
            except KeyError:
                raise RuntimeError("Can't determine home directory "
                                   "for %r" % username)


class FakePath(pathlib.PurePath):
    filesystem = None

    def __new__(cls, *args, **kwargs):
        if cls is FakePathlibModule.Path:
            cls = FakePathlibModule.WindowsPath if os.name == 'nt' else FakePathlibModule.PosixPath
        self = cls._from_parts(args, init=True)
        return self

    def _path(self):
        return str(self)

    def _init(self):
        self._closed = False

    def __enter__(self):
        if self._closed:
            self._raise_closed()
        return self

    def __exit__(self, t, v, tb):
        self._closed = True

    @staticmethod
    def _raise_closed():
        raise ValueError("I/O operation on closed path")

    @classmethod
    def cwd(cls):
        """Return a new path pointing to the current working directory
        (as returned by os.getcwd()).
        """
        return cls.filesystem.cwd

    @classmethod
    def home(cls):
        """Return a new path pointing to the user's home directory (as
        returned by os.path.expanduser('~')).
        """
        return cls(cls()._flavour.gethomedir(None))

    def samefile(self, other_path):
        """Return whether other_path is the same or not as this file
        (as returned by os.path.samefile()).
        """
        st = self.stat()
        try:
            other_st = other_path.stat()
        except AttributeError:
            other_st = self.filesystem.stat(other_path)
        return st.st_ino == other_st.st_ino and st.st_dev == other_st.st_dev

    def iterdir(self):
        """Iterate over the files in this directory.  Does not yield any
        result for the special paths '.' and '..'.
        """
        if self._closed:
            self._raise_closed()
            # todo: move listdir impl to filesystem
            # for name in self.filesystem.listdir(self):
            #     if name in {'.', '..'}:
            #         # Yielding a path object for these makes little sense
            #         continue
            #     yield self._make_child_relpath(name)
            #     if self._closed:
            #         self._raise_closed()

    # def glob(self, pattern):
    #     """Iterate over this subtree and yield all existing files (of any
    #     kind, including directories) matching the given pattern.
    #     """
    #     pattern = self._flavour.casefold(pattern)
    #     drv, root, pattern_parts = self._flavour.parse_parts((pattern,))
    #     if drv or root:
    #         raise NotImplementedError("Non-relative patterns are unsupported")
    #     selector = _make_selector(tuple(pattern_parts))
    #     for p in selector.select_from(self):
    #         yield p
    #
    # def rglob(self, pattern):
    #     """Recursively yield all existing files (of any kind, including
    #     directories) matching the given pattern, anywhere in this subtree.
    #     """
    #     pattern = self._flavour.casefold(pattern)
    #     drv, root, pattern_parts = self._flavour.parse_parts((pattern,))
    #     if drv or root:
    #         raise NotImplementedError("Non-relative patterns are unsupported")
    #     selector = _make_selector(("**",) + tuple(pattern_parts))
    #     for p in selector.select_from(self):
    #         yield p
    #
    # def absolute(self):
    #     """Return an absolute version of this path.  This function works
    #     even if the path doesn't point to anything.
    #
    #     No normalization is done, i.e. all '.' and '..' will be kept along.
    #     Use resolve() to get the canonical path to a file.
    #     """
    #     # XXX untested yet!
    #     if self._closed:
    #         self._raise_closed()
    #     if self.is_absolute():
    #         return self
    #     # FIXME this must defer to the specific flavour (and, under Windows,
    #     # use nt._getfullpathname())
    #     obj = self._from_parts([os.getcwd()] + self._parts, init=False)
    #     obj._init(template=self)
    #     return obj
    #
    def resolve(self):
        """
        Make the path absolute, resolving all symlinks on the way and also
        normalizing it (for example turning slashes into backslashes under
        Windows).
        """
        if self._closed:
            self._raise_closed()
        s = self._flavour.resolve(self)
        if s is None:
            # No symlink resolution => for consistency, raise an error if
            # the path doesn't exist or is forbidden
            self.stat()
            s = str(self.absolute())
        # Now we have no symlinks in the path, it's safe to normalize it.
        normed = self.filesystem.CollapsePath(s)
        obj = self._from_parts((normed,), init=False)
        obj._init(template=self)
        return obj

    def stat(self):
        """
        Return the result of the stat() system call on this path, like
        os.stat() does.
        """
        return self.filesystem.GetStat(self._path())

    # def owner(self):
    #     """
    #     Return the login name of the file owner.
    #     """
    #     import pwd
    #     return pwd.getpwuid(self.stat().st_uid).pw_name
    #
    # def group(self):
    #     """
    #     Return the group name of the file gid.
    #     """
    #     import grp
    #     return grp.getgrgid(self.stat().st_gid).gr_name
    #
    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        """
        Open the file pointed by this path and return a file object, as
        the built-in open() function does.
        """
        if self._closed:
            self._raise_closed()
        return FakeFileOpen(self.filesystem)(str(self), mode, buffering, encoding, errors, newline)

    def read_bytes(self):
        """
        Open the file in bytes mode, read it, and close the file.
        """
        with self.filesystem.FakeOpen(mode='rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        """
        Open the file in text mode, read it, and close the file.
        """
        with self.filesystem.FakeOpen(mode='r', encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        """
        Open the file in bytes mode, write to it, and close the file.
        """
        # type-check for the buffer interface before truncating the file
        view = memoryview(data)
        with self.filesystem.FakeOpen(mode='wb') as f:
            return f.write(view)

    def write_text(self, data, encoding=None, errors=None):
        """
        Open the file in text mode, write to it, and close the file.
        """
        if not isinstance(data, str):
            raise TypeError('data must be str, not %s' %
                            data.__class__.__name__)
        with self.filesystem.FakeOpen(mode='w', encoding=encoding, errors=errors) as f:
            return f.write(data)

    # def touch(self, mode=0o666, exist_ok=True):
    #     """
    #     Create this file with the given access mode, if it doesn't exist.
    #     """
    #     if self._closed:
    #         self._raise_closed()
    #     if exist_ok:
    #         # First try to bump modification time
    #         # Implementation note: GNU touch uses the UTIME_NOW option of
    #         # the utimensat() / futimens() functions.
    #         try:
    #             self._accessor.utime(self, None)
    #         except OSError:
    #             # Avoid exception chaining
    #             pass
    #         else:
    #             return
    #     flags = os.O_CREAT | os.O_WRONLY
    #     if not exist_ok:
    #         flags |= os.O_EXCL
    #     fd = self._raw_open(flags, mode)
    #     os.close(fd)

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if self._closed:
            self._raise_closed()
            # todo: move mkdir and makedirs implementation to FileSystem
            # if not parents:
            #     try:
            #         self._accessor.mkdir(self, mode)
            #     except FileExistsError:
            #         if not exist_ok or not self.is_dir():
            #             raise
            # else:
            #     try:
            #         self._accessor.mkdir(self, mode)
            #     except FileExistsError:
            #         if not exist_ok or not self.is_dir():
            #             raise
            #     except OSError as e:
            #         if e.errno != ENOENT:
            #             raise
            #         self.parent.mkdir(parents=True)
            #         self._accessor.mkdir(self, mode)

    def chmod(self, mode):
        """
        Change the permissions of the path, like os.chmod().
        """
        if self._closed:
            self._raise_closed()
        self.filesystem.ChangeMode(self._path(), mode)

    # def lchmod(self, mode):
    #     """
    #     Like chmod(), except if the path points to a symlink, the symlink's
    #     permissions are changed, rather than its target's.
    #     """
    #     if self._closed:
    #         self._raise_closed()
    #     self._accessor.lchmod(self, mode)
    #
    def unlink(self):
        """
        Remove this file or link.
        If the path is a directory, use rmdir() instead.
        """
        if self._closed:
            self._raise_closed()
        self.filesystem.RemoveObject(self._path())

    def rmdir(self):
        """
        Remove this directory.  The directory must be empty.
        """
        if self._closed:
            self._raise_closed()
        self.filesystem.RemoveObject(self._path())

    def lstat(self):
        """
        Like stat(), except if the path points to a symlink, the symlink's
        status information is returned, rather than its target's.
        """
        if self._closed:
            self._raise_closed()
        return self.filesystem.GetLStat(self._path())

    def rename(self, target):
        """
        Rename this path to the given path.
        """
        if self._closed:
            self._raise_closed()
        if isinstance(target, FakePath):
            target = target.path
        self.filesystem.RenameObject(self._path(), target)

    def replace(self, target):
        """
        Rename this path to the given path, clobbering the existing
        destination if it exists.
        """
        if self._closed:
            self._raise_closed()
        # todo: real replace
        self.filesystem.RenameObject(self._path(), target)

    def symlink_to(self, target, target_is_directory=False):
        """
        Make this path a symlink pointing to the given path.
        Note the order of arguments (self, target) is the reverse of os.symlink's.
        """
        if self._closed:
            self._raise_closed()
        # todo: handle target_is_directory
        self.filesystem.CreateLink(self._path(), target)

    # Convenience functions for querying the stat results

    def exists(self):
        """
        Whether this path exists.
        """
        return self.filesystem.Exists(self._path())

    def _is_type(self, st_flag):
        try:
            path_object = self.filesystem.ResolveObject(self._path())
            if path_object:
                return stat.S_IFMT(path_object.st_mode) == st_flag
        except IOError:
            return False
        return False

    def _is_ltype(self, st_flag):
        try:
            path_object = self.filesystem.LResolveObject(self._path())
            if path_object:
                return stat.S_IFMT(path_object.st_mode) == st_flag
        except IOError:
            return False
        return False

    def is_dir(self):
        """
        Whether this path is a directory.
        """
        return self._is_type(stat.S_IFDIR)

    def is_file(self):
        """
        Whether this path is a regular file (also True for symlinks pointing
        to regular files).
        """
        return self._is_type(stat.S_IFREG)

    def is_symlink(self):
        """
        Whether this path is a symbolic link.
        """
        return self._is_ltype(stat.S_IFLNK)

    def is_block_device(self):
        """
        Whether this path is a block device.
        """
        return self._is_ltype(stat.S_IFBLK)

    def is_char_device(self):
        """
        Whether this path is a character device.
        """
        return self._is_type(stat.S_IFCHR)

    def is_fifo(self):
        """
        Whether this path is a FIFO.
        """
        return self._is_type(stat.S_IFIFO)

    def is_socket(self):
        """
        Whether this path is a socket.
        """
        return self._is_type(stat.S_IFSOCK)

    def expanduser(self):
        """ Return a new path with expanded ~ and ~user constructs
        (as returned by os.path.expanduser)
        """
        return FakePath(os.path.expanduser(self._path())
                        .replace(os.path.sep, self.filesystem.path_separator))


class FakePathlibModule(object):
    """Uses FakeFilesystem to provide a fake pathlib module replacement.
       Currently only used to wrap pathlib.Path

    # You need a fake_filesystem to use this:
    filesystem = fake_filesystem.FakeFilesystem()
    fake_pathlib_module = fake_filesystem.FakePathlibModule(filesystem)
    """

    def __init__(self, filesystem):
        """
        Args:
          filesystem:  FakeFilesystem used to provide file system information
        """
        init_module(filesystem)
        self._pathlib_module = pathlib

    class PurePosixPath(pathlib.PurePath):
        __slots__ = ()

    class PureWindowsPath(pathlib.PurePath):
        __slots__ = ()

    if sys.platform == 'win32':
        class WindowsPath(FakePath, PureWindowsPath):
            __slots__ = ()
    else:
        class PosixPath(FakePath, PurePosixPath):
            __slots__ = ()

    Path = FakePath

    def __getattr__(self, name):
        """Forwards any unfaked calls to the standard pathlib module."""
        return getattr(self._pathlib_module, name)
