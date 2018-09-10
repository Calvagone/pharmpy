# -*- encoding: utf-8 -*-
"""Run directory module.

This module defines the :class:`RunDirectory` class, which initialization creates a filesystem
directory that :class:`~pysn.tool.Tool` instances and :class:`~pysn.model.Model` methods can utilize
for input->output during evaluation, estimation & simulation tasks.

.. testcode::
    :pyversion: > 3.6

    from pysn.execute.run_directory import RunDirectory

Usage
-----

Creating a directory

    .. doctest::
        :pyversion: > 3.6

        >>> dir = RunDirectory('.')
        >>> print(list(dir.path.iterdir()))
        []

Defining clean options:

    .. doctest::
        :pyversion: > 3.6

        >>> dir.cleanlevel = 1
        >>> dir.def_cleanlevel(level=1, patterns=['*.txt', 'remove*'], rm_dirs=False)
        >>> files = ['remove_this', 'file.txt', 'keep_this', 'file.py']
        >>> for file in files:
        ...     open(dir.path / file, 'a').close()

Destroying object (triggering cleanup):

    .. doctest::
        :pyversion: > 3.6

        >>> path = dir.path
        >>> print([x.name for x in path.iterdir()])
        ['remove_this', 'file.txt', 'keep_this', 'file.py']

    .. doctest::
        :pyversion: > 3.6

        >>> del dir
        >>> print([x.name for x in path.iterdir()])
        ['keep_this', 'file.py']

    .. doctest::
        :pyversion: > 3.6

        >>> (path / 'keep_this').unlink()
        >>> (path / 'file.py').unlink()
        >>> path.rmdir()

TODO
----

    Create a derived class at :class:`pysn.api_nonmem.execute.run_directory`.

Definitions
-----------
"""

import itertools
import re
from pathlib import Path
from tempfile import TemporaryDirectory


class RunDirectory:
    """Execution run directory.

    Will contain input/output files for a job and handle cleanup. Is generated by
    :class:`~.engine.Engine` class (and tools).

    Args:
        parent: Parent (directory). If None, a temporary directory is created.
        name: (Base) name of directory (when parent is not None). (This) class name if False.
        template: Template for directory naming. '%s' substitutes for 'name' and '%d' for an int.

    Raises:
        FileExistsError: Constructed name is occupied (and '%d' is missing from 'template').

    Temporary directories are removed entirely on garbage collection. Default 'template' is
    '%s_dir%d'. First number in range (1, ∞) with a unique filesystem path is used.
    """

    cleanlevel = 0
    """The active clean *level* of this directory."""

    def __init__(self, parent=None, name=None, template='%s_dir%d'):
        if not name:
            name = self.__class__.__name__

        if parent is None:
            self._tempdir = TemporaryDirectory(prefix='%s.' % (name,) if name else None)
            path = Path(self._tempdir.name)
        else:
            head = Path(str(parent)).resolve()
            if re.search(r'(?<!%)%d', template):
                for num in itertools.count(1):
                    path = head / (template % (name, num))
                    if not path.exists():
                        break
            else:
                path = head / (template % name)
            path.mkdir(exist_ok=False)

        self.path = path
        self.template = template

    @property
    def name(self):
        """The name of this directory."""
        return self.path.name

    def def_cleanlevel(self, level, patterns, rm_dirs=False):
        """Define a clean level.

        Args:
            level: The clean level (positive integer only). 0 ought to be reserved as the "no-op".
            patterns: List of path-globbing patterns to target for deletion.
            rm_dirs: If True, will also delete non-empty directories matching 'patterns'.
        """
        nglobs = len(self.cleanlevels)
        if nglobs <= level:
            self._cleanlevels += [list() for _ in range(1 + nglobs - level)]
        self._cleanlevels[level] = {'glob': list(patterns), 'rm_dirs': bool(rm_dirs)}

    @property
    def cleanlevels(self):
        """The active cleanlevel *definitions* of this directory."""
        try:
            levels = self._cleanlevels
        except AttributeError:
            levels = self._cleanlevels = [[]]
        return levels

    def cleanup(self, level=None):
        """Delete files/dirs up to clean level (is run after completion).

        Args:
            level: The clean level to target. If None, (class) default clean level is used.
        """
        if level is None:
            level = self.cleanlevel
        levels = self.cleanlevels[:(1+level)]
        for child in self.path.iterdir():
            clean = dict()
            for level in levels:
                if not level:
                    continue
                if any(child.match(glob) for glob in level['glob']):
                    clean = level
                    break
            if not clean:
                continue

            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir() and clean['rm_dirs']:
                for rchild in child.iterdir():
                    rchild.unlink()
                try:
                    rchild.rmdir()
                except OSError:
                    pass

    def __repr__(self):
        args = ['%r' % str(self.path.parent), '%r' % str(self.name)]
        if self.template != '%s_dir%d':
            args += ['%r' % self.template]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(args))

    def __str__(self):
        return str(self.path)

    def __del__(self):
        self.cleanup()
