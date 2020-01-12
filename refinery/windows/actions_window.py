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

from pathlib import Path, PureWindowsPath
from tkinter import messagebox
from binilla.windows.filedialog import asksaveasfilename, askdirectory
from traceback import format_exc

from binilla.widgets.binilla_widget import BinillaWidget
from binilla.widgets.scroll_menu import ScrollMenu

from refinery import editor_constants as e_c
from refinery.constants import MAX_TAG_NAME_LEN, BAD_CLASSES
from refinery.util import is_protected_tag
from refinery.windows.meta_window import MetaWindow

from reclaimer.common_descs import blam_header, QStruct

from supyr_struct.defs.tag_def import TagDef


meta_tag_def = TagDef("meta tag",
    blam_header('\xFF\xFF\xFF\xFF'),
    QStruct('tagdata'),
    )


class RefineryActionsWindow(tk.Toplevel, BinillaWidget):
    app_root = None
    settings = None
    renamable = True
    accept_rename = None
    accept_settings = None
    tag_index_ref = None

    rename_string = None
    newtype_string = None
    recursive_rename = None

    original_name = ""

    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        self.renamable = kwargs.pop('renamable', self.renamable)
        self.settings = settings = kwargs.pop('settings', {})
        self.tag_index_ref = kwargs.pop('tag_index_ref', self.tag_index_ref)
        BinillaWidget.__init__(self, *args, **kwargs)
        tk.Toplevel.__init__(self, *args, **kwargs)

        try:
            self.iconbitmap(e_c.REFINERY_ICON_PATH)
        except Exception:
            if not e_c.IS_LNX:
                print("Could not load window icon.")

        self.bind('<Escape>', lambda e=None, s=self, *a, **kw: s.destroy())

        if self.app_root is None and hasattr(self.master, 'app_root'):
            self.app_root = self.master.app_root

        self.accept_rename   = settings.get('accept_rename', tk.IntVar(self))
        self.accept_settings = settings.get('accept_settings', tk.IntVar(self))
        self.rename_string   = settings.get('rename_string', tk.StringVar(self))
        self.newtype_string  = settings.get('newtype_string', tk.StringVar(self))
        self.extract_to_dir  = settings.get('out_dir', tk.StringVar(self))
        self.tagslist_path   = settings.get('tagslist_path', tk.StringVar(self))
        self.extract_mode    = settings.get('extract_mode', tk.StringVar(self))
        self.recursive_rename = tk.IntVar(self)
        self.resizable(1, 0)

        if title is None:
            title = self.rename_string.get()
            if not title:
                title = "Options"
        self.title(title)

        self.original_name = PureWindowsPath(self.rename_string.get())
        if self.tag_index_ref is not None:
            # this ActionsWindow is displaying a single tag. the
            # original name will have an extension. remove it
            self.original_name = self.original_name.with_suffix("")

        self.rename_string.set(str(self.original_name))
        self.newtype_string.set("")

        self.accept_rename.set(0)
        self.accept_settings.set(0)

        # frames
        self.rename_frame        = tk.LabelFrame(self, text="Rename to")
        self.rename_frame_inner0 = tk.Frame(self.rename_frame)
        self.rename_frame_inner1 = tk.Frame(self.rename_frame)
        self.tags_list_frame  = tk.LabelFrame(
            self, text="Tags list log(erase to disable logging)")
        self.extract_to_frame = tk.LabelFrame(self, text="Directory to extract to")
        self.settings_frame   = tk.LabelFrame(self, text="Extract settings")

        self.button_frame = tk.Frame(self)
        self.accept_frame = tk.Frame(self.button_frame)
        self.cancel_frame = tk.Frame(self.button_frame)

        # rename
        self.rename_entry = tk.Entry(
            self.rename_frame_inner0, width=50, textvariable=self.rename_string)
        self.rename_button = tk.Button(self.rename_frame_inner0, text="Rename",
                                       command=self.rename, width=6)
        self.class_scroll_menu = ScrollMenu(self.rename_frame_inner1,
                                            menu_width=35)
        self.recursive_rename_cbtn = tk.Checkbutton(
            self.rename_frame_inner1, text="Recursive",
            variable=self.recursive_rename)

        if self.tag_index_ref:
            # populate the class_scroll_menu options
            opts = sorted([n for n in self.tag_index_ref.class_1.NAME_MAP])
            self.class_scroll_menu.set_options(opts)
            try:
                self.class_scroll_menu.sel_index = opts.index(
                    self.tag_index_ref.class_1.enum_name)
            except ValueError:
                pass

        # tags list
        self.tags_list_entry = tk.Entry(
            self.tags_list_frame, width=50, textvariable=self.tagslist_path)
        self.browse_tags_list_button = tk.Button(
            self.tags_list_frame, text="Browse", command=self.tags_list_browse)

        # extract to dir
        self.extract_to_entry = tk.Entry(
            self.extract_to_frame, width=50, textvariable=self.extract_to_dir)
        self.browse_extract_to_button = tk.Button(
            self.extract_to_frame, text="Browse",
            command=self.extract_to_browse)

        # settings
        self.recursive_cbtn = tk.Checkbutton(
            self.settings_frame, text="Recursive extraction",
            variable=settings.get("recursive", tk.IntVar(self)))
        self.overwrite_cbtn = tk.Checkbutton(
            self.settings_frame, text="Overwrite tags(not recommended)",
            variable=settings.get("overwrite", tk.IntVar(self)))
        self.do_printout_cbtn = tk.Checkbutton(
            self.settings_frame, text="Print extracted tag names",
            variable=settings.get("do_printout", tk.IntVar(self)))

        # accept/cancel
        self.accept_button = tk.Button(
            self.accept_frame, text="Add to queue",
            command=self.add_to_queue, width=14)
        self.cancel_button = tk.Button(
            self.cancel_frame, text="Cancel",
            command=self.destroy, width=14)
        self.show_meta_button = tk.Button(
            self, text="Display metadata", command=self.show_meta)

        # pack everything
        # frames
        if self.renamable:
            self.rename_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.rename_frame_inner0.pack(expand=True, fill="x")
        self.rename_frame_inner1.pack(expand=True, fill="x")
        self.tags_list_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.extract_to_frame.pack(padx=4, pady=2, expand=True, fill="x")
        self.settings_frame.pack(padx=4, pady=2, expand=True, fill="x")

        self.button_frame.pack(pady=2, expand=True, fill="x")
        self.accept_frame.pack(padx=4, side='left',  fill='x', expand=True)
        self.cancel_frame.pack(padx=4, side='right', fill='x', expand=True)

        # rename
        self.rename_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.rename_button.pack(padx=4, side='left', fill='x')
        if self.tag_index_ref:
            self.class_scroll_menu.pack(padx=4, side='left', fill='x')
        #self.recursive_rename_cbtn.pack(padx=4, side='left', fill='x')

        # extract to
        self.extract_to_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.browse_extract_to_button.pack(padx=4, side='left', fill='x')

        # tags list
        self.tags_list_entry.pack(padx=4, side='left', fill='x', expand=True)
        self.browse_tags_list_button.pack(padx=4, side='left', fill='x')

        # settings
        self.recursive_cbtn.pack(padx=4, anchor='w')
        self.overwrite_cbtn.pack(padx=4, anchor='w')
        self.do_printout_cbtn.pack(padx=4, anchor='w')

        # accept/cancel
        self.accept_button.pack(side='right')
        self.cancel_button.pack(side='left')
        if self.tag_index_ref is not None:
            self.show_meta_button.pack(padx=4, pady=4, expand=True, fill='x')

        # make the window not show up on the start bar
        self.transient(self.master)
        self.wait_visibility()
        self.lift()
        self.grab_set()
        self.apply_style()

        try:
            self.update()
            self.app_root.place_window_relative(self)
            # I would use focus_set, but it doesn't seem to always work
            self.accept_button.focus_force()
        except AttributeError:
            pass

    def apply_style(self, seen=None):
        BinillaWidget.apply_style(self, seen)
        self.update()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry("%sx%s" % (w, h))
        self.minsize(width=w, height=h)

    def add_to_queue(self, e=None):
        self.accept_settings.set(1)
        self.destroy()

    def rename(self, e=None):
        if not self.renamable:
            return

        new_name = self.rename_string.get()
        new_name = str(PureWindowsPath(new_name)).lower().strip(".")
        if self.tag_index_ref is None and new_name:
            # directory of tags
            new_name += "\\"

        old_class = new_class = None
        try:
            old_class = self.tag_index_ref.class_1.enum_name
        except Exception:
            pass

        try:
            new_class = self.class_scroll_menu.get_option()
        except Exception:
            new_class = ""

        #new_name = os.path.splitext(new_name)[0]
        self.rename_string.set(new_name)
        str_len = len(new_name)
        if str_len > MAX_TAG_NAME_LEN:
            messagebox.showerror(
                "Max name length exceeded",
                ("The max length for a tag is limited to %s characters\n" +
                 "Remove %s characters(excluding extension).") %
                (MAX_TAG_NAME_LEN, str_len - MAX_TAG_NAME_LEN), parent=self)
            return
        elif is_protected_tag(new_name):
            messagebox.showerror(
                "Invalid name",
                "The entered string is not a valid filename.", parent=self)
            return
        elif not str_len and self.tag_index_ref is not None:
            messagebox.showerror(
                "Invalid name",
                "The entered string cannot be empty.", parent=self)
            return
        self.accept_rename.set(1)

        # change the type if applicable
        if new_class and new_class != old_class:
            self.newtype_string.set(new_class)

        self.destroy()

    def tags_list_browse(self):
        try:
            init_dir = os.path.dirname(self.tagslist_path.get())
        except Exception:
            init_dir = None
        dirpath = asksaveasfilename(
            initialdir=init_dir, parent=self,
            title="Select where to save the tag list log",
            filetypes=(("text log", "*.txt"), ("All", "*")))

        if not dirpath:
            return

        self.tagslist_path.set(str(Path(dirpath)))

    def extract_to_browse(self):
        dirpath = askdirectory(
            initialdir=self.extract_to_dir.get(), parent=self,
            title="Select the directory to extract tags to")

        if not dirpath:
            return

        self.extract_to_dir.set(str(Path(dirpath)))

    def show_meta(self):
        index_ref = self.tag_index_ref
        if not index_ref:
            return

        try:
            halo_map = self.settings.get("halo_map")
            if halo_map is None:
                print("Could not get map.")
                return

            disable_safe_mode = getattr(self.app_root, "disable_safe_mode")
            disable_tag_cleaning = getattr(self.app_root, "disable_tag_cleaning")

            meta = halo_map.get_meta(
                index_ref.id & 0xFFff, True,
                allow_corrupt=self.settings["allow_corrupt"].get(),
                disable_safe_mode=disable_safe_mode,
                disable_tag_cleaning=disable_tag_cleaning)
            if meta is None:
                print("Could not get meta.")
                return

            meta_tag = meta_tag_def.build()
            meta_tag.data.tagdata = meta
            tag_path = index_ref.path
            meta_tag.filepath = tag_path
            if index_ref.class_1.enum_name not in BAD_CLASSES:
                ext = ".%s" % index_ref.class_1.enum_name
            else:
                ext = ".INVALID"

            w = MetaWindow(self.app_root, meta_tag, engine=halo_map.engine,
                           tag_path=tag_path + ext)
            self.destroy()
            w.focus_set()
        except Exception:
            print(format_exc())
            return


class RefineryEditActionsWindow(RefineryActionsWindow):

    def apply_style(self, seen=None):
        self.rename_frame.pack_forget()
        self.button_frame.pack_forget()
        self.title("Edit: %s" % self.title())
        RefineryActionsWindow.apply_style(self, seen)
