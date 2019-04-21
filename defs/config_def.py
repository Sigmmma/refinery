from supyr_struct.defs.tag_def import TagDef
from supyr_struct.defs.common_descs import remaining_data_length
from supyr_struct.defs.constants import *
from supyr_struct.field_types import *

bitmap_file_formats = ("dds", "tga", "png")

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
        Bit("do_printout"),
        Bit("autoload_resources"),
        SIZE=4
        ),
    Bool32("extraction_flags",
        "force_lower_case_paths",
        "extract_yelo_cheape",
        Pad(1),
        "rename_duplicates_in_scnr",
        "overwrite",
        "recursive",
        "decode_adpcm",
        "generate_uncomp_verts",
        "generate_comp_verts",
        Pad(3),
        "use_tag_index_for_script_names",
        "use_scenario_names_for_script_names",
        "bitmap_extract_keep_alpha",
        ),
    Bool32("deprotection_flags",
        "fix_tag_classes",
        "fix_tag_index_offset",
        "use_minimum_priorities",
        "use_heuristics",
        "valid_tag_paths_are_accurate",
        "scrape_tag_paths_from_scripts",
        "limit_tag_path_lengths",
        "shallow_ui_widget_nesting",
        "rename_cached_tags",
        "print_heuristic_name_changes",
        ),
    Bool32("preview_flags",
        "show_all_fields",
        "edit_all_fields",
        "allow_corrupt",
        ),
    Pad(48 - 4*6),

    UEnum8("bitmap_extract_format", *bitmap_file_formats),

    Pad(128 - 48 - 2*1 - 4*2),
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
    NAME_MAP=("last_dir", "tagslist", "tags_dir", "data_dir"),
    VISIBLE=False
    )

config_def = TagDef("refinery_config",
    config_header,
    array_sizes,
    app_window,
    paths,
    ENDIAN='<', ext=".cfg",
    )
