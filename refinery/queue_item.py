#
# This file is part of Mozzarilla.
#
# For authors and copyright check AUTHORS.TXT
#
# Mozzarilla is free software under the GNU General Public License v3.0.
# See LICENSE for more information.
#

class RefineryQueueItem:
    __slots__ = ("_op", "_op_kwargs")

    def __init__(self, operation, **kwargs):
        op = str(operation)
        provided_kwargs = set(kwargs)

        if op in ("load_map", "switch_map_by_filepath"):
            required = ("filepath", )

        elif op in ("extract_tags", "extract_data"):
            required = ("tag_ids", )

        elif op in ("deprotect_map", "save_map", "extract_cheape",
                    "print_dir", "print_files", "print_map_info", "unload_map",
                    "print_dir_ct", "print_dir_names", "print_total_dir_ct",
                    "print_file_ct", "print_file_names", "print_total_file_ct"):
            required = ()

        elif op == "extract_tag": required = ("tag_id", )
        elif op == "switch_map":  required = ("map_name", )
        elif op == "switch_engine": required = ("engine", )
        elif op == "spoof_crc": required = ("new_crc", )
        elif op == "set_vars": required = ("names", "values")
        elif op == "rename_map": required = ("new_name", )
        elif op == "rename_tag_by_id": required = ("tag_id", "new_path")
        elif op == "rename_tag": required = ("tag_path", "new_path")
        elif op == "rename_dir": required = ("dir_path", "new_path")
        else:
            raise ValueError('The hell kind of operation is "%s"' % op)

        missing_kwargs = set(required).difference(provided_kwargs)

        if missing_kwargs:
            raise KeyError(
                'The following keyword arguments are required for '
                'the "%s" operation, but were not supplied:  %s' %
                (op, ", ".join(sorted(missing_kwargs))))

        assert isinstance(kwargs.get("filepath", ""), str)
        assert isinstance(kwargs.get("new_name", ""), str)
        assert isinstance(kwargs.get("map_name", ""), str)
        assert isinstance(kwargs.get("engine_name", ""), str)
        assert isinstance(kwargs.get("new_crc", 0), int)
        assert isinstance(kwargs.get("tagslist_path", ""), str)
        assert isinstance(kwargs.get("bitmap_extract_format", ""), str)
        assert isinstance(kwargs.get("tag_id", ""), (int, str))
        assert isinstance(kwargs.get("tag_ids", ()), (tuple, list, set))
        assert isinstance(kwargs.get("tag_path", ""), str)
        assert isinstance(kwargs.get("dir_path", ""), str)
        assert isinstance(kwargs.get("new_path", ""), str)

        assert len(kwargs.get("names", ())) == len(kwargs.get("values", ()))
        for name in kwargs.get("names", ()):
            assert name[0] != "_" # disallow setting private variables

        assert kwargs.get("new_crc", 0) in range(0, 0x100000000)

        self._op = op
        self._op_kwargs = kwargs

    def __getattribute__(self, attr_name):
        try:
            return object.__getattribute__(self, attr_name)
        except AttributeError:
            return self.operation_kwargs[attr_name]

    def __setattr__(self, attr_name, new_val):
        try:
            object.__setattr__(self, attr_name, new_val)
        except AttributeError:
            self.operation_kwargs[attr_name] = new_val

    @property
    def operation(self): return self._op
    @property
    def operation_kwargs(self): return dict(self._op_kwargs)
