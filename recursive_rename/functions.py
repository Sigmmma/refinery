from reclaimer.enums import materials_list
from refinery.recursive_rename.constants import *
from traceback import format_exc

VERY_HIGH_PRIORITY = 10.0
VEHICLE_WEAP_PRIORITY = 5.0
NAMED_OBJE_PRIORITY = 4.0
SCNR_BSPS_PRIORITY = 2.5
SCNR_PALETTES_PRIORITY = 1.5
MATG_REFS_PRIORITY = 1.5
DEFAULT_PRIORITY = 1.0


def sanitize_name(name):
    for c in ':*?"<>|':
        name = name.replace(c, '')
    return name.lower().replace('/', '\\').strip()


def get_tag_id(tag_ref):
    if tag_ref.id[0] == 0xFFFF and tag_ref.id[1] == 0xFFFF:
        return None
    return tag_ref.id[0]


def recursive_rename(tag_id, halo_map, tag_path_handler,
                     root_dir="", sub_dir="", name="", **kwargs):
    if tag_id is None or tag_id > len(halo_map.tag_index.tag_index):
        return

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
                                  kwargs.get("priority", 0.5))


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

    tag_path_handler.set_path(
        tag_id, root_dir + level_dir + name, INF)
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # rename the open sauce stuff
    try:
        recursive_rename(
            get_tag_id(meta.project_yellow_definitions),
            priority=INF, name=name, sub_dir=level_dir + globals_dir, **kwargs)
    except AttributeError:
        pass

    # rename the references at the bottom of the scenario tag
    tag_path_handler.set_path(
        get_tag_id(meta.custom_object_names), level_dir + "object_names", INF)

    tag_path_handler.set_path(
        get_tag_id(meta.ingame_help_text), level_dir + "help_text", INF)

    tag_path_handler.set_path(
        get_tag_id(meta.hud_messages), level_dir + "hud_messages", INF)

    # rename sky references
    i = 0
    for b in meta.skies.STEPTREE:
        recursive_rename(get_tag_id(b.sky), sub_dir=level_dir,
                         name="sky %s" % i, **kwargs)
        i += 1

    devices_dir = level_dir + level_devices_dir
    palette_renames = (
        ("machines_palette", devices_dir + "machines\\"),
        ("controls_palette", devices_dir + "controls\\"),
        ("light_fixtures_palette", devices_dir + "light fixtures\\"),
        ("sound_sceneries_palette", level_dir + 'sfx emitters\\'),
        ("decals_palette", level_dir + 'decals\\'),
        ("detail_object_collection_palette", level_dir + 'detail objects\\'),
        ("actors_palette", level_dir + "actors\\"),
        )

    # do deep renaming
    if kwargs.get("deep_rename", True):
        palette_renames += (
            ("sceneries_palette", level_dir + scenery_dir),
            ("bipeds_palette", characters_dir),
            ("vehicles_palette", vehicles_dir),
            ("equipments_palette", powerups_dir),
            ("weapons_palette", weapons_dir)
            )

        # rename player starting weapon references
        for profile in meta.player_starting_profiles.STEPTREE:
            rename_weap(get_tag_id(profile.primary_weapon),
                        sub_dir=weapons_dir, **kwargs)
            rename_weap(get_tag_id(profile.secondary_weapon),
                        sub_dir=weapons_dir, **kwargs)

        item_coll_dir = level_dir + level_item_coll_dir

        # netgame flags
        i = 0
        for b in meta.netgame_flags.STEPTREE:
            recursive_rename(
                get_tag_id(b.weapon_group), sub_dir=item_coll_dir,
                name="ng flag", priority=SCNR_PALETTES_PRIORITY, **kwargs)
            i += 1

        # netgame equipment
        i = 0
        for b in meta.netgame_equipments.STEPTREE:
            recursive_rename(
                get_tag_id(b.item_collection), sub_dir=item_coll_dir,
                name="ng equipment", priority=SCNR_PALETTES_PRIORITY, **kwargs)
            i += 1

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
                    priority=SCNR_PALETTES_PRIORITY, **kwargs)
                j += 1
            i += 1

    # rename palette references
    for b_name, sub_dir in palette_renames:
        palette_array = meta[b_name].STEPTREE

        for i in range(len(palette_array)):
            sub_name = "protected %s" % tag_id
            recursive_rename(get_tag_id(palette_array[i].name),
                             sub_dir=sub_dir + sub_name + "\\", name=sub_name,
                             priority=SCNR_PALETTES_PRIORITY, **kwargs)

    # rename animation references
    i = 0
    for b in meta.ai_animation_references.STEPTREE:
        anim_name = sanitize_name(b.animation_name)
        if not anim_name:
            anim_name = "ai anim"

        recursive_rename(get_tag_id(b.animation_graph), name=anim_name,
                         sub_dir=level_dir + cinematics_dir + "animations\\",
                         priority=SCNR_PALETTES_PRIORITY, **kwargs)
        i += 1

    # rename bsp references
    bsp_name = ('%s_' % name) + '%s'
    for b in meta.structure_bsps.STEPTREE:
        recursive_rename(get_tag_id(b.structure_bsp),
                         priority=SCNR_BSPS_PRIORITY,
                         sub_dir=level_dir, name=bsp_name, **kwargs)

    # final deep renaming
    if kwargs.get("deep_rename", True):
        # rename ai conversation sounds
        i = 0
        conv_dir = level_dir + "ai convos\\"
        for b in meta.ai_conversations.STEPTREE:
            j = 0
            conv_name = sanitize_name(b.name)
            if not conv_name:
                conv_name = "conv %s " % i

            for b in b.lines.STEPTREE:
                line = conv_name + "line %s " % j
                for k in range(1, 7):
                    recursive_rename(
                        get_tag_id(b['variant %s' % i]), sub_dir=conv_dir,
                        priority=SCNR_PALETTES_PRIORITY, name=line, **kwargs)
                j += 1
            i += 1

        # rename tag references
        kwargs['priority'] = 0.6
        for b in meta.references.STEPTREE:
            recursive_rename(
                get_tag_id(b.reference), name="tag reference",
                sub_dir=level_dir + "reffed tags\\", **kwargs)


