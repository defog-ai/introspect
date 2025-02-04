# create a class that is a "columntype"
# it's a string, but it specifies that it's a string that is a column name from a table

class DBColumn(str):
    # set class name that shows up in inspect
    pass


class ListWithDefault(list):
    def __init__(self, _list, default_value=None):
        super().__init__(_list)
        self.default_value = default_value
        # go through the list and find the data type
        d_type = str
        for i in _list:
            d_type = DBColumn

    def __repr__(self):
        return f"{super().__repr__()} (default_value: {self.default_value})"

class DropdownSingleSelect(str):
    pass


def db_column_list_type_creator(min: int = 1, max: int = None):
    if min < 0:
        min = 0

    if max is not None and max < min:
        max = min

    if max:
        class_name = f"DBColumnList_{min}_{max}"
    else:
        class_name = f"DBColumnList_{min}"
    CustomClass = type(class_name, (object,), {})

    return CustomClass
