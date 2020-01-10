#!/usr/bin/env python3
#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import argparse
import os
import sys

from time import time
from traceback import format_exc

from refinery import core
from refinery import repl
from refinery.tag_index import tag_path_tokens


def queue_action(unparsed_command):
    command_args = repl.util.convert_arg_line_to_args(unparsed_command.strip())
    if not command_args:
        return None, None

    try:
        args = repl.arg_parsers.repl_parser.parse_args(command_args)
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
    elif op in ("tag_id_tokens", "tag_id_macros"):
        if op == "tag_id_tokens":
            prefix = args.prefix.lower()
            help_strs = repl.help_strs.token_help_strings
        else:
            prefix = args.prefix.upper()
            help_strs = repl.help_strs.macro_help_strings

        for name in sorted(help_strs):
            # print the tag-id macro and token help strings with the same
            # formatting as the help strings in the rest of the program.
            if not name.strip("<>").startswith(prefix.strip("<>")):
                continue

            print("    %s" % name, end=("\n" if len(name) > 18 else ""))
            if len(name) < 19:
                print(" " * (20 - len(name)), end="")
            else:
                print(" " * 24, end="")

            help_str = help_strs[name].replace("\r", "\n").replace("\t", "    ").\
                       replace("\f", " ").replace("\v", " ")
            while help_str:
                curr_line = help_str[: 55]
                help_str = help_str[55: ]

                lines = curr_line.split("\n", 1)
                if len(lines) == 2:
                    curr_line = lines[0]
                    help_str = lines[1] + help_str

                if (help_str and curr_line) and curr_line[-1] != " ":
                    curr_line_pieces = curr_line.split(" ")
                    new_curr_line = ""
                    while curr_line_pieces:
                        line_piece = curr_line_pieces.pop(0)
                        if new_curr_line and (len(line_piece) +
                                              len(new_curr_line) >= 53):
                            curr_line_pieces.insert(0, line_piece)
                            break

                        if new_curr_line: new_curr_line += " "
                        new_curr_line += line_piece

                    curr_line = new_curr_line
                    help_str = "".join(curr_line_pieces + [help_str])

                print(curr_line)
                if help_str:
                    print(" " * 24, end="")

        return None, None
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
        all_tag_ids = []
        for val in kw["tag_ids"]:
            macro = tag_path_tokens.ALL_TOKEN_MACROS_BY_NAMES.get(val.upper())
            if allow_macros and macro:
                tag_ids = macro
            else:
                tag_ids = (val, )

            for tag_id in tag_ids:
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
                if args.level is None:
                    print(prompt_level)
                else:
                    prompt_level = args.level
            elif op == "verbose":
                if args.level is None:
                    print(verbose_level)
                else:
                    verbose_level = args.level
            elif queue_item is not None:
                refinery_instance.process_queue_item(queue_item)
        except Exception:
            print(format_exc(verbose_level))


if __name__ == '__main__':
    start = time()
    init_arg_parser = argparse.ArgumentParser(
        description=repl.help_strs.refinery_desc_string,
        epilog=repl.help_strs.refinery_epilog_string,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    if not hasattr(sys, "orig_stdout"):
        sys.orig_stdout = sys.stdout

    init_arg_parser.add_argument(
        'filepath', nargs='?',
        help='Path to a text file of operations to batch process.')
    init_arg_parser.add_argument(
        '-b', '--batch-mode', default=False, action="store_const", const=True,
        help='Whether to skip going into read-eval-print-loop after batch processing.')


    args = init_arg_parser.parse_args()
    refinery_actions = []
    if args.batch_mode:
        refinery_actions.append("set-vars --globals-overwrite-mode 1")

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
