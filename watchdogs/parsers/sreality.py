import requests
from bs4 import BeautifulSoup

DOMAIN = "www.sreality.cz"
SOURCE_WEB_URL = f"https://{DOMAIN}/hledani"

HEADERS = {  # Bypass ad agreement
    "Cookie": "last-redirect=1; __cw_snc=1; szncmpone=1; cw_referrer=; euconsent-v2=CQGvaEAQGvaEAD3ACQCSBMFsAP_gAEPgAATIJNQIwAFAAQAAqABkAEAAKAAZAA0ACSAEwAJwAWwAvwBhAGIAQEAggCEAEUAI4ATgAoQBxADuAIQAUgA04COgE2gKkAW4AvMBjID_AIDgRmAk0BecBIACoAIAAZAA0ACYAGIAPwAhABHACcAGaAO4AhABFgE2gKkAW4AvMAAA.YAAAAAAAAWAA"
}


def list_offers(query: str = "/?") -> list[dict]:
    response = requests.get(
        f"{SOURCE_WEB_URL}{query}",
        headers=HEADERS,
    )
    soup = BeautifulSoup(response.content, features="html.parser")
    return [
        {"url": f'https://{DOMAIN}{el.attrs["href"]}'}
        for el in soup.select(
            'li[id^="estate-list-item"] > a.MuiLink-root:nth-of-type(1)'
        )
    ]


def fetch_offer_by_url(url: str):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.content, features="html.parser")

    _author_base = "#__next > div.MuiBox-root.css-17gcfrm > div.MuiBox-root.css-14kccxu > div.MuiBox-root.css-vq9zkb > div > div.MuiBox-root.css-0 > div > div > section > div > div > div"
    author = soup.select(f"{_author_base}> a,p:nth-child(0)") or soup.select(
        f"{_author_base}> p"
    )
    description = soup.select(
        "#__next > div.MuiBox-root.css-17gcfrm > div.MuiBox-root.css-14kccxu > div.MuiBox-root.css-1ivt71a > div > div > section.MuiBox-root.css-i3pbo > div.MuiBox-root.css-zbebq3 > div:nth-child(1) > pre"
    )
    title = soup.select(
        "#__next > div.MuiBox-root.css-17gcfrm > div.MuiBox-root.css-14kccxu > div.MuiBox-root.css-1uikywc > h1"
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
    #         # "https://www.sreality.cz/detail/prodej/dum/rodinny/jimramov-jimramov-padelek/2012865100"
    #         # 'https://www.sreality.cz/detail/prodej/byt/2+kk/kolin-kolin-ii-fugnerova/22925900'
    #     )
    # )
    pass
