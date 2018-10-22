from reclaimer.enums import materials_list, material_effect_types
from refinery.recursive_rename.constants import *
from traceback import format_exc

VERY_HIGH_PRIORITY = 10.0
VEHICLE_WEAP_PRIORITY = 5.0
HIGH_PRIORITY = 4.0
SCNR_BSPS_PRIORITY = 2.5
MEDIUM_HIGH_PRIORITY = 2.0
MEDIUM_PRIORITY = 1.5
DEFAULT_PRIORITY = 1.0
LOW_PRIORITY = 0.5



# TODO:
#   Implement OSv4 unit attribute renaming
#   Implement these rename functions:
#       actor_variant_transform_collection = rename_avtc,
#       actor_variant_transform_in = rename_atvi,
#       actor_variant_transform_out = rename_atvo,
#       effect_postprocess_collection = rename_efpc,
#       effect_postprocess_generic = rename_efpg,
#       shader_postprocess_generic = rename_shpg,
#       text_value_pair_definition = rename_sily,
#       multilingual_unicode_string_list = rename_unic,



def sanitize_path(name):
    for c in ':*?"<>|':
        name = name.replace(c, '')
    return name.lower().replace('/', '\\').strip()


def sanitize_name(name):
    return sanitize_path(name).replace("~", "").\
           replace("\\", " ").lower().strip()


def get_tag_id(tag_ref):
    if tag_ref.id[0] == 0xFFFF and tag_ref.id[1] == 0xFFFF:
        return None
    return tag_ref.id[0]


def join_names(names, max_len=100):
    if len(names) == 1:
        return names[0]
    elif not names:
        return ""

    name = " & ".join(names)
    if len(name) > max_len:
        name = " & ".join(name[: max_len + 2].split(" & ")[: -1]).rstrip(" &")
    return name


def get_model_name(halo_map, tag_id, model_name=""):
    meta = halo_map.get_meta(tag_id)
    if not meta:
        return model_name

    names = set()
    for region in meta.regions.STEPTREE:
        for perm in region.permutations.STEPTREE:
            name = sanitize_name(perm.name).strip(" _")
            while name and name[-1] in "0123456789":
                name = name[: -1].strip(" _")
            names.add(name)

    if not names or len(names) > 1:
        return model_name

    for name in names:
        if name not in ("base", "blur", "def", "default", "damaged"):
            return name

    return model_name


def get_sound_sub_dir_and_name(snd_meta, sub_dir="", snd_name=""):
    if not snd_meta:
        return sub_dir, snd_name

    snd_class = snd_meta.sound_class.enum_name
    if "dialog" in snd_class:
        sub_dir = snd_dialog_dir
    elif snd_class == "device_door":
        sub_dir = imp_doors_dir
    elif snd_class == "unit_footsteps":
        sub_dir = imp_footsteps_dir
    elif snd_class == "vehicle_collision":
        sub_dir = sfx_vehicles_dir + "collision\\"
    elif snd_class == "vehicle_engine":
        sub_dir = sfx_vehicles_dir + "engine\\"
    elif "projectile" in snd_class:
        sub_dir = sfx_impulse_dir + snd_class.replace("_", " ") + "\\"
    elif "weapon" in snd_class:
        sub_dir = sfx_weapons_dir + snd_class.strip("weapon_") + "\\"
    elif "ambient" in snd_class:
        sub_dir = sfx_ambience_dir
    elif "device" in snd_class:
        sub_dir = sfx_ambience_dir + devices_dir
    elif snd_class == "music":
        sub_dir = snd_music_dir
    else:
        sub_dir = cinematics_dir + snd_sfx_dir

    for pr in snd_meta.pitch_ranges.STEPTREE:
        for perm in pr.permutations.STEPTREE:
            perm_name = sanitize_name(perm.name)
            while perm_name and perm_name[-1] in "0123456789":
                perm_name = perm_name[: -1].strip()

            if perm_name:
                snd_name = perm.name
                break

    return sub_dir, snd_name


def recursive_rename(tag_id, halo_map, tag_path_handler,
                     root_dir="", sub_dir="", name="", **kwargs):
    # create a copy of this set for each recursion level to prevent
    # infinite recursion, but NOT prevent revisiting the
    seen = kwargs.setdefault("seen", set())
    if tag_id is None or tag_id > len(halo_map.tag_index.tag_index):
        return
    elif tag_id in seen:
        return
    seen.add(tag_id)

    rename_func = recursive_rename_functions.get(
        halo_map.tag_index.tag_index[tag_id].class_1.enum_name)
    if rename_func:
        try:
            rename_func(tag_id, halo_map, tag_path_handler,
                        root_dir, sub_dir, name, **kwargs)
        except Exception:
            print(format_exc())
    else:
        tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                                  kwargs.get("priority", LOW_PRIORITY),
                                  kwargs.get("override"))
    # remove the tag_id so this tag can be revisited by higher up references
    seen.remove(tag_id)


