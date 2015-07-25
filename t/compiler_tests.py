from tlib.php2pytests import *


class CompilerTests(Php2PyTestCase):

    @parse_t
    def test_hello(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        transformer.transform(root_node)
        print_tree(root_node)
        sc = self.compiler.statement_compile(get_body(root_node).get("STATEMENT"))
        self.assertEqual('echo(u"Hello World")', sc[0])

    @parse_t
    def test_asign(self, root_node):
        """Simple assignment
        <?php $a = 1; ?>
        """
        transformer.transform(root_node)
        cs = self.compiler.statement_compile(get_body(root_node).get("STATEMENT"))
        self.assertEqual("_g_.a = 1", cs[0])

    @parse_t
    def test_array_append(self, root_node):
        """ I don't have much to say about this
        <?php $a[] = "bob"; ?>
        """
        transformer.transform(root_node)
        cs = self.compiler.statement_compile(get_body(root_node).get("STATEMENT"))
        self.assertEqual('_g_.a[u"MagicEmptyArrayIndex"] = u"bob"', cs[0])

    @parse_t
    def test_while(self, root_node):
        """ Simple while loop
        <?php
        while($a == $b) {
            $b++;
        }
        """
        transformer.transform(root_node)
        wc = self.compiler.while_compile(get_body(root_node).get("WHILE"))
        self.assertEqual("while (_g_.a == _g_.b):", wc[-2])

    # TODO: Can valid php end a php block without a semicolon?
    @parse_t
    def test_call(self, root_node):
        """ Simple multi argument call
        <?php
        a("B", C, $d);
        """
        transformer.transform(root_node)
        print_tree(root_node)
        cs = self.compiler.statement_compile(get_body(root_node).get("STATEMENT"))
        self.assertEqual('_f_.a(u"B", _constants_.C, _g_.d)', cs[0])

    @parse_t
    def test_blank_line(self, root_node):
        """ Php block with a blank line in it
        <?php
        echo("Before blank");

        echo("After blank");
        """
        print_tree(root_node)
        transformer.transform(root_node)
        print_tree(root_node)
        main = self.compiler.block_compile(get_body(root_node))
        from pprint import pprint
        pprint(main.lines)
        self.assertEqual("", main[2].strip())

    @parse_t
    def test_class_compilation(self, root_node):
        """ A class with a static classmethod in it
        <?php
        class TestClass2
        {
            static public function blah() {
                return "class,blah";
            }
            private function baz() {
                return "object,baz";
            }
        }
        """
        transformer.transform(root_node)
        print_tree(root_node)
        cc = self.compiler.class_compile(root_node.match("CLASS|TestClass2"))
        self.assertEqual("class TestClass2(_c_.PhpBase):", cc[0])

    @parse_t
    def test_compile_deep_attr(self, root_node):
        """ Compile something with deep attributes
        <?php
        c = $this->a->b();
        """
        print_tree(root_node)
        transformer.transform(root_node)
        print("-" * 50)
        print_tree(root_node)
        main = self.compiler.block_compile(get_body(root_node))
        print_tree(root_node)
        print(main)

    @parse_t
    def test_compile_getattr(self, root_node):
        """ Funky php getattr equivalent
        <?php
        $r = $s->{"a"};
        """
        transformer.transform(root_node)
        print_tree(root_node)
        statement = self.compiler.statement_compile(get_body(root_node)["STATEMENT"])
        self.assertEqual('_g_.r = getattr(_g_.s, u"a")', statement[0])

    @parse_t
    def test_compile_ternary(self, root_node):
        """ Compile a ternary operator
        <?php
        $a = 1 ? "a" : "b";
        """
        transformer.transform(root_node)
        statement = self.compiler.statement_compile(get_body(root_node)["STATEMENT"])
        self.assertEqual('_g_.a = u"a" if 1 else u"b"', statement[0])

    @parse_t
    def test_compile_foreach(self, root_node):
        """ Test foreach compilation
        <?php
        foreach ($parameters as $key => $value) {
             $key;
        }
        """
        transformer.transform(root_node)
        pyfor = get_body(root_node)["PYFOR"]
        fxc = self.compiler.pyfor_compile(pyfor)
        self.assertEqual("for _g_.key, _g_.value in _g_.parameters.items():", fxc[0])

    @parse_t
    def test_compile_foreach2(self, root_node):
        """ A simpler kind of foreach compilation
        <?php
        foreach ($a as $b) {
            1;
        }
        """
        transformer.transform(root_node)
        print_tree(root_node)
        pyfor = get_body(root_node)["PYFOR"]
        fxc = self.compiler.pyfor_compile(pyfor)
        self.assertEqual("for _g_.b in _g_.a:", fxc[0])

    @compile_body_t
    def test_compile_try(self, lines):
        """ Compile a try statement
        <?php
        try {
            $a = $db;
        } catch (ex $e) {
            1;
        }
        """
        expected = [
            "try:",
            "_g_.a = _g_.db",
            "except ex as _g_.e:",
            "1"
        ]
        self.assertLinesMatch(expected, lines)

    @compile_body_t
    def test_compile_dirname(self, lines):
        """ Compile a dirname call
        <?php
            $a = dirname(__DIR__);
        """
        self.assertLinesMatch([
            '_g_.a = _f_.dirname(_f_.dirname(__file__))'
        ], lines)
