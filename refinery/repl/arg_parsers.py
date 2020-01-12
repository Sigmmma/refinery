#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import argparse

from refinery.tag_index import tag_path_tokens
from refinery.repl.help_strs import command_help_strings,\
     command_arg_strings, refinery_desc_string, refinery_epilog_string

__all__ = ("repl_parser", "repl_subparser",)


repl_parser = argparse.ArgumentParser(
    description=refinery_desc_string,
    epilog=refinery_epilog_string,
    formatter_class=argparse.RawDescriptionHelpFormatter
    )
# make an argument to specify whether commands are to be queued or executed
repl_subparser = repl_parser.add_subparsers(dest="operation")

_ops = {}
# define the arg parsers for each operation
for name in sorted((
        "extract_tags", "extract_data", "extract_tag", "extract_cheape",
        "deprotect_map", "load_map", "unload_map", "save_map", "rename_map",
        "spoof_crc", "rename_tag_by_id", "rename_tag", "rename_dir",
        "set_vars", "get_vars", "map_info", "tag_id_tokens", "tag_id_macros",
        "switch_map", "switch_map_by_filepath", "switch_engine",
        "dir", "files", "dir_ct", "file_ct", "dir_names", "file_names",
        "quit", "maps", "engines", "verbose", "prompt", "cls")):
    _ops[name] = repl_subparser.add_parser(
        name.replace("_", "-"), help=command_help_strings[name])


#########################################################################
# add the positional arguments
#########################################################################
_ops["rename_tag"].add_argument(
    'tag-path', help=command_arg_strings["rename_tag"]['tag-path'])

_ops["rename_dir"].add_argument(
    'dir-path', help=command_arg_strings["rename_dir"]['dir-path'])

_ops["prompt"].add_argument(
    'level', default=None, choices=(0, 1, 2), type=int, nargs="?",
    help=command_arg_strings["prompt"]['level'])

_ops["verbose"].add_argument(
    'level', default=None, type=int, choices=(0, 1), nargs="?",
    help=command_arg_strings["verbose"]['level'])

_ops["maps"].add_argument(
    'engine', default=None, nargs="?",
    help=command_arg_strings["maps"]['engine'])

_ops["rename_map"].add_argument(
    'new-name', help=command_arg_strings["rename_map"]['new-name'])

_ops["switch_map"].add_argument(
    'map-name', help=command_arg_strings["switch_map"]['map-name'])

_ops["switch_engine"].add_argument(
    'engine', help=command_arg_strings["switch_engine"]['engine'])

_ops["spoof_crc"].add_argument(
    'new-crc', type=int, help=command_arg_strings["spoof_crc"]['new-crc'])

for name in ("tag_id_tokens", "tag_id_macros"):
    _ops[name].add_argument(
        'prefix', default="", nargs="?",
        help=command_arg_strings[name]['prefix'])

for name in ("load_map", "extract_cheape", "switch_map_by_filepath"):
    _ops[name].add_argument(
        'filepath', help=command_arg_strings[name]['filepath'])

for name in ("deprotect_map", "save_map"):
    _ops[name].add_argument(
        'filepath', default=None, nargs="?",
        help=command_arg_strings[name]['filepath'])

for name in ("dir", "files", "dir_ct", "file_ct",
             "dir_names", "file_names"):
    _ops[name].add_argument(
        'dir', default=None, nargs="?",
        help=command_arg_strings[name]['dir'])

for name in ("rename_tag_by_id", "extract_tag"):
    _ops[name].add_argument(
        'tag-id', help=command_arg_strings[name]['tag-id'])

for name in ("rename_tag_by_id", "rename_tag", "rename_dir"):
    _ops[name].add_argument(
        'new-path', help=command_arg_strings[name]['new-path'])


# most args accept map-name and engine as their last optional positional args
for name in (
        "extract_tags", "extract_data", "extract_tag", "extract_cheape",
        "unload_map", "save_map", "deprotect_map", "rename_map",
        "spoof_crc", "rename_tag_by_id", "rename_tag", "rename_dir",
        "dir", "files", "map_info", "dir_ct", "file_ct",
        "dir_names", "file_names"):
    _ops[name].add_argument(
        'map-name', default=None, nargs="?",
        help=command_arg_strings[name]['map-name'])
    _ops[name].add_argument(
        'engine', default=None, nargs="?",
        help=command_arg_strings[name]['engine'])