def rename_scnr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = levels_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = sanitize_name(halo_map.map_header.map_name)

    level_dir = sub_dir + '%s\\' % name

    tag_path_handler.set_path(tag_id, root_dir + level_dir + name,
                              INF, kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # rename the open sauce stuff
    try:
        recursive_rename(
            get_tag_id(meta.project_yellow_definitions),
            priority=INF, name=name, sub_dir=sub_dir + globals_dir, **kwargs)
    except AttributeError:
        pass

    # rename the references at the bottom of the scenario tag
    tag_path_handler.set_path(get_tag_id(meta.custom_object_names),
                              sub_dir + "object_names",
                              INF, kwargs.get("override"))

    tag_path_handler.set_path(get_tag_id(meta.ingame_help_text),
                              sub_dir + "help_text",
                              INF, kwargs.get("override"))

    tag_path_handler.set_path(get_tag_id(meta.hud_messages),
                              sub_dir + "hud_messages",
                              INF, kwargs.get("override"))

    # rename sky references
    for b in meta.skies.STEPTREE:
        recursive_rename(get_tag_id(b.sky), sub_dir=sky_dir + name + "\\",
                         name=name + " sky", **kwargs)

    devices_dir = sub_dir + level_devices_dir
    palette_renames = (
        ("machines_palette", devices_dir + "machines\\"),
        ("controls_palette", devices_dir + "controls\\"),
        ("light_fixtures_palette", devices_dir + "light fixtures\\"),
        ("sound_sceneries_palette", sub_dir + 'sfx emitters\\'),
        ("sceneries_palette", sub_dir + scenery_dir),
        ("actors_palette", characters_dir),
        ("bipeds_palette", characters_dir),
        ("vehicles_palette", vehicles_dir),
        ("equipments_palette", powerups_dir),
        ("weapons_palette", weapons_dir)
        )

    # rename player starting weapon references
    for profile in meta.player_starting_profiles.STEPTREE:
        recursive_rename(get_tag_id(profile.primary_weapon),
                         sub_dir=weapons_dir, **kwargs)
        recursive_rename(get_tag_id(profile.secondary_weapon),
                         sub_dir=weapons_dir, **kwargs)

    item_coll_dir = sub_dir + level_item_coll_dir

    # starting equipment
    i = 0
    for b in meta.starting_equipments.STEPTREE:
        j = 0
        profile_name = sanitize_name(b.name)
        if not profile_name:
            profile_name = "start equipment"

        for i in range(1, 7):
            recursive_rename(
                get_tag_id(b['item collection %s' % i]),
                sub_dir=item_coll_dir, name=profile_name,
                priority=MEDIUM_PRIORITY, **kwargs)
            j += 1
        i += 1

    # rename detail objects palette
    for b in meta.detail_object_collection_palette.STEPTREE:
        recursive_rename(
            get_tag_id(b.name), sub_dir=sub_dir + "detail objects\\",
            priority=MEDIUM_PRIORITY, **kwargs)

    # rename decal palette references
    for swatch in meta.decals_palette.STEPTREE:
        recursive_rename(get_tag_id(swatch.name), priority=MEDIUM_PRIORITY, 
                         sub_dir=sub_dir + "decals\\", **kwargs)

    # rename palette references
    for b_name, pal_sub_dir in palette_renames:
        for swatch in meta[b_name].STEPTREE:
            recursive_rename(get_tag_id(swatch.name), priority=MEDIUM_PRIORITY, 
                             sub_dir=pal_sub_dir, **kwargs)

    # netgame flags
    for b in meta.netgame_flags.STEPTREE:
        recursive_rename(
            get_tag_id(b.weapon_group), sub_dir=item_coll_dir,
            name="ng flag", priority=MEDIUM_PRIORITY, **kwargs)

    # netgame equipment
    for b in meta.netgame_equipments.STEPTREE:
        ng_name = ""
        ng_coll_meta = halo_map.get_meta(get_tag_id(b.item_collection))
        if ng_coll_meta:
            item_names = []
            for item in ng_coll_meta.item_permutations.STEPTREE:
                item_name = tag_path_handler.get_basename(get_tag_id(item.item))
                if item_name:
                    item_names.append(item_name)

            ng_name = join_names(sorted(item_names), 96)

        if not ng_name:
            ng_name = "ng equipment"

        recursive_rename(
            get_tag_id(b.item_collection), sub_dir=item_coll_dir,
            name=ng_name, priority=MEDIUM_PRIORITY, **kwargs)

    # rename animation references
    for b in meta.ai_animation_references.STEPTREE:
        anim_name = sanitize_name(b.animation_name)
        if not anim_name:
            anim_name = "ai anim"

        recursive_rename(get_tag_id(b.animation_graph), name=anim_name,
                         sub_dir=sub_dir + cinematics_dir + "animations\\",
                         priority=LOW_PRIORITY, **kwargs)

    # rename bsp references
    for b in meta.structure_bsps.STEPTREE:
        recursive_rename(get_tag_id(b.structure_bsp),
                         priority=SCNR_BSPS_PRIORITY,
                         sub_dir=sub_dir, name=name, **kwargs)

    # rename bsp modifiers
    bsp_modifiers = getattr(getattr(meta, "bsp_modifiers", ()), "STEPTREE", ())
    for modifier in bsp_modifiers:
        try:
            bsp_name = tag_path_handler.get_basename(
                get_tag_id(
                    meta.structure_bsps.STEPTREE[b.bsp_index].structure_bsp))
        except Exception:
            bsp_name = ""

        lightmap_sub_dir = sub_dir + (bsp_name + " lightmaps\\").strip()
        for b in modifier.lightmap_sets.STEPTREE:
            recursive_rename(
                get_tag_id(b.std_lightmap), priority=VERY_HIGH_PRIORITY,
                sub_dir=lightmap_sub_dir, name=b.name + " std", **kwargs)
            recursive_rename(
                get_tag_id(b.dir_lightmap_1), priority=VERY_HIGH_PRIORITY,
                sub_dir=lightmap_sub_dir, name=b.name + " dlm1", **kwargs)
            recursive_rename(
                get_tag_id(b.dir_lightmap_2), priority=VERY_HIGH_PRIORITY,
                sub_dir=lightmap_sub_dir, name=b.name + " dlm2", **kwargs)
            recursive_rename(
                get_tag_id(b.dir_lightmap_3), priority=VERY_HIGH_PRIORITY,
                sub_dir=lightmap_sub_dir, name=b.name + " dlm3", **kwargs)

        sky_set_dir = sub_dir + (bsp_name + " sky sets\\").strip()
        for sky_set in modifier.sky_sets.STEPTREE:
            for b in sky_set.skies.STEPTREE:
                recursive_rename(
                    get_tag_id(b.sky), sub_dir=sky_set_dir,
                    name=sky_set.name, **kwargs)

    # rename ai conversation sounds
    i = 0
    conv_dir = sub_dir + "ai convos\\"
    for b in meta.ai_conversations.STEPTREE:
        j = 0
        conv_name = sanitize_name(b.name)
        if not conv_name:
            conv_name = "conv %s " % i

        for b in b.lines.STEPTREE:
            line = conv_name + "line %s " % j
            for k in range(1, 7):
                recursive_rename(
                    get_tag_id(b['variant_%s' % k]), sub_dir=conv_dir,
                    priority=MEDIUM_PRIORITY, name=line, **kwargs)
            j += 1
        i += 1

    # rename tag references
    for b in meta.references.STEPTREE:
        kwargs['priority'] = LOW_PRIORITY
        sub_id = get_tag_id(b.reference)
        tag_cls = b.reference.tag_class.enum_name
        tag_name = "protected %s" % sub_id

        if tag_cls == "model_animations":
            ref_sub_dir = cinematic_anims_dir
        elif tag_cls == "effect":
            ref_sub_dir = cinematic_effects_dir
        elif tag_cls == "biped":
            ref_sub_dir = cinematics_dir + "bipeds\\"
        elif tag_cls == "vehicle":
            ref_sub_dir = cinematics_dir + vehicles_dir
        elif tag_cls == "weapon":
            ref_sub_dir = cinematics_dir + weapons_dir
        elif tag_cls == "projectile":
            ref_sub_dir = cinematics_dir + "projectiles\\"
        elif tag_cls == "garbage":
            ref_sub_dir = cinematics_dir + garbage_dir
        elif tag_cls == "equipment":
            ref_sub_dir = cinematics_dir + powerups_dir
        elif tag_cls == "scenery":
            ref_sub_dir = cinematics_dir + scenery_dir
        elif tag_cls == "sound_scenery":
            ref_sub_dir = cinematics_dir + "sfx emitters\\"
        elif "device" in tag_cls:
            ref_sub_dir = (cinematics_dir + (
                tag_cls.lstrip("device_").replace("_", " ") + "s\\"))
        elif tag_cls == "sound_looping":
            ref_sub_dir = sub_dir + "music\\"
        elif tag_cls == "sound":
            snd_meta = halo_map.get_meta(sub_id)
            if snd_meta is None:
                continue
            new_ref_sub_dir, new_tag_name = get_sound_sub_dir_and_name(
                snd_meta, ref_sub_dir, tag_name)
            if tag_name != new_tag_name:
                kwargs['priority'] = DEFAULT_PRIORITY
            ref_sub_dir, tag_name = new_ref_sub_dir, new_tag_name

        else:
            ref_sub_dir = sub_dir + "referenced tags\\"

        recursive_rename(sub_id, sub_dir=ref_sub_dir, **kwargs)


def rename_matg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = globals_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  priority=MEDIUM_PRIORITY,
                  tag_path_handler=tag_path_handler)
    kwargs_no_priority = dict(kwargs)
    kwargs_no_priority.pop('priority')

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'globals'

    # rename this globals tag
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    for i in range(len(meta.sounds.STEPTREE)):
        water_name = {0:"enter_water", 1:"exit_water"}.get(i, "unknown")
        recursive_rename(
            get_tag_id(meta.sounds.STEPTREE[i].sound),
            name=water_name, priority=INF,
            sub_dir="sound\\sfx\\impulse\\coolant\\", **kwargs_no_priority)

    for b in meta.cameras.STEPTREE:
        recursive_rename(get_tag_id(b.camera), sub_dir=sub_dir, priority=INF,
                         name="default unit camera track", **kwargs_no_priority)

    i = 0
    for b in meta.grenades.STEPTREE:
        g_dir = weapons_dir + "grenade %s\\" % i
        g_name = "grenade %s" % i

        eqip_tag_id = get_tag_id(b.equipment)
        g_priority = 1.5
        recursive_rename(eqip_tag_id, sub_dir=g_dir, name=g_name,
                         priority=g_priority, **kwargs_no_priority)
        if eqip_tag_id is not None:
            g_dir = tag_path_handler.get_sub_dir(eqip_tag_id, root_dir)
            g_name = tag_path_handler.get_basename(eqip_tag_id)
            g_priority = tag_path_handler.get_priority(eqip_tag_id)

        recursive_rename(get_tag_id(b.throwing_effect), sub_dir=g_dir,
                         name=g_name + " throw", priority=g_priority,
                         **kwargs_no_priority)
        recursive_rename(get_tag_id(b.hud_interface), sub_dir=g_dir,
                         name=g_name + " hud", priority=g_priority,
                         **kwargs_no_priority)
        recursive_rename(get_tag_id(b.projectile), sub_dir=g_dir,
                         name=g_name + " projectile", priority=g_priority,
                         **kwargs_no_priority)
        i += 1

    rast_kwargs = dict(kwargs)
    exp_tex_kwargs = dict(kwargs)
    rast_kwargs.update(priority=INF, sub_dir=rasterizer_dir)
    exp_tex_kwargs.update(priority=INF, sub_dir="levels\\a10\\bitmaps\\")
    for b in meta.rasterizer_datas.STEPTREE:
        func_tex = b.function_textures
        def_tex = b.default_textures
        exp_tex = b.experimental_textures
        vid_eff_tex = b.video_effect_textures

        recursive_rename(get_tag_id(func_tex.distance_attenuation),
                         name="distance attenuation", **rast_kwargs)
        recursive_rename(get_tag_id(func_tex.vector_normalization),
                         name="vector normalization", **rast_kwargs)
        recursive_rename(get_tag_id(func_tex.atmospheric_fog_density),
                         name="atmospheric fog density", **rast_kwargs)
        recursive_rename(get_tag_id(func_tex.planar_fog_density),
                         name="planar fog density", **rast_kwargs)
        recursive_rename(get_tag_id(func_tex.linear_corner_fade),
                         name="linear corner fade", **rast_kwargs)
        recursive_rename(get_tag_id(func_tex.active_camouflage_distortion),
                         name="active camouflage distortion", **rast_kwargs)
        recursive_rename(get_tag_id(func_tex.glow), name="glow", **rast_kwargs)

        recursive_rename(get_tag_id(def_tex.default_2d),
                         name="default 2d", **rast_kwargs)
        recursive_rename(get_tag_id(def_tex.default_3d),
                         name="default 3d", **rast_kwargs)
        recursive_rename(get_tag_id(def_tex.default_cubemap),
                         name="default cube map", **rast_kwargs)

        recursive_rename(get_tag_id(exp_tex.test0),
                         name="water_ff", **rast_kwargs)
        recursive_rename(get_tag_id(exp_tex.test1),
                         name="cryo glass", **exp_tex_kwargs)

        recursive_rename(get_tag_id(vid_eff_tex.video_scanline_map),
                         name="video mask", **rast_kwargs)
        recursive_rename(get_tag_id(vid_eff_tex.video_noise_map),
                         name="video noise", **rast_kwargs)

    old_tags_kwargs = dict(kwargs)
    ui_bitm_kwargs = dict(kwargs)
    old_tags_kwargs.update(priority=VERY_HIGH_PRIORITY,
                           sub_dir="old tags\\")
    ui_bitm_kwargs.update(priority=VERY_HIGH_PRIORITY,
                          sub_dir=ui_hud_dir + "bitmaps\\")
    for b in meta.interface_bitmaps.STEPTREE:
        recursive_rename(get_tag_id(b.font_system), sub_dir=ui_dir,
                         name="system font", **kwargs)
        recursive_rename(get_tag_id(b.font_terminal), sub_dir=ui_dir,
                         name="terminal font", **kwargs)

        recursive_rename(get_tag_id(b.hud_globals),
                         sub_dir=ui_hud_dir, name="default", **kwargs)
        recursive_rename(get_tag_id(b.hud_digits_definition),
                         sub_dir=ui_hud_dir, name="counter", **kwargs)

        recursive_rename(get_tag_id(b.screen_color_table),
                         name="internal screen", **old_tags_kwargs)
        recursive_rename(get_tag_id(b.hud_color_table),
                         name="internal hud", **old_tags_kwargs)
        recursive_rename(get_tag_id(b.editor_color_table),
                         name="internal editor", **old_tags_kwargs)
        recursive_rename(get_tag_id(b.dialog_color_table),
                         name="internal dialog", **old_tags_kwargs)
        recursive_rename(get_tag_id(b.localization),
                         name="internal string localization", **old_tags_kwargs)

        recursive_rename(get_tag_id(b.motion_sensor_sweep_bitmap),
                         name="hud_sweeper", **ui_bitm_kwargs)
        recursive_rename(get_tag_id(b.motion_sensor_sweep_bitmap_mask),
                         name="hud_sweeper_mask", **ui_bitm_kwargs)
        recursive_rename(get_tag_id(b.multiplayer_hud_bitmap),
                         name="hud_multiplayer", **ui_bitm_kwargs)
        recursive_rename(get_tag_id(b.motion_sensor_blip),
                         name="hud_sensor_blip", **ui_bitm_kwargs)
        recursive_rename(get_tag_id(b.interface_goo_map1),
                         name="hud_sensor_blip_custom", **ui_bitm_kwargs)
        recursive_rename(get_tag_id(b.interface_goo_map2),
                         name="hud_msg_icons_sm", **ui_bitm_kwargs)
        #recursive_rename(get_tag_id(b.interface_goo_map3),
        #                 sub_dir="characters\\jackal\\bitmaps\\",
        #                 name="shield noise", **kwargs)

    for b in meta.multiplayer_informations.STEPTREE:
        recursive_rename(get_tag_id(b.flag), name="flag",
                         sub_dir="weapons\\flag\\", **kwargs)
        recursive_rename(get_tag_id(b.ball), name="ball",
                         sub_dir="weapons\\ball\\", **kwargs)

        recursive_rename(get_tag_id(b.hill_shader), name="hilltop",
                         sub_dir="scenery\\hilltop\\shaders\\", **kwargs)
        recursive_rename(get_tag_id(b.flag_shader), name="flag_blue",
                         sub_dir="weapons\\flag\\shaders\\", **kwargs)

        recursive_rename(get_tag_id(b.unit), name="player_mp",
                         priority=VERY_HIGH_PRIORITY,
                         sub_dir="characters\\player_mp\\", **kwargs_no_priority)

    for b in meta.player_informations.STEPTREE:
        recursive_rename(get_tag_id(b.unit), name="player_sp",
                         priority=VERY_HIGH_PRIORITY,
                         sub_dir="characters\\player_sp\\", **kwargs_no_priority)
        recursive_rename(get_tag_id(b.coop_respawn_effect),
                         priority=VERY_HIGH_PRIORITY, sub_dir=effects_dir,
                         name="coop teleport", **kwargs_no_priority)

    for b in meta.first_person_interfaces.STEPTREE:
        recursive_rename(get_tag_id(b.first_person_hands),
                         sub_dir="characters\\player_sp\\fp\\", name="fp",
                         priority=VERY_HIGH_PRIORITY, **kwargs_no_priority)
        recursive_rename(get_tag_id(b.base_bitmap),
                         name="hud_health_base", **ui_bitm_kwargs)

        recursive_rename(get_tag_id(b.shield_meter), sub_dir=ui_hud_dir,
                         name="cyborg shield", **kwargs)
        recursive_rename(get_tag_id(b.body_meter), sub_dir=ui_hud_dir,
                         name="cyborg body", **kwargs)

        recursive_rename(get_tag_id(b.night_vision_toggle_on_effect),
                         sub_dir=sfx_weapons_dir, name="night_vision_on",
                         **kwargs)
        recursive_rename(get_tag_id(b.night_vision_toggle_off_effect),
                         sub_dir=sfx_weapons_dir, name="night_vision_off",
                         **kwargs)

    fall_kwargs = dict(kwargs)
    fall_kwargs.update(priority=VERY_HIGH_PRIORITY, sub_dir=sub_dir)
    for b in meta.falling_damages.STEPTREE:
        recursive_rename(get_tag_id(b.falling_damage),
                         name="falling", **fall_kwargs)
        recursive_rename(get_tag_id(b.distance_damage),
                         name="distance", **fall_kwargs)
        recursive_rename(get_tag_id(b.vehicle_environment_collision_damage),
                         name="vehicle_hit_environment", **fall_kwargs)
        recursive_rename(get_tag_id(b.vehicle_killed_unit_damage),
                         name="vehicle_killed_unit", **fall_kwargs)
        recursive_rename(get_tag_id(b.vehicle_collision_damage),
                         name="vehicle_collision", **fall_kwargs)
        recursive_rename(get_tag_id(b.flaming_death_damage),
                         name="flaming_death", **fall_kwargs)

    i = 0
    mats_kwargs = dict(kwargs)
    mats_kwargs["priority"] = VERY_HIGH_PRIORITY
    for b in meta.materials.STEPTREE:
        mat_name = "unknown" if i not in range(len(materials_list)) else materials_list[i]
        recursive_rename(get_tag_id(b.sound), name=mat_name,
                         sub_dir="sound\\sfx\\impulse\\", **mats_kwargs)
        recursive_rename(get_tag_id(b.melee_hit_sound), name=mat_name,
                         sub_dir="sound\\sfx\\impulse\\melee\\", **mats_kwargs)

        for particle_effect in b.particle_effects.STEPTREE:
            recursive_rename(get_tag_id(particle_effect.particle_type),
                             sub_dir="effects\\particles\\solid\\",
                             name="%s breakable" % mat_name, **mats_kwargs)
        i += 1


