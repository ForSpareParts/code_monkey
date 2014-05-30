from ast import literal_eval
import os

from astroid.manager import AstroidManager
from astroid.node_classes import Assign
from astroid.scoped_nodes import Class, Function
from logilab.common.modutils import modpath_from_file

from code_monkey.change import (
    ChangeGenerator,
    SourceChangeGenerator,
    VariableChangeGenerator)
from code_monkey.utils import (
    absolute_index_to_line_column,
    line_column_to_absolute_index)

def get_modules(fs_path):
    '''Find all Python modules in fs_path. Returns a list of tuples of the form:
    (full_path, is_package)'''

    modules = []

    for filename in os.listdir(fs_path):

        full_path = os.path.join(fs_path, filename)

        if os.path.isdir(full_path) and '__init__.py' in os.listdir(full_path):
            #directories with an __init__.py file are Python packages
            modules.append((full_path, True))

        elif filename.endswith('.py'):
            #files ending in .py are assumed to be Python modules
            modules.append((full_path, False))

    return modules


class Node(object):

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

    def __unicode__(self):
        return '{}: {}'.format(
            str(self.__class__.__name__),
            self.path)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()



class ProjectNode(Node):

    def __init__(self, project_path):
        super(ProjectNode, self).__init__()

        #gets the python 'dotpath' of the project root. If the project root
        #itself is in the Python path, this will be an empty string
        self.name = '.'.join(modpath_from_file(project_path))

        self.parent = None
        self.scope = None

        #the file system (not python) path to the project
        self._fs_path = project_path

    @property
    def children(self):
        '''astroid doesn't expose the children of packages in a convenient way,
        so we the filesystem to list them and build child nodes'''

        fs_children = get_modules(self.fs_path)

        children = {}

        for fs_path, is_package in fs_children:
            if is_package:
                child = PackageNode(
                    parent=self,
                    fs_path=fs_path)
                children[child.name] = child
            else:
                child = ModuleNode(
                    parent=self,
                    fs_path=fs_path)
                children[child.name] = child

        return children

    @property
    def path(self):
        return self.name

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '{}: {}'.format(
            str(self.__class__.__name__),
            self.name)


class PackageNode(Node):

    def __init__(self, parent, fs_path):
        super(PackageNode, self).__init__()

        self.parent = parent
        self._fs_path = fs_path

        #gets the module name -- the whole return value of modpath_from_file
        #is a list containing each element of the dotpath
        self.name = modpath_from_file(fs_path)[-1]

    @property
    def children(self):
        '''astroid doesn't expose the children of packages in a convenient way,
        so we use pkgutil to access them and build child nodes'''

        fs_children = get_modules(self.fs_path)

        children = {}

        for fs_path, is_package in fs_children:
            if is_package:
                child = PackageNode(
                    parent=self,
                    fs_path=fs_path)
                children[child.name] = child
            else:
                child = ModuleNode(
                    parent=self,
                    fs_path=fs_path)
                children[child.name] = child

        return children


class ModuleNode(Node):

    def __init__(self, parent, fs_path):
        super(ModuleNode, self).__init__()

        self.parent = parent
        self._fs_path = fs_path

        #gets the module name -- the whole return value of modpath_from_file
        #is a list containing each element of the dotpath
        self.name = modpath_from_file(fs_path)[-1]

        self._astroid_object = AstroidManager().ast_from_file(fs_path)

    @property
    def change(self):
        return SourceChangeGenerator(self)

    @property
    def children(self):
        #all of the children found by astroid:

        astroid_children = self._astroid_object.get_children()
        children = {}

        for child in astroid_children:

            if isinstance(child, Class):

                children[child.name] = ClassNode(
                    parent=self,
                    name=child.name,
                    astroid_object=child)

            elif isinstance(child, Function):

                children[child.name] = FunctionNode(
                    parent=self,
                    name=child.name,
                    astroid_object=child)

            elif isinstance(child, Assign):
                #Assign is the class representing a variable assignment.

                #we don't know the name of the variable until we build the Node,
                #so we build the node before adding it to the children dict
                child_node = VariableNode(
                    parent=self,
                    astroid_object=child)

                children[child_node.name] = child_node

        return children

    @property
    def start_line(self):
        #for modules, astroid gives 0 as the start line -- so we don't want to
        #subtract 1
        return self._astroid_object.fromlineno

    @property
    def start_column(self):
        #for modules, astroid gives None as the column offset -- by our
        #conventions, it should be 0
        return 0


class ClassNode(Node):

    def __init__(self, parent, name, astroid_object):
        super(ClassNode, self).__init__()

        self.parent = parent
        self.name = name
        self._astroid_object = astroid_object

    @property
    def change(self):
        return SourceChangeGenerator(self)

    @property
    def children(self):
        #all of the children found by astroid:

        astroid_children = self._astroid_object.get_children()
        children = {}

        for child in astroid_children:

            if isinstance(child, Class):

                children[child.name] = ClassNode(
                    parent=self,
                    name=child.name,
                    astroid_object=child)

            elif isinstance(child, Function):

                children[child.name] = FunctionNode(
                    parent=self,
                    name=child.name,
                    astroid_object=child)

            elif isinstance(child, Assign):
                #Assign is the class representing a variable assignment.

                #we don't know the name of the variable until we build the Node,
                #so we build the node before adding it to the children dict
                child_node = VariableNode(
                    parent=self,
                    astroid_object=child)

                children[child_node.name] = child_node

        return children

    @property
    def fs_path(self):
        return self.parent.fs_path

    @property
    def body_start_line(self):
        #TODO: account for multi-line class signatures
        return self.start_line + 1

    @property
    def body_start_column(self):
        return 0


