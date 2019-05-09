import argparse
import os
import sys

from time import time
from traceback import format_exc

from refinery import core
from refinery import tag_path_tokens
from refinery import repl_arg_parsers
from refinery import repl_util


# TODO: Fill out the tag-id-macros function


def queue_action(unparsed_command):
    command_args = repl_util.convert_arg_line_to_args(unparsed_command.strip())
    if not command_args:
        return None, None

    try:
        args = repl_arg_parsers.repl_parser.parse_args(command_args)
        op = args.operation.replace("-", "_").lower()
    except SystemExit:
        op = args = None

    if op in ("quit", "prompt", "verbose", None):
        return op, args
    elif op in ("engines", "maps"):
        if op == "engines":
            keys = set(refinery_instance.maps_by_engine)
        elif args.engine:
            keys = set(refinery_instance.maps_by_engine.get(args.engine, {}))
        else:
            keys = set(refinery_instance.active_maps)

        try: keys.remove(core.ACTIVE_INDEX)
        except Exception: pass

        print(list(sorted(keys)))
        return None, None
    elif op == "get_vars":
        print_flags = vars(args)
        print_flags.pop("operation", None)
        if not sum(print_flags.values()):
            for name in print_flags:
                print_flags[name] = True

        for name in sorted(print_flags):
            if not print_flags[name]: continue

            val = getattr(refinery_instance, name)
            name = "--" + name.replace("_", "-")
            if isinstance(val, str):
                print('%s "%s"' % (name, val))
            elif isinstance(val, bool):
                print('%s %s' % (name, int(val)))
            else:
                print('%s %s' % (name, val))
        return None, None
    elif op == "cls":
        os.system('cls')
        return None, None

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
                    if token in tag_path_tokens.tokens_to_tag_paths:
                        token = tag_path_tokens.tokens_to_tag_paths[token]

                    if token:
                        tag_id = token

                try:
                    all_tag_ids.append(int(tag_id))
                except ValueError:
                    all_tag_ids.append(tag_id)

        kw["tag_ids"] = all_tag_ids

    refinery_instance.enqueue(op, **kw)
    return None, None


def main_loop():
    prompt_level = 1
    verbose_level = 10
    while True:
        if prompt_level == 0 or not refinery_instance.active_map_name:
            prompt = "Refinery: "
        elif refinery_instance.maps_by_engine:
            prompt = ""
            if prompt_level == 2 and refinery_instance.active_engine_name:
                prompt = "%s: " % refinery_instance.active_engine_name
            prompt = "%s%s: " % (prompt, refinery_instance.active_map_name)

        try:
            op, args = queue_action(input(prompt))
            queue_item = refinery_instance.dequeue(0)
            if op == "quit":
                break
            elif op == "prompt":
                prompt_level = args.level
            elif op == "verbose":
                verbose_level = args.level
            elif queue_item is not None:
                refinery_instance.process_queue_item(queue_item)
        except Exception:
            print(format_exc(verbose_level))


if __name__ == '__main__':
    start = time()
    init_arg_parser = argparse.ArgumentParser(
        description="This is Refinery!")

    if not hasattr(sys, "orig_stdout"):
        sys.orig_stdout = sys.stdout

    init_arg_parser.add_argument(
        'filepath', nargs='?',
        help='Path to a text file where each line is an action to execute.')
    init_arg_parser.add_argument(
        '-b', '--batch-mode', default=False, action="store_const", const=True,
        dest="batch_mode")


    args = init_arg_parser.parse_args()
    refinery_actions = []
    try:
        with open(args.filepath, "r") as f:
            refinery_actions.extend(line.strip() for line in f if line.strip())
    except Exception:
        pass

    refinery_instance = core.RefineryCore()

    if refinery_actions:
        for unparsed_action in refinery_actions:
            try:
                queue_action(unparsed_action)
            except Exception:
                print(format_exc())

        try:
            refinery_instance.process_queue()
        except Exception:
            print(format_exc())

        print("Finished. Took %s seconds." % round(time() - start, 1))

    if not args.batch_mode:
        main_loop()