def rename_yelo(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = levels_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', INF)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'yelo'

    # rename this project_yellow tag
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # rename the yelo globals
    recursive_rename(get_tag_id(meta.yelo_globals),
                     sub_dir=sub_dir, name="yelo globals", **kwargs)

    # rename the globals override
    recursive_rename(get_tag_id(meta.globals_override),
                     sub_dir=sub_dir, name="globals", **kwargs)

    # rename the explicit references
    recursive_rename(get_tag_id(meta.scenario_explicit_references),
                     sub_dir=sub_dir, name="scenario references", **kwargs)

    # rename scripted ui widget references
    kwargs['priority'], i = 0.6, 0
    widgets_dir = ui_dir + "yelo widgets\\"
    for b in meta.scripted_ui_widgets.STEPTREE:
        widget_name = sanitize_name(b.name)
        if not widget_name:
            widget_name = "y scripted ui widget %s" % i
        recursive_rename(get_tag_id(b.definition), sub_dir=widgets_dir,
                         name=widget_name, **kwargs)
        i += 1


def rename_gelo(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = levels_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', INF)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'yelo globals'

    # rename this project_yellow_globals tag
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # rename the explicit references
    recursive_rename(get_tag_id(meta.global_explicit_references),
                     name="global references", **kwargs)

    # rename the chokin victim globals
    try:
        sub_id = get_tag_id(meta.chokin_victim_globals)
    except AttributeError:
        sub_id = None
    if sub_id is not None:
        recursive_rename(sub_id, sub_dir=sub_dir,
                         name="yelo globals cv", **kwargs)

    # rename scripted ui widget references
    widgets_dir = ui_dir + "gelo widgets\\"
    for b in meta.scripted_ui_widgets.STEPTREE:
        widget_name = sanitize_name(b.name)
        if not widget_name:
            widget_name = "y scripted ui widget %s" % i
        recursive_rename(get_tag_id(b.definition), sub_dir=widgets_dir,
                         name=widget_name, **kwargs)
        i += 1


def rename_gelc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = levels_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', INF)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'yelo globals cv'

    # rename this project_yellow_globals tag
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # I'm not typing up the rest of this right now. Might be pointless anyway.


def rename_hudg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir=ui_hud_dir, name="", **kwargs):
    if not sub_dir: sub_dir = ui_hud_dir
    if not name:
        name = "default"

    kwargs.setdefault('priority', MEDIUM_HIGH_PRIORITY)
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    msg_param = meta.messaging_parameters
    recursive_rename(get_tag_id(msg_param.single_player_font),
                     sub_dir=ui_dir, name="font sp", **kwargs)
    recursive_rename(get_tag_id(msg_param.multi_player_font),
                     sub_dir=ui_dir, name="font mp", **kwargs)
    recursive_rename(get_tag_id(msg_param.item_message_text),
                     sub_dir=ui_hud_dir, name="hud item messages", **kwargs)
    recursive_rename(get_tag_id(msg_param.alternate_icon_text),
                     sub_dir=ui_hud_dir, name="hud icon messages", **kwargs)
    recursive_rename(get_tag_id(msg_param.icon_bitmap),
                     sub_dir=ui_hud_dir + bitmaps_dir,
                     name="hud msg icons", **kwargs)

    recursive_rename(get_tag_id(meta.waypoint_parameters.arrow_bitmaps),
                     sub_dir=ui_hud_dir + bitmaps_dir + "combined\\",
                     name="hud waypoints", **kwargs)

    recursive_rename(get_tag_id(meta.hud_globals.default_weapon_hud),
                     sub_dir=ui_hud_dir, name="empty", **kwargs)

    recursive_rename(get_tag_id(meta.hud_damage_indicators.indicator_bitmap),
                     sub_dir=ui_hud_dir + bitmaps_dir + "combined\\",
                     name="hud damage arrows", **kwargs)

    recursive_rename(get_tag_id(meta.carnage_report_bitmap),
                     sub_dir=ui_shell_dir + bitmaps_dir,
                     name="postgame carnage report", **kwargs)


def rename_sbsp(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault("priority", MEDIUM_PRIORITY if
                      sub_dir else DEFAULT_PRIORITY)

    recursive_rename(get_tag_id(meta.lightmap_bitmaps),
                     sub_dir=sub_dir, name=name, **kwargs)

    coll_shdr_dir     = sub_dir + "shaders collidable\\"
    non_coll_shdr_dir = sub_dir + "shaders non collidable\\"
    override = kwargs.pop("override", None)
    for b in meta.collision_materials.STEPTREE:
        recursive_rename(
            get_tag_id(b.shader), sub_dir=coll_shdr_dir,
            name="protected %s" % get_tag_id(b.shader),
            override=True, **kwargs)

    kwargs["override"] = override
    for lightmap in meta.lightmaps.STEPTREE:
        for mat in lightmap.materials.STEPTREE:
            recursive_rename(
                get_tag_id(mat.shader), sub_dir=non_coll_shdr_dir,
                name="protected %s" % get_tag_id(mat.shader), **kwargs)

    for b in meta.lens_flares.STEPTREE:
        recursive_rename(
            get_tag_id(b.shader), sub_dir=sub_dir + "lens flares\\",
            name="protected %s" % get_tag_id(b.shader), **kwargs)

    for b in meta.fog_palettes.STEPTREE:
        recursive_rename(get_tag_id(b.fog), sub_dir=sub_dir + weather_dir,
                         name=b.name if b.name else "protected %s" %
                         get_tag_id(b.fog), **kwargs)

    for b in meta.weather_palettes.STEPTREE:
        recursive_rename(get_tag_id(b.particle_system),
                         sub_dir=sub_dir + weather_dir,
                         name=b.name if b.name else "protected weather %s" %
                         get_tag_id(b.particle_system), **kwargs)
        recursive_rename(get_tag_id(b.wind), sub_dir=sub_dir + weather_dir,
                         name=b.name if b.name else "protected wind %s" %
                         get_tag_id(b.wind), **kwargs)

    for b in meta.background_sounds_palette.STEPTREE:
        recursive_rename(get_tag_id(b.background_sound),
                         sub_dir=sub_dir + sounds_dir,
                         name=b.name if b.name else
                         "protected background sound %s" %
                         get_tag_id(b.background_sound), **kwargs)

    for b in meta.sound_environments_palette.STEPTREE:
        recursive_rename(get_tag_id(b.sound_environment),
                         sub_dir=snd_sound_env_dir,
                         name=b.name if b.name else
                         "protected sound environment %s" %
                         get_tag_id(b.sound_environment), **kwargs)


def rename_sky_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = sky_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'sky'

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir, sub_dir=sub_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault("priority", DEFAULT_PRIORITY)

    recursive_rename(get_tag_id(meta.model), name=name, **kwargs)
    for b in meta.lights.STEPTREE:
        light_name = sanitize_name(b.global_function_name)
        if not light_name:
            widget_name = "light"
        recursive_rename(get_tag_id(b.lens_flare), name=light_name, **kwargs)


def rename_obje(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    obje_attrs = meta.obje_attrs
    obje_type = obje_attrs.object_type.enum_name

    i = 1
    for f in obje_attrs.functions.STEPTREE:
        kwargs["func_%s_name" % i] = sanitize_name(f.usage).\
                                     replace(" source", "").replace(" src", "")
        i += 1

    if not name:
        if obje_type in ("weap", "eqip"):
            name = tag_path_handler.get_item_string(
                meta.item_attrs.message_index)
            eqip_attrs = getattr(meta, "eqip_attrs", None)
            if eqip_attrs and eqip_attrs.powerup_type.data in (1, 4):
                name = eqip_attrs.powerup_type.enum_name.replace("_", " ")

        elif obje_type == "vehi":
            name = tag_path_handler.get_icon_string(
                meta.obje_attrs.hud_text_message_index)

        if name:
            # up the priority if we could detect a name for
            # this in the strings for the weapon or vehicles
            kwargs.setdefault('priority', HIGH_PRIORITY)
        else:
            kwargs.setdefault('priority', MEDIUM_HIGH_PRIORITY)
            name = get_model_name(halo_map, get_tag_id(obje_attrs.model),
                                  "protected %s" % tag_id)

    if not sub_dir:
        if obje_type == "bipd":
            sub_dir += characters_dir
        elif obje_type == "vehi":
            sub_dir += vehicles_dir
        elif obje_type == "weap":
            sub_dir += weapons_dir
        elif obje_type == "eqip":
            sub_dir += powerups_dir
        elif obje_type == "garb":
            sub_dir += "garbage\\"
        elif obje_type == "proj":
            sub_dir += weapons_dir + "projectiles\\"
        elif obje_type == "scen":
            sub_dir = scenery_dir
        elif obje_type == "mach":
            sub_dir += level_devices_dir + "machines\\"
        elif obje_type == "ctrl":
            sub_dir += level_devices_dir + "controls\\"
        elif obje_type == "lifi":
            sub_dir += level_devices_dir + "light fixtures\\"
        elif obje_type == "plac":
            sub_dir += "placeholders\\"
        elif obje_type == "ssce":
            sub_dir += "sfx emitters\\"

    if not sub_dir.lower().endswith(name + "\\"):
        sub_dir += name + "\\"

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))

    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    if obje_type in ("weap", "eqip", "garb"):
        rename_item_attrs(meta, tag_id, sub_dir=sub_dir, name=name, **kwargs)
    elif obje_type in ("bipd", "vehi"):
        rename_unit_attrs(meta, tag_id, sub_dir=sub_dir, name=name, **kwargs)
    elif obje_type in ("mach", "ctrl", "lifi"):
        rename_devi_attrs(meta, tag_id, sub_dir=sub_dir, name=name, **kwargs)

    for b in (obje_attrs.model, obje_attrs.animation_graph,
              obje_attrs.collision_model, obje_attrs.physics):
        recursive_rename(get_tag_id(b), sub_dir=sub_dir, name=name, **kwargs)

    recursive_rename(get_tag_id(obje_attrs.creation_effect),
                     sub_dir=sub_dir + effects_dir,
                     name="creation effect", **kwargs)

    recursive_rename(get_tag_id(obje_attrs.modifier_shader),
                     sub_dir=sub_dir + shaders_dir,
                     name="modifier shader", **kwargs)

    for b in obje_attrs.attachments.STEPTREE:
        a_name = kwargs.get("func_%s_name" % b.primary_scale.data, "")
        if not a_name and b.type.tag_class.enum_name in ("contrail", "light"):
            a_name = b.marker.replace("\\", " ")
            if a_name: a_name += " "
            if b.type.tag_class.enum_name not in a_name.lower():
                a_name += b.type.tag_class.enum_name

        recursive_rename(get_tag_id(b.type), name=a_name,
                         sub_dir=sub_dir + obje_effects_dir, **kwargs)

    for b in obje_attrs.widgets.STEPTREE:
        recursive_rename(get_tag_id(b.reference),
                         sub_dir=sub_dir + "widgets\\", **kwargs)

    proj_attrs = getattr(meta, "proj_attrs", None)
    if obje_type != "proj" or not proj_attrs:
        return

    recursive_rename(get_tag_id(proj_attrs.super_detonation),
                     sub_dir=sub_dir + effects_dir,
                     name="super detonation", **kwargs)
    recursive_rename(get_tag_id(proj_attrs.detonation.effect),
                     sub_dir=sub_dir + effects_dir,
                     name="detonation", **kwargs)

    recursive_rename(get_tag_id(proj_attrs.physics.detonation_started),
                     sub_dir=sub_dir + effects_dir,
                     name="detonation started", **kwargs)
    recursive_rename(get_tag_id(proj_attrs.physics.flyby_sound),
                     sub_dir=sub_dir + sound_dir, name="flyby sound", **kwargs)
    recursive_rename(get_tag_id(proj_attrs.physics.attached_detonation_damage),
                     sub_dir=sub_dir, name="attached detonation", **kwargs)
    recursive_rename(get_tag_id(proj_attrs.physics.impact_damage),
                     sub_dir=sub_dir, name="impact", **kwargs)

    i = 0
    for b in proj_attrs.material_responses.STEPTREE:
        if i >= len(materials_list):
            mat_name = "mat %s" % i
        else:
            mat_name = materials_list[i].replace("_", " ")

        recursive_rename(get_tag_id(b.effect),
                         sub_dir=sub_dir + "impact effects\\",
                         name=mat_name, **kwargs)
        recursive_rename(get_tag_id(b.potential_response.effect),
                         sub_dir=sub_dir + "impact effects\\",
                         name="alt %s" % mat_name, **kwargs)
        recursive_rename(get_tag_id(b.detonation_effect),
                         sub_dir=sub_dir + "impact effects\\",
                         name="detonation %s" % mat_name, **kwargs)
        i += 1


def rename_shdr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = obje_shaders_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    shdr_type = meta.shdr_attrs.shader_type.enum_name
    func_name = ""
    if shdr_type == "smet":
        smet_attrs = meta.smet_attrs
        func_name = kwargs.get(
            "func_%s_name" % smet_attrs.external_function_sources.value.data, "")
    elif shdr_type == "spla":
        spla_attrs = meta.spla_attrs
        func_name = kwargs.get(
            "func_%s_name" % spla_attrs.intensity.source.data, "")

    if func_name and ("protected" in name or not name):
        name = func_name

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))

    name = tag_path_handler.get_basename(tag_id)
    bitmaps_sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    bitmaps_sub_dir = "\\".join(sub_dir.split("\\")[: -2])
    if bitmaps_sub_dir: bitmaps_sub_dir += "\\"
    bitmaps_sub_dir += bitmaps_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  sub_dir=bitmaps_sub_dir, tag_path_handler=tag_path_handler)

    if shdr_type == "senv":
        senv_attrs = meta.senv_attrs
        recursive_rename(get_tag_id(senv_attrs.diffuse.base_map),
                         name="senv %s diffuse" % name, **kwargs)
        recursive_rename(get_tag_id(senv_attrs.diffuse.primary_detail_map),
                         name="senv %s pri detail" % name, **kwargs)
        recursive_rename(get_tag_id(senv_attrs.diffuse.secondary_detail_map),
                         name="senv %s sec detail" % name, **kwargs)
        recursive_rename(get_tag_id(senv_attrs.diffuse.micro_detail_map),
                         name="senv %s micro detail" % name, **kwargs)
        recursive_rename(get_tag_id(senv_attrs.bump_properties.map),
                         name="senv %s bump" % name, **kwargs)
        recursive_rename(get_tag_id(senv_attrs.self_illumination.map),
                         name="senv %s self illum" % name, **kwargs)
        recursive_rename(get_tag_id(senv_attrs.reflection.cube_map),
                         name="senv %s reflection" % name, **kwargs)

        senv_ext = getattr(getattr(senv_attrs, "os_shader_environment_ext", ()),
                           "STEPTREE", ())
        for b in senv_ext:
            recursive_rename(get_tag_id(b.specular_color_map),
                             name="senv %s spec color" % name, **kwargs)
            

    elif shdr_type == "soso":
        soso_attrs = meta.soso_attrs
        recursive_rename(get_tag_id(soso_attrs.maps.diffuse_map),
                         name="soso %s diffuse" % name, **kwargs)
        recursive_rename(get_tag_id(soso_attrs.maps.multipurpose_map),
                         name="soso %s multi" % name, **kwargs)
        recursive_rename(get_tag_id(soso_attrs.maps.detail_map),
                         name="soso %s detail" % name, **kwargs)
        recursive_rename(get_tag_id(soso_attrs.reflection.cube_map),
                         name="soso %s reflection" % name, **kwargs)
        soso_ext = getattr(getattr(soso_attrs, "os_shader_model_ext", ()),
                           "STEPTREE", ())
        for b in soso_ext:
            recursive_rename(get_tag_id(b.specular_color_map),
                             name="soso %s spec color" % name, **kwargs)
            recursive_rename(get_tag_id(b.base_normal_map),
                             name="soso %s normal" % name, **kwargs)
            recursive_rename(get_tag_id(b.detail_normal_1_map),
                             name="soso %s normal detail 1" % name, **kwargs)
            recursive_rename(get_tag_id(b.detail_normal_2_map),
                             name="soso %s normal detail 2" % name, **kwargs)

    elif shdr_type in ("sotr", "schi", "scex"):
        if shdr_type == "scex":
            extra_layers = meta.scex_attrs.extra_layers
            maps_list = [meta.scex_attrs.four_stage_maps,
                         meta.scex_attrs.two_stage_maps]
        elif shdr_type == "schi":
            extra_layers = meta.schi_attrs.extra_layers
            maps_list = [meta.schi_attrs.maps]
        else:
            extra_layers = meta.sotr_attrs.extra_layers
            maps_list = [meta.sotr_attrs.maps]

        for maps in maps_list:
            for map in maps.STEPTREE:
                recursive_rename(get_tag_id(map.bitmap), name="%s %s" %
                                 (shdr_type, name), **kwargs)

        kwargs.update(sub_dir=sub_dir)
        i = 0
        for extra_layer in extra_layers.STEPTREE:
            ex_layer_name = name
            if "ex " not in name:
                ex_layer_name += " ex "
            else:
                ex_layer_name += " ex %s" % i
            recursive_rename(get_tag_id(extra_layer),
                             name=ex_layer_name, **kwargs)
            i += 1

    elif shdr_type == "swat":
        water_shader = meta.swat_attrs.water_shader
        recursive_rename(get_tag_id(water_shader.base_map),
                         name="swat %s base" % name, **kwargs)
        recursive_rename(get_tag_id(water_shader.reflection_map),
                         name="swat %s reflection" % name, **kwargs)
        recursive_rename(get_tag_id(water_shader.ripple_maps),
                         name="swat %s ripples" % name, **kwargs)

    elif shdr_type == "sgla":
        sgla_attrs = meta.sgla_attrs
        recursive_rename(
            get_tag_id(sgla_attrs.background_tint_properties.map),
            name="sgla %s background tint" % name, **kwargs)

        recursive_rename(get_tag_id(sgla_attrs.reflection_properties.map),
                         name="sgla %s reflection" % name, **kwargs)
        recursive_rename(get_tag_id(sgla_attrs.reflection_properties.bump_map),
                         name="sgla %s bump" % name, **kwargs)

        recursive_rename(get_tag_id(sgla_attrs.diffuse_properties.map),
                         name="sgla %s diffuse" % name, **kwargs)
        recursive_rename(get_tag_id(sgla_attrs.diffuse_properties.detail_map),
                         name="sgla %s diffuse detail" % name, **kwargs)

        recursive_rename(get_tag_id(sgla_attrs.specular_properties.map),
                         name="sgla %s specular" % name, **kwargs)
        recursive_rename(get_tag_id(sgla_attrs.specular_properties.detail_map),
                         name="sgla %s specular detail" % name, **kwargs)

    elif shdr_type == "smet":
        smet_attrs = meta.smet_attrs
        smet_srcs = smet_attrs.external_function_sources
        meter_name = ""
        for b in (smet_srcs.value, smet_srcs.flash_extension):
            func_name = kwargs.get("func_%s_name" % b.data, "")
            if func_name:
                meter_name = func_name

        if not meter_name:
            meter_name = name if  "meter" in name else name + " meter"

        recursive_rename(get_tag_id(smet_attrs.meter_shader.map),
                         name="smet %s" % name, **kwargs)

    elif shdr_type == "spla":
        spla_attrs = meta.spla_attrs
        plasma_name = ""
        func_name = kwargs.get(
            "func_%s_name" % spla_attrs.intensity.source.data, "")
        if func_name:
            plasma_name = func_name

        recursive_rename(get_tag_id(spla_attrs.primary_noise_map.noise_map),
                         name="spla %s noise" % plasma_name, **kwargs)
        recursive_rename(get_tag_id(spla_attrs.primary_noise_map.noise_map),
                         name="spla %s noise sec" % plasma_name, **kwargs)