def rename_matg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = globals_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  priority=MATG_REFS_PRIORITY,
                  tag_path_handler=tag_path_handler)
    kwargs_no_priority = dict(kwargs)
    kwargs_no_priority.pop('priority')

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif not name:
        name = 'globals'

    # rename this globals tag
    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs['priority'])
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
        g_dir = weapons_dir + "grenade_%s\\" % i
        g_name = "grenade_%s" % i

        eqip_tag_id = get_tag_id(b.equipment)
        g_priority = 1.5
        recursive_rename(eqip_tag_id, sub_dir=g_dir, name=g_name,
                         priority=g_priority, **kwargs_no_priority)
        if eqip_tag_id is not None:
            g_dir = tag_path_handler.get_sub_dir(eqip_tag_id, root_dir)
            g_name = tag_path_handler.get_basename(eqip_tag_id)
            g_priority = tag_path_handler.get_priority(eqip_tag_id)

        recursive_rename(get_tag_id(b.throwing_effect), sub_dir=g_dir,
                         name=g_name + "_throw", priority=g_priority,
                         **kwargs_no_priority)
        recursive_rename(get_tag_id(b.hud_interface), sub_dir=g_dir,
                         name=g_name + "_hud", priority=g_priority,
                         **kwargs_no_priority)
        recursive_rename(get_tag_id(b.projectile), sub_dir=g_dir,
                         name=g_name + "_projectile", priority=g_priority,
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
                         sub_dir="characters\\player\\", **kwargs_no_priority)

    for b in meta.player_informations.STEPTREE:
        recursive_rename(get_tag_id(b.unit), name="player_sp",
                         priority=VERY_HIGH_PRIORITY,
                         sub_dir="characters\\player\\", **kwargs_no_priority)
        recursive_rename(get_tag_id(b.coop_respawn_effect),
                         priority=VERY_HIGH_PRIORITY, sub_dir=effects_dir,
                         name="coop teleport", **kwargs_no_priority)

    for b in meta.first_person_interfaces.STEPTREE:
        recursive_rename(get_tag_id(b.first_person_hands),
                         sub_dir="characters\\player\\fp\\", name="fp",
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
    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs['priority'])
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
    for b in meta.references.STEPTREE:
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
    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs['priority'])
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # rename the explicit references
    recursive_rename(get_tag_id(meta.global_explicit_references),
                     name="global references", **kwargs)

    # rename the chokin victim globals
    sub_id = get_tag_id(meta.chokin_victim_globals)
    if sub_id is not None:
        recursive_rename(sub_id, sub_dir=sub_dir,
                         name="yelo globals cv", **kwargs)

    # rename scripted ui widget references
    kwargs['priority'], i = 0.6, 0
    widgets_dir = ui_dir + "yelo widgets\\"
    for b in meta.references.STEPTREE:
        widget_name = sanitize_name(b.name)
        if not widget_name:
            widget_name = "g scripted ui widget %s" % i
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
    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs['priority'])
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    # I'm not typing up the rest of this right now. Might be pointless anyway.


def rename_hudg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir=ui_hud_dir, name="", **kwargs):
    if not sub_dir: sub_dir = ui_hud_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sbsp(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sky_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_itmc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)




