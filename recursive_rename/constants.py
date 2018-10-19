"""
Some of these are here for shorthand, but they are mainly here as
a reminder to me of what types of folders are expected to be where.
"""
from os.path import join, splitext, dirname, basename
from reclaimer.meta.class_repair import tag_cls_int_to_fcc, tag_cls_int_to_ext

INF = float('inf')
MAX_TAG_NAME_LEN = 243


# directories inside the root_dir
camera_dir     = "camera\\"
characters_dir = "characters\\"
cinematics_dir = "cinematics\\"
devices_dir    = "devices\\"
decals_dir     = "decals\\"
dialog_dir     = "dialog\\"
effects_dir    = "effects\\"
garbage_dir    = "garbage\\"
globals_dir    = "globals\\"
item_coll_dir  = "item collections\\"
levels_dir     = "levels\\"
powerups_dir   = "powerups\\"
rasterizer_dir = "rasterizer\\"
scenery_dir    = "scenery\\"
sky_dir        = "sky\\"
sound_dir      = "sound\\"
ui_dir         = "ui\\"
vehicles_dir   = "vehicles\\"
weapons_dir    = "weapons\\"
weather_dir    = "weather\\"


# general purpose directories used in MANY things
shaders_dir = "shaders\\"
bitmaps_dir = "bitmaps\\"
sounds_dir  = "sounds\\"
shared_dir  = "shared\\"  # for anything shared between tags


# directories inside the levels directory
level_bitmaps_dir = bitmaps_dir
level_decals_dir  = decals_dir
level_devices_dir = devices_dir
level_music_dir   = "music\\"
level_scenery_dir = scenery_dir
level_shaders_dir = shaders_dir
level_item_coll_dir = item_coll_dir
level_weather_dir = weather_dir

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