def rename_item_attrs(meta, tag_id, halo_map, tag_path_handler,
                      root_dir="", sub_dir="", name="", **kwargs):
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    item_attrs = meta.item_attrs
    eqip_attrs = getattr(meta, "eqip_attrs", None)
    weap_attrs = getattr(meta, "weap_attrs", None)

    items_dir = '\\'.join(sub_dir.split('\\')[: -2])
    if items_dir: items_dir += "\\"
    recursive_rename(get_tag_id(item_attrs.material_effects),
                     sub_dir=items_dir, name="material effects", **kwargs)
    recursive_rename(get_tag_id(item_attrs.collision_sound),
                     sub_dir=sub_dir + "sfx\\",
                     name="collision sound", **kwargs)
    recursive_rename(get_tag_id(item_attrs.detonating_effect),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="item detonating", **kwargs)
    recursive_rename(get_tag_id(item_attrs.detonation_effect),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="item detonation", **kwargs)

    if eqip_attrs:
        recursive_rename(get_tag_id(eqip_attrs.pickup_sound),
                         sub_dir=sub_dir + sound_dir,
                         name="pickup sound", **kwargs)

    if not weap_attrs:
        return

    recursive_rename(get_tag_id(weap_attrs.ready_effect),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="weap ready", **kwargs)
    recursive_rename(get_tag_id(weap_attrs.heat.overheated),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="weap overheated", **kwargs)
    recursive_rename(get_tag_id(weap_attrs.heat.detonation),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="weap detonation", **kwargs)

    recursive_rename(get_tag_id(weap_attrs.melee.player_damage),
                     sub_dir=sub_dir, name="melee", **kwargs)
    recursive_rename(get_tag_id(weap_attrs.melee.player_response),
                     sub_dir=sub_dir, name="melee response", **kwargs)

    recursive_rename(get_tag_id(weap_attrs.aiming.actor_firing_parameters),
                     sub_dir=sub_dir, name="firing parameters", **kwargs)

    recursive_rename(get_tag_id(weap_attrs.light.power_on_effect),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="light power on", **kwargs)
    recursive_rename(get_tag_id(weap_attrs.light.power_off_effect),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="light power off", **kwargs)

    interface = weap_attrs.interface
    recursive_rename(get_tag_id(interface.first_person_model),
                     sub_dir=sub_dir + weap_fp_dir, name="fp", **kwargs)
    recursive_rename(get_tag_id(interface.first_person_animations),
                     sub_dir=sub_dir + weap_fp_dir, name="fp", **kwargs)
    recursive_rename(get_tag_id(interface.hud_interface),
                     sub_dir=sub_dir, name=name, **kwargs)
    recursive_rename(get_tag_id(interface.pickup_sound), name="weap pickup",
                     sub_dir=sub_dir + "sfx\\", **kwargs)
    recursive_rename(get_tag_id(interface.zoom_in_sound), name="zoom in",
                     sub_dir=sub_dir + "sfx\\", **kwargs)
    recursive_rename(get_tag_id(interface.zoom_out_sound), name="zoom out",
                     sub_dir=sub_dir + "sfx\\", **kwargs)

    i = 0
    for mag in weap_attrs.magazines.STEPTREE:
        mag_str = ""
        if len(weap_attrs.magazines.STEPTREE) > 1:
            mag_str = "secondary " if i else "primary "

        recursive_rename(
            get_tag_id(mag.reloading_effect), name="%sreloading" % mag_str,
            sub_dir=sub_dir + obje_effects_dir, **kwargs)
        recursive_rename(
            get_tag_id(mag.chambering_effect), name="%schambering" % mag_str,
            sub_dir=sub_dir + obje_effects_dir, **kwargs)

        j = 0
        for mag_item in mag.magazine_items.STEPTREE:
            mag_item_name = mag_str
            if len(mag.magazine_items.STEPTREE) > 1:
                mag_item_name += "secondary " if j else "primary "

            mag_item_name = "%s%s ammo" % (mag_item_name, name)
            recursive_rename(
                get_tag_id(mag_item.equipment), name=mag_item_name,
                sub_dir=powerups_dir + mag_item_name + "\\", **kwargs)
            j += 1

        i += 1

    i = 0
    kwargs["override"] = True
    for trig in weap_attrs.triggers.STEPTREE:
        trig_str = ""
        if len(weap_attrs.triggers.STEPTREE) > 1:
            trig_str = "secondary " if i else "primary "

        recursive_rename(
            get_tag_id(trig.charging.charging_effect),
            name="%scharging" % trig_str,
            sub_dir=sub_dir + obje_effects_dir, **kwargs)
        recursive_rename(
            get_tag_id(trig.projectile.projectile), name="projectile",
            sub_dir=sub_dir + "%sprojectile\\" % trig_str, **kwargs)

        for b in trig.misc.firing_effects.STEPTREE:
            recursive_rename(
                get_tag_id(b.firing_effect), name=trig_str + "fire",
                sub_dir=sub_dir + obje_effects_dir, **kwargs)
            recursive_rename(
                get_tag_id(b.misfire_effect), name=trig_str + "misfire",
                sub_dir=sub_dir + obje_effects_dir, **kwargs)
            recursive_rename(
                get_tag_id(b.empty_effect), name=trig_str + "empty",
                sub_dir=sub_dir + obje_effects_dir, **kwargs)

            recursive_rename(
                get_tag_id(b.firing_damage), name=trig_str + "fire response",
                sub_dir=sub_dir + "firing effects\\", **kwargs)
            recursive_rename(
                get_tag_id(b.misfire_damage), name=trig_str + "misfire response",
                sub_dir=sub_dir + "firing effects\\", **kwargs)
            recursive_rename(
                get_tag_id(b.empty_damage), name=trig_str + "empty response",
                sub_dir=sub_dir + "firing effects\\", **kwargs)

        i += 1


