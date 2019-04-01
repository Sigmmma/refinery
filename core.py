import mmap
import gc
import os
import refinery
import shutil
import sys
import zlib

from os.path import dirname, basename, exists, join, isfile, splitext
from struct import unpack
from time import time
from traceback import format_exc

from supyr_struct.buffer import BytearrayBuffer, PeekableMmap
from supyr_struct.defs.constants import *
from supyr_struct.field_types import FieldType


from reclaimer.constants import GEN_1_HALO_ENGINES, GEN_2_ENGINES
from reclaimer.data_extraction import h1_data_extractors, h2_data_extractors,\
     h3_data_extractors
from reclaimer.hsc import get_h1_scenario_script_object_type_strings,\
     get_hsc_data_block
from reclaimer.meta.wrappers.halo1_map import Halo1Map
from reclaimer.meta.wrappers.halo1_anni_map import Halo1AnniMap
from reclaimer.meta.wrappers.halo1_rsrc_map import Halo1RsrcMap
from reclaimer.meta.wrappers.halo2_map import Halo2Map
from reclaimer.meta.wrappers.halo3_map import Halo3Map
from reclaimer.meta.wrappers.halo3_beta_map import Halo3BetaMap
from reclaimer.meta.wrappers.halo_reach_map import HaloReachMap
from reclaimer.meta.wrappers.halo_reach_beta_map import HaloReachBetaMap
from reclaimer.meta.wrappers.halo3_odst_map import Halo3OdstMap
from reclaimer.meta.wrappers.halo4_map import Halo4Map
from reclaimer.meta.wrappers.halo4_beta_map import Halo4BetaMap
from reclaimer.meta.wrappers.halo5_map import Halo5Map
from reclaimer.meta.wrappers.stubbs_map import StubbsMap
from reclaimer.meta.wrappers.shadowrun_map import ShadowrunMap

from reclaimer.meta.halo_map import get_map_header, get_map_version,\
     get_tag_index
from reclaimer.meta.class_repair import class_repair_functions,\
     get_tagc_refs
from reclaimer.meta.rawdata_ref_editing import rawdata_ref_move_functions
from reclaimer.meta.halo1_map_fast_functions import class_bytes_by_fcc

from refinery import crc_functions
from refinery.util import *
from refinery.recursive_rename.tag_path_handler import TagPathHandler
from refinery.recursive_rename.functions import recursive_rename


platform = sys.platform.lower()
curr_dir = get_cwd(__file__)
INF = float("inf")


def get_halo_map_section_ends(halo_map):
    head  = halo_map.map_header
    index = halo_map.tag_index
    raw_data_end    = index.model_data_offset
    vertex_data_end = index.vertex_data_size + raw_data_end
    index_data_end  = index.model_data_size  + raw_data_end
    meta_data_end   = head.tag_data_size +  head.tag_index_header_offset
    return raw_data_end, vertex_data_end, index_data_end, meta_data_end


def expand_halo_map(halo_map, raw_data_expansion=0, meta_data_expansion=0,
                    vertex_data_expansion=0, triangle_data_expansion=0):
    map_file   = halo_map.map_data
    map_header = halo_map.map_header
    tag_index  = halo_map.tag_index
    tag_index_array = tag_index.tag_index
    index_header_offset = map_header.tag_index_header_offset

    raw_data_end, vertex_data_end, index_data_end, meta_data_end = \
                  get_halo_map_section_ends(halo_map)


    expansions = ((raw_data_end,    raw_data_expansion),
                  (vertex_data_end, vertex_data_expansion),
                  (index_data_end,  triangle_data_expansion),
                  (meta_data_end,   meta_data_expansion))

    # expand the map's sections
    map_end = inject_file_padding(map_file, *expansions)
    diffs_by_offsets, diff = dict(expansions), 0
    for off in sorted(diffs_by_offsets):
        diff += diffs_by_offsets[off]
        diffs_by_offsets[off] = diff

    meta_ptr_diff = diff - meta_data_expansion

    # update the map_header and tag_index_header's offsets and sizes
    tag_index.model_data_offset += raw_data_expansion
    tag_index.vertex_data_size  += vertex_data_expansion
    tag_index.model_data_size   += vertex_data_expansion + triangle_data_expansion
    halo_map.map_magic                 -= meta_ptr_diff
    map_header.tag_index_header_offset += meta_ptr_diff
    map_header.decomp_len = map_end
    map_header.tag_data_size += meta_data_expansion

    # adjust rawdata pointers in various tags if the index header moved
    if meta_ptr_diff:
        for ref in tag_index_array:
            func = rawdata_ref_move_functions.get(fourcc(ref.class_1.data))
            if func is None or ref.indexed:
                continue
            func(ref.id & 0xFFff, tag_index_array, map_file,
                 halo_map.map_magic, halo_map.engine, diffs_by_offsets)

    map_file.flush()
    return map_end


class RefineryCore:
    pass
