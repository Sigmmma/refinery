import os
import refinery
import tkinter as tk

from tkinter import messagebox
from traceback import format_exc

from binilla.widgets.binilla_widget import BinillaWidget

from refinery.util import get_cwd, is_protected_tag as is_protected_filename


curr_dir = get_cwd(refinery.__file__)


class RefineryRenameWindow(tk.Toplevel, BinillaWidget):
    active_map = None

    def __init__(self, *args, **kwargs):
        self.active_map = kwargs.pop('active_map', None)
        BinillaWidget.__init__(self, *args, **kwargs)
        tk.Toplevel.__init__(self, *args, **kwargs)
        
        try:
            try:
                self.iconbitmap(os.path.join(curr_dir, 'refinery.ico'))
            except Exception:
                self.iconbitmap(os.path.join(curr_dir, 'icons', 'refinery.ico'))
        except Exception:
            print("Could not load window icon.")

        self.geometry("300x80")
        self.title("Rename map")
        self.resizable(0, 0)

        self.rename_string = tk.StringVar(self)
        if self.active_map:
            self.rename_string.set(self.active_map.map_header.map_name)

        # frames
        self.rename_frame = tk.LabelFrame(self, text="Rename to")

        self.button_frame = tk.Frame(self)
        self.button_frame_l = tk.Frame(self.button_frame)
        self.button_frame_r = tk.Frame(self.button_frame)

        # rename
        self.rename_entry = tk.Entry(
            self.rename_frame, textvariable=self.rename_string)

        # accept/cancel
        self.rename_button = tk.Button(
            self.button_frame_l, text="Rename", command=self.rename, width=10)
        self.cancel_button = tk.Button(
            self.button_frame_r, text="Cancel", command=self.destroy, width=10)

        # pack everything
        self.rename_frame.pack(padx=4, expand=True, fill="x", pady=2)
        self.button_frame.pack(pady=2, expand=True, fill="x")

        self.button_frame_l.pack(padx=4, side='left',  fill='x', expand=True)
        self.button_frame_r.pack(padx=4, side='right', fill='x', expand=True)

        self.rename_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.rename_button.pack(side='right')
        self.cancel_button.pack(side='left')

        # make the window not show up on the start bar
        self.transient(self.master)
        self.apply_style()

    def destroy(self):
        try: self.master.rename_window = None
        except AttributeError: pass
        tk.Toplevel.destroy(self)

    def rename(self, e=None):
        new_name = self.rename_string.get()
        if len(new_name) > 31:
            messagebox.showerror(
                "Max name length exceeded",
                "The max length for a map is limited to 31 characters.\n",
                parent=self)
        elif is_protected_filename(new_name) or "/" in new_name or "\\" in new_name:
            messagebox.showerror(
                "Invalid name",
                "The entered string is not a valid map name.", parent=self)
        elif not new_name:
            messagebox.showerror(
                "Invalid name",
                "The entered string cannot be empty.", parent=self)
        else:
            old_name = self.active_map.map_header.map_name
            self.active_map.maps.pop(old_name, None)
            self.active_map.map_header.map_name = new_name
            self.active_map.maps[new_name] = self.active_map

            self.master.display_map_info()
            self.master.reload_map_select_options()
            self.destroy()
