#
# This file is part of Refinery.
#
# For authors and copyright check AUTHORS.TXT
#
# Refinery is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from supyr_struct.defs.frozen_dict import FrozenDict
from supyr_struct.defs.constants import INVALID, UNPRINTABLE

# max number of characters long a tag name can be before halo wont accept it
MAX_TAG_NAME_LEN = 243

INF = float('inf')

ACTIVE_INDEX = "<active>"
MAP_TYPE_ANY = "any"
MAP_TYPE_REGULAR = "regular"
MAP_TYPE_RESOURCE = "resource"

BAD_CLASSES = frozenset(
    (INVALID, "NONE",)
    )

H1_SHADER_TAG_CLASSES = frozenset((
    "shader_environment",
    "shader_model",
    "shader_transparent_generic",
    "shader_transparent_chicago",
    "shader_transparent_chicago_extended",
    "shader_plasma",
    "shader_meter",
    "shader_water",
    "shader_glass",
    ))
H1_UNIT_TAG_CLASSES = frozenset((
    "biped", "vehicle"
    ))
H1_ITEM_TAG_CLASSES = frozenset((
    "weapon", "equipment", "garbage"
    ))
H1_DEVICE_TAG_CLASSES = frozenset((
    "device_machine", "device_control", "device_light_fixture"
    ))
H1_OBJECT_TAG_CLASSES = frozenset((
    "projectile", "scenery", "placeholder", "sound_scenery"
    ))

H1_TAG_SUPERCLASSES = dict(
    effect_postprocess_generic=("effect_postprocess", "NONE"),
    shader_postprocess_generic=("shader_postprocess", "NONE"),
    **{cls: ("shader",  "NONE")     for cls in H1_SHADER_TAG_CLASSES},
    **{cls: ("object",  "NONE")     for cls in H1_OBJECT_TAG_CLASSES},
    )
    
H1_TAG_SUPERCLASSES.update({cls: ("unit",    "object")   for cls in H1_UNIT_TAG_CLASSES})
H1_TAG_SUPERCLASSES.update({cls: ("unit",    "object")   for cls in H1_ITEM_TAG_CLASSES})
H1_TAG_SUPERCLASSES.update({cls: ("unit",    "object")   for cls in H1_DEVICE_TAG_CLASSES})

H1_TAG_SUPERCLASSES = FrozenDict(H1_TAG_SUPERCLASSES)

del FrozenDict