def rename_unit_attrs(meta, tag_id, halo_map, tag_path_handler,
                      root_dir="", sub_dir="", name="", **kwargs):
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    unit_attrs = meta.unit_attrs
    bipd_attrs = getattr(meta, "bipd_attrs", None)
    vehi_attrs = getattr(meta, "vehi_attrs", None)

    weap_array = unit_attrs.weapons.STEPTREE
    weap_kwargs = dict(kwargs)
    weap_kwargs['priority'] = (VEHICLE_WEAP_PRIORITY if
                               kwargs.get("priority", 0) < VEHICLE_WEAP_PRIORITY
                               else kwargs.get("priority", 0))

    recursive_rename(get_tag_id(unit_attrs.integrated_light_toggle),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="integrated light toggle", **kwargs)

    parent_dir = '\\'.join(sub_dir.split('\\')[: -2])
    if parent_dir: parent_dir += "\\"

    recursive_rename(get_tag_id(unit_attrs.spawned_actor), sub_dir=parent_dir,
                     name=(name + " spawned actor").strip(), **kwargs)

    recursive_rename(get_tag_id(unit_attrs.melee_damage),
                     sub_dir=sub_dir, name="melee impact", **kwargs)

    trak_array = unit_attrs.camera_tracks.STEPTREE
    unhi_array = unit_attrs.new_hud_interfaces.STEPTREE
    udlg_array = unit_attrs.dialogue_variants.STEPTREE
    for i in range(len(trak_array)):
        recursive_rename(
            get_tag_id(trak_array[i].track), sub_dir=sub_dir,
            name={0:"loose", 1:"tight"}.get(i, "unknown"), **kwargs)

    for i in range(len(unhi_array)):
        recursive_rename(
            get_tag_id(unhi_array[i].unit_hud_interface), sub_dir=sub_dir,
            name={0:"sp", 1:"mp"}.get(i, "unknown"), **kwargs)

    for i in range(len(udlg_array)):
        recursive_rename(
            get_tag_id(udlg_array[i].dialogue),
            sub_dir=sub_dir, name=name + " dialogue", **kwargs)


    trak_kwargs = dict(kwargs)
    trak_kwargs["priority"] = (DEFAULT_PRIORITY if
                               kwargs.get("priority", 0) < DEFAULT_PRIORITY
                               else kwargs.get("priority", 0))
    for seat in unit_attrs.seats.STEPTREE:
        seat_name = tag_path_handler.get_icon_string(
            seat.hud_text_message_index)
        if seat_name:
            seat_name += " "

        trak_array = seat.camera_tracks.STEPTREE
        unhi_array = seat.new_hud_interfaces.STEPTREE
        for i in range(len(trak_array)):
            recursive_rename(
                get_tag_id(trak_array[i].track), sub_dir=sub_dir,
                name=seat_name + {0:"loose", 1:"tight"}.get(i, "unknown"),
                **trak_kwargs)

        for i in range(len(unhi_array)):
            recursive_rename(
                get_tag_id(unhi_array[i].unit_hud_interface), sub_dir=sub_dir,
                name=seat_name + {0:"sp", 1:"mp"}.get(i, "unknown"), **kwargs)

        recursive_rename(get_tag_id(seat.built_in_gunner),
                         sub_dir=sub_dir, name="built in gunner", **kwargs)


    if bipd_attrs:
        recursive_rename(get_tag_id(bipd_attrs.movement.footsteps),
                         sub_dir=sub_dir, name="footsteps", **kwargs)


    if vehi_attrs:
        recursive_rename(get_tag_id(vehi_attrs.suspension_sound),
                         sub_dir=sub_dir, name="suspension sound", **kwargs)
        recursive_rename(get_tag_id(vehi_attrs.crash_sound),
                         sub_dir=sub_dir, name="crash sound", **kwargs)
        recursive_rename(get_tag_id(vehi_attrs.effect),
                         sub_dir=sub_dir, name="unknown effect", **kwargs)

        vehi_dir = '\\'.join(sub_dir.split('\\')[: -2])
        if vehi_dir: vehi_dir += "\\"
        recursive_rename(get_tag_id(vehi_attrs.material_effect),
                         sub_dir=vehi_dir, name="material effects", **kwargs)


    for i in range(len(weap_array)):
        gun_id = get_tag_id(weap_array[i].weapon)
        gun_meta = halo_map.get_meta(gun_id)
        gun_obje_attrs = getattr(gun_meta, "obje_attrs", None)
        if gun_obje_attrs is None:
            continue

        gun_mod2_id = get_tag_id(gun_obje_attrs.model)
        if gun_mod2_id is not None:
            continue

        gun_name = name + " gun"
        if len(weap_array) > 1:
            gun_name += " %s" % i

        recursive_rename(gun_id, name=gun_name,
                         sub_dir=sub_dir + gun_name + "\\", **weap_kwargs)


