#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

import tkinter as tk

from refinery.widgets.explorer_hierarchy_tree import ExplorerHierarchyTree
from refinery.windows.actions_window import RefineryEditActionsWindow


class QueueTree(ExplorerHierarchyTree):
    # keys are the iid's of the items in the queue
    # values are dictionaries containing extraction details
    queue_info = None

    def __init__(self, *args, **kwargs):
        self.queue_info = {}
        kwargs['select_mode'] = 'browse'
        ExplorerHierarchyTree.__init__(self, *args, **kwargs)

        self.tags_tree.bind('<BackSpace>', self.remove_curr_selection)
        self.tags_tree.bind('<Delete>', self.remove_curr_selection)

    def get_item(self, item_name):
        return self.queue_info.get(item_name)

    def get_item_names(self):
        return self.tags_tree.get_children()

    def setup_columns(self):
        pass

    def activate_item(self, e=None):
        tags_tree = self.tags_tree
        if not tags_tree.selection():
            return

        # edit queue
        iids = self.tags_tree.selection()

        if len(iids):
            settings = self.queue_info[iids[0]]
            w = RefineryEditActionsWindow(
                self, settings=settings, title=settings.get('title'))
            # make the queue freeze until the settings ask window is done
            self.wait_window(w)

    def add_to_queue(self, item_name, new_queue_info):
        self.queue_info[item_name] = new_queue_info

        if self.tags_tree.exists(item_name):
            self.tags_tree.delete(item_name)
        self.tags_tree.insert('', 'end', iid=item_name,
                              text=item_name, tags=("item", ))

    def remove_items(self, items=None):
        if items is None:
            items = self.tags_tree.get_children()
        if not hasattr(items, "__iter__"):
            items = (items, )

        for item in items:
            self.queue_info.pop(item, None)

        self.tags_tree.delete(*items)

    def remove_curr_selection(self, e=None):
        self.remove_items(self.tags_tree.selection())

    def reload(self, active_map=None):
        self.setup_columns()

        # remove any currently existing children
        self.remove_items()
