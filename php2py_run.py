import sys

from php2py.php import ConsoleApp

base_file = sys.argv[1]
app = ConsoleApp(base_file)
app.run()
