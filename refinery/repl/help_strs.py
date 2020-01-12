#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

from refinery.tag_index.tag_path_tokens import tokens_to_tag_paths,\
     TOKEN_PC_SCNR_MAP_TYPE_TAGC, TOKEN_PC_SCNR_ALL_TYPE_TAGC,\
     TOKEN_ALL, TOKEN_SCNR, TOKEN_MATG, TOKEN_XBOX_SOUL

__all__ = ("macro_help_strings", "token_help_strings",
           "command_help_strings", "command_arg_strings")

refinery_desc_string = """
Welcome to Refinery! This program is designed to extract
tags and data from map files used by various Halo engines.
Currently supports extracting from Halo 1 Xbox/PC/CE/
Anniversary/PC Demo/Xbox demo, Stubbs the Zombie Xbox/PC,
Halo 2 Vista, and Halo 3.


To use Refinery, load a map(s), set your default tags and
data extraction directories, and extract whatever you need.
If this script is given a filepath to a text file, it will
be parsed, and Refinery will execute each line. Passing the
-b parameter will close Refinery once it finishes processing.
"""

refinery_epilog_string = """
Usage example:

Refinery: set-vars --tags-dir "C:/map_test/tags/" --tagslist-path "C:/map_test/tagslist.txt"
Refinery: load-map "C:/lockout_test/maps/bloodgulch.map"
    Loading definitions in 'reclaimer.os_v4_hek.defs'
    Loading definitions in 'reclaimer.hek.defs'
bloodgulch: extract-tags --tag-ids PC_ALL_TAGS
"""


macro_help_strings = dict(
    PC_ALL_TAGS="All tags required to build a Halo PC map:\n\
<scenario> <globals> PC_SPECIFIC_TAGS",
    PC_SPECIFIC_TAGS="All tags specific to Halo PC maps:\n\
<pc_tagc_all_type> PC_MAGICALLY_INCLUDED <pc_tagc_map_type>",
    PC_MAGICALLY_INCLUDED="Misc tags explicitly seeked out when building a PC map:\n\
<pc_background> <pc_loading> <pc_mp_map_list> <pc_trouble> <pc_cursor> <pc_forward> \
<pc_back> <pc_flag_failure>",
    XBOX_ALL_TAGS="All tags required to build a Halo Xbox map:\n\
<scenario> <globals> XBOX_UI_MAGICALLY_INCLUDED",
    XBOX_UI_MAGICALLY_INCLUDED="Misc tags explicitly seeked out when building a Xbox ui.map:\n\
XBOX_MAGICALLY_INCLUDED <xbox_ui_keyboard> <xbox_ui_random_names> <xbox_ui_multiplayer_desc> \
<xbox_ui_saved_games> <xbox_ui_default_gametype_names> <xbox_ui_gametype_descs> \
<xbox_ui_default_players> <xbox_ui_button_long_desc> <xbox_ui_button_short_desc> \
<xbox_ui_joystick_short_desc> <xbox_cursor> <xbox_flag_failure> <xbox_title>",
    XBOX_MAGICALLY_INCLUDED="Misc tags explicitly seeked out when building a Xbox map:\n\
<xb_mp_game_text> <xb_shell_white> <xb_soul>",
    )

token_help_strings = dict(tokens_to_tag_paths)
token_help_strings.update({
    TOKEN_ALL: "Every tag in the map.",
    TOKEN_SCNR: "The maps scenario tag.",
    TOKEN_MATG: "The maps globals tag.",
    TOKEN_PC_SCNR_MAP_TYPE_TAGC: "The tag_collection containing all map-type specific PC ui tags.",
    TOKEN_PC_SCNR_ALL_TYPE_TAGC: "The tag_collection containing all general PC ui tags.",
    TOKEN_XBOX_SOUL: "The ui_widget_collection containing all map-type specific Xbox ui tags.",
    })

