import json
import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.facebook.com/marketplace/category/propertyforsale"
SOURCE_ITEM_URL = "https://www.facebook.com/marketplace"

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Chromium";v="127", "Not)A;Brand";v="99"',
    "sec-ch-ua-full-version-list": '"Chromium";v="127.0.6533.72", "Not)A;Brand";v="99.0.0.0"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Linux"',
    "sec-ch-ua-platform-version": '"5.15.0"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
}


def list_offers(query: str = "/?") -> list[str]:
    response = requests.get(
        f"{SOURCE_URL}{query}",
        headers=HEADERS,
    )
    soup = BeautifulSoup(response.content, features="html.parser")
    data = json.loads(
        [
            el
            for el in soup.select('script[type="application/json"]')
            if "GroupCommerceProductItem" in str(el)
            and "marketplace_feed_stories" in str(el)
        ]
        .pop()
        .text
    )
    data = data["require"][0][3][0]["__bbox"]["require"][0][3][1]["__bbox"]["result"][
        "data"
    ]["viewer"]["marketplace_feed_stories"]["edges"]
    return [f'{SOURCE_ITEM_URL}/item/{node["node"]["listing"]["id"]}' for node in data]


def fetch_offer_by_url(url: str):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.content, features="html.parser")
    data = json.loads(
        [
            el
            for el in soup.select('script[type="application/json"]')
            if "marketplace_product_details_page" in str(el)
        ]
        .pop()
        .text
    )
    data = data["require"][0][3][0]["__bbox"]["require"][3][3][1]["__bbox"]["result"][
        "data"
    ]["viewer"]["marketplace_product_details_page"]["target"]

    return {
        "author": None,
        "title": (
            data["base_marketplace_listing_title"]
            if "base_marketplace_listing_title" in data
            else data["marketplace_listing_title"]
        ),
        "description": data["redacted_description"]["text"],
    }


if __name__ == "__main__":
    # print(list_offers())
    print(
        fetch_offer_by_url("https://www.facebook.com/marketplace/item/1139894651084886")
    )
    pass
