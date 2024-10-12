import re
import time
import random
import logging
import requests_cache
import pandas as pd
from bs4 import BeautifulSoup
from typing import List


from scrappers.common import Assembler as BaseAssembler, Product as BaseProduct
from scrappers.exceptions import NotFound, get_log_wrapper


logger = logging.getLogger("ziener")
logging.basicConfig(level=logging.INFO)

DO_SLEEP = False

ESHOP_NAME = 'ziener'
ESHOP_URL = 'https://ziener.com'

BASE_URL = ['https://ziener.com/en', ['winter', 'summer']]


class Product(BaseProduct):

    css_colors_url = "https://ziener.com/templates/ziener/css/nagel.werbeagentur.css"
    css_colors_content = None

    @property
    @get_log_wrapper(logger)
    def product_name(self):
        try:
            return self.soup.css.select('article > div > div > div > h1')[0].text
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def sku(self):
        try:
            for r in self.soup.css.select('#pills-info tr'):
                if r.css.select('td:nth-child(1)')[0].text == 'Item No.':
                    return r.css.select('td:nth-child(2)')[0].text
        except Exception as e:
            raise NotFound() from e
        raise NotFound()

    @property
    @get_log_wrapper(logger)
    def product_description(self):
        try:
            return str(self.soup.css.select('#features-home')[0])
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def color_codes(self):
        codes = []
        for e in self.soup.css.select('#pills-farben #detail_name'):
            cs = e.css.select('[class^="icon-colors"]')
            var_codes = []
            for c in cs:
                c = [cl for cl in c.get('class') if 'icon-colors' in cl]
                c = c[0]
                c = c.replace('icon-colors_', '')
                var_codes.append(c)
            codes.append(','.join(var_codes))
        return codes

    @property
    @get_log_wrapper(logger)
    def colors(self):
        codes = self.color_codes
        colors = []
        if len(codes):
            for cs in codes:
                var_colors = []
                for c in cs.split(','):
                    var_colors.append(self._get_color_name(c))
                colors.append(','.join(var_colors))
        return colors

    @property
    @get_log_wrapper(logger)
    def product_material(self):
        try:
            return str(self.soup.css.select('#pills-technologie')[0])
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def images(self):
        try:
            return [a.get('href') for a in self.soup.css.select('article div.slider_detail_produkt figure a')]
        except Exception as e:
            raise NotFound() from e

    def _get_color_name(self, code):
        exp = re.compile(f'(?<=icon-colors_{code}' + r'::after\s){.*}')
        m = exp.search(self.css_colors_content)
        if m is None:
            return 'unknown'
        else:
            color = m.group(0)
            color = color.replace('{', '')
            color = color.replace('}', '')
            color = color.replace('content:', '')
            color = color.replace('"', '')
            color = color.replace(';', '')
            color = color.strip()
            return color


class Assembler(BaseAssembler):
    INDEX = "url"
    COLUMNS = [
        "url",
        "sku",
        "product_name",
        "colors",
        "color_codes",
        "product_description",
        "product_material",
        "images"
    ]

    def build(self):
        table = pd.DataFrame(columns=self.COLUMNS, index=[self.INDEX]).dropna()
        for product in self._products_url_map.values():
            product_dict = {}
            for col in self.COLUMNS:
                try:
                    value = getattr(product, col)
                except NotFound:
                    value = ''
                else:
                    value = self._finalize_value(value)

                product_dict[col] = value

            row = pd.DataFrame(product_dict, index=[self.INDEX])
            table = pd.concat([table, row], ignore_index=True)
        return table


class Workflow:
    session = requests_cache.CachedSession('production-27-12-2023')
    # session = requests_cache.CachedSession('development')

    @staticmethod
    def init_css_content():
        response = Workflow.session.get(Product.css_colors_url)
        assert response.status_code == 200

        Product.css_colors_content = response.content.decode('utf-8')

    @staticmethod
    def url_generator(base_url: str, sections: List[str]) -> str:
        response = Workflow.session.get(base_url)
        try:
            assert response.status_code == 200
        except AssertionError:
            logger.info(f"Fetch failed: {base_url}")
            raise RuntimeError()

        soup = BeautifulSoup(response.content, "html.parser")

        category_urls = []
        for section in sections:
            for tile in soup.css.select('#navbarTogglerZiener > ul > li > a'):
                if tile.text.lower().strip() == section:
                    for a in tile.parent.css.select('.dropdown-menu ul li ul.last-level li > a'):
                        category_urls.append(f"{ESHOP_URL}/{a.get('href')}")

        for category_url in category_urls:
            for product_url in Workflow._url_generator_product(category_url):
                yield f'{ESHOP_URL}/{product_url}'

    @staticmethod
    def _url_generator_product(url: str) -> str:
        response = Workflow.session.get(url)

        try:
            assert response.status_code == 200
        except AssertionError:
            logger.info(f"Fetch failed: {url}")
            raise StopIteration()
        else:
            if DO_SLEEP:
                cooldown = random.randint(5, 20)
                logger.info(f"Sleep: {cooldown}")
                time.sleep(cooldown)

        soup = BeautifulSoup(response.content, "html.parser")
        for a in soup.css.select("article figure > a"):
            yield a.get('href')

    @staticmethod
    def url_collector(url: str) -> Product:
        response = Workflow.session.get(url)
        try:
            assert response.status_code == 200
        except AssertionError as exc:
            raise RuntimeError(f"Product fetch failed: {url}") from exc

        soup = BeautifulSoup(response.content, "html.parser")
        return Product(url, soup)


LIMIT = None
if __name__ == "__main__":
    count = 0

    assembler = Assembler()
    base_url, sections = BASE_URL

    Workflow.init_css_content()
    for product_url in Workflow.url_generator(base_url, sections):
        logger.info(f'URL: {product_url}')

        count += 1
        if count and count % 100 == 0:
            logger.info(f'Count: {count}')

        try:
            product = Workflow.url_collector(product_url)
        except Exception as e:
            logger.error(product_url)
            logger.exception(e)
            continue
        assembler.collect(product)
        if LIMIT is not None and count == LIMIT:
            break

    logger.info(f'Collected: {count} products')

    table = assembler.build()
    table.to_csv(
        f"results/{ESHOP_NAME}/{ESHOP_NAME}-27-12-23-full.csv", index=False)
