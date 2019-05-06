import argparse
import os

from time import time
from traceback import format_exc
from refinery import core

from refinery.arg_parsers import repl_parser


def execute_action(refinery, unparsed_command):
    unparsed_command = unparsed_command.strip()
    if not unparsed_command:
        return None, None

    try:
        args = repl_parser.parse_args(
            convert_arg_line_to_args(unparsed_command))
        op = args.operation.replace("-", "_")
    except SystemExit:
        op = args = None

    if op in ("quit", "maps", "engines", "prompt", "get_val", "verbose",
              None):
        return op, args

    kw = {k.replace("-", "_"): v for k, v in
          vars(args).items() if v is not None}
    if op in ("dir", "files", "map_info", "dir_ct", "file_ct",
              "dir_names", "file_names"):
        op = "print_" + op
        kw["do_printout"] = True
    elif op in ("set_bool", "set_str"):
        kw["name"] = kw["name"].replace("-", "_")

    kw.pop("operation", None)
    try: kw["tag_id"] = int(kw["tag_id"])
    except: pass

    if kw.get("tag_ids"):
        tag_ids = [None] * len(kw["tag_ids"])
        i = 0
        for val in kw["tag_ids"]:
            try:
                tag_ids[i] = int(val)
            except ValueError:
                tag_ids[i] = val
            i += 1

        kw["tag_ids"] = tag_ids

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
            elif op == "get_val":
                print("%s=%s" % (args.name, getattr(
                    refinery, args.name.replace("-", "_"))))
                
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