def rename_devi_attrs(meta, tag_id, halo_map, tag_path_handler,
                      root_dir="", sub_dir="", name="", **kwargs):
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  sub_dir=sub_dir + obje_effects_dir,
                  tag_path_handler=tag_path_handler)

    devi_attrs = meta.devi_attrs
    ctrl_attrs = getattr(meta, "ctrl_attrs", None)

    recursive_rename(get_tag_id(devi_attrs.open), name="open", **kwargs)
    recursive_rename(get_tag_id(devi_attrs.close), name="close", **kwargs)
    recursive_rename(get_tag_id(devi_attrs.opened), name="opened", **kwargs)
    recursive_rename(get_tag_id(devi_attrs.closed), name="closed", **kwargs)
    recursive_rename(get_tag_id(devi_attrs.depowered), name="depowered", **kwargs)
    recursive_rename(get_tag_id(devi_attrs.repowered), name="repowered", **kwargs)

    recursive_rename(get_tag_id(devi_attrs.delay_effect), name="delay", **kwargs)

    if ctrl_attrs:
        recursive_rename(get_tag_id(ctrl_attrs.on), name="on", **kwargs)
        recursive_rename(get_tag_id(ctrl_attrs.off), name="off", **kwargs)
        recursive_rename(get_tag_id(ctrl_attrs.deny), name="deny", **kwargs)