#########################################################################
# add the optional arguments
#########################################################################
for name in ("deprotect_map", "load_map"):
    _ops[name].add_argument(
        '-p', '--do-printout', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['do-printout'])

for name in ("deprotect_map", "save_map"):
    _ops[name].add_argument(
        '-o', '--fix-tag-index-offset', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['fix-tag-index-offset'])
    _ops[name].add_argument(
        '--meta-data-expansion', default=None, type=int,
        help=command_arg_strings[name]['meta-data-expansion'])
    _ops[name].add_argument(
        '--raw-data-expansion', default=None, type=int,
        help=command_arg_strings[name]['raw-data-expansion'])
    _ops[name].add_argument(
        '--triangle-data-expansion', default=None, type=int,
        help=command_arg_strings[name]['triangle-data-expansion'])
    _ops[name].add_argument(
        '--vertex-data-expansion', default=None, type=int,
        help=command_arg_strings[name]['vertex-data-expansion'])

for name in ("dir_ct", "file_ct"):
    _ops[name].add_argument(
        '-t', '--total', default=False, action="store_const", const=True,
        dest="total", help=command_arg_strings[name]['total'])

for name in ("extract_tags", "extract_data", "deprotect_map"):
    _ops[name].add_argument(
        '-e', '--print-errors', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['print-errors'])

for name in ("dir", "files"):
    _ops[name].add_argument(
        '-g', '--guides', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['guides'])
    _ops[name].add_argument(
        '-r', '--header', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['header'])
    _ops[name].add_argument(
        '-i', '--indexed', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['indexed'])
    _ops[name].add_argument(
        '-t', '--tag-ids', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['tag-ids'])
    _ops[name].add_argument(
        '-n', '--indent', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['indent'])

for name in ("extract_tag", "extract_tags", "extract_data"):
    _ops[name].add_argument(
        '-x', '--disable-safe-mode', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['disable-safe-mode'])
    _ops[name].add_argument(
        '-z', '--disable-tag-cleaning', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['disable-tag-cleaning'])
    _ops[name].add_argument(
        '-l', '--force-lower-case-paths', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['force-lower-case-paths'])
    _ops[name].add_argument(
        '-c', '--generate-comp-verts', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['generate-comp-verts'])
    _ops[name].add_argument(
        '-u', '--generate-uncomp-verts', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['generate-uncomp-verts'])
    _ops[name].add_argument(
        '-d', '--out-dir', default=None,
        help=command_arg_strings[name]['out-dir'])
    _ops[name].add_argument(
        '-o', '--overwrite', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['overwrite'])
    _ops[name].add_argument(
        '-s', '--rename-scnr-dups', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['rename-scnr-dups'])
    _ops[name].add_argument(
        '-t', '--tagslist-path', default=None,
        help=command_arg_strings[name]['tagslist-path'])

for name in ("extract_tags", "extract_data"):
    _ops[name].add_argument(
        '-m', '--macros', default=True, choices=(0, 1), type=int,
        help=command_arg_strings[name]['macros'])
    _ops[name].add_argument(
        '-r', '--recursive', default=None, choices=(0, 1), type=int,
        help=command_arg_strings[name]['recursive'])
    _ops[name].add_argument(
        '--tag-ids', nargs="*", default=(tag_path_tokens.TOKEN_ALL, ),
        help=command_arg_strings[name]['tag-ids'])

for op_name in (
        "autoload-resources", "do-printout", "print-errors",
        "force-lower-case-paths", "rename-scnr-dups", "overwrite",
        "recursive", "decode-adpcm", "generate-uncomp-verts",
        "generate-comp-verts", "use-tag-index-for-script-names",
        "use-scenario-names-for-script-names", "bitmap-extract-keep-alpha",
        "fix-tag-classes", "fix-tag-index-offset", "use-minimum-priorities",
        "valid-tag-paths-are-accurate", "scrape-tag-paths-from-scripts",
        "limit-tag-path-lengths", "print-heuristic-name-changes",
        "use-heuristics", "shallow-ui-widget-nesting", "rename-cached-tags",
        "disable-safe-mode", "disable-tag-cleaning",
        "skip-seen-tags-during-queue-processing"):
    # these dont get shorthand settings because there are too damn many of them
    _ops["set_vars"].add_argument(
        '--%s' % op_name, default=None, choices=(0, 1), type=int,
        help=command_arg_strings["set_vars"][op_name])
    _ops["get_vars"].add_argument(
        '--%s' % op_name, const=True, default=False, action="store_const",
        help=command_arg_strings["get_vars"][op_name])

