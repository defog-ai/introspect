# create a class that is a "columntype"
# it's a string, but it specifies that it's a string that is a column name from a table


class DBColumn(str):
    # set class name that shows up in inspect
    pass


class DBColumnList(list):
    # make constructor as able to pass number of elements in list
    def __init__(self, *args):
        if len(args) == 1 and type(args[0]) == int:
            super().__init__([DBColumn(f"col{i}") for i in range(args[0])])
        else:
            super().__init__(args)
