from __future__ import unicode_literals

import unittest
import php2py.parser as p
from php2py import parse_and_compile

from pprint import pprint


def parse_string(s, debug=False):
    parser = p.PhpParser(s, "test", False)
    parser.parse()
    if debug:
        parser.pt.print_()
    return parser


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

scopes = """<?php
$a = 1;
function b()
{
    echo $a;
}
test();
"""

scope_globalled = """<?php
$a = 1;
$b = 2;
function Sum()
{
    global $a, $b;
    $b = $a + $b;
}
Sum();
echo $b;
"""

comments = """<?php
// Out of band comment
$a = 1; //In band comment
/* Big groupy comment
*/
$a = 2; /* groupy comment on line */ $b=3;

"""

new_eg = """<?php
$a = new B();
$c = new D("e", "f");
"""

multiline_call = """<?php
F(  $a,
    $b,

    $c
);
"""

multiline_call2 = """<?php
F(  $a,
    $b,
//Commenting is horrid
    $c
);
"""

nested_brackets = """<?php
require_once(dirname(__FILE__) . '/lib/setup.php');
"""


more_keywords = """<?php
die;

"""

complex_if = """<?php
if (!empty($CFG->a) && ($CFG->a == CONS) && optional_param('b', 1, PARAM_BOOL) === 0) {
    die;
}
"""


class SimpleTests(unittest.TestCase):
    def test_html(self):
        p = parse_string(html)
        res = p.get_tree()
        self.assertEqual(res.node_type, "ROOT")
        self.assertEqual(res[0].node_type, "HTML")
        self.assertEqual(res[0].value, html)

        self.assertEqual(res[0].start_cursor, 0)
        self.assertEqual(res[0].end_cursor, 16)

    def test_hello(self):
        p = parse_string(hello)
        res = p.get_tree()
        php = res[0]
        self.assertEqual(php.node_type, "PHP")

    def test_hello_no_end(self):
        p = parse_string(hello_no_end)
        res = p.get_tree()
        php = res[0]
        self.assertEqual(php.node_type, "PHP")
        echo_s = php[0]
        echo_e = echo_s[0][0]
        self.assertEqual(echo_e[0][0].value, "Hello World")

    def test_while(self):
        p = parse_string(while_eg)
        res = p.get_tree()
        php_node = res[0]
        self.assertEqual(php_node.node_type, "PHP")
        while_node = php_node[2]
        self.assertEqual(while_node.node_type, "WHILE")
        echo_world_expression = php_node[3][0]
        self.assertEqual(echo_world_expression[0][0][0].value, "world")

    def test_function(self):
        p = parse_string(function)
        res = p.get_tree()
        php_node = res[0]
        function_node = php_node[0]
        self.assertEqual(function_node.value, "foo")
        function_args = function_node[0]
        self.assertEqual(function_args[0][0].value, "arg1")
        function_body = function_node[1]
        return_statement = function_body[1]
        self.assertEqual(return_statement[0][2].node_type, "CONSTANT")
        self.assertEqual(return_statement[0][2].value, "true")

    def test_double_function(self):
        t = parse_string(double_function, True).get_tree()
        function_call = t[0][1][0][0]
        self.assertEqual(function_call.node_type, "CALL")
        self.assertEqual(function_call.value, "foo")

    def test_scope(self):
        php_node = parse_string(scopes, True).get_tree()[0]
        self.assertEqual(php_node[0][0][0].node_type, "GLOBALVAR")
        function_node = php_node[1]
        block_node = function_node[1]
        echo_statement_line = block_node[0]
        echo_expression = echo_statement_line[0][0]
        self.assertEqual(echo_expression[0][0].node_type, "VAR")

    def test_scopes_global(self):
        php_node = parse_string(scope_globalled).get_tree()[0]
        function_node = php_node[2]
        self.assertEqual(function_node.value, "Sum")
        # We don't actually output the global node anywhere
        assignment_statement = function_node[1][1]
        self.assertEqual(assignment_statement[0][0].value, "b")

    def test_comments(self):
        php_node = parse_string(comments, True).get_tree()[0]
        comment_node = php_node[0]
        self.assertEqual(comment_node.value, " Out of band comment")
        comment_node3 = php_node[2]
        self.assertEqual(comment_node3.value, " Big groupy comment\n")

    def test_new(self):
        php_node = parse_string(new_eg, True).get_tree()[0]
        statement = php_node[0]
        new_call = statement[0][2]
        self.assertEqual(new_call.node_type, "NEW")
        call = new_call[0]
        print(call)
        self.assertEqual(call.node_type, "CALL")
        self.assertEqual(call.value, "B")

    def test_multiline_call(self):
        php_node = parse_string(multiline_call, True).get_tree()[0]
        fcall = php_node[0][0][0]
        self.assertEqual(fcall.node_type, "CALL")
        self.assertEqual(fcall.value, "F")
        self.assertEqual(fcall[0][0].value, "a")

    def test_multiline_call2(self):
        print("ASDFASDF")
        php_node = parse_string(multiline_call2, True).get_tree()[0]
        fcall = php_node[0][0][0]
        print(fcall)
        self.assertEqual(fcall.node_type, "CALL")
        self.assertEqual(fcall.value, "F")
        self.assertEqual(fcall[0][0].value, "a")

    def test_nested(self):
        php_node = parse_string(nested_brackets, True).get_tree()[0]
        self.assertEqual(php_node[0][0][0][0][0].node_type, "CALL")
        self.assertEqual(php_node[0][0][0][0][0][0][0].value, "__file__")

    def test_complex_if(self):
        php_node = parse_string(complex_if, True).get_tree()[0]


class CompileTest(unittest.TestCase):
    # TODO: These tests should work out why eval is failing
    def test_while(self):
        parse_and_compile(while_eg)

    def test_hello(self):
        parse_and_compile(hello)

    def test_function(self):
        parse_and_compile(function)

    def test_double_function(self):
        parse_and_compile(double_function)

    def test_recurse(self):
        parse_and_compile(recurse, debug=True)

    def test_scope(self):
        parse_and_compile(scopes)

    def test_scope_global(self):
        parse_and_compile(scope_globalled)

    def test_comments(self):
        parse_and_compile(comments)

    def test_new(self):
        parse_and_compile(new_eg)

    def test_multiline_call(self):
        parse_and_compile(multiline_call)

    def test_multiline_call2(self):
        parse_and_compile(multiline_call2, debug=True)


if __name__ == "__main__":
    unittest.main()