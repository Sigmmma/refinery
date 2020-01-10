#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

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

        if arg_line[i] == ";": break

        if arg_line[i] == '"':
            # there's a quote to start this argument. find the
            # next quote and encapsulate everything as the arg
            i += 1  # jump past the first "
            arg_end_i = arg_line.find('"', i)
        else:
            arg_end_i = -1
            for char in ';" \t':
                char_i = arg_line.find(char, i)
                if arg_end_i < 0 or (char_i < arg_end_i and char_i >= 0):
                    arg_end_i = char_i

        if arg_end_i < 0: arg_end_i = len(arg_line)

        args.append(arg_line[i: arg_end_i])
        i = arg_end_i

        if i < len(arg_line):
            if arg_line[i] == ";":
                break

            i += 1  # jump past the last "
    return args