def rename_actv(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name:
        name = "protected %s" % tag_id
    if not sub_dir:
        sub_dir = characters_dir + name + "\\"

    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    unit_id = get_tag_id(meta.unit)
    major_id = get_tag_id(meta.major_variant)
    if tag_path_handler.get_priority(unit_id) >= kwargs['priority']:
        kwargs['priority'] = tag_path_handler.get_priority(unit_id)
        sub_dir = tag_path_handler.get_sub_dir(unit_id, root_dir)
        kwargs["override"] = True
    elif tag_path_handler.get_priority(major_id) >= kwargs['priority']:
        kwargs['priority'] = tag_path_handler.get_priority(major_id)
        sub_dir = tag_path_handler.get_sub_dir(major_id, root_dir)
        kwargs["override"] = True


    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs["override"] = True
    recursive_rename(get_tag_id(meta.actor_definition), sub_dir=sub_dir,
                     name=name + " actor definition", **kwargs)
    recursive_rename(get_tag_id(meta.major_variant), sub_dir=sub_dir,
                     name=name + " major", **kwargs)
    recursive_rename(get_tag_id(meta.unit), sub_dir=sub_dir,
                     name=name, **kwargs)
    recursive_rename(get_tag_id(meta.ranged_combat.weapon), sub_dir=sub_dir,
                     name=name + " weapon", **kwargs)
    recursive_rename(get_tag_id(meta.items.equipment), sub_dir=sub_dir,
                     name=name + " dropped item", **kwargs)


def rename_flag(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'flag'

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    shader_name = name
    if "flag" not in shader_name.lower():
        shader_name += "flag"

    shdr_dir = '\\'.join(sub_dir.split('\\')[: -2])
    if shdr_dir: shdr_dir += "\\"
    shdr_dir += shaders_dir
    recursive_rename(get_tag_id(meta.red_flag_shader), sub_dir=shdr_dir,
                     name=shader_name + "_red", **kwargs)
    recursive_rename(get_tag_id(meta.blue_flag_shader), sub_dir=shdr_dir,
                     name=shader_name + "_blue", **kwargs)
    recursive_rename(get_tag_id(meta.physics), sub_dir=sub_dir,
                     name=name, **kwargs)


def rename_mode(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  sub_dir=sub_dir + shaders_dir,
                  tag_path_handler=tag_path_handler)


    shader_names = {}
    for i in range(len(meta.regions.STEPTREE)):
        region = meta.regions.STEPTREE[i]
        geoms = []

        region_name = region.name.lower().strip("_ ").replace("unnamed", "")
        if region_name: region_name += " "

        for j in range(len(region.permutations.STEPTREE)):
            perm = region.permutations.STEPTREE[j]
            shader_name = region_name + perm.name.replace(' ', '').strip("_")

            for lod in ("superhigh", "high", "medium", "low", "superlow"):
                geom_index = getattr(perm, lod + "_geometry_block")

                if geom_index not in range(len(meta.geometries.STEPTREE)):
                    continue

                parts = meta.geometries.STEPTREE[geom_index].parts.STEPTREE
                for part_i in range(len(parts)):
                    final_shader_name = shader_name
                    if len(parts) > 1:
                        final_shader_name += " part%s" % part_i
                    if lod != "superhigh":
                        final_shader_name += " " + lod
                    shader_names.setdefault(parts[part_i].shader_index,
                                            final_shader_name)

    for i in range(len(meta.shaders.STEPTREE)):
        shader_name = shader_names.get(i, "").replace("_", " ").\
                      replace(".", "_").strip()
        recursive_rename(get_tag_id(meta.shaders.STEPTREE[i].shader),
                         name=shader_name.strip(), **kwargs)


def rename_coll(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  sub_dir=sub_dir + obje_effects_dir,
                  tag_path_handler=tag_path_handler)

    body, shield = meta.body, meta.shield
    recursive_rename(get_tag_id(body.localized_damage_effect),
                     name=name + " localized damage", **kwargs)
    recursive_rename(get_tag_id(body.area_damage_effect),
                     name=name + " area damage", **kwargs)
    recursive_rename(get_tag_id(body.body_damaged_effect),
                     name=name + " body damaged", **kwargs)
    recursive_rename(get_tag_id(body.body_depleted_effect),
                     name=name + " body depleted", **kwargs)
    recursive_rename(get_tag_id(body.body_destroyed_effect),
                     name=name + " body destroyed", **kwargs)

    recursive_rename(get_tag_id(shield.shield_damaged_effect),
                     name=name + " shield damaged", **kwargs)
    recursive_rename(get_tag_id(shield.shield_depleted_effect),
                     name=name + " shield depleted", **kwargs)
    recursive_rename(get_tag_id(shield.shield_recharging_effect),
                     name=name + " shield recharging", **kwargs)

    i = 0
    for region in meta.regions.STEPTREE:
        region_name = region.name if region.name else "region %s " % i
        recursive_rename(
            get_tag_id(region.destroyed_effect),
            name=name + (region_name + " destroyed").strip(), **kwargs)
        i += 1


def rename_rain(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = weather_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    weather_bitmaps_dir = sub_dir + bitmaps_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    i = 0
    for b in meta.particle_types.STEPTREE:
        type_name = b.name if b.name else "particle %s " % i
        recursive_rename(
            get_tag_id(b.physics), sub_dir=effect_physics_dir,
            name=name + type_name, **kwargs)

        recursive_rename(
            get_tag_id(b.shader.sprite_bitmap), sub_dir=weather_bitmaps_dir,
            name=name + (type_name + " sprites").strip(), **kwargs)

        recursive_rename(
            get_tag_id(b.secondary_bitmap.bitmap), sub_dir=weather_bitmaps_dir,
            name=name + (type_name + " sec map").strip(), **kwargs)
        i += 1


def rename_fog_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = weather_dir
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    recursive_rename(
        get_tag_id(meta.screen_layers.fog_map), sub_dir=sub_dir + bitmaps_dir,
        name=(name + " fog map").strip(), **kwargs)

    recursive_rename(
        get_tag_id(meta.background_sound), sub_dir=sub_dir,
        name=(name + " fog background sound").strip(), **kwargs)
    recursive_rename(
        get_tag_id(meta.sound_environment), sub_dir=sub_dir,
        name=(name + " fog sound environment").strip(), **kwargs)


def rename_foot(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    for i in range(len(meta.effects.STEPTREE)):
        type_dir = material_effect_types[i] + "\\"
        mat_effects_dir = sub_dir + name + "\\" + effects_dir + type_dir
        mat_sounds_dir = sub_dir + name + "\\" + sounds_dir + type_dir
        materials = meta.effects.STEPTREE[i].materials.STEPTREE

        for j in range(len(materials)):
            recursive_rename(get_tag_id(materials[j].effect),
                             sub_dir=mat_effects_dir,
                             name=materials_list[j], **kwargs)
            recursive_rename(get_tag_id(materials[j].sound),
                             sub_dir=mat_sounds_dir,
                             name=materials_list[j], **kwargs)


def rename_antr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'animations'

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault("priority", DEFAULT_PRIORITY)

    sfx_names = {}
    for i in range(len(meta.animations.STEPTREE)):
        anim = meta.animations.STEPTREE[i]
        sfx_names.setdefault(anim.sound, anim.name.replace(".", " ").strip())

    anim_sfx_dir = sub_dir + "anim_sfx\\"
    for i in range(len(meta.sound_references.STEPTREE)):
        recursive_rename(
            get_tag_id(meta.sound_references.STEPTREE[i].sound),
            name=sfx_names.get(i, name), sub_dir=anim_sfx_dir, **kwargs)

    if hasattr(meta, "stock_animation"):
        recursive_rename(
            get_tag_id(meta.stock_animation),
            name=name + " base", sub_dir=sub_dir, **kwargs)


def rename_deca(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'decal %s' % tag_id

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.next_decal_in_chain), name=name + " next",
                     sub_dir=sub_dir, **kwargs)
    recursive_rename(get_tag_id(meta.shader.shader_map), name=name + " bitmaps",
                     sub_dir=sub_dir + bitmaps_dir, **kwargs)


def rename_ant_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'antenna'

        if 'antenna' not in meta.attachment_marker_name:
            name += meta.attachment_marker_name

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    bitm_dir = '\\'.join(sub_dir.split('\\')[: -2])
    if bitm_dir: bitm_dir += "\\"
    bitm_dir += bitmaps_dir
    recursive_rename(get_tag_id(meta.bitmaps), sub_dir=bitm_dir,
                     name=name, **kwargs)
    recursive_rename(get_tag_id(meta.physics), sub_dir=sub_dir,
                     name=name, **kwargs)


def rename_dobc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    dobc_type_names = set()
    for b in meta.detail_object_types.STEPTREE:
        dobc_name = b.name.lower().replace("_", " ").strip()
        if dobc_name:
            dobc_type_names.add(dobc_name)

    dobc_name = join_names(sorted(dobc_type_names), 96)
    if (not name or "protected" in name) and dobc_name: name = dobc_name

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(
        get_tag_id(meta.sprite_plate), halo_map, tag_path_handler,
        root_dir, sub_dir + bitmaps_dir, dobc_name, **kwargs)


def rename_udlg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    name = tag_path_handler.get_basename(tag_id)
    sub_dir = snd_dialog_dir + name + "\\"

    for struct in (meta.idle, meta.involuntary, meta.hurting_people,
                   meta.being_hurt, meta.killing_people, meta.actions,
                   meta.player_kill_responses, meta.friends_dying,
                   meta.shouting, meta.group_communication, meta.exclamations,
                   meta.post_combat_actions, meta.post_combat_chatter):
        snd_dir = sub_dir + "%s\\" % struct.NAME
        for dep in struct:
            recursive_rename(get_tag_id(dep), halo_map, tag_path_handler,
                             root_dir, snd_dir, dep.NAME, **kwargs)


def rename_DeLa(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    if not name:
        name = kwargs.get("dela_name", "").replace("_", " ").strip()
        if not name:
            name = sanitize_name(meta.name)
    if not sub_dir:
        sub_dir = ui_shell_dir

    kwargs.pop("dela_name", None)
    seen = kwargs.get("seen", set())

    if not name:
        name = "protected %s" % tag_id

    kwargs["priority"] = (DEFAULT_PRIORITY if
                          kwargs.get("priority", 0) < DEFAULT_PRIORITY
                          else kwargs.get("priority", 0))

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    for b in meta.event_handlers.STEPTREE:
        recursive_rename(get_tag_id(b.sound_effect),
                         sub_dir=sub_dir + "sfx\\", **kwargs)

        if (tag_path_handler.get_priority(get_tag_id(b.widget_tag)) >=
            kwargs["priority"] and tag_id in seen):
            continue
        recursive_rename(get_tag_id(b.widget_tag), sub_dir=sub_dir, **kwargs)


    kwargs.update(sub_dir=sub_dir + bitmaps_dir)
    recursive_rename(get_tag_id(meta.background_bitmap),
                     name="background bitmap", **kwargs)
    recursive_rename(get_tag_id(meta.spinner_list.list_header_bitmap),
                     name="list header bitmap", **kwargs)
    recursive_rename(get_tag_id(meta.spinner_list.list_footer_bitmap),
                     name="list footer bitmap", **kwargs)

    kwargs.update(sub_dir=sub_dir + name + "\\")
    recursive_rename(get_tag_id(meta.text_box.text_label_unicode_strings_list),
                     name="text labels", **kwargs)
    recursive_rename(get_tag_id(meta.text_box.text_font),
                     name="text font", **kwargs)
    recursive_rename(get_tag_id(meta.column_list.extended_description_widget),
                     name="ext desc", **kwargs)

    for b in meta.conditional_widgets.STEPTREE:
        if (tag_path_handler.get_priority(get_tag_id(b.widget_tag)) >=
            kwargs["priority"] and tag_id in seen):
            continue
        recursive_rename(get_tag_id(b.widget_tag),
                         dela_name=sanitize_name(b.name), **kwargs)

    for b in meta.child_widgets.STEPTREE:
        if (tag_path_handler.get_priority(get_tag_id(b.widget_tag)) >=
            kwargs["priority"] and tag_id in seen):
            continue
        recursive_rename(get_tag_id(b.widget_tag),
                         dela_name=sanitize_name(b.name), **kwargs)


def rename_lsnd(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = snd_music_dir
    if not name: name = "protected %s" % tag_id

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.continuous_damage_effect),
                     name=name + " continuous damage",
                     sub_dir=sub_dir, **kwargs)

    i = 0
    tracks_dir = sub_dir + name + " tracks & details\\"
    for b in meta.tracks.STEPTREE:
        recursive_rename(get_tag_id(b.start), name="track %s start" % i,
                         sub_dir=tracks_dir, **kwargs)
        recursive_rename(get_tag_id(b.loop), name="track %s loop" % i,
                         sub_dir=tracks_dir, **kwargs)
        recursive_rename(get_tag_id(b.end), name="track %s end" % i,
                         sub_dir=tracks_dir, **kwargs)
        recursive_rename(get_tag_id(b.alternate_loop),
                         name="track %s alt loop" % i,
                         sub_dir=tracks_dir, **kwargs)
        recursive_rename(get_tag_id(b.alternate_end),
                         name="track %s alt end" % i,
                         sub_dir=tracks_dir, **kwargs)
        i += 1

    i = 0
    for b in meta.detail_sounds.STEPTREE:
        recursive_rename(get_tag_id(b.sound), name="detail sound %s" % i,
                         sub_dir=tracks_dir, **kwargs)
        i += 1


def rename_snd_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    sub_dir2, name2 = get_sound_sub_dir_and_name(meta, sub_dir, name)
    if not sub_dir: sub_dir = sub_dir2
    if (not name or "protected" in name) and name2: name = name2

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority'), kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.promotion_sound), halo_map,
                     tag_path_handler, root_dir, sub_dir,
                     name + "promo", **kwargs)


def rename_vcky(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = ui_dir
    if not name: name = "virtual kbd english"

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.display_font),
                     sub_dir=sub_dir, name="virtual kbd font", **kwargs)
    recursive_rename(get_tag_id(meta.special_key_labels_string_list),
                     sub_dir=sub_dir, name="virtual kbd key labels", **kwargs)

    kwargs.update(sub_dir=sub_dir + "virtual kbd bitmaps\\")
    recursive_rename(get_tag_id(meta.background_bitmap),
                     name="background", **kwargs)
    for b in meta.virtual_keys.STEPTREE:
        key_name = b.keyboard_key.enum_name
        recursive_rename(get_tag_id(b.unselected_background_bitmap),
                         name=key_name, **kwargs)
        recursive_rename(get_tag_id(b.selected_background_bitmap),
                         name="highlight " + key_name, **kwargs)
        recursive_rename(get_tag_id(b.active_background_bitmap),
                         name="select " + key_name, **kwargs)
        recursive_rename(get_tag_id(b.sticky_background_bitmap),
                         name="engaged " + key_name, **kwargs)


def rename_soul(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = ui_shell_dir
    if not name: name = "protected %s" % tag_id

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)
    for b in meta.ui_widget_definitions.STEPTREE:
        recursive_rename(get_tag_id(b.ui_widget_definition),
                         sub_dir=sub_dir, **kwargs)


def rename_tagc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', LOW_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(sub_dir=sub_dir + name + " references\\")
    for b in meta.tag_references.STEPTREE:
        recursive_rename(get_tag_id(b.tag), **kwargs)


def rename_trak(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    tag_path_handler.set_path(
        tag_id, root_dir + (sub_dir if sub_dir else camera_dir) + name,
        kwargs.get('priority', LOW_PRIORITY), kwargs.get("override"))


def rename_snde(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    tag_path_handler.set_path(
        tag_id, root_dir + (sub_dir if sub_dir else snd_sound_env_dir) + name,
        kwargs.get('priority', LOW_PRIORITY), kwargs.get("override"))


def rename_devc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir:
        sub_dir = ui_devc_def_dir
        kwargs.setdefault("priority", MEDIUM_PRIORITY)
    if not name:
        name = tag_path_handler.get_basename(tag_id)

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY),
                              kwargs.get("override"))


def rename_ligh(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_lights_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.lens_flare),
                     sub_dir=sub_dir, name=name + " lens flare", **kwargs)

    sub_dir = sub_dir + bitmaps_dir
    recursive_rename(get_tag_id(meta.gel_map.primary_cube_map),
                     sub_dir=sub_dir, name=name + " gel glow pri", **kwargs)
    recursive_rename(get_tag_id(meta.gel_map.secondary_cube_map),
                     sub_dir=sub_dir, name=name + " gel glow sec", **kwargs)


def rename_glw_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_lights_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.texture), name=name + " glow sprite",
                     sub_dir=sub_dir + bitmaps_dir, **kwargs)


def rename_lens(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_lens_flares_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.bitmaps.bitmap),
                     name=name + " bitmaps",
                     sub_dir=sub_dir + bitmaps_dir, **kwargs)


def rename_mgs2(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_lens_flares_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.map), name=name + " light vol map",
                     sub_dir=sub_dir + bitmaps_dir, **kwargs)


def rename_elec(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_lens_flares_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.bitmap), name=name + " electricity map",
                     sub_dir=sub_dir + bitmaps_dir, **kwargs)


def rename_part(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_particles_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.physics),
                     sub_dir=sub_dir + effects_dir, name=name, **kwargs)
    recursive_rename(get_tag_id(meta.impact_effect),
                     sub_dir=sub_dir + effects_dir,
                     name=name + " impact effect", **kwargs)
    recursive_rename(get_tag_id(meta.collision_effect),
                     sub_dir=sub_dir + effects_dir,
                     name=name + " collision", **kwargs)
    recursive_rename(get_tag_id(meta.death_effect),
                     sub_dir=sub_dir + effects_dir,
                     name=name + " death", **kwargs)

    recursive_rename(get_tag_id(meta.bitmap),
                     sub_dir=sub_dir + bitmaps_dir,
                     name=name + " sprite", **kwargs)
    recursive_rename(get_tag_id(meta.secondary_map.bitmap),
                     sub_dir=sub_dir + bitmaps_dir,
                     name=name + " sprite sec", **kwargs)


