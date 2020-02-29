#!/usr/bin/env python3
#
# This file is part of Refinery.
#
# For authors and copyright check AUTHORS.TXT
#
# Refinery is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import sys

def main():
    info = sys.version_info

    if info[0] < 3 or (info[0] == 3 and info[1] < 5):
        input(
            "You must have python 3.5 or higher installed to run Refinery.\n"
            "You currently have %s.%s.%s installed instead." % info[:3])
        raise SystemExit(0)

    from datetime import datetime
    from traceback import format_exc

    try:
        from refinery.main import Refinery
        main_window = Refinery()
        main_window.mainloop()

    except Exception:
        exception = format_exc()
        try:
            main_window.log_file.write('\n' + exception)
        except Exception:
            try:
                with open('startup_crash.log', 'a+') as cfile:
                    time = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
                    cfile.write("\n%s%s%s\n" % ("-"*30, time, "-"*(50-len(time))))
                    cfile.write(time + exception)
            except Exception:
                pass
        print(exception, file=sys.stderr)
        return 1;

if __name__ == "__main__":
    main()
