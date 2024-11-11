import requests
from bs4 import BeautifulSoup

DOMAIN = "www.sreality.cz"
SOURCE_WEB_URL = f"https://{DOMAIN}/hledani"


def list_offers(query: str = "/?") -> list[str]:
    response = requests.get(
        f"{SOURCE_WEB_URL}{query}",
        headers={  # Bypass ad agreement
            "Cookie": "last-redirect=1; __cw_snc=1; szncmpone=1; cw_referrer=; euconsent-v2=CQGvaEAQGvaEAD3ACQCSBMFsAP_gAEPgAATIJNQIwAFAAQAAqABkAEAAKAAZAA0ACSAEwAJwAWwAvwBhAGIAQEAggCEAEUAI4ATgAoQBxADuAIQAUgA04COgE2gKkAW4AvMBjID_AIDgRmAk0BecBIACoAIAAZAA0ACYAGIAPwAhABHACcAGaAO4AhABFgE2gKkAW4AvMAAA.YAAAAAAAAWAA"
        },
    )
    soup = BeautifulSoup(response.content, features="html.parser")
    return [
        f'https://{DOMAIN}{el.attrs["href"]}'
        for el in soup.select(
            'li[id^="estate-list-item"] > a.MuiLink-root:nth-of-type(1)'
        )
    ]


if __name__ == "__main__":
    print(list_offers())
