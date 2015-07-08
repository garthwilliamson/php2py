from tlib.php2pytests import *


class TransformerTests(Php2PyTestCase):
    """ Test the transformer

    Parser needs to be working properly first.

    """
    @parse_t
    def test_creates_body(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        transformer.transform(root_node)
        self.assertEqual("FUNCTION", root_node[0].node_type)
        self.assertContainsNode(root_node, "FUNCTION|body/BLOCK")

    @parse_t
    def test_increment(self, root_node):
        """ Transform an unary increment operator
        <?php
        $i++;
        """
        transformer.transform(root_node)
        statement_node = get_body(root_node).get("STATEMENT")
        op_node = statement_node.get("EXPRESSION")[0]
        self.assertEqual("+=", op_node.value)
        self.assertContainsNode(op_node, "GLOBALVAR|i")
        self.assertContainsNode(op_node, "INT|1")

    @parse_t
    def test_function_simple(self, root_node):
        """Simple function transform
        <?php
        function foo() {
            return 0;
        }"""
        transformer.transform(root_node)
        self.assertContainsNode(root_node, "FUNCTION|foo")
        body = get_body(root_node)
        self.assertContainsNode(body, "ASSIGNMENT")

    @parse_t
    def test_array_keyvalue(self, root_node):
        """ Array creation with key value assigments
        <?php
        $a = array (
          'b' => 1,
          'c' => 2,
        );
        """
        transformer.transform(root_node)
        print_tree(root_node)
        ex = get_body(root_node).get("STATEMENT").get("EXPRESSION")
        od = ex.get("ASSIGNMENT")[0]
        self.assertEqual(od.node_type, "CALLSPECIAL")
        self.assertEqual(od.value, "array")
        l = od.get("ARGSLIST").get("EXPRESSION")[0]
        self.assertEqual("LIST", l.node_type)
        self.assertEqual(l[0].node_type, "TUPLE")
        self.assertEqual(l[0][0].node_type, "STRING")
        self.assertEqual(l[0][1].node_type, "INT")
        # TODO: Move to compiler tests
        self.assertEqual(self.compiler.expression_compile_str(ex), 'p.g.a = array(p, [(u"b", 1), (u"c", 2)])')

    @parse_t
    def test_assign_in_if(self, root_node):
        """ Assign in an if statment
        <?php
        if ($a = 3) {
        }
        """
        transformer.transform(root_node)
        body_block = get_body(root_node)
        assign_statement = body_block.get("STATEMENT")
        if_statement = body_block.get("IF")
        self.assertContainsNode(assign_statement, "EXPRESSION/ASSIGNMENT/GLOBALVAR|a")
        self.assertContainsNode(if_statement, "EXPRESSION/GLOBALVAR|a")

    @parse_t
    def test_switch_simple(self, root_node):
        """ Switch statement as simple as possible
        <?php
        switch($a) {
            case 1:
                break;
        }
        """
        transformer.transform(root_node)
        self.assertContainsNode(get_body(root_node), "STATEMENT/EXPRESSION/ASSIGNMENT|=")

    @parse_t
    def test_switch(self, root_node):
        """ Switch statement without fallthrough
        <?php
        switch($a) {
            case 1:
                echo "case1";
                break;
            case 2:
                echo "case2";
                break;
            default:
                echo "default";
        }
        """
        transformer.transform(root_node)
        self.assertContainsNode(get_body(root_node), "STATEMENT/EXPRESSION/ASSIGNMENT|=")

    @parse_t
    def test_comments(self, root_node):
        """ Test single line comments
        <?php
        // Comment 1
        $a = 1; // Comment 2
        """
        print_tree(root_node)
        transformer.transform(root_node)
        bod = get_body(root_node)
        print_tree(root_node)
        statements = bod.match("STATEMENT*")
        self.assertContainsNode(statements[0], "COMMENTLINE")
        self.assertContainsNode(statements[1], "COMMENTLINE")
        self.assertContainsNode(statements[1], "EXPRESSION")
