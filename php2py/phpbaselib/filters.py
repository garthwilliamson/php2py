import urllib.parse
""" Here follows a whole heap of filters

Each filter takes two arguments - the input and the options.

"""

def filter_sanitize_url(url, options):
    return urllib.parse.quote_plus(url)
