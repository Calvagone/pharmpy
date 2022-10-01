import os
from os.path import normpath, relpath
from pathlib import Path


def path_relative_to(root: Path, path: Path) -> Path:
    return Path(normpath(relpath(str(path), start=str(root))))


def path_absolute(path: Path) -> Path:
    # NOTE strict=True would check for the existence of the path.
    path = path.resolve(strict=False)

    if os.name == 'nt' and not path.is_absolute():
        # NOTE This seems needed because of
        # https://bugs.python.org/issue38671
        path = Path.cwd() / path

    # NOTE We always return an absolute path
    assert path.is_absolute()
    return path
