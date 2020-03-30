#
# This file is part of Refinery.
#
# For authors and copyright check AUTHORS.TXT
#
# Refinery is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from mozzarilla.editor_constants import *
from pathlib import Path

REFINERYLIB_DIR = Path(__file__).parent

REFINERY_ICON_PATH = Path(REFINERYLIB_DIR, "refinery.ico")
if not REFINERY_ICON_PATH.is_file():
    REFINERY_ICON_PATH = ""

REFINERY_BITMAP_PATH = Path(REFINERYLIB_DIR, "refinery.png")
if not REFINERY_BITMAP_PATH.is_file():
    REFINERY_BITMAP_PATH = ""


# not for export
del Path
