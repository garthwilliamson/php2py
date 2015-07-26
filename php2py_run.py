import sys

from php2py.php import ConsoleApp

config = {
    "root": "",
    "code_root": "./",
    "script_name": sys.argv[1],
}

app = ConsoleApp(config)
app.run()
