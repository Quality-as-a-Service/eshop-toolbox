import logging
import time
import copy
import re
import random
import requests
import pandas as pd
from typing import List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger('main')
logging.basicConfig(level=logging.INFO)

DO_SLEEP = False

MULTIPLE_JOIN_EL = '|'
ESHOP_URL_TEMPLATE = 'https://www.millers-oils.cz/shop/page/{page}?product_count=30'
ESHOP_IMAGE_URL_RE = re.compile(r'-\d+x\d+\.')
ESHOP_PRICE_RE = re.compile(r'[^\d\,]')

INDEX = 'product_sku'
COLUMNS_MAP = [
    ['url', 'url'],
    ['product_sku', 'product_sku'],
    ['product_sales', 'product_sales'],
    ['product_override_price', 'product_override_price'],
    ['additional_info', 'dalsi_info'],
    ['profile', 'vykonovy_profil'],
    ['characteristic', 'charakteristika'],
    ['image_url_list', 'file_url'],
    ['related_product_sku_list', 'related_products'],
    ['product_desc', 'product_desc'],
    ['type_list', 'typ'],
    ['category_list', 'category_name'],
    ['product_s_desc', 'product_s_desc'],
    ['volume_list', 'objem'],
    ['product_name', 'product_name'],
]
COLUMNS = [col for _, col in COLUMNS_MAP]


class Product:
    soup: BeautifulSoup

    product_sku: int
    product_name: str
    product_s_desc: Optional[str] = None
    product_desc: Optional[str] = None

    product_override_price: Optional[float] = None
    product_sales: float

    type_list: List[str]
    volume_list: List[str]
    profile: str
    characteristic: str
    additional_info: Optional[str]

    category_list: List[str]

    image_url_list: List[str]

    related_product_url_list: List[int]

    def __init__(self, url, soup: BeautifulSoup):
        self.url = url
        self.soup = soup

        self.product_sku = self._parse_sku()
        self.product_name = self._parse_name()
        self.product_s_desc = self._parse_short_desc()
        self.product_desc = self._parse_desc()

        # > Keep order!
        self.product_override_price = self._prase_product_override_price()
        self.product_sales = self._prase_product_sales()
        # < Keep order!

        self.type_list = self._parse_type()
        self.volume_list = self._parse_volume()
        self.profile = self._parse_profile()
        self.characteristic = self._parse_characteristic()
        self.additional_info = self._parse_additional_info()

        self.category_list = self._parse_category_name()
        self.image_url_list = self._parse_image_url_list()
        self.related_product_url_list = self._parse_related_product_url_list()
        self.related_product_sku_list = []

    def assign_related_product_sku_list(self, rp_sku: list):
        self.related_product_sku_list = rp_sku

    def _parse_sku(self):
        try:
            return int(self.soup.css.select('.sku')[0].text)
        except (ValueError, IndexError) as exc:
            raise RuntimeError('SKU not found') from exc

    def _parse_name(self):
        try:
            return self.soup.css.select('.product_title')[0].text
        except IndexError as exc:
            raise RuntimeError('Product name not found') from exc

    def _parse_short_desc(self):
        desc = self.soup.css.select('.description')
        if len(desc):
            el = self._remove_attrs(desc[0])
            return str(el)

    def _parse_desc(self):
        desc = self.soup.css.select('#tab-description')
        if len(desc):
            el = self._remove_attrs(desc[0])
            return str(el)

    def _prase_product_override_price(self):
        try:
            price = self.soup.css.select('p.price del .amount')[0].text
        except IndexError:
            return None

        price = re.sub(ESHOP_PRICE_RE, '', price).replace(',', '.')
        try:
            price = float(price)
        except ValueError:
            return None

        return price

    def _prase_product_sales(self):
        try:
            price = self.soup.css.select('p.price ins .amount')[0].text
        except IndexError as exc:
            if self.product_override_price is None:
                try:
                    price = self.soup.css.select('p.price .amount')[0].text
                except IndexError as exc:
                    print(self.soup.css.select('p.price .amount'), 2)
                    raise RuntimeError('Product price not found') from exc
            else:
                print(self.soup.css.select('p.price .amount'), 1)
                raise RuntimeError('Product price not found') from exc

        price = re.sub(ESHOP_PRICE_RE, '', price).replace(',', '.')
        try:
            price = float(price)
        except ValueError as exc:
            raise RuntimeError('Product price not found') from exc

        return price

    def _parse_type(self):
        return [el.text for el in self.soup.css.select('.tagged_as a')]

    def _parse_category_name(self):
        return [el.text for el in self.soup.css.select('.posted_in a')]

    def _parse_volume(self):
        return [el.text for el in self.soup.css.select('.description > span.label')]

    def _parse_profile(self):
        uid = None
        tabs = self.soup.css.select('.woocommerce-tabs > ul > li')
        for tab in tabs:
            if 'VÝKONOVÝ PROFIL' in tab.text:
                uid = tab.get('aria-controls')
        if uid is None:
            logger.warning(f'[{self.product_sku}] VÝKONOVÝ PROFIL not found')
            return ''
        content = self.soup.css.select(f'div#{uid}')
        if len(content):
            el = self._remove_attrs(content[0])
            return str(el)

    def _parse_characteristic(self):
        uid = None
        tabs = self.soup.css.select('.woocommerce-tabs > ul > li')
        for tab in tabs:
            if 'CHARAKTERISTIKA' in tab.text:
                uid = tab.get('aria-controls')
        if uid is None:
            logger.warning(f'[{self.product_sku}] CHARAKTERISTIKA not found')
            return ''
        content = self.soup.css.select(f'div#{uid}')
        if len(content):
            el = self._remove_attrs(content[0])
            return str(el)

    def _parse_additional_info(self):
        uid = None
        tabs = self.soup.css.select('.woocommerce-tabs > ul > li')
        for tab in tabs:
            if 'Další informace' in tab.text:
                uid = tab.get('aria-controls')
        if uid is None:
            logger.warning(f'[{self.product_sku}] Další informace not found')
            return ''
        content = self.soup.css.select(f'div#{uid}')
        if len(content):
            el = self._remove_attrs(content[0])
            return str(el)

    def _parse_image_url_list(self):
        imgs = [el.get('src') for el in self.soup.css.select(
            '.thumbnails .attachment-shop_thumbnail')]
        imgs = [re.sub(ESHOP_IMAGE_URL_RE, '.', img) for img in imgs]
        return imgs

    def _parse_related_product_url_list(self):
        return [el.get('href') for el in self.soup.css.select('.product-row .product > div > a')]

    def _remove_attrs(self, el, deep=True):
        el = copy.copy(el)
        keys = list(el.attrs.keys())
        for attr in keys:
            del el[attr]

        if deep:
            tag_list = el.findAll(lambda tag: len(tag.attrs) > 0)
            for t in tag_list:
                self._remove_attrs(t, False)
        return el


