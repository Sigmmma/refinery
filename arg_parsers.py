import argparse

__all__ = ("repl_parser", "repl_subparser",)


repl_parser = argparse.ArgumentParser(
    description="This is Refinery!"
    )
# make an argument to specify whether commands are to be queued or executed
repl_subparser = repl_parser.add_subparsers(dest="operation")

_ops = {}
# define the arg parsers for each operation
for name in sorted((
        "extract_tags", "extract_data", "extract_tag", "extract_cheape",
        "deprotect_map", "load_map", "unload_map", "save_map", "rename_map",
        "spoof_crc", "rename_tag_by_id", "rename_tag", "rename_dir",
        "set_bool", "set_str", "map_info", "switch_map", "switch_engine",
        "dir", "files", "dir_ct", "file_ct", "dir_names", "file_names",
        "get_val", "quit", "maps", "engines", "verbose", "prompt")):
    _ops[name] = repl_subparser.add_parser(name.replace("_", "-"))


#########################################################################
# add the positional arguments
#########################################################################
_ops["rename_tag"].add_argument(
    'tag-path')

_ops["rename_dir"].add_argument(
    'dir-path')

_ops["prompt"].add_argument(
    'full', default=False, type=int)

_ops["verbose"].add_argument(
    'full', default=False, type=int)

_ops["rename_map"].add_argument(
    'new-name')

_ops["switch_map"].add_argument(
    'map-name')

_ops["switch_engine"].add_argument(
    'engine')

_ops["spoof_crc"].add_argument(
    'new-crc', type=int)

_ops["set_bool"].add_argument('name', choices=(
    "autoload-resources", "do-printout", "print-errors",
    "force-lower-case-paths", "rename-scnr-dups", "overwrite",
    "recursive", "decode-adpcm", "generate-uncomp-verts",
    "generate-comp-verts", "use-tag-index-for-script-names",
    "use-scenario-names-for-script-names", "bitmap-extract-keep-alpha",
    "fix-tag-classes", "fix-tag-index-offset", "use-minimum-priorities",
    "valid-tag-paths-are-accurate", "scrape-tag-paths-from-scripts",
    "limit-tag-path-lengths", "print-heuristic-name-changes",
    "use-heuristics", "shallow-ui-widget-nesting", "rename-cached-tags",
    ))
_ops["set_bool"].add_argument(
    'value', type=int)

_ops["set_str"].add_argument('name', choices=(
    "tags-dir", "data-dir", "tagslist-path",
    "bitmap-extract-format",
    ))
_ops["set_str"].add_argument(
    'value')

_ops["get_val"].add_argument('name', choices=(
    "autoload-resources", "do-printout", "print-errors",
    "force-lower-case-paths", "rename-scnr-dups", "overwrite",
    "recursive", "decode-adpcm", "generate-uncomp-verts",
    "generate-comp-verts", "use-tag-index-for-script-names",
    "use-scenario-names-for-script-names", "bitmap-extract-keep-alpha",
    "fix-tag-classes", "fix-tag-index-offset", "use-minimum-priorities",
    "valid-tag-paths-are-accurate", "scrape-tag-paths-from-scripts",
    "limit-tag-path-lengths", "print-heuristic-name-changes",
    "use-heuristics", "shallow-ui-widget-nesting", "rename-cached-tags",
    "tags-dir", "data-dir", "tagslist-path",
    "bitmap-extract-format",
    ))


for name in ("load_map", "extract_cheape"):
    _ops[name].add_argument(
        'filepath', default=None)

for name in ("deprotect_map", "save_map"):
    _ops[name].add_argument(
        'filepath', default=None, nargs="?")

for name in ("dir", "files", "dir_ct", "file_ct",
             "dir_names", "file_names"):
    _ops[name].add_argument(
        'dir', default=None, nargs="?")

for name in ("rename_tag_by_id", "extract_tag"):
    _ops[name].add_argument(
        'tag-id')

for name in ("rename_tag_by_id", "rename_tag", "rename_dir"):
    _ops[name].add_argument(
        'new-path')


