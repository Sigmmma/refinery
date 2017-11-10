#!/usr/bin/env python
from os.path import dirname, join
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

curr_dir = dirname(__file__)

#               YYYY.MM.DD
release_date = "2017.11.09"  # DONT FORGET TO UPDATE THE VERSION IN main.py
version = (1, 5, 3)

try:
    try:
        long_desc = open(join(curr_dir, "readme.rst")).read()
    except Exception:
        long_desc = open(join(curr_dir, "readme.md")).read()
except Exception:
    long_desc = 'Could not read long description from readme.'

setup(
    name='refinery',
    description='A map extractor for games built with the Blam engine',
    long_description=long_desc,
    version='%s.%s.%s' % version,
    url='https://bitbucket.org/Moses_of_Egypt/refinery',
    author='Devin Bobadilla',
    author_email='MosesBobadilla@gmail.com',
    license='MIT',
    packages=[
        'refinery',
        'refinery.defs',
        'refinery.recursive_rename',
        ],
    package_data={
        '': ['*.txt', '*.md', '*.rst'],
        },
    platforms=['POSIX', 'Windows'],
    keywords='refinery, halo',
    install_requires=['mozzarilla', 'supyr_struct', 'reclaimer', 'binilla'],
    requires=['mozzarilla', 'supyr_struct', 'reclaimer', 'binilla'],
    provides=['refinery'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        ],
    zip_safe=False,
    )
