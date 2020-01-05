#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import os
import refinery
import tkinter as tk

from traceback import format_exc

from binilla.widgets.binilla_widget import BinillaWidget

from refinery import editor_constants as e_c
from refinery import crc_functions


class RefineryChecksumEditorWindow(tk.Toplevel, BinillaWidget):
    active_map = None
    validating = False

    def __init__(self, *args, **kwargs):
        self.active_map = kwargs.pop('active_map', None)
        BinillaWidget.__init__(self, *args, **kwargs)
        tk.Toplevel.__init__(self, *args, **kwargs)

        try:
            self.iconbitmap(e_c.REFINERY_ICON_PATH)
        except Exception:
            if not e_c.IS_LNX:
                print("Could not load window icon.")

        self.geometry("300x80")
        self.title("Change map checksum")
        self.resizable(0, 0)

        self.cs = tk.StringVar(self, 'Checksum functions unavailable')
        self.cs.trace("w", self.validate)

        # frames
        self.checksum_frame = tk.LabelFrame(self, text="Current random checksum")
        self.button_frame = tk.Frame(self)

        # rename
        self.checksum_entry = tk.Entry(
            self.checksum_frame, textvariable=self.cs, justify='center')

        self.apply_button = tk.Button(
            self.button_frame, text="Apply to current map",
            command=self.apply, width=20)

        # pack everything
        self.checksum_frame.pack(padx=4, expand=True, fill="x", pady=2)
        self.button_frame.pack(expand=True, fill="x")

        self.checksum_entry.pack(padx=4, pady=3, side='left',
                                 fill='x', expand=True)
        self.apply_button.pack(side='left', expand=True, padx=4)

        # make the window not show up on the start bar
        self.transient(self.master)

        if self.active_map:
            s = ""
            for c in "%08x" % self.active_map.map_header.crc32:
                s += c
                if len(s) % 3 == 2:
                    s += " "
            self.cs.set(s[: 11])
        self.apply_style()

    def destroy(self):
        try: self.master.checksum_window = None
        except AttributeError: pass
        tk.Toplevel.destroy(self)

    def validate(self, *a):
        if self.active_map is None or self.validating:
            return

        self.validating = True
        try:
            s, ts = self.cs.get(), ""
            test = set("0123456789abcdefABCDEF")
            spaces = 0
            for c in s:
                if c in test:
                    ts += c
                if len(ts) % 3 == 2:
                    ts += " "
                    spaces += 1

            ts = ts[: 11]
            index = self.checksum_entry.index(tk.INSERT)
            self.checksum_entry.icursor(index + spaces)

            if len(ts.replace(" ", "")) == 8:
                c = int(ts.replace(" ", ""), 16)
                self.checksum_entry.config(bg="white")
            else:
                self.checksum_entry.config(bg="red")

            self.cs.set(ts)
        except Exception:
            print(format_exc())

        self.validating = False

    def apply(self, e=None):
        c = self.cs.get().replace(' ', '')
        if self.active_map is None or not c:
            return

        try:
            self.active_map.map_header.crc32 = int(c, 16)
        except Exception:
            return
        self.active_map.force_checksum = True
        self.destroy()
