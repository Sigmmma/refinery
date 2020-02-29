#!/usr/bin/env python3
#
# This file is part of Refinery.
#
# For authors and copyright check AUTHORS.TXT
#
# Refinery is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#


# Legacy run module, used by older MEKs

from .__main__ import main
if main():
    # Input was how the terminal window was kept open on Windows to show the
    # error.
    input()
