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


class Product:
    url: str
    soup: BeautifulSoup

    def __init__(self, url, soup: BeautifulSoup):
        self.url = url
        self.soup = soup


class Assembler:
    MULTIPLE_JOIN_EL = "|"

    INDEX = "id"
    COLUMNS = [
        "id"
    ]

    def __init__(self):
        self._products_url_map = {}

    def collect(self, product: Product):
        self._products_url_map[product.url] = product

    def _finalize_value(self, value):
        if isinstance(value, list):
            value = [str(v).strip() for v in value]
            value = self.MULTIPLE_JOIN_EL.join(value)
        value = str(value).strip()
        return value