command_help_strings = dict(
    extract_tags="Extracts specified tags from the map. \
If --tag-ids is unspecified, extracts all tags in the map.",
    extract_data="Extracts specified tags from the map to their pre-compiled 'data' formats. \
If --tag-ids is unspecified, extracts all tags in the map.",
    extract_tag="Extracts a single tags from the map.",
    extract_cheape="Extracts cheape.map from an OpenSauce map.",
    deprotect_map="Saves the map and then runs deprotection on it. \
Map is saved again after deprotection finishes.",
    load_map="Loads a map from the specified filepath.",
    unload_map="Unloads a map.",
    save_map="Saves the map as well as any pending changes to it.",
    rename_map="Sets the internal name of the map. \
Does not relocate the map to be loaded under that name. \
NOTE: A separate save-map command must be called to save this change.",
    spoof_crc="Sets the checksum of the map and modifies the map to hash to it. \
NOTE: A separate save-map command must be called to save this change.",
    rename_tag_by_id="Renames a tag by its tag-id. \
NOTE: A separate save-map command must be called to save this change.",
    rename_tag="Renames a tag by its path. \
NOTE: A separate save-map command must be called to save this change.",
    rename_dir="Renames a directory by its path. \
NOTE: A separate save-map command must be called to save this change.",
    set_vars="Sets the current values of default variables. \
Unprovided arguments are set to the current default variables any time a command is executed.",
    get_vars="Displays the current values of default variables. \
If no variable names are provided, all variables are printed.",
    map_info="Displays map header and tag index information.",
    tag_id_tokens="Displays the available tag-id tokens and what they represent. \
Tokens may be used whenever a tag-id is needed. \
Any provided prefix string will be used to filter which tokens are displayed.",
    tag_id_macros="Displays the available tag-id token macros and what tokens they contain. \
Macros may be used whenever multiple tag-ids are needed. \
Any provided prefix string will be used to filter which macros are displayed.",
    switch_map="Switches which map is active by the maps name.",
    switch_map_by_filepath="Switches which map is active by the maps filepath.",
    switch_engine="Switches which engine type is active. \
If a map is currently active under that engine, it will become the active map.",
    dir="Displays the files and directories in the specified directory.",
    files="Displays the files in the specified directory.",
    dir_ct="Displays the number of directories in the specified directory.",
    file_ct="Displays the number of files in the specified directory.",
    dir_names="Displays the directory names immediately in the specified directory.",
    file_names="Displays the file names immediately in the specified directory.",
    quit="Closes Refinery.",
    cls="Clears the console history.",
    maps="Displays the names of all loaded maps under the active engine.",
    engines="Displays the names of all loaded engine types.",
    verbose="Displays/sets the level of error information displayed.",
    prompt="Displays/sets the information displayed in the prompt.",
    )

