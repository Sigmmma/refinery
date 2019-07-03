__all__ = ("get_filtered_tag_index_ids", "TagPathDetokenizer", )

import os

from refinery.tag_index.tag_path_tokens import tokens_to_tag_paths,\
     ALL_TOKENS, TOKEN_SCNR, TOKEN_MATG, TOKEN_ALL,\
     TOKEN_XBOX_SOUL, TOKEN_PC_SCNR_MAP_TYPE_TAGC,\
     PC_SCNR_TAGC_TAG_PATHS, XBOX_SOUL_TAG_PATHS


def get_filtered_tag_index_ids(tag_index_array, tag_path=None,
                               tag_class="", exact=False):
    tag_index_ids = set()
    tag_path  = tag_path.lower()
    tag_class = tag_class.lower()
    for i in range(len(tag_index_array)):
        curr_tag_class = tag_index_array[i].class_1.enum_name.lower()
        curr_tag_path  = tag_index_array[i].path.lower()
        if ((exact and tag_path == curr_tag_path) or
            (not exact and curr_tag_path.startswith(tag_path))):
            if not tag_class or curr_tag_class == tag_class:
                tag_index_ids.add(i)

    return list(tag_index_ids)


class TagPathDetokenizer(list):

    def get_filtered_tag_ids(self, halo_map):
        tag_index = halo_map.tag_index.STEPTREE
        tag_ids = self
        tag_index_ids = set()

        tag_ids = self.detokenize_tag_ids(halo_map)
        for tag_id in tag_ids:
            if isinstance(tag_id, int):
                tag_index_ids.add(tag_id)
                continue

            tag_path_pieces = tag_id.replace("\\", "/").lower().split("/")
            tag_path, tag_class = os.path.splitext(tag_path_pieces[-1])
            if len(tag_path_pieces) > 1:
                tag_path = "\\".join(
                    tuple(tag_path_pieces[: -1]) + (tag_path, ))
            elif tag_path == ("*" * len(tag_path)):
                tag_path = ""

            exact = tag_path and tag_class
            tag_index_ids.update(get_filtered_tag_index_ids(
                tag_index, tag_path, tag_class.lstrip("."), exact))

        # make sure all the tag_ids are valid
        tag_id_range = range(len(tag_index))
        for i in tuple(tag_index_ids):
            if i not in tag_id_range:
                tag_index_ids.remove(i)

        return list(tag_index_ids)

    def detokenize_tag_ids(self, halo_map):
        if TOKEN_ALL in self:
            return list(range(len(halo_map.tag_index.STEPTREE)))

        new_tag_ids = [None]*len(self)
        i = 0
        for token in self:
            if isinstance(token, int) or token not in ALL_TOKENS:
                tag_id = token
            elif token in tokens_to_tag_paths:
                tag_id = tokens_to_tag_paths[token]
            else:
                tag_id = self.detokenize_special_token(token, halo_map)

            if tag_id is not None:
                new_tag_ids[i] = tag_id
                i += 1

        if i < len(new_tag_ids):
            del new_tag_ids[i: ]

        return new_tag_ids

    def detokenize_special_token(self, token, halo_map):
        tag_index = halo_map.tag_index
        map_type = halo_map.map_header.map_type.data
        if token in (TOKEN_SCNR, TOKEN_MATG):
            tag_class = "scenario" if token == TOKEN_SCNR else "globals"
            if hasattr(tag_index, tag_class + "_tag_id"):
                return getattr(tag_index, tag_class + "_tag_id") & 0xFFff

            for i in range(len(tag_index.STEPTREE)):
                if tag_index.STEPTREE[i].class_1.enum_name == tag_class:
                    return i

        elif token == TOKEN_PC_SCNR_MAP_TYPE_TAGC:
            if map_type in range(len(PC_SCNR_TAGC_TAG_PATHS)):
                return PC_SCNR_TAGC_TAG_PATHS[map_type]

        elif token == TOKEN_XBOX_SOUL:
            if map_type in range(len(XBOX_SOUL_TAG_PATHS)):
                return XBOX_SOUL_TAG_PATHS[map_type]

        return token
