#
# This file is part of Refinery.
#
# For authors and copyright check AUTHORS.TXT
#
# Refinery is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import re
from refinery.util import sanitize_win32_path
from refinery.heuristic_deprotection import constants as const


INVALID_NAME_CHAR_SUB       = re.compile(r'[~\\/]')
REDUCE_ID_DIV_NAME_SUB      = re.compile(r'[-_\s.<>{};:\'"|=+`!@#$%^&*()[\]]+')
REMOVE_PERM_AND_TRAIL_SUB   = re.compile(r'^_|[\d_]+$')


class MinPriority:
    _val = const.INF
    @property
    def val(self): return self._val
    @val.setter
    def val(self, new_val): self._val = min(new_val, self.val)


def sanitize_name(name):
    return INVALID_NAME_CHAR_SUB.sub(
        '', str(sanitize_win32_path(name))
        ).lower().strip()


def sanitize_name_piece(name, default_name):
    name = sanitize_name(name)
    return name if name else default_name


def get_tag_id(tag_ref):
    if tag_ref.id == 0xFFffFFff:
        return None
    return tag_ref.id & 0xFFff


def join_names(names, max_len=100):
    if len(names) == 1:
        return names[0]
    elif not names:
        return ""

    name = " & ".join(names)
    if len(name) > max_len:
        name = " & ".join(name[: max_len + 2].split(" & ")[: -1]).rstrip(" &")
    return name


def sanitize_model_or_sound_name(name, def_name=''):
    name = REMOVE_PERM_AND_TRAIL_SUB.sub('', 
        REDUCE_ID_DIV_NAME_SUB.sub('_', sanitize_name(name)
        ))
    return def_name if name in const.INVALID_MODEL_NAMES else name


def get_model_name(meta=None, halo_map=None, tag_id=None, name=""):
    if meta is None:
        meta = halo_map.get_meta(tag_id)

    regions = getattr(meta, "regions", None)
    nodes   = getattr(meta, "nodes", None)
    node_name = perm_name = region_name = ""
    if regions and regions.STEPTREE:
        names = []
        for region in regions.STEPTREE:
            for perm in region.permutations.STEPTREE:
                perm_name = sanitize_model_or_sound_name(perm.name, perm_name)
                if perm_name: break

        if len(regions.STEPTREE) == 1:
            # couldn't find a valid name amidst the permutations, or there is
            # more than 1 permutation. try to get a valid name from the regions
            region_name = sanitize_model_or_sound_name(regions.STEPTREE[0].name, "")

    if nodes and nodes.STEPTREE:
        for node in nodes.STEPTREE:
            node_name = sanitize_model_or_sound_name(
                node.name.split("frame", 1)[-1].split("bip01", 1)[-1].
                split("bone24", 1)[-1].strip(" \r\n\t-_")
                )
            break

    if len(region_name) <= 2: region_name   = ""
    if len(perm_name)   <= 2: perm_name     = ""
    if len(node_name)   <= 2: node_name     = ""

    #print("%s '%s' '%s' '%s' '%s'" % (tag_id, perm_name, region_name, node_name, name))

    return (
        perm_name   if perm_name    not in const.INVALID_MODEL_NAMES else
        region_name if region_name  not in const.INVALID_MODEL_NAMES else
        node_name   if node_name    not in const.INVALID_MODEL_NAMES else
        name
        )


def get_sound_sub_dir_and_name(snd_meta, sub_dir="", snd_name=""):
    if not hasattr(snd_meta, "sound_class"):
        return sub_dir, snd_name

    snd_class = snd_meta.sound_class.enum_name
    if "dialog" in snd_class:
        sub_dir = const.snd_dialog_dir
    elif snd_class == "device_door":
        sub_dir = const.imp_doors_dir
    elif snd_class == "unit_footsteps":
        sub_dir = const.imp_footsteps_dir
    elif snd_class == "vehicle_collision":
        sub_dir = const.sfx_vehicles_dir + "collision\\"
    elif snd_class == "vehicle_engine":
        sub_dir = const.sfx_vehicles_dir + "engine\\"
    elif "projectile" in snd_class:
        sub_dir = const.sfx_impulse_dir + snd_class.replace("_", " ") + "\\"
    elif "weapon" in snd_class:
        sub_dir = const.sfx_weapons_dir + snd_class.strip("weapon_") + "\\"
    elif "ambient" in snd_class:
        sub_dir = const.sfx_ambience_dir
    elif "device" in snd_class:
        sub_dir = const.sfx_ambience_dir + const.devices_dir
    elif snd_class == "music":
        sub_dir = const.snd_music_dir
    else:
        sub_dir = const.cinematics_dir + const.snd_sfx_dir

    for pr in snd_meta.pitch_ranges.STEPTREE:
        for perm in pr.permutations.STEPTREE:
            perm_name = sanitize_model_or_sound_name(perm.name)
            if perm_name:
                snd_name = perm_name
                break

    return sub_dir, snd_name


def get_sound_looping_name(meta, halo_map, def_name=""):
    if meta is None:
        return def_name
    elif not(hasattr(meta, "tracks") and hasattr(meta, "detail_sounds")):
        return def_name

    # try and determine a name for this sound_looping from its sound tags
    for b in meta.tracks.STEPTREE:
        for tag_ref in (
                b.start, b.loop, b.end, b.alternate_loop, b.alternate_end
                ):
            _, snd_name = get_sound_sub_dir_and_name(
                halo_map.get_meta(get_tag_id(tag_ref), ignore_rawdata=True))
            snd_name = snd_name.lower()
            if snd_name not in ("", "in", "start", "begin", "loops", "loop",
                                "lp", "lps", "out", "stop", "end"):
                return snd_name

    for b in meta.detail_sounds.STEPTREE:
        _, snd_name = get_sound_sub_dir_and_name(
            halo_map.get_meta(get_tag_id(b.sound), ignore_rawdata=True))
        snd_name = snd_name.lower()
        if snd_name not in ("", "detail", "details", "lp", "loops", "loop"):
            return snd_name

    return def_name


def get_sound_scenery_name(meta, halo_map, def_name=""):
    if not(hasattr(meta, "obje_attrs") and meta.obje_attrs.attachments.STEPTREE):
        return def_name

    for b in meta.obje_attrs.attachments.STEPTREE:
        lsnd_meta = halo_map.get_meta(get_tag_id(b.type))
        if not hasattr(lsnd_meta, "tracks"):
            continue

        lsnd_name = get_sound_looping_name(lsnd_meta, halo_map, "")
        if lsnd_name:
            return lsnd_name

    return def_name