def rename_obje(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    obje_attrs = meta.obje_attrs
    obje_type = obje_attrs.object_type.enum_name

    if not name:
        if obje_type in ("weap", "eqip"):
            name = tag_path_handler.get_item_string(
                meta.item_attrs.message_index)
        elif obje_type == "vehi":
            name = tag_path_handler.get_icon_string(
                meta.obje_attrs.hud_text_message_index)

        if name:
            # up the priority if we could detect a name for
            # this in the strings for the weapon or vehicles
            kwargs.setdefault('priority', NAMED_OBJE_PRIORITY)
        else:
            kwargs.setdefault('priority', DEFAULT_PRIORITY)
            name = "protected %s" % tag_id

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

        sub_dir += name +  "\\"

    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs.get('priority')
        )

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
                     sub_dir=sub_dir, name="creation effect", **kwargs)

    # not as sure about everything below, so lower priority
    kwargs['priority'] = DEFAULT_PRIORITY
    recursive_rename(get_tag_id(obje_attrs.modifier_shader),
                     sub_dir=sub_dir, name="modifier shader", **kwargs)

    # THIS IS NOT RENAMING PROJECTILE CONTRAILS FOR THE SENTINEL ACTORS WEAPON
    for b in obje_attrs.attachments.STEPTREE:
        recursive_rename(get_tag_id(b.type),
                         sub_dir=sub_dir + obje_effects_dir, **kwargs)

    for b in obje_attrs.widgets.STEPTREE:
        recursive_rename(get_tag_id(b.reference),
                         sub_dir=sub_dir + "widgets\\", **kwargs)


