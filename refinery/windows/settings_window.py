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
import tkinter.font
import tkinter as tk

from pathlib import Path
from binilla.windows.filedialog import asksaveasfilename, askdirectory
from tkinter import ttk
from traceback import format_exc

from binilla.widgets.binilla_widget import BinillaWidget
from binilla.widgets.scroll_menu import ScrollMenu
from binilla import editor_constants as e_c

from refinery import editor_constants as e_c
from refinery.defs.config_def import bitmap_file_formats, \
     globals_overwrite_gui_names


class RefinerySettingsWindow(tk.Toplevel, BinillaWidget):
    settings = None

    def __init__(self, *args, **kwargs):
        self.settings = settings = kwargs.pop('settings', {})
        BinillaWidget.__init__(self, *args, **kwargs)
        tk.Toplevel.__init__(self, *args, **kwargs)
        try:
            self.iconbitmap(e_c.REFINERY_ICON_PATH)
        except Exception:
            if not e_c.IS_LNX:
                print("Could not load window icon.")

        self.geometry("550x350")
        self.minsize(width=450, height=350)
        self.resizable(1, 1)
        self.title("Settings")

        self.tabs = ttk.Notebook(self)
        self.dirs_frame         = tk.Frame(self.tabs)
        self.extract_frame      = tk.Frame(self.tabs)
        self.data_extract_frame = tk.Frame(self.tabs)
        self.tag_fixup_frame    = tk.Frame(self.tabs)
        self.deprotect_frame    = tk.Frame(self.tabs)
        self.heuristics_frame   = tk.Frame(self.tabs)
        self.fonts_frame        = tk.Frame(self.tabs)
        self.other_frame        = tk.Frame(self.tabs)

        self.tabs.add(self.dirs_frame, text="Directories")
        self.tabs.add(self.extract_frame, text="Extraction")
        self.tabs.add(self.data_extract_frame, text="Data extraction")
        self.tabs.add(self.tag_fixup_frame, text="Tag fixup")
        self.tabs.add(self.deprotect_frame, text="Deprotection")
        self.tabs.add(self.heuristics_frame, text="Heuristics")
        self.tabs.add(self.fonts_frame, text="Fonts")
        self.tabs.add(self.other_frame, text="Other")

        font_families = tuple(sorted(tkinter.font.families()))

        self.tags_dir_frame  = tk.LabelFrame(
            self.dirs_frame, text="Default tags extraction folder")
        self.data_dir_frame  = tk.LabelFrame(
            self.dirs_frame, text="Default data extraction folder")
        self.tags_list_frame = tk.LabelFrame(
            self.dirs_frame, text="Tags list log (erase to disable logging)")

        for attr in ("overwrite", "recursive",
                     "rename_scnr_dups", "decode_adpcm",
                     "bitmap_extract_keep_alpha",
                     "generate_comp_verts", "generate_uncomp_verts",
                     "force_lower_case_paths", "fix_tag_classes",
                     "autoload_resources", "extract_yelo_cheape",
                     "use_minimum_priorities", "use_heuristics",
                     "rename_cached_tags", "show_all_fields",
                     "show_structure_meta",
                     "edit_all_fields", "allow_corrupt",
                     "valid_tag_paths_are_accurate", "limit_tag_path_lengths",
                     "scrape_tag_paths_from_scripts", "shallow_ui_widget_nesting",
                     "fix_tag_index_offset", "use_tag_index_for_script_names",
                     "do_printout", "print_heuristic_name_changes",
                     "use_scenario_names_for_script_names",
                     "skip_seen_tags_during_queue_processing",
                     "disable_safe_mode", "disable_tag_cleaning",):
            object.__setattr__(self, attr, settings.get(attr, tk.IntVar(self)))

        for attr in ("bitmap_extract_format", "globals_overwrite_mode",
                     "tags_dir", "data_dir", "tagslist_path"):
            object.__setattr__(self, attr, settings.get(attr, tk.StringVar(self)))


        # tags directory
        self.tags_dir_entry = tk.Entry(
            self.tags_dir_frame, state='disabled',
            textvariable=self.tags_dir)
        self.tags_dir_browse_button = tk.Button(
            self.tags_dir_frame, text="Browse",
            command=self.tags_dir_browse, width=6)

        # data directory
        self.data_dir_entry = tk.Entry(
            self.data_dir_frame, state='disabled',
            textvariable=self.data_dir)
        self.data_dir_browse_button = tk.Button(
            self.data_dir_frame, text="Browse",
            command=self.data_dir_browse, width=6)

        # tags list
        self.tags_list_entry = tk.Entry(
            self.tags_list_frame, textvariable=self.tagslist_path)
        self.browse_tags_list_button = tk.Button(
            self.tags_list_frame, text="Browse",
            command=self.tags_list_browse, width=6)


        self.rename_scnr_dups_cbtn = tk.Checkbutton(
            self.tag_fixup_frame, text=(
                "Rename duplicate camera points, cutscene\n"+
                "flags, and recorded animations in scenario"),
            variable=self.rename_scnr_dups, justify="left")
        self.generate_comp_verts_cbtn = tk.Checkbutton(
            self.tag_fixup_frame, text="Generate compressed lightmap vertices",
            variable=self.generate_comp_verts)
        self.generate_uncomp_verts_cbtn = tk.Checkbutton(
            self.tag_fixup_frame, text="Generate uncompressed lightmap vertices",
            variable=self.generate_uncomp_verts)

        self.dont_touch_frame = tk.LabelFrame(
            self.tag_fixup_frame,
            text="ONLY CHECK THESE IF YOU ARE NOT DEALING WITH PROTECTED MAPS")
        self.disable_safe_mode_cbtn = tk.Checkbutton(
            self.dont_touch_frame, variable=self.disable_safe_mode, justify="left",
            text="Disable safe-mode")
        self.disable_tag_cleaning_cbtn = tk.Checkbutton(
            self.dont_touch_frame, variable=self.disable_tag_cleaning, justify="left",
            text="Disable cleaning errors from tags when reading them.")


        self.overwrite_cbtn = tk.Checkbutton(
            self.extract_frame, text="Overwrite files(not recommended)",
            variable=self.overwrite)
        self.recursive_cbtn = tk.Checkbutton(
            self.extract_frame, text="Recursive extraction",
            variable=self.recursive)
        self.do_printout_cbtn = tk.Checkbutton(
            self.extract_frame, text="Print extracted file names",
            variable=self.do_printout)
        self.force_lower_case_paths_cbtn = tk.Checkbutton(
            self.extract_frame, text="Force all tag paths to lowercase",
            variable=self.force_lower_case_paths)
        self.skip_seen_tags_during_queue_processing_cbtn = tk.Checkbutton(
            self.extract_frame, text="During processing, skip any tags that were already extracted",
            variable=self.skip_seen_tags_during_queue_processing)
        self.globals_overwrite_mode_frame = tk.LabelFrame(
            self.extract_frame, relief="flat",
            text="When to overwrite an existing globals.globals")

        sel_index = self.globals_overwrite_mode.get()
        if sel_index not in range(len(globals_overwrite_gui_names)):
            sel_index = 0

        self.globals_overwrite_mode_menu = ScrollMenu(
            self.globals_overwrite_mode_frame, sel_index=sel_index,
            variable=self.globals_overwrite_mode, menu_width=50,
            options=globals_overwrite_gui_names)


        self.decode_adpcm_cbtn = tk.Checkbutton(
            self.data_extract_frame, variable=self.decode_adpcm,
            text="Decode Xbox audio")
        self.bitmap_extract_frame = tk.LabelFrame(
            self.data_extract_frame, relief="flat",
            text="Bitmap extraction format")
        self.bitmap_extract_keep_alpha_cbtn = tk.Checkbutton(
            self.bitmap_extract_frame, variable=self.bitmap_extract_keep_alpha,
            text="Preserve alpha when extracting to PNG")
        self.use_tag_index_for_script_names_cbtn = tk.Checkbutton(
            self.data_extract_frame, variable=self.use_tag_index_for_script_names,
            text=("When extracting scripts, redirect tag references to\n"
                  "what the tag is currently named(guarantees scripts\n"
                  "point to a valid tag, even if you rename them)"),
            justify="left")
        self.use_scenario_names_for_script_names_cbtn = tk.Checkbutton(
            self.data_extract_frame, variable=self.use_scenario_names_for_script_names,
            text=("When extracting scripts, extract names for encounters,\n"
                  "command lists, scripts, cutscene titles/camera points/flags,\n"
                  "trigger volumes, recorded animations, ai conversations,\n"
                  "object names, device groups, and player starting profiles\n"
                  "from the scenarios reflexives, rather than script strings."),
            justify="left")

        try:
            sel_index = bitmap_file_formats.index(self.bitmap_extract_format.get())
        except Exception:
            sel_index = 0

        self.bitmap_extract_format_menu = ScrollMenu(
            self.bitmap_extract_frame, str_variable=self.bitmap_extract_format,
            menu_width=10, options=bitmap_file_formats, sel_index=sel_index)


        self.fix_tag_classes_cbtn = tk.Checkbutton(
            self.deprotect_frame, text="Fix tag classes",
            variable=self.fix_tag_classes)
        self.use_heuristics_cbtn = tk.Checkbutton(
            self.deprotect_frame, text="Use heuristic deprotection methods",
            variable=self.use_heuristics)
        self.scrape_tag_paths_from_scripts_cbtn = tk.Checkbutton(
            self.deprotect_frame, text="Scrape tag paths from scenario scripts",
            variable=self.scrape_tag_paths_from_scripts)
        self.rename_cached_tags_cbtn = tk.Checkbutton(
            self.deprotect_frame, text=("Rename cached tags using tag paths in\n"
                                        "bitmaps/loc/sounds resource maps"),
            variable=self.rename_cached_tags, justify="left")
        self.limit_tag_path_lengths_cbtn = tk.Checkbutton(
            self.deprotect_frame, text="Limit tag paths to 254 characters (tool.exe limitation)",
            variable=self.limit_tag_path_lengths)
        self.fix_tag_index_offset_cbtn = tk.Checkbutton(
            self.deprotect_frame, text=("Fix tag index offset when saving\n"
                                        "WARNING: Can corrupt certain maps"),
            variable=self.fix_tag_index_offset, justify='left')


        self.valid_tag_paths_are_accurate_cbtn = tk.Checkbutton(
            self.heuristics_frame, text="Do not rename non-protected tag paths",
            variable=self.valid_tag_paths_are_accurate)
        self.shallow_ui_widget_nesting_cbtn = tk.Checkbutton(
            self.heuristics_frame, text="Use shallow ui_widget_definition nesting",
            variable=self.shallow_ui_widget_nesting)
        self.use_fast_heuristics_cbtn = tk.Checkbutton(
            self.heuristics_frame, text="Use fast heuristics",
            variable=self.use_minimum_priorities)
        self.print_heuristic_progress_cbtn = tk.Checkbutton(
            self.heuristics_frame, text=("Print heuristic tag path changes"),
            variable=self.print_heuristic_name_changes, justify='left')


        font_frame_widgets = {}
        for font_type in sorted(self.font_settings):
            if font_type not in ("default", "treeview", "console", "heading",
                                 "heading_small", "frame_title",):
                continue

            if font_type == "console":
                font_type_name_text = "Map info"
            elif font_type == "treeview":
                font_type_name_text = "Map contents / Extraction queue"
            elif font_type == "heading_small":
                font_type_name_text = "Map contents columns / Settings tabs"
            else:
                font_type_name_text = font_type.replace("_", " ").capitalize()

            font_frame = tk.LabelFrame(
                self.fonts_frame, text=font_type_name_text)

            font_info = self.font_settings[font_type]
            try:
                sel_index = font_families.index(font_info.family)
            except Exception:
                sel_index = -1

            family_var = tk.StringVar(self)
            size_var = tk.StringVar(self, str(font_info.size))
            weight_var = tk.IntVar(self, int(font_info.weight == "bold"))
            self.write_trace(family_var, lambda *a, v=family_var, t=font_type:
                             self.update_font_family(v, t))
            self.write_trace(size_var, lambda *a, v=size_var, t=font_type:
                             self.update_font_size(v, t))
            self.write_trace(weight_var, lambda *a, v=weight_var, t=font_type:
                             self.update_font_weight(v, t))

            family_label = tk.Label(font_frame, text="Family ")
            family_menu = ScrollMenu(
                font_frame, str_variable=family_var, menu_width=20,
                options=font_families, sel_index=sel_index)
            weight_btn = tk.Checkbutton(font_frame, text="bold", variable=weight_var)
            size_label = tk.Label(font_frame, text="Size ")
            size_menu = tk.Spinbox(
                font_frame, width=3, state="readonly",
                textvariable=size_var, from_=0, to=200)

            font_frame_widgets[font_type_name_text] = (
                font_frame, (family_label, family_menu, weight_btn,
                             size_label, size_menu))

        self.apply_fonts_btn = tk.Button(
            self.fonts_frame, text="Apply changes", command=self.apply_fonts)


        self.autoload_resources_cbtn = tk.Checkbutton(
            self.other_frame, text=("Load resource maps automatically\n" +
                                    "when loading a non-resource map"),
            variable=self.autoload_resources, justify="left")
        self.extract_yelo_cheape_cbtn = tk.Checkbutton(
            self.other_frame, variable=self.extract_yelo_cheape,
            text="Extract cheape.map when extracting from yelo maps")
        self.show_all_fields_cbtn = tk.Checkbutton(
            self.other_frame, variable=self.show_all_fields,
            text="Show hidden fields when viewing metadata")
        self.show_structure_meta_cbtn = tk.Checkbutton(
            self.other_frame, variable=self.show_structure_meta,
            text="Show hidden meta structure fields when viewing metadata")
        self.edit_all_fields_cbtn = tk.Checkbutton(
            self.other_frame, variable=self.edit_all_fields,
            text="Allow editing all fields when viewing metadata")
        self.allow_corrupt_cbtn = tk.Checkbutton(
            self.other_frame, variable=self.allow_corrupt,
            text="Allow previewing corrupt tags")


        # pack everything
        self.tabs.pack(fill="both", expand=True)
        for w in (self.tags_dir_frame, self.data_dir_frame,
                  self.tags_list_frame):
            w.pack(padx=4, pady=2, fill="x")

        for w in (self.overwrite_cbtn, self.recursive_cbtn,
                  self.do_printout_cbtn, self.force_lower_case_paths_cbtn,
                  self.skip_seen_tags_during_queue_processing_cbtn,
                  self.globals_overwrite_mode_frame):
            w.pack(padx=4, anchor='w')

        for w in (self.bitmap_extract_keep_alpha_cbtn,
                  self.bitmap_extract_format_menu, self.globals_overwrite_mode_menu):
            w.pack(padx=16, anchor='w')

        for w in (self.decode_adpcm_cbtn, self.bitmap_extract_frame,
                  self.use_tag_index_for_script_names_cbtn,
                  self.use_scenario_names_for_script_names_cbtn):
            w.pack(padx=4, anchor='w')

        for w in (self.rename_scnr_dups_cbtn,
                  self.generate_uncomp_verts_cbtn, self.generate_comp_verts_cbtn):
            w.pack(padx=4, anchor='w')

        self.dont_touch_frame.pack(padx=4, anchor='w', expand=True, fill="both")
        for w in (self.disable_safe_mode_cbtn, self.disable_tag_cleaning_cbtn):
            w.pack(padx=4, anchor='w')

        for w in (self.fix_tag_classes_cbtn, self.use_heuristics_cbtn,
                  self.fix_tag_index_offset_cbtn, self.rename_cached_tags_cbtn,
                  self.limit_tag_path_lengths_cbtn,
                  self.scrape_tag_paths_from_scripts_cbtn,
                  ):
            w.pack(padx=4, anchor='w')

        for w in (self.print_heuristic_progress_cbtn,
                  self.valid_tag_paths_are_accurate_cbtn,
                  self.shallow_ui_widget_nesting_cbtn,
                  self.use_fast_heuristics_cbtn,
                  ):
            w.pack(padx=4, anchor='w')

        for w in (self.autoload_resources_cbtn, self.extract_yelo_cheape_cbtn,
                  self.show_all_fields_cbtn, self.show_structure_meta_cbtn,
                  self.edit_all_fields_cbtn, self.allow_corrupt_cbtn,
                  ):
            w.pack(padx=4, anchor='w')

        for k in sorted(font_frame_widgets):
            font_frame, font_widgets = font_frame_widgets[k]
            font_frame.pack(padx=4, anchor='w', expand=True, fill="x")
            for w in font_widgets:
                w.pack(padx=(0, 4), pady=2, side='left', fill='both',
                       expand=isinstance(w, ScrollMenu))

        self.apply_fonts_btn.pack(padx=4, anchor='w', expand=True, fill="both")

        for w1, w2 in ((self.tags_dir_entry, self.tags_dir_browse_button),
                       (self.data_dir_entry, self.data_dir_browse_button),
                       (self.tags_list_entry, self.browse_tags_list_button)):
            w1.pack(padx=(4, 0), pady=2, side='left', expand=True, fill='x')
            w2.pack(padx=(0, 4), pady=2, side='left')

        # make the window not show up on the start bar
        self.transient(self.master)
        self.apply_style()

    def update_font_family(self, var, font_type):
        self.set_font_config(font_type, False, family=str(var.get()))

    def update_font_size(self, var, font_type):
        self.set_font_config(font_type, False, size=int(var.get()))

    def update_font_weight(self, var, font_type):
        self.set_font_config(font_type, False,
                             weight=("bold" if var.get() else "normal"))

    def apply_fonts(self):
        self.reload_fonts()
        self.master.apply_style()

    def destroy(self):
        try: self.master.settings_window = None
        except AttributeError: pass
        self.delete_all_traces()
        tk.Toplevel.destroy(self)

    def tags_dir_browse(self):
        dirpath = askdirectory(initialdir=self.tags_dir.get(), parent=self,
                               title="Select the tags extraction directory")

        if not dirpath:
            return

        self.tags_dir.set(str(Path(dirpath)))

    def data_dir_browse(self):
        dirpath = askdirectory(initialdir=self.data_dir.get(), parent=self,
                               title="Select the data extraction directory")

        if not dirpath:
            return

        self.data_dir.set(str(Path(dirpath)))

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
