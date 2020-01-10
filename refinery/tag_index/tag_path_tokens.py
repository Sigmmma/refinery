#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

TOKEN_ALL = "<all_tags>"

TOKEN_SCNR = "<scenario>"
TOKEN_MATG = "<globals>"

TOKEN_PC_SCNR_ALL_TYPE_TAGC = "<pc_tagc_all_type>"
TOKEN_PC_BACKGROUND_BITM = "<pc_background>"
TOKEN_PC_LOADING_USTR = "<pc_loading>"
TOKEN_PC_MP_MAP_LIST_USTR = "<pc_mp_map_list>"
TOKEN_PC_TROUBLE_BITM = "<pc_trouble>"
TOKEN_PC_CURSOR_SND = "<pc_cursor>"
TOKEN_PC_FORWARD_SND = "<pc_forward>"
TOKEN_PC_BACK_SND = "<pc_back>"
TOKEN_PC_FLAG_FAILURE_SND = "<pc_flag_failure>"
TOKEN_PC_SCNR_MAP_TYPE_TAGC = "<pc_tagc_map_type>"
# After this point, the following pc tags are exclusively bsp tags and
# their shaders, bitmaps, fog, background sounds, lens flares, etc


TOKEN_XBOX_MP_GAME_TEXT_USTR = "<xb_mp_game_text>"
TOKEN_XBOX_SHELL_WHITE_BITM = "<xb_shell_white>"
TOKEN_XBOX_SOUL = "<xb_soul>"

# NOTE: These next tags are only magically added in xbox UI maps
TOKEN_XBOX_UI_VCKY = "<xbox_ui_keyboard>"
TOKEN_XBOX_UI_RANDOM_NAMES_USTR = "<xbox_ui_random_names>"
TOKEN_XBOX_UI_MPLY = "<xbox_ui_multiplayer_desc>"
TOKEN_XBOX_UI_SAVED_GAMES_USTR = "<xbox_ui_saved_games>"
TOKEN_XBOX_UI_DEFAULT_GAMETYPE_NAMES_USTR = "<xbox_ui_default_gametype_names>"
TOKEN_XBOX_UI_GAMETYPE_DESCS_USTR = "<xbox_ui_gametype_descs>"
TOKEN_XBOX_UI_DEFAULT_PLAYERS_USTR = "<xbox_ui_default_players>"
TOKEN_XBOX_UI_BUTTON_LONG_DESC_USTR = "<xbox_ui_button_long_desc>"
TOKEN_XBOX_UI_BUTTON_SHORT_DESC_USTR = "<xbox_ui_button_short_desc>"
TOKEN_XBOX_UI_JOYSTICK_SHORT_DESC_USTR = "<xbox_ui_joystick_short_desc>"
TOKEN_XBOX_UI_CURSOR_SND = "<xbox_cursor>"
TOKEN_XBOX_UI_FLAG_FAILURE_SND = "<xbox_flag_failure>"
TOKEN_XBOX_UI_TITLE_LSND = "<xbox_title>"
# After this point, the following xbox tags are exclusively bsp tags and
# their shaders, bitmaps, fog, background sounds, lens flares, etc


# NOTE: These tokens are specified in the order those tags will
# appear in a compiled map. I'm unsure if they need to be in this
# order, but regardless this is the order you should find them.
EXTRACT_PC_MAGICALLY_INCLUDED = (
    TOKEN_PC_BACKGROUND_BITM, TOKEN_PC_LOADING_USTR, TOKEN_PC_MP_MAP_LIST_USTR,
    TOKEN_PC_TROUBLE_BITM, TOKEN_PC_CURSOR_SND, TOKEN_PC_FORWARD_SND,
    TOKEN_PC_BACK_SND, TOKEN_PC_FLAG_FAILURE_SND
    )

EXTRACT_XBOX_MAGICALLY_INCLUDED = (
    TOKEN_XBOX_MP_GAME_TEXT_USTR, TOKEN_XBOX_SHELL_WHITE_BITM, TOKEN_XBOX_SOUL
    )

EXTRACT_XBOX_UI_MAGICALLY_INCLUDED = EXTRACT_XBOX_MAGICALLY_INCLUDED + (
    TOKEN_XBOX_UI_VCKY, TOKEN_XBOX_UI_RANDOM_NAMES_USTR, TOKEN_XBOX_UI_MPLY,
    TOKEN_XBOX_UI_SAVED_GAMES_USTR, TOKEN_XBOX_UI_DEFAULT_GAMETYPE_NAMES_USTR,
    TOKEN_XBOX_UI_GAMETYPE_DESCS_USTR, TOKEN_XBOX_UI_DEFAULT_PLAYERS_USTR,
    TOKEN_XBOX_UI_BUTTON_LONG_DESC_USTR, TOKEN_XBOX_UI_BUTTON_SHORT_DESC_USTR,
    TOKEN_XBOX_UI_JOYSTICK_SHORT_DESC_USTR, TOKEN_XBOX_UI_CURSOR_SND,
    TOKEN_XBOX_UI_FLAG_FAILURE_SND, TOKEN_XBOX_UI_TITLE_LSND
    )

