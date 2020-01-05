#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
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

H1_TAG_SUPERCLASSES = FrozenDict(
    shader_environment=("shader", "NONE"),
    shader_model=("shader", "NONE"),
    shader_transparent_generic=("shader", "NONE"),
    shader_transparent_chicago=("shader", "NONE"),
    shader_transparent_chicago_extended=("shader", "NONE"),
    shader_plasma=("shader", "NONE"),
    shader_meter=("shader", "NONE"),
    shader_water=("shader", "NONE"),
    shader_glass=("shader", "NONE"),

    biped=("unit", "object"),
    vehicle=("unit", "object"),

    weapon=("item", "object"),
    equipment=("item", "object"),
    garbage=("item", "object"),

    device_machine=("device", "object"),
    device_control=("device", "object"),
    device_light_fixture=("device", "object"),

    projectile=("object", "NONE"),
    scenery=("object", "NONE"),
    placeholder=("object", "NONE"),
    sound_scenery=("object", "NONE"),

    effect_postprocess_generic=("effect_postprocess", "NONE"),
    shader_postprocess_generic=("shader_postprocess", "NONE"),
    )

del FrozenDict
