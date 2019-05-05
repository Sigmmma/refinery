import os

from time import time
from traceback import format_exc
from refinery import core

from refinery.arg_parsers import repl_parser, operation_parsers


def execute_action(refinery, unparsed_command):
    unparsed_command = unparsed_command.strip()
    if not unparsed_command:
        return

    try:
        repl_args, remainder = repl_parser.parse_known_args(
            convert_arg_line_to_args(unparsed_command))
        op = repl_args.operation.replace("-", "_")
    except SystemExit:
        op = None

    print(op)
    if op in ("quit", "prompt_simple", "prompt_full"):
        return op
    elif op == "map_info":
        print(refinery.generate_map_info_string())
        return
    elif op not in operation_parsers:
        return

    args = operation_parsers[op].parse_args(
        convert_arg_line_to_args(unparsed_command))


def main_loop(refinery):
    prompt_full = False
    while True:
        if not refinery.active_map_name:
            prompt = "Refinery: "
        elif refinery.maps_by_engine:
            prompt = ""
            if prompt_full and refinery.active_engine_name:
                prompt = "%s: " % refinery.active_engine_name
            prompt = "%s%s: " % (prompt, refinery.active_map_name)

        try:
            result = execute_action(refinery, input(prompt))
            if result == "quit":
                break
            elif result in ("prompt_simple", "prompt_full"):
                prompt_full = result == "prompt_full"
        except Exception:
            print(format_exc())
            input()
            break


def convert_arg_line_to_args(arg_line):
    arg_line = arg_line.strip()
    args = []
    i = 0
    while i < len(arg_line):
        # find the next non-whitespace character
        while i < len(arg_line):
            if arg_line[i] != " ":
                break
            i += 1

        if arg_line[i] == '"':
            # there's a quote to start this argument. find the
            # next quote and encapsulate everything as the arg
            i += 1  # jump past the first "
            arg_end_i = arg_line.find('"', i)
        else:
            next_space_i = arg_line.find(' ', i)
            next_quote_i = arg_line.find('"', i)
            if next_space_i < 0 or (next_quote_i >= 0 and
                                    next_quote_i < next_space_i):
                arg_end_i = next_quote_i
            else:
                arg_end_i = next_space_i

        if arg_end_i < 0: arg_end_i = len(arg_line)

        args.append(arg_line[i: arg_end_i])
        i = arg_end_i

        if i < len(arg_line) and arg_line[arg_end_i] == '"':
            i += 1  # jump past the last "

    return args


if __name__ == '__main__':
    init_arg_parser = argparse.ArgumentParser(description="This is Refinery!")

    init_arg_parser.add_argument(
        'batch_filepath', action='store', nargs='?',
        help='Path to a text file where each line is an action to execute. '
        'Blank lines are ignored and ')

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