_ops["set_vars"].add_argument(
    '--globals-overwrite-mode', default=None, choices=tuple(range(5)), type=int,
    help=command_arg_strings["set_vars"]["globals-overwrite-mode"])
_ops["get_vars"].add_argument(
    '--globals-overwrite-mode', const=True, default=False, action="store_const",
    help=command_arg_strings["get_vars"]["globals-overwrite-mode"])

for op_name in ("tags-dir", "data-dir", "tagslist-path", "bitmap-extract-format"):
    _ops["set_vars"].add_argument(
        '--%s' % op_name, default=None,
        help=command_arg_strings["set_vars"][op_name])
    _ops["get_vars"].add_argument(
        '--%s' % op_name, const=True, default=False, action="store_const",
        help=command_arg_strings["get_vars"][op_name])

_ops["extract_tag"].add_argument(
    '-f', '--filepath', default=None,
    help=command_arg_strings["extract_tag"]['filepath'])

_ops["extract_data"].add_argument(
    '-a', '--decode-adpcm', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["extract_data"]['decode-adpcm'])
_ops["extract_data"].add_argument(
    '-b', '--bitmap-extract-format', default=None, choices=["dds", "tga", "png"],
    help=command_arg_strings["extract_data"]['bitmap-extract-format'])
_ops["extract_data"].add_argument(
    '-k', '--bitmap-extract-keep-alpha', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["extract_data"]['bitmap-extract-keep-alpha'])

_ops["load_map"].add_argument(
    '-a', '--autoload-resources', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["load_map"]['autoload-resources'])
_ops["load_map"].add_argument(
    '-m', '--make-active', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["load_map"]['make-active'])
_ops["load_map"].add_argument(
    '-r', '--replace-if-same-name', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["load_map"]['replace-if-same-name'])

_ops["dir"].add_argument(
    '--depth', default=None, type=int,
    help=command_arg_strings["dir"]['depth'])
_ops["dir"].add_argument(
    '-d', '--dirs-first', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["dir"]['dirs-first'])
_ops["dir"].add_argument(
    '-e', '--extra-dir-spacing', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["dir"]['extra-dir-spacing'])
_ops["dir"].add_argument(
    '-f', '--files', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["dir"]['files'])

_ops["deprotect_map"].add_argument(
    '-f', '--fix-tag-classes', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['fix-tag-classes'])
_ops["deprotect_map"].add_argument(
    '-l', '--limit-tag-path-lengths', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['limit-tag-path-lengths'])
_ops["deprotect_map"].add_argument(
    '-c', '--print-heuristic-name-changes', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['print-heuristic-name-changes'])
_ops["deprotect_map"].add_argument(
    '-r', '--rename-cached-tags', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['rename-cached-tags'])
_ops["deprotect_map"].add_argument(
    '-s', '--scrape-tag-paths-from-scripts', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['scrape-tag-paths-from-scripts'])
_ops["deprotect_map"].add_argument(
    '-w', '--shallow-ui-widget-nesting', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['shallow-ui-widget-nesting'])
_ops["deprotect_map"].add_argument(
    '-u', '--use-heuristics', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['use-heuristics'])
_ops["deprotect_map"].add_argument(
    '-m', '--use-minimum-priorities', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['use-minimum-priorities'])
_ops["deprotect_map"].add_argument(
    '-n', '--use-scenario-names-for-script-names', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['use-scenario-names-for-script-names'])
_ops["deprotect_map"].add_argument(
    '-t', '--use-tag-index-for-script-names', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['use-tag-index-for-script-names'])
_ops["deprotect_map"].add_argument(
    '-v', '--valid-tag-paths-are-accurate', default=None, choices=(0, 1), type=int,
    help=command_arg_strings["deprotect_map"]['valid-tag-paths-are-accurate'])
