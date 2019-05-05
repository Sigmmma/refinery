import argparse

repl_parser = argparse.ArgumentParser(
    description="This is Refinery!"
    )
# make an argument to specify whether commands are to be queued or executed
repl_parser.add_argument(
    'operation', choices=sorted([
        "extract-tags", "extract-data", "extract-tag", "extract-cheape",
        "deprotect-map", "load-map", "unload-map", "save-map", "rename-map",
        "spoof-map-crc", "rename-tag-by-id", "rename-tag", "rename-dir",
        "set", "switch-map", "switch-engine", "map-info", "print-dir",
        "quit", "prompt-simple", "prompt-full"]),
    help='''
'''
    )

# define the arg parsers for each operation
extract_tags_parser = argparse.ArgumentParser()
extract_data_parser = argparse.ArgumentParser()
extract_tag_parser = argparse.ArgumentParser()
extract_cheape_parser = argparse.ArgumentParser()
deprotect_map_parser = argparse.ArgumentParser()
load_map_parser = argparse.ArgumentParser()
unload_map_parser = argparse.ArgumentParser()
save_map_parser = argparse.ArgumentParser()
rename_map_parser = argparse.ArgumentParser()
spoof_map_crc_parser = argparse.ArgumentParser()
rename_tag_by_id_parser = argparse.ArgumentParser()
rename_tag_parser = argparse.ArgumentParser()
rename_dir_parser = argparse.ArgumentParser()
set_parser = argparse.ArgumentParser()
switch_map_parser = argparse.ArgumentParser()
switch_engine_parser = argparse.ArgumentParser()
map_info_parser = argparse.ArgumentParser()
print_dir_parser = argparse.ArgumentParser()


# add arguments to each parser for which they apply

# NOTE: Many of these are optional named arguments, but for some parsers
#       they will be required positional(rename_dir / rename_tag / print_dir).
op_parser.add_argument('--engine')
op_parser.add_argument('--map-name')

op_parser.add_argument('--do-printout', type=bool)
op_parser.add_argument('--print-errors', type=bool)

op_parser.add_argument('--filepath')

op_parser.add_argument('--make-active', type=bool)
op_parser.add_argument('--replace-if-same-name', type=bool)
op_parser.add_argument('--autoload-resources', type=bool)

op_parser.add_argument('--new-path')
op_parser.add_argument('--tag-path')
op_parser.add_argument('--dir-path')

op_parser.add_argument('--tag-ids', nargs="*")
op_parser.add_argument('--tag-id')

op_parser.add_argument('--new-name')
op_parser.add_argument('--new-crc', type=int)
op_parser.add_argument('--name')
op_parser.add_argument('--value')

op_parser.add_argument('--out-dir')
op_parser.add_argument('--tagslist-path')
op_parser.add_argument('--overwrite', type=bool)
op_parser.add_argument('--recursive', type=bool)
op_parser.add_argument('--bitmap-extract-format')
op_parser.add_argument('--bitmap-extract-keep_alpha', type=bool)
op_parser.add_argument('--decode-adpcm', type=bool)
op_parser.add_argument('--generate-uncomp-verts', type=bool)
op_parser.add_argument('--generate-comp-verts', type=bool)

save_map.add_argument('--fix-tag-index-offset', type=bool)
save_map.add_argument('--raw-data-expansion', type=int)
save_map.add_argument('--meta-data-expansion', type=int)
save_map.add_argument('--vertex-data-expansion', type=int)
save_map.add_argument('--triangle-data-expansion', type=int)

deprotect_map.add_argument('--use-heuristics', type=bool)
deprotect_map.add_argument('--use-minimum-priorities', type=bool)
deprotect_map.add_argument('--shallow-ui-widget-nesting', type=bool)
deprotect_map.add_argument('--print_heuristic-name-changes', type=bool)
deprotect_map.add_argument('--fix-tag-classes', type=bool)
deprotect_map.add_argument('--force-lower-case-paths', type=bool)
deprotect_map.add_argument('--rename-scnr-dups', type=bool)
deprotect_map.add_argument('--limit-tag-path-lengths', type=bool)
deprotect_map.add_argument('--scrape-tag-paths-from-scripts', type=bool)
deprotect_map.add_argument('--use-tag-index-for-script-names', type=bool)
deprotect_map.add_argument('--use-scenario-names-for-script-names', type=bool)
deprotect_map.add_argument('--rename-cached-tags', type=bool)
deprotect_map.add_argument('--valid-tag-paths-are-accurate', type=bool)


operation_parsers = dict(
    extract_tags = extract_tags_parser,
    extract_data = extract_data_parser,
    extract_tag = extract_tag_parser,
    extract_cheape = extract_cheape_parser,
    deprotect_map = deprotect_map_parser,
    load_map = load_map_parser,
    unload_map = unload_map_parser,
    save_map = save_map_parser,
    rename_map = rename_map_parser,
    spoof_map_crc = spoof_map_crc_parser,
    rename_tag_by_id = rename_tag_by_id_parser,
    rename_tag = rename_tag_parser,
    rename_dir = rename_dir_parser,
    set = set_parser,
    switch_map = switch_map_parser,
    switch_engine = switch_engine_parser,
    map_info = map_info_parser,
    print_dir = print_dir_parser,
    )
