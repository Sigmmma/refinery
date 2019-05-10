from refinery.tag_path_tokens import *

__all__ = ("macro_help_strings", "token_help_strings",
           "command_help_strings", "command_arg_strings",)


macro_help_strings = dict(
    PC_ALL_TAGS="All tags required to build a Halo PC map:\n\
\t<scenario> <globals> PC_SPECIFIC_TAGS",
    PC_SPECIFIC_TAGS="All tags specific to Halo PC maps:\n\
\t<pc_tagc_all_type> PC_MAGICALLY_INCLUDED <pc_tagc_map_type>",
    PC_MAGICALLY_INCLUDED="Misc tags explicitly seeked out when building a PC map.\n\
\t<pc_background> <pc_loading> <pc_mp_map_list> <pc_trouble> <pc_cursor> <pc_forward> \
<pc_back> <pc_flag_failure>",
    XBOX_ALL_TAGS="All tags required to build a Halo Xbox map:\n\
\t<scenario> <globals> XBOX_UI_MAGICALLY_INCLUDED",
    XBOX_UI_MAGICALLY_INCLUDED="Misc tags explicitly seeked out when building a Xbox ui.map:\n\
\tXBOX_MAGICALLY_INCLUDED <xbox_ui_keyboard> <xbox_ui_random_names> <xbox_ui_multiplayer_desc> \
<xbox_ui_saved_games> <xbox_ui_default_gametype_names> <xbox_ui_gametype_descs> \
<xbox_ui_default_players> <xbox_ui_button_long_desc> <xbox_ui_button_short_desc> \
<xbox_ui_joystick_short_desc> <xbox_cursor> <xbox_flag_failure> <xbox_title>",
    XBOX_MAGICALLY_INCLUDED="Misc tags explicitly seeked out when building a Xbox map:\n\
\t<xb_mp_game_text> <xb_shell_white> <xb_soul>",
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
Any provided prefix string will be used to filter which tokens are displayed.",
    tag_id_macros="Displays the available tag-id token macros and what tokens they contain. \
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


command_arg_strings = dict(
    extract_tags={
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",

        "print-errors": "",
        "force-lower-case-paths": "",
        "generate-comp-verts": "",
        "generate-uncomp-verts": "",
        "out-dir": "",
        "overwrite": "",
        "recursive": "",
        "rename-scnr-dups": "",
        "tagslist-path": "",
        "tokens": "",
        "macros": "",
        "tag-ids": "",
        },
    extract_data={
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",

        "print-errors": "",
        "force-lower-case-paths": "",
        "generate-comp-verts": "",
        "generate-uncomp-verts": "",
        "out-dir": "",
        "overwrite": "",
        "recursive": "",
        "rename-scnr-dups": "",
        "tagslist-path": "",
        "tokens": "",
        "macros": "",
        "tag-ids": "",
        "decode-adpcm": "",
        "bitmap-extract-format": "",
        "bitmap-extract-keep-alpha": "",
        },
    extract_tag={
        "tag-id": "",
        "map-name": "Name of the map to extract from. Defaults to <active>",
        "engine": "Engine of the map to extract from. Defaults to <active>",

        "force-lower-case-paths": "",
        "generate-comp-verts": "",
        "generate-uncomp-verts": "",
        "out-dir": "",
        "overwrite": "",
        "recursive": "",
        "rename-scnr-dups": "",
        "tagslist-path": "",
        "filepath": "",
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

        "do-printout": "",
        "fix-tag-index-offset": "",
        "meta-data-expansion": "",
        "raw-data-expansion": "",
        "triangle-data-expansion": "",
        "vertex-data-expansion": "",
        "print-errors": "",
        "fix-tag-classes": "",
        "limit-tag-path-lengths": "",
        "print-heuristic-name-changes": "",
        "rename-cached-tags": "",
        "scrape-tag-paths-from-scripts": "",
        "shallow-ui-widget-nesting": "",
        "use-heuristics": "",
        "use-minimum-priorities": "",
        "use-scenario-names-for-script-names": "",
        "use-tag-index-for-script-names": "",
        "valid-tag-paths-are-accurate": "",
        },
    load_map={
        "filepath": "The filepath of the map to load.",

        "do-printout": "",
        "autoload-resources": "",
        "make-active": "",
        "replace-if-same-name": "",
        },
    unload_map={
        "map-name": "Name of the map to unload. Defaults to <active>",
        "engine": "Engine of the map to unload. Defaults to <active>",
        },
    save_map={
        "filepath": "The filepath to save the map to",
        "map-name": "Name of the map to save. Defaults to <active>",
        "engine": "Engine of the map to save. Defaults to <active>",

        "fix-tag-index-offset": "",
        "meta-data-expansion": "",
        "raw-data-expansion": "",
        "triangle-data-expansion": "",
        "vertex-data-expansion": "",
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
    get_vars={
        "autoload-resources": "",
        "do-printout": "",
        "print-errors": "",
        "force-lower-case-paths": "",
        "rename-scnr-dups": "",
        "overwrite": "",
        "recursive": "",
        "decode-adpcm": "",
        "generate-uncomp-verts": "",
        "generate-comp-verts": "",
        "use-tag-index-for-script-names": "",
        "use-scenario-names-for-script-names": "",
        "bitmap-extract-keep-alpha": "",
        "fix-tag-classes": "",
        "fix-tag-index-offset": "",
        "use-minimum-priorities": "",
        "valid-tag-paths-are-accurate": "",
        "scrape-tag-paths-from-scripts": "",
        "limit-tag-path-lengths": "",
        "print-heuristic-name-changes": "",
        "use-heuristics": "",
        "shallow-ui-widget-nesting": "",
        "rename-cached-tags": "",
        "tags-dir": "",
        "data-dir": "",
        "tagslist-path": "",
        "bitmap-extract-format": "",
        },
    map_info={
        "map-name": "Name of the map to display. Defaults to <active>",
        "engine": "Engine of the map to display. Defaults to <active>",
        },
    tag_id_tokens={
        "token-prefix": "",
        },
    tag_id_macros={
        "macro-prefix": "",
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

        "depth": "",
        "guides": "",
        "header": "",
        "indexed": "",
        "tag-ids": "",
        "dirs-first": "",
        "extra-dir-spacing": "",
        "files": "",
        "indent": "",
        },
    files={
        "dir": "The directory whose files to display.",
        "map-name": "Name of the map whose files to display. Defaults to <active>",
        "engine": "Engine of the map whose files to display. Defaults to <active>",

        "guides": "",
        "header": "",
        "indexed": "",
        "tag-ids": "",
        "indent": "",
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

command_arg_strings["set_vars"] = command_arg_strings["get_vars"]