def rename_shdr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = shared_dir + obje_shaders_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs.get('priority')
        )

    name = tag_path_handler.get_basename(tag_id)
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    sub_dir = "\\".join(sub_dir.split("\\")[: -2])
    if sub_dir: sub_dir += "\\"
    sub_dir += bitmaps_dir

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  sub_dir=sub_dir, tag_path_handler=tag_path_handler)


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
                         sub_dir=sub_dir + "sounds\\",
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
                     sub_dir=sub_dir, name="melee damage", **kwargs)
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
    kwargs['priority'] = kwargs.get('priority', 0) + 0.5
    for trig in weap_attrs.triggers.STEPTREE:
        trig_str = ""
        if len(weap_attrs.triggers.STEPTREE) > 1:
            trig_str = "secondary " if i else "primary "
            
        recursive_rename(
            get_tag_id(trig.charging.charging_effect),
            name="%scharging" % trig_str,
            sub_dir=sub_dir + obje_effects_dir, **kwargs)
        recursive_rename(
            get_tag_id(trig.projectile.projectile),
            name="%sprojectile" % trig_str, sub_dir=sub_dir, **kwargs)

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
    weap_kwargs['priority'] = VEHICLE_WEAP_PRIORITY

    recursive_rename(get_tag_id(unit_attrs.integrated_light_toggle),
                     sub_dir=sub_dir + obje_effects_dir,
                     name="integrated_light_toggle", **kwargs)


    # not checking spawned_actor
    recursive_rename(get_tag_id(unit_attrs.melee_damage),
                     sub_dir=sub_dir, name="melee_impact_damage", **kwargs)

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
            sub_dir=sub_dir, name=name + "_dialogue", **kwargs)


    trak_kwargs = dict(kwargs)
    trak_kwargs["priority"] = DEFAULT_PRIORITY
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
                         sub_dir=sub_dir, name="built_in_gunner", **kwargs)


    if bipd_attrs:
        recursive_rename(get_tag_id(bipd_attrs.movement.footsteps),
                         sub_dir=sub_dir, name="footsteps", **kwargs)

        i = 0
        for weap in weap_array:
            gun_id = get_tag_id(weap.weapon)
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
            i += 1


    if vehi_attrs:
        recursive_rename(get_tag_id(vehi_attrs.suspension_sound),
                         sub_dir=sub_dir, name="suspension_sound", **kwargs)
        recursive_rename(get_tag_id(vehi_attrs.crash_sound),
                         sub_dir=sub_dir, name="crash_sound", **kwargs)
        recursive_rename(get_tag_id(vehi_attrs.effect),
                         sub_dir=sub_dir, name="unknown_effect", **kwargs)

        vehi_dir = '\\'.join(sub_dir.split('\\')[: -2])
        if vehi_dir: vehi_dir += "\\"
        recursive_rename(get_tag_id(vehi_attrs.material_effect),
                         sub_dir=vehi_dir, name="material_effects", **kwargs)

        for i in range(len(weap_array)):
            gun_name = name + " gun"
            if len(weap_array) > 1:
                gun_name += " %s" % i

            recursive_rename(
                get_tag_id(weap_array[i].weapon), name=gun_name,
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
        


def rename_actr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_actv(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_flag(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mode(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = shared_dir

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return

    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name, kwargs.get('priority')
        )
    sub_dir = tag_path_handler.get_sub_dir(tag_id, root_dir)
    name = tag_path_handler.get_basename(tag_id)

    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  sub_dir=sub_dir + shaders_dir,
                  tag_path_handler=tag_path_handler)


    shader_names = {}
    for i in range(len(meta.regions.STEPTREE)):
        region = meta.regions.STEPTREE[i]
        geoms = []

        region_name = region.name.replace("__unnamed", "").replace(' ', '').strip("_")
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
        shader_name = shader_names.get(i, "").replace("_", " ").strip()
        recursive_rename(get_tag_id(meta.shaders.STEPTREE[i].shader),
                         name=shader_name.strip(), **kwargs)


def rename_coll(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_foot(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_effe(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_grhi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_unhi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_wphi(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ligh(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_rain(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_fog_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


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


def rename_antr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_deca(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ant_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_cont(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_jpt_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_dobc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_udlg(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_glw_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_hud_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_lens(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mgs2(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_elec(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mply(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_part(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_pctl(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ngpr(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_lsnd(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_DeLa(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    if not sub_dir: sub_dir = ui_shell_dir

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY))


def rename_snd_(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_vcky(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = ui_dir
    if not name: name = "english"

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', 0.5))

def rename_trak(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = camera_dir

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', 0.5))

def rename_snde(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = snd_sound_env_dir

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', 0.5))

def rename_devc(tag_id, halo_map, tag_path_handler,
                root_dir="", sub_dir="", name="", **kwargs):
    if not sub_dir: sub_dir = ui_devc_def_dir

    tag_path_handler.set_path(tag_id, root_dir + sub_dir + name,
                              kwargs.get('priority', DEFAULT_PRIORITY))


recursive_rename_functions = dict(
    scenario = rename_scnr,

    project_yellow = rename_yelo,
    project_yellow_globals = rename_gelo,
    project_yellow_globals_cv = rename_gelc, #
    globals = rename_matg, #
    hud_globals = rename_hudg, #

    input_device_defaults = rename_devc,
    ui_widget_definition = rename_DeLa, #
    virtual_keyboard = rename_vcky, #

    biped = rename_obje, #
    vehicle = rename_obje, #
    weapon = rename_obje, #
    equipment = rename_obje, #
    garbage = rename_obje, #
    projectile = rename_obje, #
    scenery = rename_obje, #
    device_machine = rename_obje, #
    device_control = rename_obje, #
    device_light_fixture = rename_obje, #
    placeholder = rename_obje, #
    sound_scenery = rename_obje, #
    
    camera_track = rename_trak, #
    sound_environment = rename_snde, #

    gbxmodel = rename_mode, #
    model = rename_mode, #

    shader_transparent_chicago = rename_shdr, #
    shader_transparent_chicago_extended = rename_shdr, #
    shader_transparent_generic = rename_shdr, #
    shader_environment = rename_shdr, #
    shader_transparent_glass = rename_shdr, #
    shader_transparent_meter = rename_shdr, #
    shader_model = rename_shdr, #
    shader_transparent_plasma = rename_shdr, #
    shader_transparent_water = rename_shdr, #
    )
'''
    scenario_structure_bsp = rename_sbsp, #
    sky = rename_sky_, #

    item_collection = rename_itmc, #

    actor = rename_actr, #
    actor_variant = rename_actv, #

    flag = rename_flag, #
    model_collision_geometry = rename_coll, #

    material_effects = rename_foot, #

    effect = rename_effe, #

    grenade_hud_interface = rename_grhi, #
    unit_hud_interface = rename_unhi, #
    weapon_hud_interface = rename_wphi, #

    light = rename_ligh, #
    weather_particle_system = rename_rain, #
    fog = rename_fog_, #

    actor_variant_transform_collection = rename_avtc, #
    actor_variant_transform_in = rename_atvi, #
    actor_variant_transform_out = rename_atvo, #

    effect_postprocess_collection = rename_efpc, #
    effect_postprocess_generic = rename_efpg, #
    shader_postprocess_generic = rename_shpg, #


    text_value_pair_definition = rename_sily, #
    multilingual_unicode_string_list = rename_unic, #

    model_animations = rename_antr, #
    model_animations_yelo = rename_antr, #

    decal = rename_deca, #
    antenna = rename_ant_, #
    contrail = rename_cont, #
    damage_effect = rename_jpt_, #
    detail_object_collection = rename_dobc, #
    dialogue = rename_udlg, #
    glow = rename_glw_, #
    hud_number = rename_hud_, #
    lens_flare = rename_lens, #
    light_volume = rename_mgs2, #
    lightning = rename_elec, #
    multiplayer_scenario_description = rename_mply, #
    particle = rename_part, #
    particle_system = rename_pctl, #
    preferences_network_game = rename_ngpr, #
    sound_looping = rename_lsnd, #

    sound = rename_snd_, #
    )

'''
