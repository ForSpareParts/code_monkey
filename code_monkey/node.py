import os
import pkgutil

from astroid.manager import AstroidManager
from astroid.node_classes import Assign, AssName
from astroid.scoped_nodes import Class, Function

from code_monkey.utils import string_to_lines

def get_modules(fs_path):
    '''Find all Python modules in fs_path. Returns a list of tuples of the form:
    (module_name, is_package)'''

    modules = []

    for filename in os.listdir(fs_path):

        full_path = os.path.join(fs_path, filename)

        if os.path.isdir(full_path) and '__init__.py' in os.listdir(full_path):
            #directories with an __init__.py file are Python packages
            modules.append((filename, True))
        elif filename.endswith('.py') and not filename == '__init__.py':
            #TODO: figure out how to handle source in init files, since astroid
            #doesn't acknowledge them

            #strip the extension
            module_name = os.path.splitext(filename)[0]

            #files ending in .py are assumed to be Python modules
            modules.append((module_name, False))

    return modules


def make_astroid_project(project_path):
    project_files = []

    for dirpath, dirname, filenames in os.walk(project_path):
        #get all python files and add them to a list we can use with astroid's
        #project builder
        for filename in filenames:
            if filename.endswith(".py"):
                project_files.append(os.path.join(dirpath, filename))

                if filename == '__init__.py':
                    #this is a package, so we should add the whole folder
                    project_files.append(dirpath) 

    return AstroidManager().project_from_files(project_files)


class Node(object):

    def __init__(self):
        self.parent = None
        self.path = None

    @property
    def children(self):
        return []

    @property
    def name(self):
        '''the name is the last component of the path'''
        if not self.path:
            return '[root]'

        path_components = self.path.split('.')
        return path_components[
            len(path_components) - 1]

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
    def end_line(self):
        #astroid gives line numbers starting with 1
        return self._astroid_object.tolineno - 1

    @property
    def start_column(self):
        return self._astroid_object.col_offset

    def get_source_code(self):
        '''return a string of the source code the Node represents'''

        with open(self.fs_path, 'r') as source_file:

            if not source_file:
                return None

            source_lines = source_file.readlines()

            starts_at = self.start_line
            ends_at = self.end_line

            #take the lines that make up the source code and join them into one
            #string
            source = ''.join(source_lines[starts_at:(ends_at+1)])
            source = source[self.start_column:]
            return source

    def generate_change(self, new_source):
        '''return a change (for use with ChangeSet) that overwrites the contents
        of this Node and replaces them with new_source. Only valid on Nodes with
        a source_file.

        A change is a tuple of the form (starting_line, ending_line, new_lines),
        where starting_line and ending_line are line indices and new_lines is a
        list of line strings.'''

        with self.get_source_file() as source_file:
            source_lines = source_file.readlines()

            starts_at = self.start_line
            ends_at = self.end_line

            new_lines = string_to_lines(new_source)

            return (starts_at, ends_at, new_lines)

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

        self._astroid_project = make_astroid_project(project_path)
        self.parent = None
        self.scope = None
        self.path = ''

        #the file system (not python) path to the project
        self._fs_path = project_path

    @property
    def children(self):
        '''astroid doesn't expose the children of packages in a convenient way,
        so we the filesystem to list them and build child nodes'''

        #NOTE: pkgutil.iter_modules should do this, but for some reason it is
        #occasionally iterating down and grabbing modules that aren't on the
        #surface. Would be worth finding out why.
        child_names = get_modules(self.fs_path)

        children = []

        for name, is_package in child_names:
            if is_package:
                children.append(PackageNode(
                    parent=self,
                    path=name))
            else:
                children.append(ModuleNode(
                    parent=self,
                    path=name))

        return children

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '{}: {}'.format(
            str(self.__class__.__name__),
            self.name)


class PackageNode(Node):
    
    def __init__(self, parent, path):
        super(PackageNode, self).__init__()

        self.parent = parent
        self.path = path

        self._fs_path = os.path.join(
            self.root.fs_path,
            self.path.replace('.', '/'))

    @property
    def children(self):
        '''astroid doesn't expose the children of packages in a convenient way,
        so we use pkgutil to access them and build child nodes'''

        child_names = get_modules(self.fs_path)
        children = []

        for name, is_package in child_names:
            if is_package:
                children.append(PackageNode(
                    parent=self,
                    path=self.path + '.' + name))
            else:
                children.append(ModuleNode(
                    parent=self,
                    path=self.path + '.' + name))

        return children


class ModuleNode(Node):

    def __init__(self, parent, path):
        super(ModuleNode, self).__init__()

        self.parent = parent
        self.path = path

        #TODO: this is a hacky way of getting the name of the folder that the
        #whole project is in (and it's broken under Windows). come up with
        #something more robust!
        root_package_name = self.root.fs_path.split('/')[-1]
        self._astroid_object = self.root._astroid_project.get_module(
            root_package_name + '.' + self.path)

        self._fs_path = os.path.join(
            self.root.fs_path,
            self.path.replace('.', '/')) + '.py'

    @property
    def children(self):
        #all of the children found by astroid:

        astroid_children = self._astroid_object.get_children()
        children = []

        for child in astroid_children:
            
            if isinstance(child, Class):

                children.append(ClassNode(
                    parent=self,
                    path=self.path + '.' + child.name,
                    astroid_object=child))

            elif isinstance(child, Function):

                children.append(FunctionNode(
                    parent=self,
                    path=self.path + '.' + child.name,
                    astroid_object=child))

            elif isinstance(child, Assign):
                #Assign is the class representing a variable assignment.

                children.append(VariableNode(
                    parent=self,
                    astroid_object=child))

        return children

    @property
    def start_line(self):
        #for modules, astroid gives 0 as the start line -- so we don't want to
        #subtract 1
        return self._astroid_object.fromlineno

 
class ClassNode(Node):
    def __init__(self, parent, path, astroid_object):
        super(ClassNode, self).__init__()

        self.parent = parent
        self.path = path
        self._astroid_object = astroid_object

    @property
    def fs_path(self):
        return self.parent.fs_path

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

        self.path = self.parent.path + '.' + self._astroid_name.name

    @property
    def fs_path(self):
        return self.parent.fs_path 


class FunctionNode(Node):
    def __init__(self, parent, path, astroid_object):
        super(FunctionNode, self).__init__()

        self.parent = parent
        self.path = path
        self._astroid_object = astroid_object

    @property
    def fs_path(self):
        return self.parent.fs_path
