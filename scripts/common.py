from copy import copy

from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup


def remove_query_params(url):
    parsed_url = urlparse(url)
    # Use _replace method to create a modified version of the parsed URL without query parameters
    modified_url = parsed_url._replace(query='')
    return urlunparse(modified_url)


def remove_attrs(el):
    el = copy(el)
    el.attrs = {}
    for tag in el.find_all(True):
        tag.attrs = {}
    return el
