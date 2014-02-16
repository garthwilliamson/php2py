import unittest
import php2py.parser as p
from pprint import pprint


def parse_string(s, tree=False):
    parser = p.PhpParser(s, "test", False)
    parser.parse()
    if tree:
        return parser.get_tree()
    return parser.to_list()


html = "<div>hello</div>"

hello = """<?php echo "Hello World"; ?>
"""

hello_no_end = """<?php echo "Hello World";
"""

while_eg = """<?php
$a = 0;
$b = 0;
while($a == $b) {
    echo "Hi there";
    $b++;
}
echo "world"
"""

function = """<?php
function foo($arg1, $arg2) {
    echo "In the function";
    return $arg1 || True;
}

"""

# PHP scopes functions globally. wtf?
double_function = """<?php
function foo()
{
  function bar()
  {
    echo "Inner function\n";
  }
}
foo();
bar();
?>
"""

recurse = """<?php
function recursion($a)
{
    if ($a < 20) {
        echo "$a\n";
        recursion($a + 1);
    }
}
recursion(10);
"""

class ParserTests(unittest.TestCase):
    def setUp(self):
        self.matching = "AABBCC1234<?php"
        self.simple_parser = p.Parser(self.matching, "test1", False)

    def test_create_pattern(self):
        res = p.create_pattern(("AA", "BB"))
        self.assertEqual(res.pattern, "AA|BB")
        self.assertEqual(res.match(self.matching).group(0), "AA")

    def test_sizing(self):
        pat = p.create_pattern(("AABBD", "AABBC", "AAB", "BC", "B"))
        self.assertEqual(pat.search(self.matching).group(0), "AABBC")

    def test_matching(self):
        pat = p.create_pattern(("BB", "CC"))
        self.assertIs(None, self.simple_parser.match_for(pat))
        pat = p.create_pattern(("BB", "AA"))
        self.assertEqual("AA", self.simple_parser.match_for(pat))

    def test_searching(self):
        pat = p.create_pattern(("DD",))
        match, until = self.simple_parser.search_until(pat)
        self.assertEqual(match, "EOF")
        pat = p.create_pattern(("CC",))
        match, until = self.simple_parser.search_until(pat)
        self.assertEqual(match, "CC")
        self.assertEqual(until, "AABB")
        match, until = self.simple_parser.search_until(p.create_pattern(("<?php",)))
        self.assertEqual(match, "<?php")
        self.assertEqual(until, "1234")


class SimpleTests(unittest.TestCase):
    def test_html(self):
        res = parse_string(html)
        self.assertEqual(res[0], "ROOT")
        self.assertEqual(res[2][0][0], "HTML")
        self.assertEqual(res[2][0][1], html)

    def test_hello(self):
        res = parse_string(hello)[2]
        self.assertEqual(res[0][0], "PHP")

    def test_hello_no_end(self):
        res = parse_string(hello_no_end)[2]
        self.assertEqual(res[0][0], "PHP")

    def test_while(self):
        res = parse_string(while_eg, tree=True)
        php_node = res[0]
        self.assertEqual(php_node.node_type, "PHP")
        while_node = php_node[2]
        self.assertEqual(while_node.node_type, "WHILE")
        echo_world = php_node[3]
        #p.print_tree(echo_world)
        self.assertEqual(echo_world[0][0].value, "world")

    def test_function(self):
        t = parse_string(function, tree=True)
        p.print_tree(t)
        php_node = t[0]
        function_node = php_node[0]
        self.assertEqual(function_node.value, "foo")
        function_args = function_node[0]
        self.assertEqual(function_args[0][0].value, "arg1")
        function_body = function_node[1]
        return_statement = function_body[1]
        self.assertEqual(return_statement[0][2].node_type, "CONSTANT")
        self.assertEqual(return_statement[0][2].value, "true")

    def test_double_function(self):
        t = parse_string(double_function, tree=True)
        #p.print_tree(t)
        function_call = t[0][1][0]
        self.assertEqual(function_call.node_type, "CALL")
        self.assertEqual(function_call.value, "foo")


class CompileTest(unittest.TestCase):
    # TODO: These tests should work out why eval is failing
    def test_while(self):
        p.parse_and_compile(while_eg)

    def test_hello(self):
        p.parse_and_compile(hello)

    def test_function(self):
        p.parse_and_compile(function)

    def test_double_function(self):
        p.parse_and_compile(double_function)

    def test_recurse(self):
        print(p.parse_and_compile(recurse))


if __name__ == "__main__":
    unittest.main()