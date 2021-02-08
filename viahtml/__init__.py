"""Setup environment before loading app."""

import ctypes.util
import sys
from ctypes import CDLL


def patch_ctypes_on_macos_11():  # pragma: no cover
    """Work around a problem loading pywb under macOS 11.

    pywb has a dependency on an old version of fakeredis which fails to load
    when using Python <= 3.8 under macOS 11.  This function patches `ctypes.util.find_library`
    to work around the issue.

    See https://github.com/hypothesis/viahtml/issues/55.
    """

    if sys.platform != "darwin":
        return

    def _find_library_patched(name):
        path = f"lib{name}.dylib"
        try:
            # In macOS 11, some system libraries don't exist on disk. Instead you test
            # the validity of a library path by trying to load it.
            # See https://bugs.python.org/issue41179.
            CDLL(path)
        except OSError:
            # Fall back to the un-patched version.
            path = ctypes.util.find_library(name)
        return path

    ctypes.util.find_library = _find_library_patched


# Apply ctypes patch before pywb is imported.
patch_ctypes_on_macos_11()
