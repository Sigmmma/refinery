#!/usr/bin/env python
#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from os.path import dirname, join
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

curr_dir = dirname(__file__)

import refinery

try:
    long_desc = open(join(curr_dir, "README.md")).read()
except Exception:
    long_desc = 'Could not read long description from readme.'

setup(
    name='refinery',
    description='A map extractor for games built with the Blam engine',
    long_description=long_desc,
    long_description_content_type='text/markdown',
    version='%s.%s.%s' % refinery.__version__,
    url=refinery.__website__,
    author=refinery.__author__,
    author_email='MosesBobadilla@gmail.com',
    license='GPLv3',
    packages=[
        'refinery',
        'refinery.defs',
        'refinery.heuristic_deprotection',
        'refinery.repl',
        'refinery.tag_index',
        'refinery.widgets',
        'refinery.windows',
        ],
    package_data={
        '': ['*.txt', '*.md', '*.rst', '*.ico', '*.png', 'msg.dat']
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
