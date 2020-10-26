"""Copy all required static content out of `pywb` so NGINX can serve it."""
import os
import os.path
from shutil import copyfile, rmtree

from pkg_resources import resource_filename

# All the pywb resources we know we need
MANIFEST = ("wombat.js",)


def _create_static(source, target):
    if os.path.exists(target):
        print(f"Removing old static directory: {target}")
        rmtree(target)

    os.makedirs(target)

    print(f"Copying `pywb` static content: {source}")
    for path in MANIFEST:
        source_file, target_file = os.path.join(source, path), os.path.join(
            target, path
        )
        print(f"{source_file} >>> {target_file}")
        copyfile(source_file, target_file)

    print(f"Created: {target}")


if __name__ == "__main__":
    # pylint: disable=invalid-name
    bin_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(bin_dir, "../static/static/pywb"))

    _create_static(
        source=resource_filename("pywb", "static"),
        target=root_dir,
    )
