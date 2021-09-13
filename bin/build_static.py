"""Copy all required static content out of `pywb` so NGINX can serve it."""
import os
import os.path
from shutil import copyfile, rmtree

import importlib_resources

# All the pywb resources we know we need
MANIFEST = (
    "autoFetchWorker.js",
    "default_banner.js",
    "flowplayer/toolbox.flashembed.js",
    "js/bootstrap.min.js",
    "js/jquery-latest.min.js",
    "js/url-polyfill.min.js",
    "query.js",
    "queryWorker.js",
    "search.js",
    "transclusions.js",
    "vidrw.js",
    "wb_frame.js",
    "wombat.js",
    "wombatProxyMode.js",
    "wombatWorkers.js",
)


def _copy(source_file, target_file):
    print(f"{source_file} >>> {target_file}")

    dir_name = os.path.dirname(target_file)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    copyfile(source_file, target_file)


def _create_static(source, target):
    if os.path.exists(target):
        print(f"Removing old static directory: {target}")
        rmtree(target)

    print(f"Copying `pywb` static content: {source}")
    for path in MANIFEST:
        source_file, target_file = os.path.join(source, path), os.path.join(
            target, path
        )
        _copy(source_file, target_file)

    print(f"Created: {target}")


if __name__ == "__main__":
    bin_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(bin_dir, "../static/static/pywb"))

    _create_static(
        source=importlib_resources.files("pywb") / "static",
        target=root_dir,
    )
