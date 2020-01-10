#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from supyr_struct.defs.tag_def import TagDef
from supyr_struct.field_types import *

__all__ = (
    "get", "bitmap_file_formats", "config_def",
    "globals_overwrite_gui_names", "globals_overwrite_modes",
    )

bitmap_file_formats = (
    "dds",
    "tga",
    "png"
    )
globals_overwrite_gui_names = (
    "prompt user",
    "always",
    "never",
    "always overwrite with MP globals(prompt for UI and SP maps)",
    "always overwrite with MP globals(never for UI and SP maps)",
    )
globals_overwrite_modes = (
    "prompt",
    "always",
    "never",
    "mp_only_prompt_otherwise",
    "mp_only_ignore_othewise",
    )

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
        "skip_seen_tags_during_queue_processing",
        "rename_scnr_dups",
        "overwrite",
        "recursive",
        "decode_adpcm",
        "generate_uncomp_verts",
        "generate_comp_verts",
        Pad(3),
        "use_tag_index_for_script_names",
        "use_scenario_names_for_script_names",
        "bitmap_extract_keep_alpha",
        Pad(1), # this flag has never been used

        # upper 16 bits
        "disable_safe_mode",
        "disable_tag_cleaning",
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
        "show_structure_meta",
        ),
    Pad(48 - 4*6),

    UEnum8("bitmap_extract_format", *bitmap_file_formats),
    UEnum8("globals_overwrite_mode",
        *(dict(NAME=globals_overwrite_modes[i],
               GUI_NAME=globals_overwrite_gui_names[i])
          for i in range(len(globals_overwrite_modes)))
        ),

    Pad(128 - 48 - 2*1 - 4*2),
    Timestamp32("date_created", EDITABLE=False),
    Timestamp32("date_modified", EDITABLE=False),

    SIZE=128
    )

path = Container("path",
    UInt16("length", VISIBLE=False),
    StrUtf8("path", SIZE=".length")
    )

font = Struct("font",
    UInt16("size"),
    Bool16("flags",
        "bold",
        ),
    Pad(12),
    StrUtf8("family", SIZE=240),
    )

array_sizes = Struct("array_sizes",
    UInt32("path_count"),
    UInt16("column_widths_size"),
    UInt16("font_count"),
    SIZE=64, VISIBLE=False,
    )

app_window = Struct("app_window",
    UInt16("app_width", DEFAULT=640),
    UInt16("app_height", DEFAULT=450),
    SInt16("app_offset_x"),
    SInt16("app_offset_y"),
    SInt16("sash_position"),
    SIZE=64
    )

paths = Array("paths",
    SUB_STRUCT=path, SIZE=".array_sizes.path_count",
    NAME_MAP=("last_dir", "tagslist", "tags_dir", "data_dir"),
    VISIBLE=False
    )

column_widths = UInt16Array("column_widths",
    SIZE=".array_sizes.column_widths_size",
    VISIBLE=False
    )

fonts = Array("fonts",
    SUB_STRUCT=font, SIZE=".array_sizes.font_count",
    )

config_def = TagDef("refinery_config",
    config_header,
    array_sizes,
    app_window,
    paths,
    column_widths,
    fonts,
    ENDIAN='<', ext=".cfg",
    )
