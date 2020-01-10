#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from refinery.util import sanitize_win32_path
from refinery.heuristic_deprotection import constants as const


class MinPriority:
    _val = const.INF
    @property
    def val(self): return self._val
    @val.setter
    def val(self, new_val): self._val = min(new_val, self.val)


def sanitize_name(name):
    return str(sanitize_win32_path(name)).lower()\
           .replace("~", "").replace("\\", " ").strip()


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


def sanitize_tag_name(name, def_name):
    name = sanitize_name(name).replace("_", " ").replace("-", " ").strip()
    name = " ".join(s for s in name.split(" ") if s)
    while name and name[-1] in "0123456789":
        name = name[: -1].strip()

    if name not in const.INVALID_MODEL_NAMES:
        return name

    return def_name


def get_model_name(halo_map, tag_id, model_name=""):
    meta = halo_map.get_meta(tag_id)
    if not(hasattr(meta, "regions") and meta.regions.STEPTREE):
        return model_name

    names = []
    for region in meta.regions.STEPTREE:
        for perm in region.permutations.STEPTREE:
            names.append(sanitize_tag_name(perm.name, ""))

    name = "" if not names else names.pop()
    if not names and name not in const.INVALID_MODEL_NAMES:
        # just one single valid name was found amidst the permutations
        return name

    if len(meta.regions.STEPTREE) == 1:
        # more than 1 perm name found. try to get a valid name from the regions
        name = sanitize_tag_name(meta.regions.STEPTREE[0].name, "")
        if name not in const.INVALID_MODEL_NAMES:
            return name

    return model_name


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
            perm_name = sanitize_tag_name(perm.name, "")
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
        for snd_id in (get_tag_id(b.start), get_tag_id(b.loop), get_tag_id(b.end)):
            _, snd_name = get_sound_sub_dir_and_name(
                halo_map.get_meta(snd_id, ignore_rawdata=True))
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
