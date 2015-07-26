import urllib.parse
import string
""" Here follows a whole heap of filters

Each filter takes two arguments - the input and the options.

"""
SANATIZE_URL_SAFE = """$-_.+!*'(),{}|\\^~[]`<>#%";/?:@&=.""" + string.ascii_letters + string.digits
def filter_sanitize_url(url, options):
    return "".join([c for c in url if c in SANATIZE_URL_SAFE])
