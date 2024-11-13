import requests
from bs4 import BeautifulSoup

DOMAIN = "reality.bazos.cz"
SOURCE_URL = f"https://{DOMAIN}/prodam/byt"


def list_offers(query: str = "/?") -> list[dict]:
    response = requests.get(f"{SOURCE_URL}{query}")
    soup = BeautifulSoup(response.content, features="html.parser")
    return [
        {"url": f'https://{DOMAIN}{el.attrs["href"]}'}
        for el in soup.select("body div.maincontent .inzeraty .inzeratynadpis > a")
    ]


def fetch_offer_by_url(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, features="html.parser")

    author = soup.select(
        "body > div > div.flexmain > div.maincontent td.listadvlevo table tr:nth-child(1) td:nth-child(2)"
    )
    title = soup.select(
        "body > div.sirka > div.flexmain > div.maincontent > div.listainzerat.inzeratyflex > div.inzeratydetnadpis > h1"
    )
    description = soup.select(
        "body > div.sirka > div.flexmain > div.maincontent > div.popisdetail"
    )
    return {
        "title": title[0].text if len(title) else None,
        "description": description[0].text if len(description) else None,
        "author": author[0].text if len(author) else None,
    }


if __name__ == "__main__":
    # print(list_offers())
    # print(
    #     fetch_offer_by_url(
    #         # "https://reality.bazos.cz/inzerat/193319261/prodej-bytu-3kk-73-m-v-plzni-slovanech.php"
    #     )
    # )
    pass
