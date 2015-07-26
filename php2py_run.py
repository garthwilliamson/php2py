import sys

from php2py.php import ConsoleApp

config = {
    "root": sys.argv[1]
}

app = ConsoleApp(config)
app.run()
