from tlib.php2pytests import *


class TransformerTests(Php2PyTestCase):
    """ Test the transformer

    Parser needs to be working properly first.

    """
    @transform_t
    def test_creates_body(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        self.assertContainsNode(root_node, "FUNCTION|body/BLOCK")

    @transform_t
    def test_echo(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        self.assertContainsNode(root_node, "FUNCTION|body/BLOCK/EX_STATEMENT")

    @transform_t
    def test_increment(self, root_node):
        """ Transform an unary increment operator
        <?php
        $i++;
        """
        op_node = get_body(root_node)["EX_STATEMENT"]["OPERATOR2"]
        self.assertEqual("+=", op_node.value)
        self.assertContainsNode(op_node, "OPERATOR2|./VAR|i")
        self.assertContainsNode(op_node, "INT|1")

    @transform_t
    def test_function_simple(self, root_node):
        """Simple function transform
        <?php
        function foo() {
            return 0;
        }"""
        self.assertContainsNode(root_node, "FUNCTION|foo")
        body = get_body(root_node)
        self.assertContainsNode(body, "EX_STATEMENT/ASSIGNMENT")

    @transform_t
    def test_array_keyvalue(self, root_node):
        """ Array creation with key value assigments
        <?php
        $a = array (
          'b' => 1,
          'c' => 2,
        );
        """
        ex = get_body(root_node).get("EX_STATEMENT")
        od = ex.get("ASSIGNMENT").rhs
        self.assertEqual("CALL", od.kind)
        self.assertEqual(od.value, "array")
        t = od.args[0]
        self.assertEqual(t.kind, "TUPLE")
        self.assertEqual(t.children[0].kind, "STRING")
        self.assertEqual(t.children[1].kind, "INT")
        # TODO: Move to compiler tests
        # self.assertEqual(self.compiler.expression_compile_str(ex), '_g_.a = _f_.array([(u"b", 1), (u"c", 2)])')

    @transform_t
    def test_array_assign_lookup(self, root_node):
        """ Array lookup which is actually an append
        <?php
        $a[] = "bob";
        """
        assign = get_body(root_node)["EX_STATEMENT"].child
        self.assertEqual("INDEX", assign.lhs.kind)
        self.assertEqual("STRING", assign.rhs.kind)
        self.assertContainsNode(assign.lhs, "OPERATOR2|./VAR|a")
        self.assertContainsNode(assign.lhs, "STRING|MagicEmptyArrayIndex")

    @transform_t
    def test_assign_in_if(self, root_node):
        """ Assign in an if statment
        <?php
        if ($a = 3) {
        }
        """
        body_block = get_body(root_node)
        assign_statement = body_block.get("EX_STATEMENT")
        if_statement = body_block.get("IF")
        self.assertContainsNode(assign_statement, "ASSIGNMENT/OPERATOR2|./VAR|a")
        self.assertContainsNode(if_statement, "OPERATOR2|./VAR|a")

    @transform_t
    def test_one_line_if(self, root_node):
        """ If on one line
        <?php
        if (1) echo "hi";
        """
        if_node = get_body(root_node)["IF"]
        self.assertContainsNode(if_node, "INT|1")
        self.assertContainsNode(if_node, "BLOCK/EX_STATEMENT")

    @transform_t
    def test_if_else(self, root_node):
        """ If with an elseif and an else
        <?php
        if (1) {
            2;
        } elseif (2) {
            4;
        } else {
            6;
        }
        """
        if_node = get_body(root_node)["IF"]
        self.assertContainsNode(if_node, "INT|1")
        self.assertContainsNode(if_node, "BLOCK/EX_STATEMENT/INT|2")
        self.assertContainsNode(if_node, "ELIF/INT|2")
        self.assertContainsNode(if_node, "ELIF/BLOCK/EX_STATEMENT/INT|4")
        self.assertContainsNode(if_node, "ELSE/BLOCK/EX_STATEMENT/INT|6")

    @transform_t
    def test_switch_simple(self, root_node):
        """ Switch statement as simple as possible
        <?php
        switch($a) {
            case 1:
                break;
        }
        """
        self.assertContainsNode(get_body(root_node), "EX_STATEMENT/ASSIGNMENT|=")

    @transform_t
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
        self.assertContainsNode(get_body(root_node), "EX_STATEMENT/ASSIGNMENT|=")

    @transform_t
    def test_comments(self, root_node):
        """ Test single line comments
        <?php
        // Comment 1
        $a = 1; // Comment 2
        """
        bod = get_body(root_node)
        statements = bod.children
        self.assertContainsNode(statements[1], "COMMENT")
        self.assertContainsNode(statements[2], "COMMENT")
        self.assertEqual(statements[2].kind, "EX_STATEMENT")

    @transform_t
    def test_foreach(self, root_node):
        """ Test foreach statement
        <?php
        foreach ($parameters as $key) {
             $key;
        }
        """
        bod = get_body(root_node)
        for_node = bod["FOR"]
        self.assertContainsNode(for_node.thing, "VAR|key")
        self.assertContainsNode(for_node.items, "VAR|parameters")  # foreach is at global or function scope
        self.assertContainsNode(for_node, "BLOCK/EX_STATEMENT/OPERATOR2|./VAR|key")

    @transform_t
    def test_foreach_tricky(self, root_node):
        """ Test foreach statement
        <?php
        foreach ($parameters as $key => $value) {
             $key;
        }
        """
        bod = get_body(root_node)
        for_node = bod["FOR"]

        self.assertContainsNode(for_node.thing, "OPERATOR2|./VAR|value")
        self.assertContainsNode(for_node.thing, "OPERATOR2|./VAR|key")
        self.assertContainsNode(for_node, "BLOCK/EX_STATEMENT/OPERATOR2|./VAR|key")
        self.assertEqual("CALL", for_node.items.kind)
        self.assertContainsNode(for_node.items.callee, "VAR|items")
        self.assertContainsNode(for_node.items.callee, "OPERATOR2|./VAR|parameters")

    @transform_t
    def test_class_simple(self, root_node):
        """ A simple class with no content
        <?php
        class TestClass
        {
            $a = 1;
        }
        """
        class_node = root_node["CLASS"]
        self.assertEqual("TestClass", class_node.value)
        self.assertEqual("PhpBase", class_node.parent.rhs.value)
        bod = get_body(root_node)
        self.assertContainsNode(bod, "EX_STATEMENT/ASSIGNMENT/OPERATOR2|./VAR|TestClass")

    @transform_t
    def test_class_parents(self, root_node):
        """ A class with parents
        <?php
        class TestClass extends TestBaseClass{
            $a = 1;
        }
        """
        class_node = root_node["CLASS"]
        self.assertEqual("TestBaseClass", class_node.parent.rhs.value)

    @transform_t
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
        # Function names are case insensitive, so lowercase all
        function_node = root_node.match("CLASS|TestClass42/BLOCK/CLASSMETHOD|testfunction")
        # TODO: if we can get away with it, avoid making things static etc.
        # self.assertContainsNode(function_node("PROPERTY|php_static"))
        for_node = function_node["BLOCK"]["FOR"]
        self.assertContainsNode(for_node, "BLOCK/EX_STATEMENT/VAR")

    # TODO: Need to work out what rules php uses to strip a newline at end of file and replicate

    @transform_t
    def test_deep_attr(self, root_node):
        """ Compile something with deep attributes
        <?php
        c = $this->a->b();
        """
        # TODO: The precendence of calls might be too low. or too high. I've forgotten this stuff already
        rhs = get_body(root_node)["EX_STATEMENT"].child["CALL"]
        self.assertEqual(rhs.kind, "CALL")
        self.assertContainsNode(rhs, "OPERATOR2|./OPERATOR2|./OPERATOR2|./VAR|this")

    @transform_t
    def test_new(self, root_node):
        """ Creation of an instance of a class
        <?php
        $a = new B();
        """
        assign = get_body(root_node)["EX_STATEMENT"].child
        self.assertContainsNode(assign, "OPERATOR2|./VAR|a")
        self.assertContainsNode(assign, "CALL/OPERATOR2|./VAR|_c_")

    @transform_t
    def test_new_attr(self, root_node):
        """ New class defined by a variable
        <?php
        $a = new $b->C(1);
        """
        # $b->C in this case is actually probably always a string variable
        # Transforms to getattr(_c_, b.C)(1)
        assign = get_body(root_node)["EX_STATEMENT"].child
        self.assertContainsNode(assign, "CALL/CALL/IDENT|getattr")
        self.assertContainsNode(assign, "CALL/CALL/OPERATOR2|./OPERATOR2|./VAR|b")
        self.assertContainsNode(assign, "CALL/CALL/VAR|_c_")
        self.assertContainsNode(assign, "CALL/INT|1")

    @transform_t
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
        class_ = root_node["CLASS"]["BLOCK"]
        method_body = class_["METHOD"]["BLOCK"]
        s1 = method_body.children[0]
        self.assertContainsNode(s1, "OPERATOR2|+=/OPERATOR2|./IDENT|a")
        s2 = method_body.children[1]
        self.assertContainsNode(s2, "CALL/OPERATOR2|./IDENT|play")
        self.assertContainsNode(s2, "CALL/OPERATOR2|./VAR|this")

    @transform_t
    def test_class_with_comment(self, root_node):
        """ A comment in the body of the class
        <?php
        class A {
            private $a = 1;
            /**
             * Block comment
             */
        }
        """
        class_block = root_node["CLASS"]["BLOCK"]
        self.assertContainsNode(class_block, "EX_STATEMENT/COMMENT")

    @transform_t
    def test_isset_plain_variable(self, root_node):
        """ php isset function on a normal variable
        <?php
        $b = isset($a);
        """
        bod = get_body(root_node)
        try_node = bod.children[1]
        self.assertEqual(try_node.kind, "TRY")
        # tempvar = not _g_.a is None
        self.assertEqual(try_node.catches[0].kind, "CATCH")
        # catch NameError:
        #     _tempvar = False
        self.assertContainsNode(try_node, "CATCH/EXCEPTION|NameError")
        self.assertContainsNode(try_node, "CATCH/EXCEPTION|KeyError")
        self.assertContainsNode(try_node, "CATCH/BLOCK/EX_STATEMENT/ASSIGNMENT/BOOL|False")
        # _g_.b = _tempvar

    @transform_t
    def test_isset_in_if(self, root_node):
        """ Isset with some added junk
        <?php
         if (isset($_POST["a"])) {
            1;
        }
        """
        bod = get_body(root_node)
        if_node = bod.children[2]
        self.assertContainsNode(if_node, "VAR|_tempvar")

    @transform_t
    def test_unset(self, root_node):
        """ Try to unset some things
        <?php
        unset($a[0], $a[1])
        """
        call = get_body(root_node)["EX_STATEMENT"].child
        self.assertContainsNode(call, "INDEX/INT|0")
        self.assertContainsNode(call, "IDENT|del")

    @transform_t
    def test_static_attr(self, root_node):
        """ Double colon lookup means class on lhs
        <?php
        PDO::Something;
        """
        attr_lookup = get_body(root_node)["EX_STATEMENT"].child
        self.assertEqual(".", attr_lookup.value)
        self.assertContainsNode(attr_lookup, "OPERATOR2|./VAR|_c_")
        self.assertContainsNode(attr_lookup, "OPERATOR2|./VAR|PDO")
