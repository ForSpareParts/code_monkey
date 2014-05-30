from os import path

from nose.tools import assert_equal, assert_is_instance

from code_monkey.node import (
    ClassNode,
    ModuleNode,
    PackageNode,
    ProjectNode,
    VariableNode)

TEST_PROJECT_PATH = path.join(
    path.dirname(path.realpath(__file__)),
    '../test_project')

TEST_CLASS_SOURCE = '''class Employee(object):

    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
        self.pay_rate = settings.BASE_PAY

    def full_name(self):
        return self.first_name + ' ' + self.last_name
'''

CLASS_BODY_SOURCE = '''
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
        self.pay_rate = settings.BASE_PAY

    def full_name(self):
        return self.first_name + ' ' + self.last_name
'''

VARIABLE_SOURCE = '''MULTILINE_SETTING = {
    'some_key': 42,
    'other_key': {


        'baz': 'quux'
    }  #some comment


}'''

VARIABLE_BODY_SOURCE = '''{
    'some_key': 42,
    'other_key': {


        'baz': 'quux'
    }  #some comment


}'''

VARIABLE_VALUE = {
    'some_key': 42,
    'other_key': {
        'baz': 'quux'
    }
}

#vars needed in more than one test
#we can just make these once and leave them -- since these tests don't change
#data, there's no need for setup or teardown
project = ProjectNode(TEST_PROJECT_PATH)
package = project.children['lib']
root_module = project.children['settings']

employee_module = package.children['employee']

module_var = root_module.children['MULTILINE_SETTING']
employee_class = employee_module.children['Employee']
memo_function = package.children['edge_cases'].children['send_memo']


def test_node_tree():
    '''Test that nodes are correctly created from source'''

    assert_equal(len(project.children), 3)

    assert_is_instance(package, PackageNode)
    assert_is_instance(root_module, ModuleNode)
    assert_is_instance(employee_module, ModuleNode)

    assert_is_instance(module_var, VariableNode)
    assert_is_instance(employee_class, ClassNode)

    assert_equal(employee_class.path, 'test_project.lib.employee.Employee')


def test_source():
    '''Test that nodes correctly identify their own source.'''
    assert_equal(employee_class.get_source(), TEST_CLASS_SOURCE)

    assert_equal(employee_class.get_body_source(), CLASS_BODY_SOURCE)

    assert_equal(module_var.get_source(), VARIABLE_SOURCE)
    assert_equal(module_var.get_body_source(), VARIABLE_BODY_SOURCE)

    assert_equal(module_var.eval_body(), VARIABLE_VALUE)

    #has a multiline signature
    lair_class = package.children['edge_cases'].children['Lair']
    assert_equal(
        lair_class.body_start_index,
        lair_class.get_file_source_code().find(
            '    pass #Lair body starts here'))

    #has a multiline signature
    assert_equal(
        memo_function.body_start_index,
        memo_function.get_file_source_code().find(
            '#send_memo body starts here'))


def test_indentation():
    '''Test that nodes correctly detect their indentation level.'''

    assert_equal(memo_function.outer_indentation, '')
    assert_equal(memo_function.inner_indentation, '    ')