class Assembler:
    def __init__(self, index, columns, mapping):
        self._table = pd.DataFrame(columns=columns, index=[index]).dropna()
        self._products_url_map = {}

        self._index = index
        self._mapping = mapping

    @property
    def table(self):
        return self._table

    @property
    def products(self):
        return self._products_url_map.values()

    def collect(self, product: Product):
        self._products_url_map[product.url] = product

    def _resolve_related_products(self, product: Product):
        related_sku_list = []
        for rp_url in product.related_product_url_list:
            try:
                rp = self._products_url_map[rp_url]
            except KeyError:
                logger.warning(
                    f'Failed to resolve related product with url: {rp_url} for {product.product_sku}')
            else:
                related_sku_list.append(rp.product_sku)
        return related_sku_list

    def add(self, product: Product):
        product_dict = {}

        rp_sku = self._resolve_related_products(product)
        product.assign_related_product_sku_list(rp_sku)

        for prop, col in self._mapping:
            value = getattr(product, prop)
            if value is not None:
                if isinstance(value, list):
                    value = [str(v).strip() for v in value]
                    value = MULTIPLE_JOIN_EL.join(value)
                value = str(value).strip()
                product_dict[col] = value
            else:
                logger.info(f'[{product.product_sku}] {prop} not found')
        row = pd.DataFrame(product_dict, index=[self._index])
        self._table = pd.concat([self._table, row], ignore_index=True)


def product_url_generator(template: str):
    page = 1
    while True:
        content_url = template.format(page=page)

        logger.info(f'Fetching content: {content_url}')
        response = requests.get(content_url)
        try:
            assert response.status_code == 200
        except AssertionError as exc:
            logger.info(f'Fetch failed, stop iteration')
            raise StopIteration() from exc
        else:
            logger.info(f'Fetch success')
            page += 1
            if DO_SLEEP:
                cooldown = random.randint(5, 20)
                logger.info(f'Sleep: {cooldown}')
                time.sleep(cooldown)
        soup = BeautifulSoup(response.content, 'html.parser')
        for url in [a.get('href') for a in soup.css.select('.product > div > a')]:
            yield url


def product_processing(url: str) -> Product:
    response = requests.get(url)
    try:
        assert response.status_code == 200
    except AssertionError as exc:
        raise RuntimeError(f'Product fetch failed: {url}') from exc

    soup = BeautifulSoup(response.content, features='html.parser')
    return Product(url, soup)


LIMIT = None
if __name__ == '__main__':
    count = 0
    assembler = Assembler(INDEX, COLUMNS, COLUMNS_MAP)
    for url in product_url_generator(ESHOP_URL_TEMPLATE):
        if LIMIT is not None and count == LIMIT:
            break
        count += 1
        try:
            product = product_processing(url)
        except RuntimeError as exc:
            logger.error(url)
            logger.exception(exc)
            continue
        assembler.collect(product)
    for product in assembler.products:
        assembler.add(product)
    assembler.table.to_csv('out.csv')
