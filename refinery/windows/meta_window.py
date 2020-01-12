#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import refinery
import tkinter as tk

from binilla import constants
from binilla.windows.tag_window import TagWindow

from mozzarilla.widgets.field_widget_picker import def_halo_widget_picker

from refinery import editor_constants as e_c
from refinery.util import is_path_empty


class MetaWindow(TagWindow):
    widget_picker = def_halo_widget_picker
    tag_path = None
    engine = ""

    def __init__(self, master, tag, *args, **kwargs):
        self.tag_path = kwargs.pop("tag_path", self.tag_path)
        self.engine = kwargs.pop("engine", "")
        self.tag = tag

        # delete the tags_dir so the FieldWidgets dont create
        # unusable browse/open buttons for dependencies
        self.tag.tags_dir = None
        del self.tag.tags_dir

        kwargs["tag_def"] = None
        TagWindow.__init__(self, master, tag, *args, **kwargs)
        self.bind('<Shift-MouseWheel>', self.mousewheel_scroll_x)
        self.bind('<MouseWheel>', self.mousewheel_scroll_y)

    def post_toplevel_init(self):
        if not is_path_empty(e_c.REFINERY_ICON_PATH):
            self.iconbitmap_filepath = e_c.REFINERY_ICON_PATH

        TagWindow.post_toplevel_init(self)

    def save(self, **kwargs):
        print("Cannot save meta-data")

    def destroy(self):
        del self.tag
        tk.Toplevel.destroy(self)

    def select_window(self, e):
        pass

    def bind_hotkeys(self, hotkeys=None):
        pass

    def unbind_hotkeys(self, hotkeys=None):
        pass

    def get_visible(self, visibility_level):
        if (visibility_level is None or
            visibility_level >= constants.VISIBILITY_SHOWN):
            return True

        try:
            if self.is_config and not (self.app_root.config_file.data.\
                                       app_window.flags.debug_mode):
                # No one should be fucking with the configs hidden values
                return False
        except Exception:
            pass

        try:
            if visibility_level == constants.VISIBILITY_METADATA:
                return bool(self.app_root.show_structure_meta.get())
            elif visibility_level == constants.VISIBILITY_HIDDEN:
                return bool(self.app_root.show_all_fields.get())
            else:
                return True
        except Exception:
            return False

    @property
    def all_editable(self):
        try:
            return bool(self.app_root.edit_all_fields.get())
        except Exception:
            return False

    @property
    def use_scenario_names_for_script_names(self):
        try:
            return bool(self.app_root.use_scenario_names_for_script_names)
        except Exception:
            return False

    def populate(self):
        '''
        Destroys the FieldWidget attached to this TagWindow and remakes it.
        '''
        # Destroy everything
        if hasattr(self.field_widget, 'destroy'):
            self.field_widget.destroy()
            self.field_widget = None

        # Get the desc of the top block in the tag
        root_block = self.tag.data.tagdata

        # Get the widget to build
        widget_cls = self.widget_picker.get_widget(root_block.desc)

        # Rebuild everything
        self.field_widget = widget_cls(self.root_frame, node=root_block,
                                       show_frame=True, tag_window=self)
        self.field_widget.pack(expand=True, fill='both')


    def update_title(self, new_title=None):
        if new_title is None:
            new_title = self.tag_path
        self.title(new_title)
