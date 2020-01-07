"""
NONMEM data record class.
"""

from pharmpy.parse_utils import AttrTree

from .option_record import OptionRecord


class DataRecord(OptionRecord):
    @property
    def filename(self):
        """The (raw, unresolved) path of the dataset."""
        filename = self.root.filename
        if filename.find('TEXT'):
            return str(filename)
        elif filename.find('QUOTE'):
            return str(filename)[1:-1]

    @filename.setter
    def filename(self, value):
        if not value:
            # erase and replace by * (for previous subproblem)
            new = [AttrTree.create(ASTERIX='*')]
            nodes = []
            for child in self.root.children[1:]:
                if new and child.rule == 'ws':
                    nodes += [child, new.pop()]
                elif child.rule in {'ws', 'comment'}:
                    nodes += [child]
            self.root = AttrTree.create('root', nodes)
        else:
            # replace only 'filename' rule and quote appropriately if, but only if, needed
            filename = str(value)
            quoted = [',', ';', '(', ')', '=', ' ', 'IGNORE', 'NULL', 'ACCEPT', 'NOWIDE', 'WIDE',
                      'CHECKOUT', 'RECORDS', 'RECORDS', 'LRECL', 'NOREWIND', 'REWIND', 'NOOPEN',
                      'LAST20', 'TRANSLATE', 'BLANKOK', 'MISDAT']
            if not any(x in filename for x in quoted):
                node = AttrTree.create('filename', {'TEXT': filename})
            else:
                if "'" in filename:
                    node = AttrTree.create('filename', {'QUOTE': '"%s"' % filename})
                else:
                    node = AttrTree.create('filename', {'QUOTE': "'%s'" % filename})
            (pre, old, post) = self.root.partition('filename')
            self.root.children = pre + [node] + post

    @property
    def ignore_character(self):
        """The comment character from ex IGNORE=C or None if not available."""
        if hasattr(self.root, 'ignchar') and self.root.ignchar.find('char'):
            char = str(self.root.ignchar.char)
            if len(char) == 3:      # It must be quoted
                char = char[1:-1]
            return char
        else:
            return None

    @ignore_character.setter
    def ignore_character(self, c):
        self.root.remove('ignchar')
        char_node = AttrTree.create('char', [{'CHAR': c}])
        node = AttrTree.create('ignchar', [char_node])
        self.root.children.append(node)

    @property
    def null_value(self):
        """The value to replace for NULL (i.e. . etc) in the dataset
           note that only +,-,0 (meaning 0) and 1-9 are allowed
        """
        if hasattr(self.root, 'null') and self.root.null.find('char'):
            char = str(self.root.null.char)
            if char == '+' or char == '-':
                return 0
            else:
                return float(char)
        else:
            return 0

    @property
    def ignore(self):
        filters = []
        for option in self.root.all('ignore'):
            for filt in option.all('filter'):
                filters.append(filt)
        return filters

    @property
    def accept(self):
        filters = []
        for option in self.root.all('accept'):
            for filt in option.all('filter'):
                filters.append(filt)
        return filters

    def remove_ignore_accept(self):
        """ Remove all IGNORE and ACCEPT options
        """
        # FIXME: Could be changed to setters for ignore/accept. Set with None
        self.root.remove("accept")
        keep = []
        for child in self.root.children:
            if not (child.rule == 'ignore' and not hasattr(child, 'char')):
                keep.append(child)
        self.root.children = keep

    # @filters.setter
    # def filters(self, filters):
    #    self.remove_ignore_accept()
    #    # Install new filters at the end
    #    if not filters:     # This was easiest kept as a special case
    #        return
    #    if filters.accept:
    #        tp = 'ACCEPT'
    #    else:
    #        tp = 'IGNORE'
    #    nodes = [{tp: tp}, {'EQUAL': '='}, {'LPAR': '('}]
    #    first = True
    #    for f in filters:
    #        if not first:
    #            nodes += [{'COMMA': ','}]
    #        new = [{'COLUMN': f.symbol}]
    #        if f.operator == InputFilterOperator.EQUAL:
    #            new.append({'OP_EQ': '.EQN.'})
    #        elif f.operator == InputFilterOperator.STRING_EQUAL:
    #            new.append({'OP_STR_EQ': '.EQ.'})
    #        elif f.operator == InputFilterOperator.NOT_EQUAL:
    #            new.append({'OP_NE': '.NEN.'})
    #        elif f.operator == InputFilterOperator.STRING_NOT_EQUAL:
    #            new.append({'OP_STR_NE': '.NE.'})
    #        elif f.operator == InputFilterOperator.LESS_THAN:
    #            new.append({'OP_LT': '.LT.'})
    #        elif f.operator == InputFilterOperator.GREATER_THAN:
    #            new.append({'OP_GT': '.GT.'})
    #        elif f.operator == InputFilterOperator.LESS_THAN_OR_EQUAL:
    #            new.append({'OP_LT_EQ': '.LE.'})
    #        elif f.operator == InputFilterOperator.GREATER_THAN_OR_EQUAL:
    #            new.append({'OP_GT_EQ': '.GE.'})
    #        new.append({'TEXT': f.value})
    #        nodes += [AttrTree.create('filter', new)]
    #        first = False
    #    nodes += [{'RPAR': ')'}]
    #    top = AttrTree.create(tp.lower(), nodes)
    #    self.root.children += [top]
