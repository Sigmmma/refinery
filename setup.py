#!/usr/bin/env python
#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import refinery

long_desc = ""
try:
    long_desc = open("README.MD").read()
except Exception:
    print("Couldn't read readme.")

setup(
    name='refinery',
    description='A map extractor for games built with the Blam engine',
    long_description=long_desc,
    long_description_content_type='text/markdown',
    version='%s.%s.%s' % refinery.__version__,
    url=refinery.__website__,
    project_urls={
        #"Documentation": <Need a string entry here>,
        "Source": refinery.__website__,
        "Funding": "https://liberapay.com/MEK/",
    },
    author=refinery.__author__,
    author_email='MoeMakesStuff@gmail.com',
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
        'refinery': [
            'styles/*.*', '*.[tT][xX][tT]', '*.MD', '*.pyw', '*.ico', '*.png',
            ]
        },
    platforms=['POSIX', 'Windows'],
    keywords=["refinery", "halo", "extraction"],
    install_requires=['mozzarilla', 'supyr_struct', 'reclaimer', 'binilla'],
    requires=['mozzarilla', 'supyr_struct', 'reclaimer', 'binilla'],
    provides=['refinery'],
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        ],
    zip_safe=False,
    )
