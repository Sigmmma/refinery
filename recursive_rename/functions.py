from refinery.recursive_rename.constants import *


def rename_scnr(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif name is None:
        name = sanitize_name(halo_map.map_header.map_name)

    level_dir = sub_dir + '%s\\' % name

    tag_path_handler.set_path(
        tag_id, root_dir + level_dir + name + ".scenario", INF)

    # rename the open sauce stuff
    try: sub_id = get_tag_id(meta.project_yellow_definitions)
    except AttributeError: sub_id = None

    if sub_id is not None:
        rename_yelo(
            sub_id, sub_dir=level_dir + globals_dir,
            name=name, priority=INF, **kwargs)

    # rename the references at the bottom of the scenario tag
    sub_id = get_tag_id(meta.custom_object_names)
    if sub_id is not None:
        tag_path_handler.set_path(
            sub_id, level_dir + "object_names.unicode_string_list", INF)

    sub_id = get_tag_id(meta.ingame_help_text)
    if sub_id is not None:
        tag_path_handler.set_path(
            sub_id, level_dir + "help_text.unicode_string_list", INF)

    sub_id = get_tag_id(meta.hud_messages)
    if sub_id is not None:
        tag_path_handler.set_path(
            sub_id, level_dir + "hud_messages.hud_message_text", INF)

    # rename sky references
    i = 0
    for b in meta.skies.STEPTREE:
        sub_id = get_tag_id(b.sky)
        if sub_id is not None:
            rename_sky_(sub_id, sub_dir=level_dir, name='sky_%s' % i, **kwargs)
            i += 1

    devices_dir = level_dir + level_devices_dir
    palette_renames = (
        ("machines_palette", devices_dir, rename_mach),
        ("controls_palette", devices_dir, rename_ctrl),
        ("light_fixtures_palette", devices_dir, rename_lifi),
        ("sound_sceneries_palette", level_dir + 'sfx_emitters\\', rename_ssce),
        ("decals_palette", level_dir + 'decals\\', rename_deca),
        ("detail_object_collection_palette", level_dir + 'detail_objects\\', rename_dobc),
        ("actors_palette", characters_dir, rename_actv),
        )

    # do deep renaming
    if kwargs.get("deep_rename"):
        palette_renames += (
            ("sceneries_palette", scenery_dir, rename_scen),
            ("bipeds_palette", characters_dir, rename_bipd),
            ("vehicles_palette", vehicles_dir, rename_vehi),
            ("equipments_palette", powerups_dir, rename_item),
            ("weapons_palette", weapons_dir, rename_weap)
            )

        # rename player starting weapon references
        for profile in meta.player_starting_profiles.STEPTREE:
            pri_weap_id = get_tag_id(profile.primary_weapon)
            sec_weap_id = get_tag_id(profile.secondary_weapon)

            if pri_weap_id is not None:
                rename_weap(pri_weap_id, sub_dir=weapons_dir, **kwargs)
            if sec_weap_id is not None:
                rename_weap(sec_weap_id, sub_dir=weapons_dir, **kwargs)

        item_coll_dir = level_dir + item_coll_dir

        # netgame flags
        i = 0
        for b in meta.netgame_flags.STEPTREE:
            sub_id = get_tag_id(b.weapon_group)
            if sub_id is not None:
                rename_itmc(sub_id, sub_dir=item_coll_dir,
                            name="ng_flag_%s" % i, **kwargs)
                i += 1

        # netgame equipment
        i = 0
        for b in meta.netgame_equipments.STEPTREE:
            sub_id = get_tag_id(b.item_collection)
            if sub_id is not None:
                rename_itmc(sub_id, sub_dir=item_coll_dir,
                            name="ng_equipment_%s" % i, **kwargs)
                i += 1

        # starting equipment
        i = 0
        for b in meta.starting_equipments.STEPTREE:
            j = 0
            profile_name = sanitize_name(b.name)
            if not profile_name:
                profile_name = "start_equipment_%s" % i

            for i in range(1, 7):
                sub_id = get_tag_id(b['item_collection_%s' % i])
                if sub_id is not None:
                    rename_itmc(sub_id, sub_dir=item_coll_dir,
                                name="%s_s" % (profile_name, j), **kwargs)
                    j += 1
            i += 1

    # rename palette references
    for b_name, sub_dir, renamer in palette_renames:
        palette_array = meta[b_name].STEPTREE

        for i in range(len(palette_array)):
            sub_id = get_tag_id(palette_array[i].name)
            if sub_id is not None:
                renamer(sub_id, sub_dir=sub_dir, name='%s' % i, **kwargs)

    # rename animation references
    i = 0
    for b in meta.ai_animation_references.STEPTREE:
        sub_id = get_tag_id(b.animation_graph)
        if sub_id is not None:
            anim_name = sanitize_name(b.animation_name)
            if not anim_name:
                anim_name = "ai_anim_%s" % i

            rename_antr(sub_id, sub_dir=level_dir + cinematics_dir,
                        name=anim_name, **kwargs)
            i += 1

    # rename bsp references
    i = 0
    bsp_name = ('%s_' % name) + '%s'
    for b in meta.structure_bsps.STEPTREE:
        sub_id = get_tag_id(b.structure_bsp)
        if sub_id is not None:
            rename_sbsp(sub_id, sub_dir=level_dir, name=bsp_name % i, **kwargs)
            i += 1

    # final deep renaming
    if kwargs.get("deep_rename"):
        # rename ai conversation sounds
        i = 0
        conv_dir = level_dir + "ai_conversations\\"
        for b in meta.ai_conversations.STEPTREE:
            j = 0
            conv_name = sanitize_name(b.name)
            if not conv_name:
                conv_name = "conv_%s_" % i

            for b in b.lines.STEPTREE:
                line_name = "line_%s_" % j
                for k in range(1, 7):
                    sub_id = get_tag_id(b['variant_%s' % i])
                    if sub_id is not None:
                        rename_snd_(sub_id, sub_dir=conv_dir, name="%s%s_%s" %
                                    (conv_name, line_name, k), **kwargs)
                j += 1
            i += 1

        # rename tag references
        kwargs['priority'], i = 0.1, 0
        for b in meta.references.STEPTREE:
            sub_id = get_tag_id(b.reference)
            if sub_id is not None:

                recursive_rename_functions[b.tag_class.enum_name](
                    sub_id, sub_dir=None, name="tag_reference_%s", **kwargs)
                i += 1


def rename_yelo(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', INF)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif name is None:
        name = 'yelo'

    # rename this project_yellow tag
    tag_path_handler.set_path(
        tag_id, root_dir+sub_dir+name+".project_yellow", kwargs['priority'])

    # rename the yelo globals
    sub_id = get_tag_id(meta.yelo_globals)
    if sub_id is not None:
        rename_gelo(sub_id, sub_dir=sub_dir, name='yelo_globals', **kwargs)

    # rename the globals override
    sub_id = get_tag_id(meta.globals_override)
    if sub_id is not None:
        rename_matg(sub_id, sub_dir=sub_dir, name='globals', **kwargs)

    # rename the explicit references
    sub_id = get_tag_id(meta.scenario_explicit_references)
    if sub_id is not None:
        tag_path_handler.set_path(
            tag_id, root_dir + sub_dir + "scenario_references.tag_collection",
            kwargs['priority'])

    # rename scripted ui widget references
    kwargs['priority'], i = 0.1, 0
    widgets_dir = ui_dir + "yelo_widgets\\"
    for b in meta.references.STEPTREE:
        sub_id = get_tag_id(b.definition)
        if sub_id is not None:
            widget_name = sanitize_name(b.name)
            if not widget_name:
                widget_name = "y_scripted_ui_widget_%s" % i
            rename_DeLa(sub_id, sub_dir=widgets_dir, name=widget_name, **kwargs)
            i += 1


def rename_gelo(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', INF)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif name is None:
        name = 'yelo_globals'

    # rename this project_yellow_globals tag
    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name + ".project_yellow_globals",
        kwargs['priority'])

    # rename the explicit references
    sub_id = get_tag_id(meta.global_explicit_references)
    if sub_id is not None:
        tag_path_handler.set_path(
            tag_id, root_dir + sub_dir + "global_references.tag_collection",
            kwargs['priority'])

    # rename the chokin victim globals
    sub_id = get_tag_id(meta.chokin_victim_globals)
    if sub_id is not None:
        rename_gelc(sub_id, sub_dir=sub_dir, name='yelo_globals_cv', **kwargs)

    # rename scripted ui widget references
    kwargs['priority'], i = 0.1, 0
    widgets_dir = ui_dir + "yelo_widgets\\"
    for b in meta.references.STEPTREE:
        sub_id = get_tag_id(b.definition)
        if sub_id is not None:
            widget_name = sanitize_name(b.name)
            if not widget_name:
                widget_name = "g_scripted_ui_widget_%s" % i
            rename_DeLa(sub_id, sub_dir=widgets_dir, name=widget_name, **kwargs)
            i += 1


def rename_gelc(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)
    kwargs.setdefault('priority', INF)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif name is None:
        name = 'yelo_globals_cv'

    # rename this project_yellow_globals tag
    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name + ".project_yellow_globals_cv",
        kwargs['priority'])

    # I'm not typing up the rest of this right now. Might be pointless anyway.


def rename_matg(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=globals_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

    meta = halo_map.get_meta(tag_id)
    if meta is None:
        return
    elif name is None:
        name = 'globals'

    tag_path_handler.set_path(
        tag_id, root_dir + sub_dir + name + ".globals",
        kwargs.get('priority', 1.0))

    ###############################################
    ''' FINISH UP THE 65 TAG REFERENCES IN HERE '''
    ###############################################


def rename_hudg(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=ui_hud_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sbsp(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sky_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_itmc(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_weap(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_item(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_garb(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_proj(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_plac(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ssce(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_scen(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_devi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ctrl(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_lifi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mach(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_vehi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_bipd(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_actr(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_actv(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_flag(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mod2(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mode(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_coll(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_foot(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_effe(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_grhi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_unhi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_wphi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ligh(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_rain(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_fog_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_avtc(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_atvi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_atvo(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_efpc(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_efpg(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_shpg(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sily(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_unic(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_antr(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_schi(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_scex(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_sotr(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_senv(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)

def rename_sgla(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_smet(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_soso(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_spla(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_swat(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_deca(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ant_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_cont(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_jpt_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_dobc(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_udlg(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_glw_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_hud_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_lens(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mgs2(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_elec(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_mply(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_part(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_pctl(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_ngpr(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_lsnd(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_DeLa(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_vcky(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


def rename_snd_(tag_id, halo_map, tag_path_handler,
                root_dir='', sub_dir=levels_dir, name=None, **kwargs):
    kwargs.update(halo_map=halo_map, root_dir=root_dir,
                  tag_path_handler=tag_path_handler)


recursive_rename_functions = dict(
    scenario = rename_scnr,

    project_yellow = rename_yelo,
    project_yellow_globals = rename_gelo,
    project_yellow_globals_cv = rename_gelc, #
    globals = rename_matg, #
    hud_globals = rename_hudg, #
    )
'''
    scenario_structure_bsp = rename_sbsp, #
    sky = rename_sky_, #

    item_collection = rename_itmc, #

    weapon = rename_weap, #
    equipment = rename_item, #
    garbage = rename_garb, #

    projectile = rename_proj, #
    placeholder = rename_plac, #
    sound_scenery = rename_ssce, #
    scenery = rename_scen, #
    device_control = rename_devi, #
    device_light_fixture = rename_lifi, #
    device_machine = rename_mach, #

    vehicle = rename_vehi, #

    biped = rename_bipd, #
    actor = rename_actr, #
    actor_variant = rename_actv, #

    flag = rename_flag, #

    gbxmodel = rename_mod2, #
    model = rename_mode, #
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

    shader_transparent_chicago = rename_schi, #
    shader_transparent_chicago_extended = rename_scex, #
    shader_transparent_generic = rename_sotr, #
    shader_environment = rename_senv, #
    shader_transparent_glass = rename_sgla, #
    shader_transparent_meter = rename_smet, #
    shader_model = rename_soso, #
    shader_transparent_plasma = rename_spla, #
    shader_transparent_water = rename_swat, #

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
    ui_widget_definition = rename_DeLa, #
    virtual_keyboard = rename_vcky, #

    sound = rename_snd_, #
    )'''
