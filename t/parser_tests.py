from __future__ import unicode_literals

from tlib.php2pytests import *
from clib.parsetree import print_tree

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


complex_if = """<?php
if (!empty($CFG->a) && ($CFG->a == CONS) && optional_param('b', 1, PARAM_BOOL) === 0) {
    die;
}
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


"""
def compiled_class(f):
    Wraps a function to parse and compile a class definition given as a doc string

    Runs the class as a python object and supplies the parsetree as the first arg
    and the class as the second it as the second argument of the function.


    @wraps(f)
    def wrapper(self, *args, **kwargs):
        tree = parse_string(f.__doc__).get_tree()
        compiled = self.compiler.compile(tree)
        f(self, tree["PHP"]["CLASS"], compiled, *args, **kwargs)

    return wrapper

    """


class ParserTests(Php2PyTestCase):
    """ Test the parser by itself

    """
    def test_html_direct(self):
        parsed = parse_string(html)
        res = parsed.get_tree()
        self.assertEqual(res.kind, "ROOT")
        self.assertEqual(res[0].kind, "HTML")
        self.assertEqual(res[0].value, html)

    @parse_t
    def test_hello(self, root_node):
        """ Simple echo
        <?php echo "Hello World"; ?>
        """
        php = root_node[1]
        self.assertEqual(php.kind, "PHP")
        self.assertEcho(php[0], "Hello World")

    @parse_t
    def test_hello_brackets(self, root_node):
        """ Test that echos get brackets now
        <? echo("Hello World!") ?>
        """
        self.assertEcho(root_node["PHP"][0], "Hello World!")

    @parse_t
    def test_hello_no_end(self, root_node):
        """ Echo without an end tag
        <?php echo "Hello World";
        """
        self.assertEcho(root_node.match("PHP/STATEMENT"), "Hello World")

    @parse_t
    def test_string_with_quote(self, root_node):
        """ String with an escaped quote in it
        <?php "quoted\\"string";
        """
        self.assertContainsNode(root_node, "PHP/STATEMENT/EXPRESSION/STRING")

    @parse_t
    def test_complex_echo(self, root_node):
        """ A complex echo statement
        <?php
        echo "$asdfasdfa(<a hreaaaaaaaf=\\"b/a.d?aaaaae=f&g;h=".i()."\\">aaaaaaaaaaaaaa". j('afasdfsdfsdk') .'</a>)';
        """
        self.assertContainsNode(root_node, "PHP/STATEMENT/EXPRESSION/CALLSPECIAL|echo")

    @parse_t
    def test_assign(self, root_node):
        """Simple assignment
        <?php $a = 1; ?>
        """
        # print_tree(root_node)
        statement = root_node.get("PHP")[0]
        self.assertEqual(statement.kind, "STATEMENT")
        expression = statement[0]
        self.assertEqual(expression.kind, "EXPRESSION")
        assignment = expression[0]
        self.assertEqual(assignment.value, "=")
        to_assign = assignment[0]
        self.assertEqual(to_assign.kind, "INT")
        assign_to = assignment[1]
        self.assertEqual(assign_to.value, "a")

    @parse_t
    def test_while(self, root_node):
        """ Simple while loop
        <?php
        while($a == $b) {
            echo "Hi there";
            $b++;
        }
        echo "world"
        """
        while_node = root_node.get("PHP")[0]
        self.assertEqual(while_node.kind, "WHILE")
        expr_node = while_node["EXPRESSIONGROUP"]["EXPRESSION"]
        self.assertContainsNode(expr_node, "OPERATOR2")
        echo_world_statement = root_node.get("PHP")[1]
        self.assertEcho(echo_world_statement, "world")

    @parse_t
    def test_while_html(self, root_node):
        """ Simple while loop
        <?php
        $a = 0;
        while($a < 10) {
            ?>lol<?php
            $a++;
        }
        """
        while_node = root_node["PHP"]["WHILE"]
        while_block = while_node["BLOCK"]
        self.assertContainsNode(while_block, "HTML|lol")
        self.assertContainsNode(while_block, "STATEMENT/EXPRESSION/OPERATOR1|++")

    @parse_t
    def test_function_simple(self, root_node):
        """Simple function
        <?php
        function foo() {
            return 0;
        }"""
        function_node = root_node.match("PHP/FUNCTION|foo")
        arg_list = function_node[0]
        self.assertEqual(len(arg_list.children), 0)
        function_block = function_node[1]
        self.assertEqual(function_block.kind, "BLOCK")
        return_statement = function_block[0]
        self.assertEqual(return_statement.kind, "RETURN")
        return_expression = return_statement.get("EXPRESSION")
        self.assertContainsNode(return_expression, "INT|0")

    def test_function(self):
        parsed = parse_string(function)
        res = parsed.get_tree()
        root_node = res[0]
        function_node = root_node[0]
        self.assertEqual(function_node.value, "foo")
        function_args = function_node[0]
        self.assertEqual(function_args[0][0].value, "arg1")
        function_body = function_node[1]
        return_statement = function_body[1]
        self.assertEqual(return_statement.kind, "RETURN")
        self.assertEqual(return_statement.get("EXPRESSION").get("OPERATOR2")[0].value, "True")

    def test_double_function(self):
        t = parse_string(double_function, True).get_tree()
        function_call = t[0][1][0][0]
        self.assertEqual(function_call.kind, "CALL")
        self.assertEqual(function_call[1].value, "foo")

    @parse_t
    def test_blank_lines(self, root_node):
        """ Php block with a blank line in it
        <?php
        echo("Before blank");

        echo("After blank");
        """
        print_tree(root_node)
        php_node = root_node.get("PHP")
        self.assertEcho(php_node[0], "Before blank")
        self.assertEqual("NOOP", php_node[1].kind)

    @parse_t
    def test_scope(self, root_node):
        """Scopes
        <?php
        $a = 1;
        function b()
        {
            echo $a;
            $_GET;
        }
        test();
        """
        var_a = root_node.match("PHP/STATEMENT/EXPRESSION/ASSIGNMENT")[1]
        self.assertEqual(var_a.kind, "GLOBALVAR")
        block_node = root_node.match("PHP/FUNCTION/BLOCK")
        self.assertEcho(block_node[0], "a", kind="VAR")
        self.assertContainsNode(block_node[1], "EXPRESSION/GLOBALVAR|_GET")

    def test_scopes_global(self):
        root_node = parse_string(scope_globalled).get_tree()[0]
        function_node = root_node[2]
        self.assertEqual(function_node.value, "sum")
        # We don't actually output the global node anywhere
        assignment_expression = function_node.get("BLOCK")[1].get("EXPRESSION")
        self.assertEqual(assignment_expression[0].kind, "ASSIGNMENT")
        self.assertEqual(assignment_expression[0][0].value, "a")
        self.assertEqual(assignment_expression[0][0].kind, "GLOBALVAR")

    @parse_t
    def test_comments(self, root_node):
        """Testing comments
        <?php
        // Out of band comment
        $a = 1; //In band comment
        /* Big groupy comment
        */
        $a = 2; /* groupy comment on line */ $b=3;

        """
        print_tree(root_node)
        php_node = root_node.get("PHP")
        comment_node = php_node[0]["COMMENTLINE"]
        self.assertEqual(comment_node.value, " Out of band comment")
        comment_node2 = php_node[1]["COMMENTLINE"]
        self.assertEqual(comment_node2.value, "In band comment")
        comment_node3 = php_node[2]["COMMENTBLOCK"]
        self.assertEqual(comment_node3.value, "Big groupy comment")
        comment_node4 = php_node[2][1]
        self.assertEqual(comment_node4.value, "")
        comment_node5 = php_node[4]["COMMENTBLOCK"]
        self.assertEqual(comment_node5.value, "groupy comment on line")

    @parse_t
    def test_new(self, root_node):
        """ Test creation of new options
        <?php
        $a = new B();
        $c = new D("e", "f");
        """
        print_tree(root_node)
        statement_1 = root_node["PHP"][0]
        assignment = statement_1.get("EXPRESSION").get("ASSIGNMENT")
        new = assignment[0]
        self.assertEqual(new.kind, "NEW")
        call = new[0]
        self.assertEqual(call.kind, "CALL")
        self.assertEqual(call["CONSTANT"].value, "B")

    @parse_t
    def test_multiline_call(self, root_node):
        """ Multiline call to a function
        <?php
        F(  $a,
            $b,

            $c
        );
        """
        fcall = root_node.match("PHP/STATEMENT/EXPRESSION")[0]
        self.assertEqual(fcall.kind, "CALL")
        self.assertEqual(fcall["CONSTANT"].value, "F")
        self.assertEqual(fcall.get("EXPRESSIONGROUP")[0][0].value, "a")

    @parse_t
    def test_multiline_call2(self, root_node):
        """ Multi line call with comments
        <?php
        F(  $a,
            $b,
        //Commenting is horrid
            $c
        );
        """
        fcall = root_node.get("PHP")[0][0][0]
        self.assertEqual(fcall.kind, "CALL")
        self.assertEqual(fcall[1].value, "F")
        self.assertEqual(fcall[0][0][0].value, "a")

    @parse_t
    def test_multiline_call3(self, root_node):
        """ Multi line call with an extra comma (empty expression)
        <?php
        c(
            'd'=> '',  // comment
        );
        """
        fcall = root_node.match("PHP/STATEMENT/EXPRESSION")[0]
        self.assertEqual(fcall.kind, "CALL")
        self.assertEqual(fcall[1].value, "c")
        self.assertEqual(fcall[0].get("EXPRESSION")[0].kind, "OPERATOR2")
        self.assertEqual(fcall[0].get("EXPRESSION")[0][1].value, "d")

    @parse_t
    def test_nested(self, root_node):
        """Nested brackets
        <?php
        require_once(dirname(1) . '/lib/setup.php');
        """
        require_once = root_node.match("PHP/STATEMENT/EXPRESSION/CALLSPECIAL")
        dirname = require_once.match("ARGSLIST/EXPRESSION/OPERATOR2/CALL")
        self.assertEqual(dirname.kind, "CALL")
        self.assertContainsNode(dirname, "EXPRESSIONGROUP/EXPRESSION/INT|1")

    @parse_t
    def test_ident_starts_new(self, root_node):
        """ If with a comment attached and an ident starting with new
        <?php
        if ($SITE->newsitems) { // Print forums only when needed
        }
        """
        # print_tree(root_node)

    @parse_t
    def test_else(self, root_node):
        """ If with else
        <?php
        if (1) {
            echo "1"
        } else {
            echo "2"
        }
        """
        # print_tree(root_node)
        if_s = root_node.match("PHP/IF")
        eg = if_s[0]
        self.assertEqual(eg.get("EXPRESSION")[0].kind, "INT")
        if_b = if_s[1]
        self.assertEqual(if_b.kind, "BLOCK")
        self.assertEcho(if_b.get("STATEMENT"), "1")
        else_s = if_s[2]
        self.assertEqual(else_s.kind, "ELSE")

    """
    def test_multi_space_comment(self):
        root_node = parse_string(multi_space_comment).get_tree()[0]
    """

    @parse_t
    def test_arith(self, root_node):
        """ Nested arithmitic
        <?php
        1 + 2 * 3 ^ 4 / 5 + 6;
        //((1 + (2 * 3)) ^ ((4 / 5) + 6))
        //    a    b     cc    d    e
        """
        # print_tree(root_node)
        ex = root_node.match("PHP/STATEMENT/EXPRESSION")
        cc = ex[0]
        self.assertEqual(cc.value, "^")
        e = cc[0]
        self.assertEqual(e.value, "+")
        a = cc[1]
        self.assertEqual(a.value, "+")
        b = a[0]
        self.assertEqual(b.value, "*")
        i = b[0]
        self.assertEqual(i.value, 3)

    @parse_t
    def test_array_lookups(self, root_node):
        """ Simple array lookup.
        <?php
        $a['a'] = "maybe";
        """
        assign_1 = root_node.match("PHP/STATEMENT/EXPRESSION/ASSIGNMENT")
        rhs, lhs = tuple(assign_1.children)
        self.assertEqual(lhs.kind, "INDEX")
        var_a = lhs[1]
        self.assertEqual(var_a.kind, "GLOBALVAR")
        self.assertEqual(var_a.value, "a")
        index_lookup = lhs[0]
        self.assertEqual(index_lookup[0].kind, "STRING")
        self.assertEqual(index_lookup[0].value, "a")

    @parse_t
    def test_array_lookups2(self, root_node):
        """ Array lookup followed by index
        <?php
        $c->d[0];
        $e = f()['g'];
        """
        ex1, ex2 = root_node.match("PHP/STATEMENT*/EXPRESSION")
        array_index = ex1[0]
        self.assertEqual(array_index.kind, "INDEX")
        attr = array_index[1]
        self.assertEqual(attr.kind, "ATTR")
        assign = ex2[0]
        self.assertEqual(assign.kind, "ASSIGNMENT")
        rhs = assign[0]
        index_node = rhs
        self.assertEqual(index_node.kind, "INDEX")
        indexee = index_node[1]
        indexer = index_node[0]
        self.assertEqual(indexee.kind, "CALL")
        self.assertEqual(indexer[0].kind, "STRING")

    @parse_t
    def test_statement_comment(self, root_node):
        """ Comments straight in a statement
        <?php
        if ($a) {
            // comment b
            if (!defined("c")) {
                $e;
            }
        }
        """
        if_s = root_node.get("PHP")[0]
        comment_s = if_s[1][0]
        self.assertEqual(comment_s[0].kind, "COMMENTLINE")

    def test_dynamic_class_creation(self):
        parse_string(dynamic_class_creation, False).get_tree()

    def test_casting(self):
        parse_string(casting, False).get_tree()

    @parse_t
    def test_try_catch(self, root_node):
        """ Basic try catch
        <?php
        try {
            1;
        } catch (Exception $e) {
            0;
        }
        """
        # print_tree(root_node)
        try_node = root_node.get("PHP")[0]
        print_tree(try_node)
        self.assertEqual(try_node.kind, "TRY")
        self.assertEqual(try_node[0].kind, "BLOCK")
        self.assertEqual(try_node[1].kind, "CATCH")
        self.assertContainsNode(try_node, "CATCH/AS/GLOBALVAR|e")
        self.assertContainsNode(try_node, "CATCH/BLOCK/STATEMENT/EXPRESSION/INT|0")

    @parse_t
    def test_one_line_if(self, root_node):
        """ If on one line
        <?php
        if (1) echo "hi";
        """
        if_node = root_node["PHP"]["IF"]
        self.assertContainsNode(if_node, "EXPRESSIONGROUP/EXPRESSION/INT|1")
        self.assertContainsNode(if_node, "STATEMENT/EXPRESSION/CALLSPECIAL|echo")

    @parse_t
    def test_class_simple(self, root_node):
        """ A simple class with no content
        <?php
        class TestClass
        {
            $a;
        }
        """
        # print_tree(root_node)
        class_node = root_node.get("PHP")[0]
        self.assertEqual(class_node.kind, "CLASS")
        self.assertEqual(class_node[0].kind, "BLOCK")

    @parse_t
    def test_class_with_method(self, root_node):
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
        print_tree(root_node)
        class_node = root_node.get("PHP")[0]
        self.assertEqual(class_node.kind, "CLASS")
        classmethod_node = class_node.get("BLOCK").get("CLASSMETHOD")
        self.assertEqual(classmethod_node.value, "blah")
        self.assertEqual(classmethod_node.get("VISIBILITY").value, "public")

        method_node = class_node.get("BLOCK").get("METHOD")
        self.assertEqual(method_node.value, "baz")
        self.assertEqual(method_node.get("VISIBILITY").value, "private")

    @parse_t
    def test_class_extends(self, root_node):
        """ A class with an extends keyword
        <?php
        class TestClass extends TestBaseClass{
            $a;
        }
        """
        print_tree(root_node)
        class_node = root_node["PHP"]["CLASS"]
        self.assertContainsNode(class_node, "EXTENDS")

    @parse_t
    def test_class_attributes(self, root_node):
        """ A class with some private attributes
        <?php
        class TestClass {
            private $a = 1;
        }
        """
        print_tree(root_node)
        class_node = root_node["PHP"]["CLASS"]
        self.assertContainsNode(class_node, "BLOCK/STATEMENT/EXPRESSION/ASSIGNMENT/VAR")

    @parse_t
    def test_ternary(self, root_node):
        """ Another version of isset
        <?php
        $f ? $u[1] : $n;
        """
        print_tree(root_node)
        tern = root_node.match("PHP/STATEMENT/EXPRESSION/OPERATOR3|?")
        self.assertContainsNode(tern, "EXPRESSION/INDEX/GLOBALVAR|u")
        self.assertContainsNode(tern, "GLOBALVAR|f")

    @parse_t
    def test_attr_method_result(self, root_node):
        """ Methods returning objects with attributes
        <?php
        $a->b()->c;
        """
        c_lookup = root_node.match("PHP/STATEMENT/EXPRESSION/ATTR|->")
        self.assertContainsNode(c_lookup, "CALL/ATTR|->/GLOBALVAR|a")


if __name__ == "__main__":
    unittest.main()
