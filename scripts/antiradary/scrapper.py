import sys
import time
import random
import logging
import requests_cache
import pandas as pd
from typing import Optional, List
from bs4 import BeautifulSoup

if __name__ == '__main__':
    # Fix import issues
    import sys
    sys.path.append('.')
    from scripts.common import remove_attrs, remove_query_params
    from scripts.exceptions import NotFound, get_log_wrapper


logger = logging.getLogger("utils.antiradary")
logging.basicConfig(level=logging.INFO)

DO_SLEEP = False
MULTIPLE_JOIN_EL = "|"

# Category, [available pages]
ESHOP_CATEGORY_LIST = [
    ["akcni-nabidka", [1]],
    ['extra', [1]],
    ["prenosne-antiradary", [1]],
    ["vestavene-antiradary", [1]],
    ["antilaserove-systemy", [1]],
    ["set-antiradaru-a-antilaseru", [1]],
    ["multifunkcni-systemy-antiradary-stinger", [1]],
    ["prislusenstvi", [1]],
    ["bazar", [1]],
    ["archiv", [1, 2, 3]],
]
ESHOP_NAME = 'antiradary_cz'
ESHOP_URL = "https://www.antiradary.cz"
ESHOP_URL_TEMPLATE = ESHOP_URL + "/{category}?page={page}"


class Product:
    soup: BeautifulSoup

    def __init__(self, url, soup: BeautifulSoup, short_desc: Optional[str] = None, parent_url: Optional[str] = None, category: Optional[str] = None):
        self.url = url
        self.soup = soup

        self._parent_url = parent_url
        self._parent_sku = None

        self._short_desc = short_desc
        self._category = category

        self._resolved_related = None
        self._resolved_alternatives = None

    @property
    @get_log_wrapper(logger)
    def sku(self):
        try:
            return self.soup.css.select(".vc-commoditydetail_info .Code dd")[0].text.strip()
        except IndexError:
            raise NotFound('SKU not found')

    @property
    @get_log_wrapper(logger)
    def ean(self):
        try:
            return self.soup.css.select(".vc-commoditydetail_info .OtherCodes dd")[0].text.strip()
        except IndexError:
            raise NotFound('Ean not found')

    @property
    @get_log_wrapper(logger)
    def name(self):
        try:
            return self.soup.css.select(".vc-commoditydetail_title span")[0].text.strip()
        except IndexError:
            raise NotFound('Name not found')

    @property
    @get_log_wrapper(logger)
    def desc(self):
        desc = self.soup.css.select(".vc-commoditydetail_description")
        if len(desc):
            el = remove_attrs(desc[0])
            return str(el)
        raise NotFound('Desc not found')

    @property
    @get_log_wrapper(logger)
    def manufacturer(self):
        try:
            manufacturer = self.soup.css.select(
                ".vc-commoditydetail_info .Person dd")[0].text.strip()
        except IndexError:
            raise NotFound('Manufacturer not found')
        if manufacturer and isinstance(manufacturer, str) and manufacturer[-1] == ',':
            manufacturer = manufacturer[:-1]
        return manufacturer

    @property
    @get_log_wrapper(logger)
    def type(self):
        flags = [el.text for el in self.soup.css.select(".flags .flag")]
        if not len(flags):
            raise NotFound('Flags not found')
        return flags

    @property
    @get_log_wrapper(logger)
    def warranty(self):
        try:
            return self.soup.css.select(".vc-commoditydetail_info .Warranty dd")[0].text.strip()
        except IndexError:
            raise NotFound('Warranty not found')

    @property
    @get_log_wrapper(logger)
    def weight(self):
        try:
            return self.soup.css.select(".vc-commoditydetail_info .Weight dd")[0].text.strip()
        except IndexError:
            raise NotFound('Weight not found')

    @property
    @get_log_wrapper(logger)
    def availability(self):
        try:
            return self.soup.css.select('.vc-commoditydetail_info .Availability dd .availability')[0].text.strip()
        except IndexError:
            raise NotFound('Availability not found')

    @property
    @get_log_wrapper(logger)
    def price(self):
        try:
            return float(self.soup.css.select('.vc-commoditydetail_pricing .price-withoutVat dd')[0]['data-price'])
        except IndexError:
            raise NotFound('Price not found')

    @property
    @get_log_wrapper(logger)
    def price_vat(self):
        try:
            return float(self.soup.css.select('.vc-commoditydetail_pricing .price-withVat dd')[0]['data-price'])
        except IndexError:
            raise NotFound('Price VAT not found')

    @property
    @get_log_wrapper(logger)
    def price_discount(self):
        try:
            price = float(self.soup.css.select(
                '.vc-commoditydetail_pricing .price-sale dd')[0]['data-price-discount'])
        except IndexError:
            raise NotFound('Discount price not found')

        if not price:
            raise NotFound('Discount price is invalid')
        return price

    @property
    @get_log_wrapper(logger)
    def amount_discount(self):
        try:
            return self.soup.css.select('.vc-commoditydetail_quantitydiscounts dd')[0].text.strip()
        except IndexError:
            raise NotFound('Amount discount not found')

    @property
    @get_log_wrapper(logger)
    def images(self):
        items = []

        main = self.soup.css.select('.vc-commoditydetail_image a')
        if len(main):
            items.append(main[0]['href'])

        for item in self.soup.css.select('.vc-commoditydetail_gallery .owl-gallery a'):
            items.append(item['href'])

        items = [remove_query_params(item) for item in items]
        if not len(items):
            raise NotFound('Images not found')

        return items

    @property
    @get_log_wrapper(logger)
    def files(self):  # TODO: fix relative url
        items = []
        for item in self.soup.css.select(".vc-commoditydetail_files a"):
            items.append(item['href'])

        items = [remove_query_params(item) for item in items]
        if not len(items):
            raise NotFound('Files not found')

        return items

    @property
    @get_log_wrapper(logger)
    def alternatives(self):
        items = []
        for item in self.soup.css.select('#CommodityAlternate article > a'):
            href = item['href']
            if 'http' not in href:
                href = ESHOP_URL + href

        items = [remove_query_params(item) for item in items]
        if not len(items):
            raise NotFound('Alternatives not found')

        return items

    @property
    @get_log_wrapper(logger)
    def related(self):
        items = []
        for item in self.soup.css.select('#CommodityRelated article > a'):
            href = item['href']
            if 'http' not in href:
                href = ESHOP_URL + href
            items.append(href)

        items = [remove_query_params(item) for item in items]
        if not len(items):
            raise NotFound('Related not found')

        return items

    @property
    @get_log_wrapper(logger)
    def parameters(self):  # TODO: Table?
        content = self.soup.css.select(".vc-commoditydetail_parameters")
        if len(content):
            el = remove_attrs(content[0])
            el = str(el).strip()
            if not el:
                raise NotFound('Parameters not found')
            return el
        else:
            raise NotFound('Parameters not found')

    @property
    def resolved_related(self):
        if self._resolved_related is None:
            raise NotFound('Related not found')
        return self._resolved_related

    @property
    def resolved_alternatives(self):
        if self._resolved_alternatives is None:
            raise NotFound('Alternatives not found')
        return self._resolved_alternatives

    @property
    def short_desc(self):
        if self._short_desc is None:
            raise NotFound('Short description not found')
        return self._short_desc

    @property
    def category(self):
        if self._category is None:
            raise NotFound('Category not found')
        return self._category

    @property
    def parent_sku(self):
        if self._parent_sku is None:
            raise NotFound('Parent sku not found')
        return self._parent_sku


