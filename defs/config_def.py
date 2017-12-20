from supyr_struct.defs.tag_def import TagDef
from supyr_struct.defs.common_descs import remaining_data_length
from supyr_struct.defs.constants import *
from supyr_struct.field_types import *

def get():
    return config_def

config_header = Struct("header",
    UEnum32("id", ('rppr', 'rppr'), VISIBLE=False, DEFAULT='rppr'),
    UInt32("version", DEFAULT=2, VISIBLE=False, EDITABLE=False),
    BitStruct("flags",
        UBitEnum("display_mode",
            ("hierarchy", 1),
            ("class",     2),
            ("hybrid",    3),
            SIZE=2
            ),
        Bit("debug_mode"),
        Bit("show_output"),
        Bit("autoload_resources"),
        SIZE=4
        ),
    Bool32("extraction_flags",
        "use_old_gelo",
        "extract_cheape",
        "extract_from_ce_resources",
        "rename_duplicates_in_scnr",
        "overwrite",
        "recursive",
        "decode_adpcm",
        "generate_uncomp_verts",
        "generate_comp_verts",
        ),
    Bool32("deprotection_flags",
        "fix_tag_classes",
        "fix_tag_index_offset",
        "use_hashcaches",
        "use_heuristics",
        ),

    Pad(128 - 5*4 - 2*4),

    Timestamp32("date_created", EDITABLE=False),
    Timestamp32("date_modified", EDITABLE=False),

    SIZE=128
    )

path = Container("path",
    UInt16("length", VISIBLE=False),
    StrUtf8("path", SIZE=".length")
    )

array_sizes = Struct("array_sizes",
    UInt32("paths_count"),
    SIZE=64, VISIBLE=False,
    )

app_window = Struct("app_window",
    UInt16("app_width", DEFAULT=640),
    UInt16("app_height", DEFAULT=450),
    SInt16("app_offset_x"),
    SInt16("app_offset_y"),
    SIZE=64
    )

paths = Array("paths",
    SUB_STRUCT=path, SIZE=".array_sizes.paths_count",
    NAME_MAP=("last_dir", "tags_list", "tags_dir", "data_dir"),
    VISIBLE=False
    )

config_def = TagDef("refinery_config",
    config_header,
    array_sizes,
    app_window,
    paths,
    # used for signing hashcaches made by the user. guarantees
    # that a hashcache was made by this user and not someone else.
    BytearrayRaw("hashcache_private_key", SIZE=128,
        DEFAULT=b'M@\x85\xa7\x85\x83M}\x99~M\x99\x85\x86\x89\x95\x85\x99\xa8\
]^@\x96~M\x99K\x96\x83\x99\x83\x83]^@}@N@\xa2\xa3\x99M\x82\xa8\xa3\x85\xa2\
\MMx96\xba\x89\xbb\xb0M\x89\\\xf1\xf9\xf1]]P\xf2\xf5\xf5@\x86\x96\x99@\x89@\
\x89\x95@\x99\x81\x95\x87\x85M\x93\x85\x95M\x96]]]k@}\xf6\xf4\xf6}]k@\x99K\
\x83\x99\x83m\x86\xa4\x95\x83\xa3\x89\x96\x95\xa2Kmm\x84\x89\x83\xa3mm]@]'),
    ENDIAN='<', ext=".cfg",
    )