# most args accept map-name and engine as their last optional positional args
for name in (
        "extract_tags", "extract_data", "extract_tag", "extract_cheape",
        "unload_map", "save_map", "deprotect_map", "rename_map",
        "spoof_crc", "rename_tag_by_id", "rename_tag", "rename_dir",
        "dir", "files", "map_info", "dir_ct", "file_ct",
        "dir_names", "file_names"):
    _ops[name].add_argument(
        'map-name', default=None, nargs="?")
    _ops[name].add_argument(
        'engine', default=None, nargs="?")


#########################################################################
# add the optional arguments
#########################################################################
for name in ("deprotect_map", "load_map"):
    _ops[name].add_argument(
        '--do-printout', default=None, type=int)

for name in ("deprotect_map", "save_map"):
    _ops[name].add_argument(
        '--fix-tag-index-offset', default=None, type=int)
    _ops[name].add_argument(
        '--meta-data-expansion', default=None, type=int)
    _ops[name].add_argument(
        '--raw-data-expansion', default=None, type=int)
    _ops[name].add_argument(
        '--triangle-data-expansion', default=None, type=int)
    _ops[name].add_argument(
        '--vertex-data-expansion', default=None, type=int)

for name in ("dir_ct", "file_ct"):
    _ops[name].add_argument(
        '-t', '--total', default=False, action="store_const", const=True,
        dest="total")

for name in ("extract_tags", "extract_data", "deprotect_map"):
    _ops[name].add_argument(
        '--print-errors', default=None, type=int)

for name in ("dir", "files"):
    _ops[name].add_argument(
        '--depth', default=None, type=int)
    _ops[name].add_argument(
        '--guides', default=None, type=int)
    _ops[name].add_argument(
        '--header', default=None, type=int)
    _ops[name].add_argument(
        '--indexed', default=None, type=int)
    _ops[name].add_argument(
        '--tag-ids', default=None, type=int)

for name in ("extract_tag", "extract_tags", "extract_data"):
    _ops[name].add_argument(
        '--force-lower-case-paths', default=None, type=int)
    _ops[name].add_argument(
        '--generate-comp-verts', default=None, type=int)
    _ops[name].add_argument(
        '--generate-uncomp-verts', default=None, type=int)
    _ops[name].add_argument(
        '--out-dir', default=None)
    _ops[name].add_argument(
        '--overwrite', default=None, type=int)
    _ops[name].add_argument(
        '--recursive', default=None, type=int)
    _ops[name].add_argument(
        '--rename-scnr-dups', default=None, type=int)
    _ops[name].add_argument(
        '--tagslist-path', default=None)

_ops["extract_tag"].add_argument(
    '--filepath', default=None)

_ops["extract_data"].add_argument(
    '--decode-adpcm', default=None, type=int)
_ops["extract_data"].add_argument(
    '--bitmap-extract-format', default=None, choices=["dds", "tga", "png"])
_ops["extract_data"].add_argument(
    '--bitmap-extract-keep_alpha', default=None, type=int)

_ops["load_map"].add_argument(
    '--autoload-resources', default=None, type=int)
_ops["load_map"].add_argument(
    '--make-active', default=None, type=int)
_ops["load_map"].add_argument(
    '--replace-if-same-name', default=None, type=int)

_ops["dir"].add_argument(
    '--dirs-first', default=None, type=int)
_ops["dir"].add_argument(
    '--extra-dir-spacing', default=None, type=int)
_ops["dir"].add_argument(
    '--files', default=None, type=int)
_ops["dir"].add_argument(
    '--indent', default=None, type=int)

_ops["deprotect_map"].add_argument(
    '--fix-tag-classes', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--limit-tag-path-lengths', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--print-heuristic-name-changes', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--rename-cached-tags', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--scrape-tag-paths-from-scripts', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--shallow-ui-widget-nesting', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--use-heuristics', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--use-minimum-priorities', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--use-scenario-names-for-script-names', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--use-tag-index-for-script-names', default=None, type=int)
_ops["deprotect_map"].add_argument(
    '--valid-tag-paths-are-accurate', default=None, type=int)


#########################################################################
# add the REQUIRED "optional" arguments
#########################################################################
for name in ("extract_tags", "extract_data"):
    _ops[name].add_argument(
        '--tag-ids', required=True, nargs="*")
