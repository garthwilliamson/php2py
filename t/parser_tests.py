from __future__ import unicode_literals

import unittest
import php2py.compiler as c
import php2py.parser as p
from php2py.parsetree import print_tree
from php2py.transformer import transform_php
from php2py import parse_and_compile

from pprint import pprint


def parse_string(s, debug=False):
    parser = p.PhpParser(iter(s.split("\n")), debug=True)
    parser.parse()
    if debug:
        parser.pt.print_()
    return parser


html = "<div>hello</div>"

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
    echo "Inner function\\n";
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

scope_globalled = """<?php
$a = 1;
$b = 2;
function Sum()
{
    global $a, $b;
    $b = $a;
}
Sum();
echo $b;
"""

new_eg = """<?php
$a = new B();
$c = new D("e", "f");
"""

multiline_call2 = """<?php
F(  $a,
    $b,
//Commenting is horrid
    $c
);
"""

more_keywords = """<?php
die;

"""

complex_if = """<?php
if (!empty($CFG->a) && ($CFG->a == CONS) && optional_param('b', 1, PARAM_BOOL) === 0) {
    die;
}
"""

array_keyvalue = """<?php
$CFG->dboptions = array (
  'dbpersist' => 0,
  'dbsocket' => 0,
);
"""

multi_space_comment = """<?php
if ($a) {
    $a;   // Comment with exta spaces
}

"""

dynamic_class_creation = """<?php
$A = new $b();
"""

casting = """<?php
$a = (array)$B;
"""

assign_in_if = """<?php
if ($a = 3) {
}
"""

assign_in_if2 = """<?php
if ($a = $B->c('d', 'e', array('f'=>'g'))) {
    h::i();
}
"""

from functools import wraps


