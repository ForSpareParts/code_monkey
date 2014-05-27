'''Code to generate new changes to the source of a Node. Every change is a
single Change object.

Nothing in this module actually overwrites files: that occurs in edit, where
Changes are grouped into ChangeSets. ChangeSets check that individual changes
do not conflict, provide previews, and commit changes to disk.
'''
import difflib

from code_monkey.utils import line_column_to_absolute_index

class Change(object):
    '''A single change to make to a single file. Replaces the file content
    from indices start through end (inclusive) with new_text.'''
    def __init__(self, path, start, end, new_text):
        self.path = path
        self.start = start
        self.end = end
        self.new_text = new_text

    def __unicode__(self):
        with open(self.path) as source_file:
            source = source_file.read()

        new_source = (
            source[:self.start] + self.new_text + source[(self.end+1):])

        #difflib works on lists of line strings, so we convert the source and
        #its replacement to lists.
        source_lines = source.splitlines(True)
        new_lines = new_source.splitlines(True)

        diff = difflib.unified_diff(
            source_lines,
            new_lines,
            fromfile=self.path,
            tofile=self.path)

        output = ''

        #diff is a generator that returns lines, so we collect it into a string
        for line in diff:
            output += line

        return output

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()

class ChangeGenerator(object):
    '''Generates change tuples for a specific node. Every node with a source
    file should have one, as its .change property.

    So, a typical use might be: change = node.change.overwrite("newtext")'''

    def __init__(self, node):
        self.node = node

    def overwrite(self, new_source):
        '''Generate a change that overwrites the contents of the Node entirely
        with new_source'''

        #find the actual index in the source at which the node begins:
        file_source = self.node.get_file_source_code()

        from_index = line_column_to_absolute_index(
            file_source,
            self.node.start_line,
            self.node.start_column)

        #to get the last index, we want the end of the previous line -- so we
        #get the beginning of the line after, and back up
        to_index = line_column_to_absolute_index(
            file_source,
            self.node.end_line + 1,
            0) - 1

        return Change(
            self.node.fs_path,
            from_index,
            to_index,
            new_source)

    def overwrite_body(self, new_source):
        '''Generate a change that overwrites the body of the node with
        new_source. In the case of a ModuleNode, this is equivalent to
        overwrite().'''

        #find the actual index in the source at which the node begins:
        file_source = self.node.get_file_source_code()

        from_index = line_column_to_absolute_index(
            file_source,
            self.node.body_start_line,
            self.node.body_start_column)

        #to get the last index, we want the end of the previous line -- so we
        #get the beginning of the line after, and back up
        to_index = line_column_to_absolute_index(
            file_source,
            self.node.end_line + 1,
            0) - 1

        return overwrite_file_region(
            self.node.fs_path,
            from_index,
            to_index,
            new_source)


    def inject_at_index(self, index, inject_source):
        '''Generate a change that inserts inject_source into the node, starting
        at index. index is relative to the beginning of the node, not the
        beginning of the file.

        TODO: rewrite so that the change only touches the lines modified. The
        current implementation rewrites the whole node, though most of it
        remains the same. A smaller change would allow multiple changes to
        one node in a single changeset.'''
        #the original source of this node
        node_source = self.node.get_source_code()

        #the node's source after we insert inject_source
        new_source = node_source[:index] + inject_source + \
            node_source[index:]

        return self.overwrite(new_source)

    def inject_at_body_index(self, index, inject_source):
        '''Generate a change that inserts inject_source into the node, starting
        at index. index is relative to the beginning of the node body, not the
        beginning of the file.'''
        #the original source of this node
        body_source = self.node.get_body_source_code()

        #the node's source after we insert inject_source
        new_source = body_source[:index] + inject_source + \
            body_source[index:]

        return self.overwrite_body(new_source)