from wsgiref.simple_server import make_server
import sys
import json

from php2py.php import WsgiApp

# TODO: Check if json file or php file, deal appropriately
config = json.load(open(sys.argv[1]))

app = WsgiApp(config)

httpd = make_server('', 8000, app)
print("Serving HTTP on port 8000...")

# Respond to requests until process is killed
httpd.serve_forever()

# Alternative: serve one request, then exit
httpd.handle_request()
