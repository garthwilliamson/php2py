from tlib.php2pytests import *


class CompilerTests(Php2PyTestCase):

    @parse_t
    def test_hello(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        root_node = transformer.transform(root_node)
        print_tree(root_node)
        sc = get_body(root_node).get("EX_STATEMENT").compile()
        self.assertEqual('_f_.echo("Hello World")', sc[0])

    @parse_t
    def test_asign(self, root_node):
        """Simple assignment
        <?php $a = 1; ?>
        """
        root_node = transformer.transform(root_node)
        cs = get_body(root_node).get("EX_STATEMENT").compile()
        self.assertEqual("_g_.a = 1", cs[0])

    @parse_t
    def test_array_append(self, root_node):
        """ I don't have much to say about this
        <?php $a[] = "bob"; ?>
        """
        root_node = transformer.transform(root_node)
        cs = get_body(root_node).get("EX_STATEMENT").compile()
        self.assertEqual('_g_.a["MagicEmptyArrayIndex"] = "bob"', cs[0])

    @compile_body_t
    def test_array_construct(self, lines):
        """ Array as a dict
        <?php
        $a = array("a" => "A", "b" => "B");
        """
        self.assertEqual('_g_.a = _f_.array(("a", "A"), ("b", "B"))', lines[0])

    @parse_t
    def test_while(self, root_node):
        """ Simple while loop
        <?php
        while($a == $b) {
            $b++;
        }
        """
        root_node = transformer.transform(root_node)
        wc = get_body(root_node).get("WHILE").compile()
        self.assertEqual("while _g_.a == _g_.b:", wc[-2])

    # TODO: Can valid php end a php block without a semicolon?
    @parse_t
    def test_call(self, root_node):
        """ Simple multi argument call
        <?php
        a("B", C, $d);
        """
        root_node = transformer.transform(root_node)
        print_tree(root_node)
        cs = get_body(root_node).get("EX_STATEMENT").compile()
        self.assertEqual('_f_.a("B", _constants_.C, _g_.d)', cs[0])

    @parse_t
    def test_blank_line(self, root_node):
        """ Php block with a blank line in it
        <?php
        echo("Before blank");

        echo("After blank");
        """
        root_node = transformer.transform(root_node)
        print("----------")
        print_tree(root_node)
        main = get_body(root_node).compile()
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
        root_node = transformer.transform(root_node)
        print_tree(root_node)
        cc = root_node.match("CLASS|TestClass2").compile()
        self.assertEqual("class TestClass2(_c_.PhpBase):", cc[0])

    @parse_t
    def test_compile_deep_attr(self, root_node):
        """ Compile something with deep attributes
        <?php
        c = $this->a->b();
        """
        print_tree(root_node)
        root_node = transformer.transform(root_node)
        print("-" * 50)
        print_tree(root_node)
        main = get_body(root_node).compile()
        print_tree(root_node)
        print(main)

    @compile_body_t
    def test_attr_method_result(self, lines):
        """ Methods returning objects with attributes
        <?php
        $a->b()->c;
        """
        self.assertSequenceEqual(lines, [
            "_g_.a.b().c",
            "",
        ])

    @parse_t
    def test_compile_getattr(self, root_node):
        """ Funky php getattr equivalent
        <?php
        $r = $s->{"a"};
        """
        root_node = transformer.transform(root_node)
        statement = get_body(root_node)["EX_STATEMENT"].compile()
        self.assertEqual('_g_.r = getattr(_g_.s, "a")', statement[0])

    @parse_t
    def test_compile_ternary(self, root_node):
        """ Compile a ternary operator
        <?php
        $a = 1 ? "a" : "b";
        """
        root_node = transformer.transform(root_node)
        statement = get_body(root_node)["EX_STATEMENT"].compile()
        self.assertEqual('_g_.a = "a" if 1 else "b"', statement[0])

    @compile_body_t
    def test_compile_foreach(self, lines):
        """ Test foreach compilation
        <?php
        foreach ($parameters as $key => $value) {
             $key;
        }
        """
        self.assertEqual("for _g_.key, _g_.value in _g_.parameters.items():", lines[0])

    @compile_body_t
    def test_compile_foreach2(self, lines):
        """ A simpler kind of foreach compilation
        <?php
        foreach ($a as $b) {
            1;
        }
        """
        self.assertEqual("for _g_.b in _g_.a:", lines[0])

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
            "1",
            "",
        ]
        self.assertSequenceEqual(expected, lines)

    @compile_body_t
    def test_compile_dirname(self, lines):
        """ Compile a dirname call
        <?php
            $a = dirname(__DIR__);
        """
        self.assertSequenceEqual([
            '_g_.a = _f_.dirname(_f_.dirname(__file__))',
            "",
        ], lines)

    @compile_body_t
    def test_compile_new(self, lines):
        """ Compile creation of a new thing
        <?php
        $a = new B();
        """
        self.assertSequenceEqual([
            "_g_.a = _c_.B()",
            "",
        ], lines)

    @compile_class_t
    def test_constructors(self, lines):
        """ Compile a class with a constructor
        <?php
        class A {
            function __construct () {
                b();
            }
        }
        """
        self.assertSequenceEqual([
            "class A(_c_.PhpBase):",
            "def _php_construct(this):",
            "_f_.b()"
        ], lines)

    @compile_class_t
    def test_self_attr_access(self, lines):
        """ A class that plays with itself
        <?php
        class A {
            private $a = 1;
            public function plaY() {
                $this->a++;
                $this->pLay();
            }
        }
        """
        self.assertSequenceEqual([
            "class A(_c_.PhpBase):",
            "a = 1",
            "def play(this):",
            "this.a += 1",
            "this.play()"
        ], lines)

    @compile_body_t
    def test_block_comments(self, lines):
        """ Test the formatting of block comments
        <?php
        1;
        /**
        * a comment
        * on two lines
        */
        2; /* Block after expression */
        """
        self.assertSequenceEqual([
            "1",
            "# ",
            "# a comment",
            "# on two lines",
            "# ",
            "2",
            "# Block after expression",
            ""
        ], lines)

    @compile_body_t
    def test_isset_compilation(self, lines):
        """ Isset with some added junk
        <?php
         if (isset($_POST["a"])) {
            1;
        }
        """
        print(lines)
        self.assertSequenceEqual([
            "try:",
            '_tempvar = _g_._POST["a"] is not None',
            "except (NameError, KeyError):",
            "_tempvar = False",
            "if _tempvar:",
            "1",
            ""
        ], lines)

    @compile_body_t
    def test_ternary(self, lines):
        """ Another version of isset
        <?php
        $a = $f ? $u[1] : $n;
        """
        self.assertSequenceEqual([
            "_g_.a = _g_.u[1] if _g_.f else _g_.n",
            "",
        ], lines)


    @compile_body_t
    def test_if_else(self, lines):
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
        self.assertSequenceEqual([
            "if 1:",
            "2",
            "elif 2:",
            "4",
            "else:",
            "6",
            "",
        ], lines)

    @compile_body_t
    def test_pdo(self, lines):
        """
        <?php
        $opts = array(PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_OBJ);
        $p = new PDO("con_string", "user", "pass", $opts);
        """
        self.assertSequenceEqual(lines, [
            "_g_.opts = _f_.array((_c_.PDO.ATTR_DEFAULT_FETCH_MODE, _c_.PDO.FETCH_OBJ))",
            "_g_.p = _c_.PDO(\"con_string\", \"user\", \"pass\", _g_.opts)",
            "",
        ])

