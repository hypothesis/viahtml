"""Copy all required static content out of `pywb` so NGINX can serve it."""
import os
import os.path
from shutil import copytree, rmtree

import importlib_resources


def _create_static(source, target):
    if os.path.exists(target):
        print(f"Removing old static directory: {target}")
        rmtree(target)

    print(f"Copying `pywb` static content: {source} to {target}")
    copytree(source, target)


if __name__ == "__main__":
    bin_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(bin_dir, "../static/static/pywb"))

    _create_static(
        source=importlib_resources.files("pywb") / "static",
        target=root_dir,
    )