default_var_help_strs = {
    "autoload-resources": "Whether to automatically find and load all required shared/resource maps.",
    "bitmap-extract-format": "The image format to extract bitmaps to when extracting as data.",
    "bitmap-extract-keep-alpha": "Whether to keep the alpha channel when extracting bitmaps to png.",
    "data-dir": "The default directory to extract data to.",
    "decode-adpcm": "Whether to decode ADPCM sounds to 16bit PCM when extracting as data.",
    "do-printout": "Whether to display debug information about the operation progress as it occurs.",
    "fix-tag-classes": "Whether to repair tag classes.",
    "fix-tag-index-offset": "Whether to move the tag index back to where most programs require it to be. \
WARNING: This can break certain maps, so don't do this unless you are sure you can.",
    "force-lower-case-paths": "Whether to lowercase all tag paths in extracted tags, and \
to lowercase the path they are extracted to.",
    "generate-comp-verts": "Whether to generate compressed lightmap vertices when extracting bsps.",
    "generate-uncomp-verts": "Whether to generate uncompressed lightmap vertices when extracting bsps.",
    "limit-tag-path-lengths": "Whether to shorten tag paths to the Win32 limit of 254 characters.",
    "overwrite": "Whether to overwrite existing files when extracting.",
    "print-errors": "Whether to print exceptions as they occur, rather than letting them stop the operation.",
    "print-heuristic-name-changes": "Whether to print a tags name each time it changes during heuristic deprotection",
    "recursive": "Whether to extract ALL tags needed by each tag being extracted.",
    "rename-cached-tags": "Whether to rename indexed tags using names taken from the loaded resource maps.",
    "rename-scnr-dups": "Whether to rename scenario names to remove unused duplicates. \
Duplicates can prevent scripts from being recompiled.",
    "scrape-tag-paths-from-scripts": "Whether to try extracting original tag paths from compiled scripts.",
    "shallow-ui-widget-nesting": "Whether to use shallow nesting for ui_widget_definition tags \
and their children. If set, ui_widget_definition tags will be flatly stored in ui\\shell\\",
    "tags-dir": "The default directory to extract tags to.",
    "tagslist-path": "Filepath to a text file to record tag and data extractions.",
    "use-heuristics": "Whether to use heuristics based deprotection. \
Heuristics assumes most tag paths are protecetd, and generates new ones based on how tags are used. \
Use this when deprotecting the most heavily protected maps.",
    "use-minimum-priorities": "Whether to use an experimental method for lowering heuristic \
deprotection. Keep this on unless you experience bugs with heuristics.",
    "use-scenario-names-for-script-names": "Whether to use the scenarios current object names \
rather than those in the script_string_data when extracting scripts.",
    "use-tag-index-for-script-names": "Whether to use the maps current tag paths rather than \
those in the script_string_data when extracting scripts.",
    "valid-tag-paths-are-accurate": "Whether to assume tag-paths NOT beginning with 'protected' \
are valid, and thus not needing deprotection.",
    "disable-safe-mode": "Whether to disables limit on size of reflexives and rawdata in tags.",
    "disable-tag-cleaning": "Whether to disable cleaning errors from tags when reading them.",
    "globals-overwrite-mode": (
        "How to handle overwriting globals tags.\n"
        "0 == prompt every time. 1 == always overwrite. "
        "2 == never overwrite. 3 == overwrite for MP maps(prompt otherwise). "
        "4 == overwrite for MP maps(dont otherwise)."
        ),
    "skip-seen-tags-during-queue-processing": "Whether to skip extracting any tags that were \
already extracted during a previous queued extraction."
    }