def rename_pctl(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_contrails_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.point_physics), sub_dir=sub_dir,
                     name=name + " default physics", **kwargs)
    i = 0
    for b in meta.particle_types.STEPTREE:
        t_name = name + " " + (b.name if b.name else "type %s" % i)

        j = 0
        for s in b.particle_states.STEPTREE:
            s_name = t_name + " " + (s.name if s.name else "state %s" % j)

            recursive_rename(get_tag_id(s.physics),
                             sub_dir=sub_dir + effects_dir,
                             name=s_name, **kwargs)
            recursive_rename(get_tag_id(s.bitmaps),
                             sub_dir=sub_dir + bitmaps_dir,
                             name=s_name + " bitmaps", **kwargs)
            recursive_rename(get_tag_id(s.secondary_map.bitmap),
                             sub_dir=sub_dir + bitmaps_dir,
                             name=s_name + " bitmaps sec", **kwargs)
            j += 1
        i += 1


def rename_cont(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effect_contrails_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.rendering.bitmap),
                     sub_dir=sub_dir + bitmaps_dir,
                     name=name + " sprite", **kwargs)
    recursive_rename(get_tag_id(meta.secondary_map.bitmap),
                     sub_dir=sub_dir + bitmaps_dir,
                     name=name + " sprite sec", **kwargs)

    for b in meta.point_states.STEPTREE:
        recursive_rename(get_tag_id(b.physics), sub_dir=sub_dir,
                         name=name, **kwargs)


def rename_jpt_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effects_dir + "damage\\"

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.sound), sub_dir=sub_dir,
                     name=name + " sfx", **kwargs)


def rename_effe(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = effects_dir
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)
    
    kwargs.update(halo_map=halo_map, sub_dir=sub_dir + name + " events\\",
                  root_dir=root_dir, tag_path_handler=tag_path_handler)
    
    i = 0
    event_name = ""
    for event in meta.events.STEPTREE:
        if len(meta.events.STEPTREE) > 1:
            event_name = "event %s " % i

        j = 0
        for b in event.parts.STEPTREE:
            recursive_rename(get_tag_id(b.type),
                             name=event_name + "part %s" % j, **kwargs)
            j += 1

        j = 0
        for b in event.particles.STEPTREE:
            recursive_rename(get_tag_id(b.particle_type),
                             name=event_name + "particle %s" % j, **kwargs)
            j += 1

        i += 1


def rename_multitex_overlay(block, name, overlay_name="", **kwargs):
    if block is None:
        return

    if overlay_name:
        name += " " + overlay_name
    else:
        name += " " + block.NAME

    recursive_rename(get_tag_id(block.primary_map), name=name + " pri", **kwargs)
    recursive_rename(get_tag_id(block.secondary_map), name=name + " sec", **kwargs)
    recursive_rename(get_tag_id(block.tertiary_map), name=name + " ter", **kwargs)


def rename_hud_background(block, name, background_name="", **kwargs):
    if block is None:
        return

    if background_name:
        name += " " + background_name
    else:
        name += " " + block.NAME.replace("background", "bg")

    recursive_rename(get_tag_id(block.interface_bitmap), name=name, **kwargs)
    for b in block.multitex_overlays.STEPTREE:
        rename_multitex_overlay(b, name, "static element", **kwargs)


def rename_grhi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = ui_hud_dir
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, tag_path_handler=tag_path_handler,
                  root_dir=root_dir, sub_dir=sub_dir + bitmaps_dir)

    rename_hud_background(meta.grenade_hud_background, name, **kwargs)
    rename_hud_background(meta.total_grenades.background, name, **kwargs)
    recursive_rename(get_tag_id(meta.total_grenades.overlay_bitmap),
                     name=name + " grenades overlay", **kwargs)

    kwargs.update(sub_dir=sub_dir + sounds_dir + name + "\\")
    for b in meta.warning_sounds.STEPTREE:
        snd_name = " "
        for flag_name in sorted(b.latched_to.NAME_MAP):
            if b.latched_to[flag_name]:
                snd_name += flag_name + " & "
        recursive_rename(get_tag_id(b.sound), name=snd_name.strip(" &"), **kwargs)


def rename_unhi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = ui_hud_dir
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, tag_path_handler=tag_path_handler,
                  root_dir=root_dir, sub_dir=sub_dir + bitmaps_dir)

    rename_hud_background(meta.unit_hud_background, name, **kwargs)
    rename_hud_background(meta.shield_panel_background, name, **kwargs)
    rename_hud_background(meta.health_panel_background, name, **kwargs)
    rename_hud_background(meta.motion_sensor_background, name, **kwargs)
    rename_hud_background(meta.motion_sensor_foreground, name, **kwargs)

    recursive_rename(get_tag_id(meta.health_panel_meter.meter_bitmap),
                     name="health meter", **kwargs)
    recursive_rename(get_tag_id(meta.shield_panel_meter.meter_bitmap),
                     name="shield meter", **kwargs)

    for b in meta.auxilary_overlays.STEPTREE:
        rename_hud_background(b.background, name, "flashlight meter", **kwargs)
        recursive_rename(get_tag_id(b.meter_bitmap),
                         name="flashlight meter", **kwargs)

    for b in meta.auxilary_overlays.STEPTREE:
        rename_hud_background(b.background, name, "flashlight overlay", **kwargs)

    kwargs.update(sub_dir=sub_dir + sounds_dir + name + "\\")
    for b in meta.warning_sounds.STEPTREE:
        snd_name = " "
        for flag_name in sorted(b.latched_to.NAME_MAP):
            if b.latched_to[flag_name]:
                snd_name += flag_name + " & "
        recursive_rename(get_tag_id(b.sound), name=snd_name.strip(" &"), **kwargs)


def rename_wphi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "protected %s" % tag_id
    if not sub_dir: sub_dir = ui_hud_dir
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, tag_path_handler=tag_path_handler,
                  root_dir=root_dir, )#sub_dir=sub_dir)

    recursive_rename(get_tag_id(meta.child_hud), name=name +
                     ("" if name.endswith("child") else " child"), **kwargs)

    kwargs.update(sub_dir=sub_dir + bitmaps_dir)
    for b in meta.static_elements.STEPTREE:
        rename_hud_background(b, name, "static elements", **kwargs)

    for b in meta.meter_elements.STEPTREE:
        recursive_rename(get_tag_id(b.meter_bitmap),
                         name=name + " meter element", **kwargs)

    for b in meta.crosshairs.STEPTREE:
        recursive_rename(get_tag_id(b.crosshair_bitmap),
                         name=name + " crosshair", **kwargs)

    for b in meta.overlay_elements.STEPTREE:
        recursive_rename(get_tag_id(b.overlay_bitmap),
                         name=name + " overlay", **kwargs)

    for b in meta.screen_effect.STEPTREE:
        recursive_rename(get_tag_id(b.mask.fullscreen_mask),
                         name=name + " fullscreen mask", **kwargs)
        recursive_rename(get_tag_id(b.mask.splitscreen_mask),
                         name=name + " splitscreen mask", **kwargs)


def rename_mply(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "multiplayer_scenarios"
    if not sub_dir: sub_dir = ui_dir
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)
    
    kwargs.update(halo_map=halo_map, tag_path_handler=tag_path_handler,
                  root_dir=root_dir, sub_dir=sub_dir + name + "\\")

    for b in meta.multiplayer_scenario_descriptions.STEPTREE:
        name = sanitize_name(b.scenario_tag_directory_path).split("\\")[-1]
        recursive_rename(get_tag_id(b.descriptive_bitmap), name=name, **kwargs)
        recursive_rename(get_tag_id(b.displayed_map_name), name=name, **kwargs)


def rename_ngpr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    meta_name = sanitize_name(meta.name)
    if not name: name = meta_name if meta_name else "protected %s" % tag_id
    if not sub_dir: sub_dir = ui_shell_dir + "netgame_prefs\\"

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.pattern), sub_dir=sub_dir + bitmaps_dir,
                     name=name + " pattern", **kwargs)
    recursive_rename(get_tag_id(meta.decal), sub_dir=sub_dir + bitmaps_dir,
                     name=name + " decal", **kwargs)


def rename_hud_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not name: name = "counter"
    if not sub_dir: sub_dir = ui_hud_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', DEFAULT_PRIORITY)
    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs['priority'], kwargs.get("override"))
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    recursive_rename(get_tag_id(meta.digits_bitmap), sub_dir=sub_dir,
                     name=name + " digits", **kwargs)

'''
def rename_avtc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_atvi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_atvo(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_efpc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_efpg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_shpg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sily(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_unic(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
'''

recursive_rename_functions = dict(
    scenario = rename_scnr,
    scenario_structure_bsp = rename_sbsp,
    detail_object_collection = rename_dobc,

    project_yellow = rename_yelo,
    project_yellow_globals = rename_gelo,
    project_yellow_globals_cv = rename_gelc,
    globals = rename_matg,
    hud_globals = rename_hudg,

    grenade_hud_interface = rename_grhi,
    weapon_hud_interface = rename_wphi,
    unit_hud_interface = rename_unhi,

    input_device_defaults = rename_devc,
    ui_widget_definition = rename_DeLa,
    virtual_keyboard = rename_vcky,

    hud_number = rename_hud_,
    multiplayer_scenario_description = rename_mply,
    preferences_network_game = rename_ngpr,

    tag_collection = rename_tagc,
    ui_widget_collection = rename_soul,

    camera_track = rename_trak,
    actor_variant = rename_actv,

    biped = rename_obje,
    vehicle = rename_obje,
    weapon = rename_obje,
    equipment = rename_obje,
    garbage = rename_obje,
    projectile = rename_obje,
    scenery = rename_obje,
    device_machine = rename_obje,
    device_control = rename_obje,
    device_light_fixture = rename_obje,
    placeholder = rename_obje,
    sound_scenery = rename_obje,

    sound = rename_snd_,
    sound_looping = rename_lsnd,
    dialogue = rename_udlg,
    sound_environment = rename_snde,

    effect = rename_effe,
    glow = rename_glw_,
    light = rename_ligh,
    light_volume = rename_mgs2,
    lightning = rename_elec,
    lens_flare = rename_lens,
    antenna = rename_ant_,
    flag = rename_flag,

    weather_particle_system = rename_rain,
    sky = rename_sky_,
    fog = rename_fog_,

    model_collision_geometry = rename_coll,

    material_effects = rename_foot,
    particle_system = rename_pctl,
    particle = rename_part,
    contrail = rename_cont,

    decal = rename_deca,
    damage_effect = rename_jpt_,

    gbxmodel = rename_mode,
    model = rename_mode,

    model_animations = rename_antr,
    model_animations_yelo = rename_antr,

    shader_transparent_chicago = rename_shdr,
    shader_transparent_chicago_extended = rename_shdr,
    shader_transparent_generic = rename_shdr,
    shader_environment = rename_shdr,
    shader_transparent_glass = rename_shdr,
    shader_transparent_meter = rename_shdr,
    shader_model = rename_shdr,
    shader_transparent_plasma = rename_shdr,
    shader_transparent_water = rename_shdr,
    )