EXTRACT_PC_SPECIFIC_TAGS = (TOKEN_PC_SCNR_ALL_TYPE_TAGC, ) +\
                           EXTRACT_PC_MAGICALLY_INCLUDED +\
                           (TOKEN_PC_SCNR_MAP_TYPE_TAGC, )

EXTRACT_PC_ALL_TAGS = (TOKEN_SCNR, TOKEN_MATG) + EXTRACT_PC_SPECIFIC_TAGS

EXTRACT_XBOX_ALL_TAGS = (TOKEN_SCNR, TOKEN_MATG) + EXTRACT_XBOX_UI_MAGICALLY_INCLUDED


tokens_to_tag_paths = {
    TOKEN_PC_SCNR_ALL_TYPE_TAGC: "ui\\ui_tags_loaded_all_scenario_types.tag_collection",
    TOKEN_PC_BACKGROUND_BITM: "ui\\shell\\bitmaps\\background.bitmap",
    TOKEN_PC_LOADING_USTR: "ui\\shell\\strings\\loading.unicode_string_list",
    TOKEN_PC_MP_MAP_LIST_USTR: "ui\\shell\\main_menu\\mp_map_list.unicode_string_list",
    TOKEN_PC_TROUBLE_BITM: "ui\\shell\\bitmaps\\trouble_brewing.bitmap",
    TOKEN_PC_CURSOR_SND: "sound\\sfx\\ui\\cursor.sound",
    TOKEN_PC_FORWARD_SND: "sound\\sfx\\ui\\forward.sound",
    TOKEN_PC_BACK_SND: "sound\\sfx\\ui\\back.sound",
    TOKEN_PC_FLAG_FAILURE_SND: "sound\\sfx\\ui\\flag_failure.sound",

    TOKEN_XBOX_MP_GAME_TEXT_USTR: "ui\\multiplayer_game_text.unicode_string_list",
    TOKEN_XBOX_SHELL_WHITE_BITM: "ui\\shell\\bitmaps\\white.bitmap",

    TOKEN_XBOX_UI_VCKY: "ui\\english.virtual_keyboard",
    TOKEN_XBOX_UI_RANDOM_NAMES_USTR: "ui\\random_player_names.unicode_string_list",
    TOKEN_XBOX_UI_MPLY: "ui\\multiplayer_scenarios.multiplayer_scenario_description",
    TOKEN_XBOX_UI_SAVED_GAMES_USTR: "ui\\saved_game_file_strings.unicode_string_list",
    TOKEN_XBOX_UI_DEFAULT_GAMETYPE_NAMES_USTR: "ui\\default_multiplayer_game_setting_names.unicode_string_list",
    TOKEN_XBOX_UI_GAMETYPE_DESCS_USTR: "ui\\shell\\strings\\game_variant_descriptions.unicode_string_list",
    TOKEN_XBOX_UI_DEFAULT_PLAYERS_USTR: "ui\\shell\\strings\\default_player_profile_names.unicode_string_list",
    TOKEN_XBOX_UI_BUTTON_LONG_DESC_USTR: "ui\\shell\\main_menu\\player_profiles_select\\button_set_long_descriptions.unicode_string_list",
    TOKEN_XBOX_UI_BUTTON_SHORT_DESC_USTR: "ui\\shell\\main_menu\\player_profiles_select\\button_set_short_descriptions.unicode_string_list",
    TOKEN_XBOX_UI_JOYSTICK_SHORT_DESC_USTR: "ui\\shell\\main_menu\\player_profiles_select\\joystick_set_short_descriptions.unicode_string_list",
    TOKEN_XBOX_UI_CURSOR_SND: "sound\\sfx\\ui\\cursor.sound",
    TOKEN_XBOX_UI_FLAG_FAILURE_SND: "sound\\sfx\\ui\\flag_failure.sound",
    TOKEN_XBOX_UI_TITLE_LSND: "sound\\music\\title1\\title1.sound_looping",
    }

PC_SCNR_TAGC_TAG_PATHS = (
    "ui\\ui_tags_loaded_solo_scenario_type.tag_collection",
    "ui\\ui_tags_loaded_multiplayer_scenario_type.tag_collection",
    "ui\\ui_tags_loaded_mainmenu_scenario_type.tag_collection"
    )

XBOX_SOUL_TAG_PATHS = (
    "ui\\shell\\solo.ui_widget_collection",
    "ui\\shell\\multiplayer.ui_widget_collection",
    "ui\\shell\\main_menu.ui_widget_collection",
    )

_ = locals()
ALL_TOKENS = {_[n] for n in _ if n.startswith("TOKEN_")}
ALL_TOKENS_BY_NAMES = {n.split("TOKEN_")[-1]:_[n] for n in _
                       if n.startswith("TOKEN_")}
ALL_TOKEN_MACROS_BY_NAMES = {n.split("EXTRACT_")[-1]:_[n] for n in _
                             if n.startswith("EXTRACT_")}
del _