class VariableNode(Node):
    def __init__(self, parent, astroid_object):
        super(VariableNode, self).__init__()

        self.parent = parent

        #the _astroid_object (an Assign object) has TWO children that we need to
        #consider: (the variable name) and another astroid node (the 'right
        #hand' value)
        self._astroid_object = astroid_object

        #TODO: account for tuple assignment
        self._astroid_name = self._astroid_object.targets[0]
        self._astroid_value = self._astroid_object.value

        try:
            self.name = self._astroid_name.name
        except AttributeError:
            #'subscript' assignments (a[b] = ...) don't have a name in astroid.
            #instead, we give them one by reading their source

            #TODO: this can result in names containing dots, which is invalid.
            #need a better solution
            self.name = self._astroid_name.as_string()

    def eval_body(self):
        '''Attempt to evaluate the body (i.e., the value) of this VariableNode
        using ast.literal_eval (which will evaluate ONLY Python literals).

        Return the value if successful, otherwise, return None.'''
        try:
            return literal_eval(self.get_body_source())
        except (SyntaxError, ValueError):
            return None

    @property
    def fs_path(self):
        return self.parent.fs_path

    @property
    def change(self):
        return VariableChangeGenerator(self)

    #the 'whole source' of a VariableNode includes the name and the value
    @property
    def start_line(self):
        return self._astroid_name.fromlineno - 1

    @property
    def start_column(self):
        return self._astroid_name.col_offset

    #in a VariableNode, the _astroid_value represents the body
    @property
    def body_start_line(self):
        return self._astroid_value.fromlineno - 1

    @property
    def body_start_column(self):
        return self._astroid_value.col_offset

    @property
    def end_index(self):
        #there's a bug in astroid where it doesn't correctly detect the last
        #line of multiline enclosed blocks (parens, brackets, etc.) -- it gives
        #the last line with content, rather than the line containing the
        #terminating character

        #we have to work around this by scanning through the source ourselves to
        #find the terminating point

        #astroid bug report submitted:
        #https://bitbucket.org/logilab/astroid/issue/31/astroid-sometimes-reports-the-wrong

        file_source_lines = self.get_file_source_code().splitlines(True)

        #we start by finding the line/column at which the next 'sibling' of
        #this node begins. if the node is at the end of the file, we get the
        #end of the file instead
        next_sibling = self._astroid_object.next_sibling()
        astroid_end_line = self._astroid_value.tolineno - 1
        if next_sibling:
            next_sibling_line = next_sibling.fromlineno
            next_sibling_column = next_sibling.col_offset
            lines_to_scan = file_source_lines[
                astroid_end_line:(next_sibling_line+1)]

            #trim the last line so that we don't include any of the sibling
            lines_to_scan[-1] = lines_to_scan[-1][0:next_sibling_column]
        else:
            #if there is no sibling, we just start from the end of the file
            lines_to_scan = file_source_lines[
                self._astroid_value.tolineno:len(file_source_lines)]

        #this string doesn't have the right formatting, but it should be
        #otherwise correct -- so we can use it to see what character our
        #variable ends on
        terminating_char = self._astroid_value.as_string()[-1]

        #scan through the lines in reverse order, looking for the end of the
        #node

        #len(lines_to_scan) - (line_index + 1) is the index of a line in
        #lines_to_scan -- basically, it takes us from the 'reversed'
        #indices that we get in line_index back to real, from-the-beginning
        #indices
        for line_index, line in enumerate(reversed(lines_to_scan)):

            #remove comments from line
            if '#' in line:
                line = line[0:line.find('#')]

            for char_index, char in enumerate(reversed(line)):
                if char == terminating_char:
                    line_index_in_file = astroid_end_line + (
                        len(lines_to_scan) - (line_index + 1))
                    char_index_in_line = len(line) - char_index
                    return line_column_to_absolute_index(
                        self.get_file_source_code(),
                        line_index_in_file,
                        char_index_in_line)


    #for variable nodes, it's easiest to find an absolute end index first, then
    #work backwards to get line and column numbers
    @property
    def end_line(self):
        return absolute_index_to_line_column(
            self.get_file_source_code(),
            self.end_index)[0]

    @property
    def end_column(self):
        return absolute_index_to_line_column(
            self.get_file_source_code(),
            self.end_index)[1]


class FunctionNode(Node):
    def __init__(self, parent, name, astroid_object):
        super(FunctionNode, self).__init__()

        self.parent = parent
        self.name = name
        self._astroid_object = astroid_object

    @property
    def change(self):
        return SourceChangeGenerator(self)

    @property
    def fs_path(self):
        return self.parent.fs_path

    @property
    def body_start_line(self):
        #TODO: account for multi-line function signatures
        return self.start_line + 1

    @property
    def body_start_column(self):
        return 0