class Assembler:
    INDEX = "product_sku"
    COLUMNS_MAP = [
        ["url", "url"],
        ["sku", "product_sku"],
        ["parent_sku", "product_parent_sku"],
        ["ean", "product_ean"],
        ["price", "price"],
        ["price_vat", "price_vat"],
        ["price_discount", "product_sales"],
        ["amount_discount", "amount_discount"],
        ["parameters", "dalsi_info"],
        ["weight", "weight"],
        ["name", "product_name"],
        ["desc", "product_desc"],
        ["short_desc", "product_s_desc"],
        ["images", "image_url"],
        ["files", "file_url"],
        ["type", "typ"],
        ["category", "category_name"],
        ["warranty", "warranty"],
        ["manufacturer", "manufacturer"],
        ["availability", "availability"],
        ["resolved_related", "related_products"],
        ["resolved_alternatives", "alternative_products"],
    ]
    COLUMNS = [col for _, col in COLUMNS_MAP]

    def __init__(self):
        self.table = pd.DataFrame(
            columns=self.COLUMNS, index=[self.INDEX]).dropna()
        self._products_url_map = {}

    @property
    def products(self):
        return self._products_url_map.values()

    def collect(self, product: Product):
        self._products_url_map[product.url] = product

    def _get_sku_list(self, urls: List[str]):
        sku_list = []
        for url in urls:
            try:
                related = self._products_url_map[url]
            except KeyError:
                logger.warning(
                    f"Failed to resolve product with url: {url} for {product.url}"
                )
            else:
                sku_list.append(related.sku)
        return sku_list

    def _finalize_value(self, value):
        if isinstance(value, list):
            value = [str(v).strip() for v in value]
            value = MULTIPLE_JOIN_EL.join(value)
        value = str(value).strip()
        return value

    def build(self, product: Product):
        product_dict = {}

        if product._parent_url is not None:
            try:
                product._parent_sku = self._get_sku_list(
                    [product._parent_url])[0]
            except NotFound:
                pass

        try:
            product._resolved_related = self._get_sku_list(
                product.related)
        except NotFound:
            pass

        try:
            product._resolved_alternatives = self._get_sku_list(
                product.alternatives)
        except NotFound:
            pass

        for prop, col in self.COLUMNS_MAP:
            try:
                value = getattr(product, prop)
            except NotFound:
                value = ''
            else:
                value = self._finalize_value(value)

            product_dict[col] = value

        row = pd.DataFrame(product_dict, index=[self.INDEX])
        self.table = pd.concat([self.table, row], ignore_index=True)