command_arg_strings = dict(
    extract_tags={
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",

        "disable-safe-mode": default_var_help_strs["disable-safe-mode"],
        "disable-tag-cleaning": default_var_help_strs["disable-tag-cleaning"],
        "print-errors": default_var_help_strs["print-errors"],
        "force-lower-case-paths": default_var_help_strs["force-lower-case-paths"],
        "generate-comp-verts": default_var_help_strs["generate-comp-verts"],
        "generate-uncomp-verts": default_var_help_strs["generate-uncomp-verts"],
        "overwrite": default_var_help_strs["overwrite"],
        "recursive": default_var_help_strs["recursive"],
        "rename-scnr-dups": default_var_help_strs["rename-scnr-dups"],
        "tagslist-path": default_var_help_strs["tagslist-path"],
        "out-dir": "The directory to extract tags to.",
        "macros": "Whether to check for macros in the tag-ids.",
        "tag-ids": "The tag-ids of the tags to extract. May also include tag-id macros.",
        },
    extract_data={
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",

        "disable-safe-mode": default_var_help_strs["disable-safe-mode"],
        "disable-tag-cleaning": default_var_help_strs["disable-tag-cleaning"],
        "print-errors": default_var_help_strs["print-errors"],
        "force-lower-case-paths": default_var_help_strs["force-lower-case-paths"],
        "generate-comp-verts": default_var_help_strs["generate-comp-verts"],
        "generate-uncomp-verts": default_var_help_strs["generate-uncomp-verts"],
        "overwrite": default_var_help_strs["overwrite"],
        "recursive": default_var_help_strs["recursive"],
        "rename-scnr-dups": default_var_help_strs["rename-scnr-dups"],
        "tagslist-path": default_var_help_strs["tagslist-path"],
        "decode-adpcm": default_var_help_strs["decode-adpcm"],
        "bitmap-extract-format": default_var_help_strs["bitmap-extract-format"],
        "bitmap-extract-keep-alpha": default_var_help_strs["bitmap-extract-keep-alpha"],
        "out-dir": "The directory to extract data to.",
        "macros": "Whether to check for macros in the tag-ids.",
        "tag-ids": "The tag-ids of the data to extract. May also include tag-id macros.",
        },
    extract_tag={
        "tag-id": "The tag-id of the tag to extract.",
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",

        "disable-safe-mode": default_var_help_strs["disable-safe-mode"],
        "disable-tag-cleaning": default_var_help_strs["disable-tag-cleaning"],
        "force-lower-case-paths": default_var_help_strs["force-lower-case-paths"],
        "generate-comp-verts": default_var_help_strs["generate-comp-verts"],
        "generate-uncomp-verts": default_var_help_strs["generate-uncomp-verts"],
        "overwrite": default_var_help_strs["overwrite"],
        "rename-scnr-dups": default_var_help_strs["rename-scnr-dups"],
        "tagslist-path": default_var_help_strs["tagslist-path"],
        "out-dir": "The directory to extract the tag to.",
        "filepath": "The filepath to extract the tag to.",
        },
    extract_cheape={
        "filepath": "The filepath to extract the cheape.map to.",
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",
        },
    deprotect_map={
        "filepath": "The filepath to save the deprotected map to.",
        "map-name": "Name of the map to deprotect. Defaults to <active>",
        "engine": "Engine of the map to deprotect. Defaults to <active>",

        "do-printout": default_var_help_strs["do-printout"],
        "fix-tag-index-offset": default_var_help_strs["fix-tag-index-offset"],
        "print-errors": default_var_help_strs["print-errors"],
        "fix-tag-classes": default_var_help_strs["fix-tag-classes"],
        "limit-tag-path-lengths": default_var_help_strs["limit-tag-path-lengths"],
        "print-heuristic-name-changes": default_var_help_strs["print-heuristic-name-changes"],
        "rename-cached-tags": default_var_help_strs["rename-cached-tags"],
        "scrape-tag-paths-from-scripts": default_var_help_strs["scrape-tag-paths-from-scripts"],
        "shallow-ui-widget-nesting": default_var_help_strs["shallow-ui-widget-nesting"],
        "use-heuristics": default_var_help_strs["use-heuristics"],
        "use-minimum-priorities": default_var_help_strs["use-minimum-priorities"],
        "use-scenario-names-for-script-names": default_var_help_strs["use-scenario-names-for-script-names"],
        "use-tag-index-for-script-names": default_var_help_strs["use-tag-index-for-script-names"],
        "valid-tag-paths-are-accurate": default_var_help_strs["valid-tag-paths-are-accurate"],
        "meta-data-expansion": "The number of bytes to expand the tag data section by.",
        "raw-data-expansion": "The number of bytes to expand the raw data section by.",
        "triangle-data-expansion": "The number of bytes to expand the indices section by.",
        "vertex-data-expansion": "The number of bytes to expand the vertices section by.",
        },
    load_map={
        "filepath": "The filepath of the map to load.",

        "do-printout": default_var_help_strs["do-printout"],
        "autoload-resources": default_var_help_strs["autoload-resources"],
        "make-active": "Whether to set this map as the active map.",
        "replace-if-same-name": "Whether to unload any map using the same engine and map-name as this one.",
        },
    unload_map={
        "map-name": "Name of the map to unload. Defaults to <active>",
        "engine": "Engine of the map to unload. Defaults to <active>",
        },
    save_map={
        "filepath": "The filepath to save the map to",
        "map-name": "Name of the map to save. Defaults to <active>",
        "engine": "Engine of the map to save. Defaults to <active>",

        "fix-tag-index-offset": default_var_help_strs["fix-tag-index-offset"],
        "meta-data-expansion": "The number of bytes to expand the tag data section by.",
        "raw-data-expansion": "The number of bytes to expand the raw data section by.",
        "triangle-data-expansion": "The number of bytes to expand the indices section by.",
        "vertex-data-expansion": "The number of bytes to expand the vertices section by.",
        },
    rename_map={
        "new-name": "The name to rename the map to. Must be under 32 characters.",
        "map-name": "Name of the map to rename. Defaults to <active>",
        "engine": "Engine of the map to rename. Defaults to <active>",
        },
    spoof_crc={
        "new-crc": "The crc to spoof the map to. Must be a 32bit unsigned integer.",
        "map-name": "Name of the map to crc spoof. Defaults to <active>",
        "engine": "Engine of the map to crc spoof. Defaults to <active>",
        },
    rename_tag_by_id={
        "tag-id": "The tag-id of the tag to rename.",
        "new-path": "The path to rename the tag to.",
        "map-name": "Name of the map to rename the tag in. Defaults to <active>",
        "engine": "Engine of the map to rename the tag in. Defaults to <active>",
        },
    rename_tag={
        "tag-path": "The path of the tag to rename.",
        "new-path": "The new path of the tag.",
        "map-name": "Name of the map to rename the tag in. Defaults to <active>",
        "engine": "Engine of the map to rename the tag in. Defaults to <active>",
        },
    rename_dir={
        "dir-path": "The path of the directory to rename.",
        "new-path": "The path to move the directory to. \
Contents of dir-path are merged into any existing directory.",
        "map-name": "Name of the map to rename the directory in. Defaults to <active>",
        "engine": "Engine of the map to rename the directory in. Defaults to <active>",
        },
    set_vars=default_var_help_strs,
    get_vars=default_var_help_strs,
    map_info={
        "map-name": "Name of the map to display. Defaults to <active>",
        "engine": "Engine of the map to display. Defaults to <active>",
        },
    tag_id_tokens={
        "prefix": "The prefix used to filter what tokens to display. \
It is not necessary to include '<' or '>'.",
        },
    tag_id_macros={
        "prefix": "The prefix used to filter what macros to display. \
It is not necessary to include '<' or '>'.",
        },
    switch_map={
        "map-name": "Name of the map to switch to.",
        },
    switch_map_by_filepath={
        "filepath": "Filepath of the map to switch to.",
        },
    switch_engine={
        "engine": "Engine of the map to switch to.",
        },
    dir={
        "dir": "The directory whose contents to display.",
        "map-name": "Name of the map whose directory to display. Defaults to <active>",
        "engine": "Engine of the map whose directory to display. Defaults to <active>",

        "guides": "Whether to display guide-lines to help in understanding the hierarchy.",
        "header": "Whether to display the names of each column as the first row.",
        "indexed": "Whether to display if the tag is indexed.",
        "tag-ids": "Whether to display the tag-id of each tag.",
        "indent": "The number of spaces to indent each sub-directory.",

        "depth": "The number of sub-directories to display. 0 displays only the current directory.",
        "dirs-first": "Whether to display directories before files.",
        "extra-dir-spacing": "The number of rows to separate the end of a directory from the next.",
        "files": "Whether to also display tags. If 0, only directories will be displayed.",
        },
    files={
        "dir": "The directory whose files to display.",
        "map-name": "Name of the map whose files to display. Defaults to <active>",
        "engine": "Engine of the map whose files to display. Defaults to <active>",

        "guides": "Whether to display guide-lines to help in understanding the hierarchy.",
        "header": "Whether to display the names of each column as the first row.",
        "indexed": "Whether to display if the tag is indexed.",
        "tag-ids": "Whether to display the tag-id of each tag.",
        "indent": "The number of spaces to indent each sub-directory.",
        },
    dir_ct={
        "dir": "The directory whose directory count to display.",
        "map-name": "Name of the map whose directory count to display. Defaults to <active>",
        "engine": "Engine of the map whose directory count to display. Defaults to <active>",

        "total": "Whether to recursively count the number of sub-directories.",
        },
    file_ct={
        "dir": "The directory whose file count to display.",
        "map-name": "Name of the map whose file count to display. Defaults to <active>",
        "engine": "Engine of the map whose file count to display. Defaults to <active>",

        "total": "Whether to recursively count the number of files in sub-directories.",
        },
    dir_names={
        "dir": "The directory whose directory names to display.",
        "map-name": "Name of the map whose directory names to display. Defaults to <active>",
        "engine": "Engine of the map whose directory names to display. Defaults to <active>",
        },
    file_names={
        "dir": "The directory whose file names to display.",
        "map-name": "Name of the map whose file names to display. Defaults to <active>",
        "engine": "Engine of the map whose file names to display. Defaults to <active>",
        },
    engines={
        },
    maps={
        "engine": "Engine of the maps to display. Defaults to <active>",
        },
    verbose={
        "level": "The max depth the traceback call stack will be printed when exceptions occur.",
        },
    prompt={
        "level": "The level of information to display in the prompt. \
0 == nothing  1 == active map name  2 == active engine and active map name",
        },
    )
