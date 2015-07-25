import os
from wsgiref.simple_server import make_server
import sys
import importlib.machinery

from php2py.php import _app_ as app

base_file = sys.argv[1]

abspath = os.path.abspath(base_file)
main_index = importlib.machinery.SourceFileLoader(abspath, abspath).load_module()

# TODO: this should probably just be abspath
app.init_http(main_index.body, os.path.abspath(os.path.dirname(__file__)))

httpd = make_server('', 8000, app)
print("Serving HTTP on port 8000...")

# Respond to requests until process is killed
httpd.serve_forever()

# Alternative: serve one request, then exit
httpd.handle_request()