def php_t(f):
    """ Wrap a function to parse a php string given as a docstring

    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        """ The wrapper

        """
        tree = parse_string(f.__doc__).get_tree()
        #print_tree(tree)
        f(self, tree[1], *args, **kwargs)
    return wrapper


class SimpleTests(unittest.TestCase):
    def setUp(self):
        self.compiler = c.Compiler()

    def assertEcho(self, node, string, node_type="STRING"):
        self.assertEqual(node[0].node_type, "EXPRESSION")
        self.assertEqual(node[0][0].node_type, "CALL")
        self.assertEqual(node[0][0][0].node_type, "ARGLIST")
        self.assertEqual(node[0][0][0][0].node_type, "EXPRESSION")
        self.assertEqual(node[0][0][0][0][0].node_type, node_type)
        self.assertEqual(node[0][0][0][0][0].value, string)

    def assertLastCompiled(self, comparison, distance=1):
        self.assertEqual(self.compiler.functions[-1][-distance], comparison)

    def test_html(self):
        p = parse_string(html)
        res = p.get_tree()
        self.assertEqual(res.node_type, "ROOT")
        self.assertEqual(res[0].node_type, "HTML")
        self.assertEqual(res[0].value, html)

    @php_t
    def test_hello(self, php):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        self.assertEqual(php.node_type, "PHP")
        self.assertEcho(php[0], "Hello World")

        transform_php(php)
        self.compiler.statement_compile(php[0])
        self.assertLastCompiled("    p.f.echo(p, u'Hello World')")

    @php_t
    def test_hello_no_end(self, php):
        """ Echo without an end tag
        <?php echo "Hello World";
        """
        self.assertEqual(php.node_type, "PHP")
        self.assertEcho(php[0], "Hello World")

        transform_php(php)
        self.compiler.statement_compile(php[0])
        self.assertLastCompiled("    p.f.echo(p, u'Hello World')")

    @php_t
    def test_assign(self, php_node):
        """Simple assignment
        <?php $a = 1; ?>
        """
        print_tree(php_node)
        statement = php_node[0]
        self.assertEqual(statement.node_type, "STATEMENT")
        expression = statement[0]
        self.assertEqual(expression.node_type, "EXPRESSION")
        assignment = expression[0]
        self.assertEqual(assignment.value, "=")
        to_assign = assignment[0]
        self.assertEqual(to_assign.node_type, "INT")
        assign_to = assignment[1]
        self.assertEqual(assign_to.value, "a")

        transform_php(php_node)
        self.compiler.statement_compile(php_node[0])
        print(self.compiler)
        self.assertLastCompiled("    p.g.a = 1")

    @php_t
    def test_while(self, php_node):
        """ Simple while loop
        <?php
        while($a == $b) {
            echo "Hi there";
            $b++;
        }
        echo "world"
        """
        self.assertEqual(php_node.node_type, "PHP")
        while_node = php_node[0]
        self.assertEqual(while_node.node_type, "WHILE")
        echo_world_statement = php_node[1]
        self.assertEcho(echo_world_statement, "world")

        transform_php(php_node)
        self.compiler.while_compile(while_node)
        print(self.compiler)
        self.assertLastCompiled("        (p.g.b += 1)")

    @php_t
    def test_function_simple(self, php_node):
        """Simple function
        <?php
        function foo() {
            return 0;
        }"""
        function_node = php_node[0]
        self.assertEqual(function_node.node_type, "FUNCTION")
        arg_list = function_node[0]
        self.assertEqual(len(arg_list.children), 0)
        function_block = function_node[1]
        self.assertEqual(function_block.node_type, "BLOCK")
        return_statement = function_block[0]
        self.assertEqual(return_statement.node_type, "RETURN")
        return_expression = return_statement.get("EXPRESSION")
        self.assertEqual(return_expression[0].node_type, "INT")

        transform_php(php_node)
        print_tree(php_node)
        self.compiler.php_compile(php_node)
        #TODO: Check the body function for the following
        #self.assertLastCompiled("p.f.foo = foo")
        self.assertLastCompiled("    return 0")

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
        self.assertEqual(return_statement.node_type, "RETURN")
        self.assertEqual(return_statement.get("EXPRESSION").get("OPERATOR")[0].value, "True")

    def test_double_function(self):
        t = parse_string(double_function, True).get_tree()
        function_call = t[0][1][0][0]
        self.assertEqual(function_call.node_type, "CALL")
        self.assertEqual(function_call.value, "foo")

    @php_t
    def test_scope(self, php_node):
        """Scopes
        <?php
        $a = 1;
        function b()
        {
            echo $a;
        }
        test();
        """
        var_a = php_node.get("STATEMENT").get("EXPRESSION").get("ASSIGNMENT")[1]
        self.assertEqual(var_a.node_type, "GLOBALVAR")
        block_node = php_node.get("FUNCTION").get("BLOCK")
        self.assertEcho(block_node[0], "a", node_type="VAR")

    def test_scopes_global(self):
        php_node = parse_string(scope_globalled).get_tree()[0]
        function_node = php_node[2]
        self.assertEqual(function_node.value, "sum")
        # We don't actually output the global node anywhere
        assignment_expression = function_node.get("BLOCK")[1].get("EXPRESSION")
        self.assertEqual(assignment_expression[0].node_type, "ASSIGNMENT")
        self.assertEqual(assignment_expression[0][0].value, "a")
        self.assertEqual(assignment_expression[0][0].node_type, "GLOBALVAR")

    @php_t
    def test_comments(self, php_node):
        """Testing comments
        <?php
        // Out of band comment
        $a = 1; //In band comment
        /* Big groupy comment
        */
        $a = 2; /* groupy comment on line */ $b=3;

        """
        print_tree(php_node)
        comment_node = php_node[0]
        self.assertEqual(comment_node.comments[0].value, " Out of band comment")
        comment_node2 = php_node[2].comments[0]
        self.assertEqual(comment_node2.value, "In band comment")
        comment_node3 = php_node[3].comments[0]
        self.assertEqual(comment_node3.value, "/* Big groupy comment")
        comment_node4 = php_node[3].comments[1]
        self.assertEqual(comment_node4.value[-2:], "*/")
        comment_node5 = php_node[4].comments[0]
        self.assertEqual(comment_node5.value, "/* groupy comment on line */")

    def test_new(self):
        php_node = parse_string(new_eg, True).get_tree()[0]
        statement_1, statement_2 = php_node.children
        assignment = statement_1.get("EXPRESSION").get("ASSIGNMENT")
        new = assignment[0]
        self.assertEqual(new.node_type, "NEW")
        call = new[0]
        self.assertEqual(call.node_type, "CALL")
        self.assertEqual(call.value, "B")

    @php_t
    def test_multiline_call(self, php_node):
        """ Multiline call to a function
        <?php
        F(  $a,
            $b,

            $c
        );
        """
        fcall = php_node.get("STATEMENT").get("EXPRESSION")[0]
        self.assertEqual(fcall.node_type, "CALL")
        self.assertEqual(fcall.value, "F")
        self.assertEqual(fcall.get("ARGSLIST")[0][0].value, "a")

    def test_multiline_call2(self):
        php_node = parse_string(multiline_call2, True).get_tree()[0]
        fcall = php_node[0][0][0]
        self.assertEqual(fcall.node_type, "CALL")
        self.assertEqual(fcall.value, "F")
        self.assertEqual(fcall.get("ARGSLIST")[0][0].value, "a")

    @php_t
    def test_nested(self, php_node):
        """Nested brackets
        <?php
        require_once(dirname(1) . '/lib/setup.php');
        """
        require_once = php_node.get("STATEMENT").get("EXPRESSION").get("CALL")
        dirname = require_once.get("ARGSLIST").get("EXPRESSION").get("OPERATOR").get("CALL")
        self.assertEqual(dirname.node_type, "CALL")
        self.assertEqual(dirname.get("ARGSLIST").get("EXPRESSION").get("INT").value, 1)

    def test_complex_if(self):
        php_node = parse_string(complex_if).get_tree()[0]

    def test_multi_space_comment(self):
        php_node = parse_string(multi_space_comment).get_tree()[0]

    @php_t
    def test_arith(self, php_node):
        """ Nested arithmitic
        <?php
        1 + 2 * 3 ^ 4 / 5 + 6;
        //((1 + (2 * 3)) ^ ((4 / 5) + 6))
        //    a    b     c     d    e
        """
        print_tree(php_node)
        ex = php_node.get("STATEMENT").get("EXPRESSION")
        c = ex[0]
        self.assertEqual(c.value, "^")
        e = c[0]
        self.assertEqual(e.value, "+")
        a = c[1]
        self.assertEqual(a.value, "+")
        b = a[0]
        self.assertEqual(b.value, "*")
        i = b[0]
        self.assertEqual(i.value, 3)

        self.assertEqual(self.compiler.expression_compile(ex), "((1 + (2 * 3)) ^ ((4 / 5) + 6))")

    @php_t
    def test_array_lookups(self, php_node):
        """ Simple array lookup.
        <?php
        $a['a'] = "maybe";
        """
        maybe_statement = php_node[0]
        assign_1 = maybe_statement.get("EXPRESSION").get("ASSIGNMENT")
        rhs, lhs = tuple(assign_1.children)
        self.assertEqual(lhs.node_type, "INDEX")
        var_a = lhs[1]
        self.assertEqual(var_a.node_type, "GLOBALVAR")
        self.assertEqual(var_a.value, "a")
        index_lookup = lhs[0]
        self.assertEqual(index_lookup[0].node_type, "STRING")
        self.assertEqual(index_lookup[0].value, "a")

    @php_t
    def test_array_lookups2(self, php_node):
        """ Array lookup followed by index
        <?php
        $c->d[0];
        $e = f()['g'];
        """
        ex = php_node.get("STATEMENT").get("EXPRESSION")
        array_index = ex[0]
        self.assertEqual(array_index.node_type, "INDEX")
        attr = array_index[1]
        self.assertEqual(attr.node_type, "ATTR")
        ex2 = php_node[1].get("EXPRESSION")
        assign = ex2[0]
        self.assertEqual(assign.node_type, "ASSIGNMENT")
        rhs = assign[0]
        index_node = rhs
        self.assertEqual(index_node.node_type, "INDEX")
        indexee = index_node[1]
        indexer = index_node[0]
        self.assertEqual(indexee.node_type, "CALL")
        self.assertEqual(indexer[0].node_type, "STRING")

    @php_t
    def test_statement_comment(self, php_node):
        """ Comments straight in a statement
        <?php
        if ($a) {
            // comment b
            if (!defined('c')) {
                $e;
            }
        }
        """
        if_s = php_node[0]
        comment_s = if_s[1][0]
        self.assertEqual(comment_s.comments[0].node_type, "COMMENTLINE")

    def test_dynamic_class_creation(self):
        php_node = parse_string(dynamic_class_creation, False).get_tree()[0]

    def test_casting(self):
        php_node = parse_string(casting, False).get_tree()[0]

    @php_t
    def test_assign_in_if(self, php_node):
        """ Assign in an if statment
        <?php
        if ($a = 3) {
        }
        """
        print_tree(php_node)
        transform_php(php_node)
        print_tree(php_node)
        assign_statement = php_node[0]
        if_statement = php_node[1]
        self.assertEqual(assign_statement.get("EXPRESSION").get("ASSIGNMENT")[1].value, "a")
        self.assertEqual(if_statement.get("EXPRESSIONGROUP").get("EXPRESSION").get("GLOBALVAR").value, "a")
        self.assertEqual(len(if_statement.get("EXPRESSIONGROUP").children), 1)

    def test_assign_in_if2(self):
        php_node = parse_string(assign_in_if2).get_tree()[0]
        print_tree(php_node)
        transform_php(php_node)
        print_tree(php_node)
        #self.assertTrue(False)

    @php_t
    def test_try_catch(self, php_node):
        """ Basic try catch
        <?php
        try {
            1;
        } catch (Exception $e) {
            0;
        }
        """
        print_tree(php_node)
        try_node = php_node[0]
        self.assertEqual(try_node.node_type, "TRY")
        self.assertEqual(try_node[0].node_type, "BLOCK")
        self.assertEqual(try_node[1].node_type, "CATCH")
        self.assertEqual(try_node[1][0].node_type, "EXCEPTION")
        self.assertEqual(try_node[1][1].node_type, "BLOCK")


"""
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

    def test_array_lookups(self):
        print(parse_and_compile(array_lookups, debug=True))
"""


if __name__ == "__main__":
    unittest.main()
