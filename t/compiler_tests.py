from tlib.php2pytests import *

class CompilerTests(Php2PyTestCase):

    @parse_t
    def test_hello(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        transformer.transform(root_node)
        sc = self.compiler.statement_compile(get_body(root_node).get("STATEMENT"))
        self.assertEqual('echo(p, u"Hello World")', sc[0])

    @parse_t
    def test_asign(self, root_node):
        """Simple assignment
        <?php $a = 1; ?>
        """
        transformer.transform(root_node)
        cs = self.compiler.statement_compile(get_body(root_node).get("STATEMENT"))
        self.assertEqual("p.g.a = 1", cs[0])

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
        self.assertEqual("while (p.g.a == p.g.b):", wc[-2])

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
        self.assertEqual('p.f.a(p, u"B", p.constants.C, p.g.d)', cs[0])

    @parse_t
    def test_blank_line(self, root_node):
        """ Php block with a blank line in it
        <?php
        echo("Before blank");

        echo("After blank");
        """
        transformer.transform(root_node)
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
        self.assertEqual("class TestClass2(p.c.PhpBase):", cc[0])
