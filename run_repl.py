import argparse
import os

from time import time
from traceback import format_exc

from refinery import core
from refinery import tag_path_tokens
from refinery import arg_parsers


def execute_action(refinery, unparsed_command):
    unparsed_command = unparsed_command.strip()
    if not unparsed_command:
        return None, None

    try:
        args = arg_parsers.repl_parser.parse_args(
            convert_arg_line_to_args(unparsed_command))
        op = args.operation.replace("-", "_")
    except SystemExit:
        op = args = None

    if op in ("quit", "maps", "engines", "prompt", "get_vars", "verbose",
              None):
        return op, args

    kw = {k.replace("-", "_"): v for k, v in
          vars(args).items() if v is not None}
    kw.pop("operation", None)

    if op in ("dir", "files", "map_info", "dir_ct", "file_ct",
              "dir_names", "file_names"):
        op = "print_" + op
        kw["do_printout"] = True
    elif op in ("set_bool", "set_str"):
        kw["name"] = kw["name"].replace("-", "_")
    elif op == "set_vars":
        names = []
        values = []
        for name in sorted(kw):
            names.append(name)
            values.append(kw[name])

        kw.clear()
        kw.update(names=names, values=values)

    try: kw["tag_id"] = int(kw["tag_id"])
    except: pass

    if kw.get("tag_ids"):
        allow_macros = kw.pop("macros", False)
        allow_tokens = kw.pop("tokens", False) or allow_macros
        all_tag_ids = []
        for val in kw["tag_ids"]:
            macro = tag_path_tokens.ALL_TOKEN_MACROS_BY_NAMES.get(val.upper())
            if allow_macros and macro:
                tag_ids = macro
            else:
                tag_ids = (val, )

            for tag_id in tag_ids:
                if allow_tokens:
                    token = tag_id
                    if token in tag_path_tokens.ALL_TOKENS_BY_NAMES:
                        token = tag_path_tokens.ALL_TOKENS_BY_NAMES[token]

                    if token in tag_path_tokens.tokens_to_tag_paths:
                        token = tag_path_tokens.tokens_to_tag_paths[token]

                    if token:
                        tag_id = token

                try:
                    all_tag_ids.append(int(tag_id))
                except ValueError:
                    all_tag_ids.append(tag_id)

        kw["tag_ids"] = all_tag_ids

    # load-map "C:\Users\Moses\Desktop\halo\maps\[H3] Imposing V2.map"
    refinery.enqueue(op, **kw)
    refinery.process_queue_item(refinery.dequeue(0))
    return None, None


def main_loop(refinery):
    prompt_level = 1
    verbose_level = 10
    while True:
        if prompt_level == 0 or not refinery.active_map_name:
            prompt = "Refinery: "
        elif refinery.maps_by_engine:
            prompt = ""
            if prompt_level == 2 and refinery.active_engine_name:
                prompt = "%s: " % refinery.active_engine_name
            prompt = "%s%s: " % (prompt, refinery.active_map_name)

        try:
            op, args = execute_action(refinery, input(prompt))
            if op == "quit":
                break
            elif op == "prompt":
                prompt_level = args.level
            elif op == "verbose":
                verbose_level = args.level
            elif op in ("engines", "maps"):
                if op == "engines":
                    keys = set(refinery.maps_by_engine)
                else:
                    keys = set(refinery.active_maps)

                try: keys.remove(core.ACTIVE_INDEX)
                except Exception: pass

                print(list(sorted(keys)))
            elif op == "get_vars":
                print_flags = vars(args)
                print_flags.pop("operation", None)
                if not sum(print_flags.values()):
                    for name in print_flags:
                        print_flags[name] = True

                for name in sorted(print_flags):
                    if not print_flags[name]: continue

                    val = getattr(refinery, name)
                    name = "--" + name.replace("_", "-")
                    if isinstance(val, str):
                        print('%s "%s"' % (name, val))
                    elif isinstance(val, bool):
                        print('%s %s' % (name, int(val)))
                    else:
                        print('%s %s' % (name, val))

        except Exception:
            print(format_exc(verbose_level))


def convert_arg_line_to_args(arg_line):
    arg_line = arg_line.strip()
    args = []
    i = 0
    while i < len(arg_line):
        # find the next non-whitespace character
        while i < len(arg_line):
            if arg_line[i] not in " \t":
                break
            i += 1

        if arg_line[i] == '"':
            # there's a quote to start this argument. find the
            # next quote and encapsulate everything as the arg
            i += 1  # jump past the first "
            arg_end_i = arg_line.find('"', i)
        else:
            arg_end_i = -1
            for char in '" \t':
                char_i = arg_line.find(char, i)
                if arg_end_i < 0 or (char_i < arg_end_i and char_i >= 0):
                    arg_end_i = char_i

        if arg_end_i < 0: arg_end_i = len(arg_line)

        args.append(arg_line[i: arg_end_i])
        i = arg_end_i

        if i < len(arg_line) and arg_line[arg_end_i] == '"':
            i += 1  # jump past the last "
    return args


if __name__ == '__main__':
    init_arg_parser = argparse.ArgumentParser(
        description="This is Refinery!")

    init_arg_parser.add_argument(
        'batch_filepath', action='store', nargs='?',
        help='Path to a text file where each line is an action to execute.')

    args = init_arg_parser.parse_args()
    try:
        with open(args.batch_filepath, "r") as f:
            refinery_actions = [line.strip() for line in f if line.strip()]
    except Exception:
        refinery_actions = []

    refinery_instance = core.RefineryCore()

    if refinery_actions:
        for unparsed_action in refinery_actions:
            try:
                execute_action(refinery_instance, unparsed_action)
            except Exception:
                print(format_exc())
    else:
        main_loop(refinery_instance)
