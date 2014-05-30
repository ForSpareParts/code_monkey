from code_monkey.change import ChangeGenerator
from code_monkey.utils import line_column_to_absolute_index

class Node(object):
    '''Base class for all Nodes in the code_monkey project tree.'''

    def __init__(self):
        self.parent = None

    @property
    def change(self):
        return ChangeGenerator(self)

    @property
    def children(self):
        return {}

    @property
    def root(self):
        '''return the root Node in the tree (should be a ProjectNode)'''
        if self.parent:
            return self.parent.root

        return self

    @property
    def fs_path(self):
        #some nodes will recurse upward to find their fs_path, which is why we
        #hide it behind a property method
        return self._fs_path

    def get_source_file(self):
        '''return a read-only file object for the file in which this Node was
        defined. only meaningful at or below the module level -- higher than
        that, source_file is None.'''

        try:
            return open(self.fs_path, 'r')
        except IOError:
            #if the path is to a directory, we'll get an IOError
            return None


    @property
    def start_line(self):
        #astroid gives line numbers starting with 1
        return self._astroid_object.fromlineno - 1

    @property
    def body_start_line(self):
        return self.start_line


    @property
    def end_line(self):
        #astroid gives line numbers starting with 1
        return self._astroid_object.tolineno

    @property
    def body_end_line(self):
        return self.end_line


    @property
    def start_column(self):
        return self._astroid_object.col_offset

    @property
    def body_start_column(self):
        return self.start_column


    @property
    def end_column(self):
        return 0

    @property
    def body_end_column(self):
        return self.end_column


    @property
    def start_index(self):
        '''The character index of the beginning of the node, relative to the
        entire source file.'''
        return line_column_to_absolute_index(
            self.get_file_source_code(),
            self.start_line,
            self.start_column)

    @property
    def end_index(self):
        '''The character index of the character after the end of the node,
        relative to the entire source file.'''
        return line_column_to_absolute_index(
            self.get_file_source_code(),
            self.end_line,
            self.end_column)

    @property
    def body_start_index(self):
        '''The character index of the beginning of the node body, relative to
        the entire source file.'''
        return line_column_to_absolute_index(
            self.get_file_source_code(),
            self.body_start_line,
            self.body_start_column)

    @property
    def body_end_index(self):
        '''The character index of the character after the end of the node body,
        relative to the entire source file.'''
        return line_column_to_absolute_index(
            self.get_file_source_code(),
            self.body_end_line,
            self.body_end_column)
 
    def _get_source_region(self, start_index, end_index):
        '''return a substring of the source code starting from start_index up to
        but not including end_index'''

        with open(self.fs_path, 'r') as source_file:

            if not source_file:
                return None

            source = source_file.read()
            source = source[start_index:end_index]

            return source

    def get_file_source_code(self):
        '''Return the text of the entire file containing Node.'''
        with open(self.fs_path, 'r') as source_file:
            if not source_file:
                return None

            return source_file.read()

    def get_source(self):
        '''return a string of the source code the Node represents'''

        return self._get_source_region(
            self.start_index,
            self.end_index)

    def get_body_source(self):
        '''return a string of only the body of the node -- i.e., excluding the
        declaration. For a Class or Function, that means the class or function
        body. For a Variable, that's the right hand of the assignment. For a
        Module, it's the same as get_source().'''
        return self._get_source_region(
            self.body_start_index,
            self.body_end_index)


    @property
    def path(self):
        parent_path = self.parent.path

        #prevents an 'empty' root from giving us paths like '.foo.bar.baz'
        if parent_path == '':
            return self.name

        return parent_path + '.' + self.name


    @property
    def outer_indentation(self):
        '''The indentation level, as a string, at the source where this node
        begins.'''
        lines = self.get_file_source_code().splitlines(True)
        return lines[self.start_line][0:self.start_column]


    def __unicode__(self):
        return '{}: {}'.format(
            str(self.__class__.__name__),
            self.path)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()