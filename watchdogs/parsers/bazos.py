import requests
from bs4 import BeautifulSoup

DOMAIN = "reality.bazos.cz"
SOURCE_URL = f"https://{DOMAIN}/prodam/byt"


def list_offers(query: str = "/?") -> list[str]:
    response = requests.get(f"{SOURCE_URL}{query}")
    soup = BeautifulSoup(response.content, features="html.parser")
    return [
        f'https://{DOMAIN}{el.attrs["href"]}'
        for el in soup.select("body div.maincontent .inzeraty .inzeratynadpis > a")
    ]


if __name__ == "__main__":
    print("\n".join(list_offers()))
