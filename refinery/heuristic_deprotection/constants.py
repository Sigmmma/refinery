#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from refinery.constants import INF, MAX_TAG_NAME_LEN, ACTIVE_INDEX,\
     MAP_TYPE_ANY, MAP_TYPE_REGULAR, MAP_TYPE_RESOURCE, BAD_CLASSES,\
     INVALID, UNPRINTABLE
"""
Some of these are here for shorthand, but they are mainly here as
a reminder to me of what types of folders are expected to be where.
"""
VERY_HIGH_PRIORITY = 10.0
VEHICLE_WEAP_PRIORITY = 5.0
HIGH_PRIORITY = 4.0
UNIT_WEAPON_PRIORITY = 3.0
SCNR_BSPS_PRIORITY = 2.5
MEDIUM_HIGH_PRIORITY = 2.0
MEDIUM_PRIORITY = 1.5
DEFAULT_PRIORITY = 1.0
LOW_PRIORITY = 0.5


INVALID_MODEL_NAMES = frozenset(
    ("", "base", "unnamed", "blur", "unnamed base",
     "def", "default", "damaged"))


# directories inside the root_dir
camera_dir       = "camera\\"
characters_dir   = "characters\\"
cinematics_dir   = "cinematics\\"
devices_dir      = "devices\\"
decals_dir       = "decals\\"
dialog_dir       = "dialog\\"
effects_dir      = "effects\\"
garbage_dir      = "garbage\\"
globals_dir      = "globals\\"
item_coll_dir    = "item collections\\"
levels_dir       = "levels\\"
powerups_dir     = "powerups\\"
rasterizer_dir   = "rasterizer\\"
scenery_dir      = "scenery\\"
sky_dir          = "sky\\"
sound_dir        = "sound\\"
placeholders_dir = "placeholders\\"
sfx_emitters_dir = "sfx emitters\\"
ui_dir           = "ui\\"
vehicles_dir     = "vehicles\\"
weapons_dir      = "weapons\\"
weather_dir      = "weather\\"


# general purpose directories used in MANY things
shaders_dir = "shaders\\"
bitmaps_dir = "bitmaps\\"
sounds_dir  = "sounds\\"
shared_dir  = "shared\\"  # for anything shared between tags

machines_dir       = devices_dir + "machines\\"
controls_dir       = devices_dir + "controls\\"
light_fixtures_dir = devices_dir + "light fixtures\\"

projectiles_dir = weapons_dir + "projectiles\\"

# directories inside ui/hud directory
hud_bitmaps_dir = bitmaps_dir

# directories inside ui/shell directory
shell_bitmaps_dir = bitmaps_dir

# directories inside the weapon directory
weap_fp_dir = "fp\\"


# directories inside "object" directories(weapon, vehicle, biped, scenery, etc)
obje_shaders_dir = shaders_dir
obje_effects_dir = effects_dir
obje_bitmaps_dir = bitmaps_dir
obje_actor_dir   = "actors\\"  # directory for actors and their variants.
#                            insert the actors name as the directory name.


# directories inside the cinematics directory
cinematic_anims_dir   = cinematics_dir + "animations\\"
cinematic_effects_dir = cinematics_dir + effects_dir
cinematic_scenery_dir = cinematics_dir + scenery_dir


# directories inside the effects directory
effect_contrails_dir   = effects_dir + "contrails\\"
effect_decals_dir      = effects_dir + "decals\\"
effect_d_objects_dir   = effects_dir + "detail_objects\\"
effect_lens_flares_dir = effects_dir + "lens flares\\"
effect_lights_dir      = effects_dir + "lights\\"
effect_p_systems_dir   = effects_dir + "particle systems\\"
effect_particles_dir   = effects_dir + "particles\\"
effect_physics_dir     = effects_dir + "point physics\\"
effect_vehicle_dir     = effects_dir + "vehicle effects\\"
effect_zmaps_dir       = effects_dir + "zmaps\\"


# directories inside the decals directory.
# each of these will have a "bitmaps" directory inside it
decal_blood_dir   = effect_decals_dir + "blood splats\\"
decal_bullets_dir = effect_decals_dir + "bullet holes\\"
decal_vehicle_dir = effect_decals_dir + "vehicle marks\\"


# directories inside the item collections directory
itmc_powerups = item_coll_dir + powerups_dir
itmc_weapons  = item_coll_dir + weapons_dir


# directories inside sound directory
snd_sfx_dir       = sound_dir + "sfx\\"
snd_dialog_dir    = sound_dir + "dialog\\"
snd_music_dir     = sound_dir + "music\\"
snd_sound_env_dir = sound_dir + "sound environments\\"


# directories inside sound\sfx directory
sfx_ambience_dir = snd_sfx_dir + "ambience\\"
sfx_impulse_dir  = snd_sfx_dir + "impulse\\"
sfx_ui_dir       = snd_sfx_dir + "ui\\"
sfx_vehicles_dir = snd_sfx_dir + vehicles_dir
sfx_weapons_dir  = snd_sfx_dir + weapons_dir


# directories inside sound\sfx\impluse directory
imp_animations_dir = sfx_impulse_dir + "animations\\"
imp_bodyfalls_dir  = sfx_impulse_dir + "bodyfalls\\"
imp_doors_dir      = sfx_impulse_dir + "doors\\"
imp_footsteps_dir  = sfx_impulse_dir + "footsteps\\"
imp_glass_dir      = sfx_impulse_dir + "glass\\"
imp_materials_dir  = sfx_impulse_dir + "material_effects\\"
imp_panel_dir      = sfx_impulse_dir + "panel\\"
imp_casings_dir    = sfx_impulse_dir + "shellcasings\\"
imp_weap_drops_dir = sfx_impulse_dir + "weapon_drops\\"


# directories inside ui directory
ui_devc_def_dir = ui_dir + "device_defaults\\"
ui_hud_dir      = ui_dir + "hud\\"
ui_shell_dir    = ui_dir + "shell\\"


# directories inside sky directory
sky_shaders_dir = shaders_dir
sky_bitmaps_dir = bitmaps_dir