class Workflow:
    session = requests_cache.CachedSession('development')

    @staticmethod
    def product_url_generator(template: str):
        for category, pages in ESHOP_CATEGORY_LIST:
            for page in pages:
                content_url = template.format(page=page, category=category)

                logger.info(f"Fetching category: {content_url}")
                response = Workflow.session.get(content_url)
                try:
                    assert response.status_code == 200
                except AssertionError as exc:
                    logger.info(f"Fetch failed, stop iteration")
                    return
                else:
                    if DO_SLEEP:
                        cooldown = random.randint(5, 20)
                        logger.info(f"Sleep: {cooldown}")
                        time.sleep(cooldown)
                soup = BeautifulSoup(response.content, "html.parser")

                category_name = soup.css.select('.categoryName')[
                    0].text.strip()

                articles = soup.css.select(
                    ".commodities > article.commodityBox")
                annotations = soup.css.select('.annotation')

                logger.info(
                    f'Found: {len(articles)} products in {category_name}')

                for article, annotation in zip(articles, annotations):
                    parent_url = ESHOP_URL + \
                        article.css.select('a')[0].get("href")
                    short_desc = annotation.text
                    yield parent_url, None, short_desc, category_name
                    if len(article.css.select('.goToDetail-variants')):
                        for variant_url in Workflow.variant_url_generator(parent_url):
                            yield variant_url, parent_url, short_desc, category_name

    @staticmethod
    def variant_url_generator(parent_product_url: str):
        logger.info(f"Fetching parent product: {parent_product_url}")
        response = Workflow.session.get(parent_product_url)
        try:
            assert response.status_code == 200
        except AssertionError:
            logger.info(f"Fetch failed, stop iteration")
            return
        else:
            if DO_SLEEP:
                cooldown = random.randint(5, 20)
                logger.info(f"Sleep: {cooldown}")
                time.sleep(cooldown)
        soup = BeautifulSoup(response.content, "html.parser")
        variants = [a.get("href") for a in soup.css.select(
            ".variants-catalog article > a")]
        logger.info(f"+ {len(variants)} variants found")
        for url in variants:
            yield ESHOP_URL + url

    @staticmethod
    def product_processing(url: str, short_desc: Optional[str] = None, parent_url: Optional[str] = None, category: Optional[str] = None) -> Product:
        response = Workflow.session.get(url)
        try:
            assert response.status_code == 200
        except AssertionError as exc:
            raise RuntimeError(f"Product fetch failed: {url}") from exc

        soup = BeautifulSoup(response.content, "html.parser")
        return Product(url, soup, short_desc=short_desc, category=category, parent_url=parent_url)


LIMIT = None
if __name__ == "__main__":
    count = 0

    assembler = Assembler()
    for url, parent_url, short_desc, category in Workflow.product_url_generator(ESHOP_URL_TEMPLATE):
        count += 1
        try:
            product = Workflow.product_processing(
                url, parent_url=parent_url, short_desc=short_desc, category=category)
        except RuntimeError as exc:
            logger.error(url)
            logger.exception(exc)
            continue
        assembler.collect(product)

    logger.info(f'Collected: {count} products')
    for product in assembler.products:
        assembler.build(product)

    assembler.table.to_csv(f"results/{ESHOP_NAME}.csv")
