import logging
import time
import copy
import re
import random
import requests
import json
import pandas as pd
from typing import List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger('utils.millers-oil')
logging.basicConfig(level=logging.INFO)

DO_SLEEP = False

MULTIPLE_JOIN_EL = '|'
ESHOP_NAME = 'millers_oils_cz'
ESHOP_URL_TEMPLATE = 'https://www.millers-oils.cz/shop/page/{page}?product_count=30'
ESHOP_IMAGE_URL_RE = re.compile(r'-\d+x\d+\.')
ESHOP_PRICE_RE = re.compile(r'[^\d\,]')

INDEX = 'product_sku'
VAR_PARENT = 'product_parent_sku'
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
COLUMNS.append(VAR_PARENT)
VAR_PROPS = ['product_sku', 'product_sales',
             'product_override_price', 'volume_list']


class Product:
    soup: BeautifulSoup

    product_sku: int
    product_name: str
    product_s_desc: Optional[str] = None
    product_desc: Optional[str] = None

    product_override_price: Optional[float] = None
    product_sales: Optional[float] = None

    type_list: List[str]
    volume_list: Optional[List[str]]
    profile: str
    characteristic: str
    additional_info: Optional[str]

    category_list: List[str]

    image_url_list: List[str]

    related_product_url_list: List[int]

    class Variant:
        product_sku: int
        product_override_price: Optional[float] = None
        product_sales: float
        volume_list: List[str]

    variants_data: Optional[List[Variant]] = None

    def __init__(self, url, soup: BeautifulSoup):
        self.url = url
        self.soup = soup

        self.variants_data = self._parse_variants_data()

        self.product_sku = self._parse_sku()
        self.product_name = self._parse_name()
        self.product_s_desc = self._parse_short_desc()
        self.product_desc = self._parse_desc()

        if self.variants_data is None:
            self.volume_list = self._parse_volume_list()
            self.product_override_price = self._prase_product_override_price(
                self.soup)
            self.product_sales = self._prase_product_sales(self.soup)
        else:
            self.volume_list = None
            self.product_override_price = None
            self.product_sales = None

        self.type_list = self._parse_type()
        self.profile = self._parse_profile()
        self.characteristic = self._parse_characteristic()
        self.additional_info = self._parse_additional_info()

        self.category_list = self._parse_category_name()
        self.image_url_list = self._parse_image_url_list()
        self.related_product_url_list = self._parse_related_product_url_list()
        self.related_product_sku_list = []

    def assign_related_product_sku_list(self, rp_sku: list):
        self.related_product_sku_list = rp_sku

    def _parse_variants_data(self):
        variants = []
        try:
            raw = json.loads(self.soup.css.select('.variations_form.cart')[
                             0]['data-product_variations'])
        except (ValueError, IndexError, KeyError) as exc:
            return None

        for raw_var in raw:
            if raw_var['variation_is_visible']:
                var = self.Variant()
                var.product_sku = int(raw_var['sku'])
                price_html = BeautifulSoup(
                    raw_var['price_html'], 'html.parser')
                var.product_override_price = self._prase_product_override_price(
                    price_html, False)
                var.product_sales = self._prase_product_sales(
                    price_html, False)
                var.volume_list = [raw_var['attributes']['attribute_pa_objem']]
                variants.append(var)
        return variants

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

    def _prase_product_override_price(self, soup, whole_page=True):
        scope = ".product-essential" if whole_page else ''
        try:
            price = soup.css.select(f'{scope} .price del .amount')[0].text
        except IndexError:
            return None

        price = re.sub(ESHOP_PRICE_RE, '', price).replace(',', '.')
        try:
            price = float(price)
        except ValueError:
            return None

        return price

    def _prase_product_sales(self, soup, whole_page=True):
        scope = ".product-essential" if whole_page else ''
        try:
            price = soup.css.select(f'{scope} .price ins .amount')[0].text
        except IndexError as exc:
            try:
                price = soup.css.select('.price .amount')[0].text
            except IndexError as exc:
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

    def _parse_volume_list(self):
        return [el.text.replace('objem', '') for el in self.soup.css.select('.description span.label')]

    def _parse_profile(self):
        uid = None
        tabs = self.soup.css.select('.woocommerce-tabs > ul > li')
        for tab in tabs:
            if 'VÝKONOVÝ PROFIL' in tab.text:
                uid = tab.get('aria-controls')
        if uid is None:
            logger.warning(f'[{self.url}] VÝKONOVÝ PROFIL not found')
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
            logger.warning(f'[{self.url}] CHARAKTERISTIKA not found')
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
            logger.warning(f'[{self.url}] Další informace not found')
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
        self._mapping_dict = dict(mapping)

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
                    f'Failed to resolve related product with url: {rp_url} for {product.url}')
            else:
                related_sku_list.append(rp.product_sku)
        return related_sku_list

    def _finalize_value(self, value):
        if isinstance(value, list):
            value = [str(v).strip() for v in value]
            value = MULTIPLE_JOIN_EL.join(value)
        value = str(value).strip()
        return value

    def add(self, product: Product):
        product_dict = {}

        rp_sku = self._resolve_related_products(product)
        product.assign_related_product_sku_list(rp_sku)

        for prop, col in self._mapping:
            value = getattr(product, prop)
            if value is not None:
                value = self._finalize_value(value)
                product_dict[col] = value
            elif not (product.variants_data is not None and prop in VAR_PROPS):
                logger.info(f'[{product.url}] {prop} not found')

        if product.variants_data is not None:
            logger.info(f'[{product.url}] variants detected')
            parent = product.product_sku
            for var in product.variants_data:
                var_dict = copy.copy(product_dict)
                for prop in VAR_PROPS:
                    col = self._mapping_dict[prop]
                    value = getattr(var, prop)
                    if value is not None:
                        value = self._finalize_value(value)
                        var_dict[col] = value
                    else:
                        logger.info(
                            f'[{product.url} variants] {prop} not found')
                var_dict[VAR_PARENT] = parent
                row = pd.DataFrame(var_dict, index=[self._index])
                self._table = pd.concat([self._table, row], ignore_index=True)

        else:
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
            return
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

    soup = BeautifulSoup(response.content, 'html.parser')
    return Product(url, soup)


LIMIT = None
if __name__ == '__main__':
    count = 0
    assembler = Assembler(INDEX, COLUMNS, COLUMNS_MAP)
    for url in product_url_generator(ESHOP_URL_TEMPLATE):
        # url = 'https://www.millers-oils.cz/shop/prevodove-oleje/prevodovy-plne-synteticky-olej-millers-oils-crx-ls-75w90-nt/'
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
    assembler.table.to_csv(f"results/{ESHOP_NAME}.csv")
