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
        self.assertContainsNode(op_node, "VAR|_g_.i")
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
        self.assertContainsNode(body, "STATEMENT/EXPRESSION/ASSIGNMENT")

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
        self.assertEqual("CALL", od.node_type)
        self.assertEqual(od.value, "array")
        l = od.get("ARGSLIST").get("EXPRESSION")[0]
        self.assertEqual("LIST", l.node_type)
        self.assertEqual(l[0].node_type, "TUPLE")
        self.assertEqual(l[0][0].node_type, "STRING")
        self.assertEqual(l[0][1].node_type, "INT")
        # TODO: Move to compiler tests
        self.assertEqual(self.compiler.expression_compile_str(ex), '_g_.a = _f_.array([(u"b", 1), (u"c", 2)])')

    @parse_t
    def test_array_assign_lookup(self, root_node):
        """ Array lookup which is actually an append
        <?php
        $a[] = "bob";
        """
        transformer.transform(root_node)
        assign_t = get_body(root_node).match("STATEMENT/EXPRESSION/ASSIGNMENT")
        rhs = assign_t[0]
        lhs = assign_t[1]
        self.assertEqual("INDEX", lhs.node_type)
        self.assertEqual("STRING", rhs.node_type)
        print_tree(root_node)
        self.assertContainsNode(lhs, "VAR|_g_.a")
        self.assertContainsNode(lhs, "EXPRESSION/STRING|MagicEmptyArrayIndex")

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
        self.assertContainsNode(assign_statement, "EXPRESSION/ASSIGNMENT/VAR|_g_.a")
        self.assertContainsNode(if_statement, "EXPRESSION/VAR|_g_.a")

    @parse_t
    def test_one_line_if(self, root_node):
        """ If on one line
        <?php
        if (1) echo "hi";
        """
        transformer.transform(root_node)
        if_node = get_body(root_node)["IF"]
        self.assertContainsNode(if_node, "EXPRESSION/INT|1")
        self.assertContainsNode(if_node, "BLOCK/STATEMENT/EXPRESSION")

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

    @parse_t
    def test_foreach(self, root_node):
        """ Test foreach statement
        <?php
        foreach ($parameters as $key) {
             $key;
        }
        """
        print_tree(root_node)
        transformer.transform(root_node)
        print_tree(root_node)
        bod = get_body(root_node)
        for_node = bod["PYFOR"]

        self.assertContainsNode(for_node, "EXPRESSION")
        self.assertContainsNode(for_node, "VAR|_g_.key")  # foreach is at global or function scope
        self.assertContainsNode(for_node, "BLOCK/STATEMENT/EXPRESSION/VAR|_g_.key")

    @parse_t
    def test_foreach_tricky(self, root_node):
        """ Test foreach statement
        <?php
        foreach ($parameters as $key => $value) {
             $key;
        }
        """
        transformer.transform(root_node)
        bod = get_body(root_node)
        for_node = bod["PYFOR"]

        self.assertContainsNode(for_node, "EXPRESSION")
        self.assertContainsNode(for_node, "ARGSLIST/VAR")  # foreach is at global or function scope
        self.assertContainsNode(for_node, "BLOCK/STATEMENT/EXPRESSION/VAR")
        self.assertContainsNode(for_node, "EXPRESSION/CALL/OPERATOR2/VAR|_g_.parameters")
        self.assertContainsNode(for_node, "EXPRESSION/CALL/OPERATOR2/IDENT|items")
        self.assertContainsNode(for_node, "EXPRESSION/CALL/ARGSLIST")

    @parse_t
    def test_class_simple(self, root_node):
        """ A simple class with no content
        <?php
        class TestClass
        {
            $a;
        }
        """
        transformer.transform(root_node)
        class_node = root_node["CLASS"]
        self.assertEqual("TestClass", class_node.value)
        self.assertContainsNode(class_node, "EXTENDS|PhpBase")
        self.assertContainsNode(class_node, "BLOCK")
        bod = get_body(root_node)
        self.assertContainsNode(bod, "STATEMENT/EXPRESSION/ASSIGNMENT/VAR|_c_.TestClass")

    @parse_t
    def test_class_parents(self, root_node):
        """ A class with parents
        <?php
        class TestClass extends TestBaseClass{
            $a;
        }
        """
        print_tree(root_node)
        transformer.transform(root_node)
        class_node = root_node["CLASS"]
        self.assertContainsNode(class_node, "EXTENDS|TestBaseClass")

    @parse_t
    def test_class_transform_function_body(self, root_node):
        """ The body of static functions should compile properly
        <?php
        class TestClass42 {
            static public function testFunction($params) {
                foreach ($params as $key => $value) {
                    $key;
                }
            }
        }
        """
        transformer.transform(root_node)
        print_tree(root_node)
        # Function names are case insensitive, so lowercase all
        function_node = root_node.match("CLASS|TestClass42/BLOCK/CLASSMETHOD|testfunction")
        # TODO: if we can get away with it, avoid making things static etc.
        # self.assertContainsNode(function_node("PROPERTY|php_static"))
        for_node = function_node["BLOCK"]["PYFOR"]
        self.assertContainsNode(for_node, "EXPRESSION")
        self.assertContainsNode(for_node, "ARGSLIST/VAR")
        self.assertContainsNode(for_node, "BLOCK/STATEMENT/EXPRESSION/VAR")

    # TODO: Need to work out what rules php uses to strip a newline at end of file and replicate

    @parse_t
    def test_deep_attr(self, root_node):
        """ Compile something with deep attributes
        <?php
        c = $this->a->b();
        """
        # TODO: The precendence of calls might be too low. or too high. I've forgotten this stuff already
        transformer.transform(root_node)
        rhs = get_body(root_node).match("STATEMENT/EXPRESSION/ASSIGNMENT/CALL")
        self.assertEqual(rhs.node_type, "CALL")
        self.assertContainsNode(rhs, "ARGSLIST")
        self.assertContainsNode(rhs, "ATTR/ATTR/VAR|_g_.this")

    @parse_t
    def test_new(self, root_node):
        """ Creation of an instance of a class
        <?php
        $a = new B();
        """
        print_tree(root_node)
        transformer.transform(root_node)
        print_tree(root_node)
        assign = get_body(root_node).match("STATEMENT/EXPRESSION/ASSIGNMENT")
        self.assertContainsNode(assign, "VAR|_g_.a")
        self.assertContainsNode(assign, "CALL/OPERATOR2|./IDENT|_c_")

    @parse_t
    def test_self_attr_access(self, root_node):
        """ A class that plays with itself
        <?php
        class A {
            private $a = 1;
            public function play() {
                $this->a++;
                $this->play();
            }
        }
        """
        transformer.transform(root_node)
        print_tree(root_node)
        class_body = root_node["CLASS"]["BLOCK"]
        method_body = class_body["METHOD"]["BLOCK"]
        s1 = method_body[0]
        self.assertContainsNode(s1, "EXPRESSION/OPERATOR2|+=/ATTR/IDENT|a")
        s2 = method_body[1]
        self.assertContainsNode(s2, "EXPRESSION/CALL/ATTR/IDENT|play")
        self.assertContainsNode(s2, "EXPRESSION/CALL/ATTR/VAR|this")

    @parse_t
    def test_isset_plain_variable(self, root_node):
        """ php isset function on a normal variable
        <?php
        $b = isset($a);
        """
        transformer.transform(root_node)
        print_tree(root_node)
        bod = get_body(root_node)
        try_node = bod[1]
        self.assertEqual(try_node.node_type, "TRY")
        self.assertEqual(try_node[0].node_type, "BLOCK")
        # tempvar = not _g_.a is None
        self.assertEqual(try_node[1].node_type, "CATCH")
        # catch NameError:
        #     _tempvar = False
        self.assertContainsNode(try_node, "CATCH/EXCEPTION|NameError")
        self.assertContainsNode(try_node, "CATCH/EXCEPTION|KeyError")
        self.assertEqual(try_node["CATCH"][1].node_type, "BLOCK")
        self.assertContainsNode(try_node, "CATCH/BLOCK/STATEMENT/EXPRESSION/ASSIGNMENT/IDENT|False")
        # _g_.b = _tempvar

    @parse_t
    def test_isset_in_if(self, root_node):
        """ Isset with some added junk
        <?php
         if (isset($_POST["a"])) {
            1;
        }
        """
        transformer.transform(root_node)
        print_tree(root_node)
        bod = get_body(root_node)
        try_node = bod[1]
        if_node = bod[2]
        self.assertContainsNode(if_node, "EXPRESSION/VAR|_tempvar")

    @parse_t
    def test_unset(self, root_node):
        """ Try to unset some things
        <?php
        unset($a[0], $a[1])
        """
        print_tree(root_node)
        transformer.transform(root_node)
        print_tree(root_node)
        bod = get_body(root_node)
        self.assertContainsNode(bod, "STATEMENT/EXPRESSION/CALL/ARGSLIST/EXPRESSION/INDEX/EXPRESSION/INT|0")
        self.assertContainsNode(bod, "STATEMENT/EXPRESSION/CALL/IDENT|del")
