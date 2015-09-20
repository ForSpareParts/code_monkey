from code_monkey.node.expression.base import ExpressionNode

class NameNode(ExpressionNode):
    def __init__(self, parent, astroid_object):
        super(NameNode, self).__init__(
            parent=parent,
            name=astroid_object.name,
            astroid_object=astroid_object)

    def consume_expression(self, detector):
        detector.consume_name()

class AssignmentNameNode(NameNode):
    #not *really* an expression -- should it be refactored?
    pass
