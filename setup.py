import os

from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(HERE, 'README.md')) as f:
    README = f.read()

setup(
    name='viahtml',
    version='1.0',
    description='Hypothesis HTML Proxy Application',
    long_description=README,
    url='https://github.com/hypothesis/viahtml',
    packages=find_packages(),
    include_package_data=True,
)
