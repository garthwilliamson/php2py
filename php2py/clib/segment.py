
class CompiledSegment(object):
    def __init__(self) -> 'CompiledSegment':
        self._indent = 0
        self.lines = []

    def append(self, item):
        """ Append a string or CompiledSegment to the end of this segment

        """
        if item is None:
            raise TypeError("Can't append a null item to compiled segment")
        if isinstance(item, CompiledSegment):
            for l, i in item:
                if not isinstance(l, str):
                    print("Bad segment was '{}'".format(l))
                    raise TypeError("CompilationSegment.append must be passed a string or a cs")
                self.lines.append((l, i + self._indent))
        elif isinstance(item, str):
            self.lines.append((item, self._indent))
        else:
            raise TypeError("Expected a string or a CompiledSegment, instead got " + str(type(item)))

    def indent(self):
        """ Increase the indent level by one

        """
        self._indent += 1

    def dedent(self):
        """ Decrease the indent level by one

        """
        self._indent -= 1

    def br(self, number=1):
        """ Add a blank line to this segment

        """

        for i in range(0, number):
            # Direct call to results to avoid extra spaces
            self.lines.append(("", 0))

    def prepend(self, line):
        """ Insert a zero indented item at the start of this segment

        """
        self.lines.insert(0, (line, 0))

    def __str__(self):
        out = ""
        for l, i in self.lines:
            try:
                out += "    " * i + l + "\n"
            except TypeError:
                print("BAD SEGMENT WAS: ")
                print(str(l))
                raise
        return out

    def __iter__(self):
        return iter(self.lines)

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, item):
        return self.lines[item][0]
