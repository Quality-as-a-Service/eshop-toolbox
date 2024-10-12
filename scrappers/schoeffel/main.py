import re
import time
import random
import logging
import requests_cache
import pandas as pd

from bs4 import BeautifulSoup

from scrappers.common import Assembler as BaseAssembler, Product as BaseProduct
from scrappers.exceptions import NotFound, get_log_wrapper

ESHOP_NAME = 'schoeffel'


logger = logging.getLogger(ESHOP_NAME)
logging.basicConfig(level=logging.INFO)

DO_SLEEP = False

ESHOP_URLS = [['https://www.schoeffel.com/de/de/damen', 43],
              ['https://www.schoeffel.com/de/de/herren', 38],
              ['https://www.schoeffel.com/de/de/kinder', 2]]


def normalize_text(text):
    lines = text.split('\n')
    n_lines = []
    for line in lines:
        line = re.sub(r'\s+', ' ', line).strip()
        if line:
            n_lines.append(line)
    text = '\n'.join(n_lines)
    return text


class Product(BaseProduct):
    parent_url: str

    sku_re = re.compile(r'(?<=Modellnummer\s)(\d+-\d+)')

    @property
    @get_log_wrapper(logger)
    def sku(self):
        desc = self.product_description_text
        if not desc:
            raise NotFound()

        m = self.sku_re.search(desc)
        if m is None:
            raise NotFound()

        return m.group(0)

    @property
    @get_log_wrapper(logger)
    def color(self):
        try:
            return self.soup.css.select(
                '#article-wrapper section.headline div.filter.color-wrapper a.active')[0].get('title')
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def color_code(self):
        try:
            return self.soup.css.select(
                '#article-wrapper section.headline div.filter.color-wrapper a.active')[0].get('data-color-number')
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def product_name(self):
        try:
            return self.soup.css.select('#article-wrapper section.headline div.content > div > div > h2')[0].text
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def product_description(self):
        try:
            return normalize_text(self.soup.css.select('#article-description')[0].get_text())
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def product_description_text(self):
        try:
            return self.soup.css.select('#article-description')[0].text
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def product_material(self):
        try:
            return normalize_text(self.soup.css.select('#article-material')[0].get_text())
        except Exception as e:
            raise NotFound() from e

    @property
    @get_log_wrapper(logger)
    def images(self):
        try:
            return [im.get('src') for im in self.soup.css.select('.main-slider img')]
        except Exception as e:
            raise NotFound() from e


class Assembler(BaseAssembler):
    INDEX = "url"
    COLUMNS = [
        "url",
        # "parent_url",
        "sku",
        "color",
        "color_code",
        "product_name",
        "product_description",
        "product_material",
        "images"
    ]

    def exist(self, url):
        return url in self._products_url_map

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
    session = requests_cache.CachedSession('production-18-02-2024')
    # session = requests_cache.CachedSession('development')

    collected = set()

    @staticmethod
    def url_generator(base_url: str, pages: int) -> str:
        for page in range(pages):
            logger.info(f'Page: {page} / {pages}')
            page_url = f'{base_url}?page={page + 1}'
            for product_url in Workflow._url_generator_product(page_url):
                for variant_url in Workflow._url_generator_variant(product_url):
                    yield product_url, variant_url

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
        for a in soup.css.select(".article-item .article-wrapper div.image-wrapper > a"):
            yield a.get('href')

    @staticmethod
    def _url_generator_variant(url: str) -> str:
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
        for a in soup.css.select("#article-wrapper .filter.color-wrapper a"):
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
    for base_url, pages in ESHOP_URLS:
        logger.info(f'Collecting: {base_url}')
        for parent_url, variant_url in Workflow.url_generator(base_url, pages):

            if assembler.exist(variant_url):
                continue

            count += 1
            if count and count % 100 == 0:
                logger.info(f'Count: {count}')
            try:
                product = Workflow.url_collector(variant_url)
            except Exception as e:
                logger.error(variant_url)
                logger.exception(e)
                continue
            product.parent_url = parent_url
            assembler.collect(product)
            if LIMIT is not None and count == LIMIT:
                break
        if LIMIT is not None and count == LIMIT:
            break

    logger.info(f'Collected: {count} products')

    table = assembler.build()
    table.to_csv(
        f"results/{ESHOP_NAME}/{ESHOP_NAME}-18-02-24-full.csv", index=False)
    # f"results/{ESHOP_NAME}/{ESHOP_NAME}-sample-10.csv", index=False)
