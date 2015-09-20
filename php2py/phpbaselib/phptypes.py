from collections import OrderedDict


class PhpArray():
    def __init__(self, *args):
        """ Args should be a series of key, value tuples

        """
        # TODO: because dicts are unordered, building an array from a dict will require a transform
        self.next_index = 0
        self.data = OrderedDict()
        self.append_many(args)

    def append_many(self, items):
        for i in items:
            self.append(i)

    def append(self, item):
        if isinstance(item, tuple):
            self[item[0]] = item[1]
        else:
            self[self.next_index] = item

    def __setitem__(self, key, value):
        # TODO: Move this to a transform, although if it were from an expression...
        # TODO: Deal with bools, warn if illegal type as key
        if isinstance(key, str):
            try:
                key = int(key)
            except ValueError:
                pass
            if key == "MagicEmptyArrayIndex":
                # This is actually an append. Magic!
                key = self.next_index
        if isinstance(key, float):
            key = int(key)
        if key is None:
            key = ""
        self.data[key] = value
        if isinstance(key, int) and key >= self.next_index:
            self.next_index = key + 1

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)

    def __delitem__(self, key):
        try:
            del self.data[key]
        except KeyError:
            # TODO: Does php actually ignore this?
            pass

    def __str__(self):
        return "Array"

    def items(self):
        return self.data.items()
