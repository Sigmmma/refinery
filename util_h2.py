

# DO NOT CHANGE THE ORDER OF THESE
HALO2_MAP_TYPES = ("local", "mainmenu", "shared", "single_player_shared")


def split_raw_pointer(ptr):
    return ptr & 0x3FffFFff, HALO2_MAP_TYPES[(ptr>>30)&3]


def get_string_id_string(string_ids, string_id):
    index = string_id.id
    if index < 0 or index >= len(string_ids):
        return ""
    return string_ids[index].string
