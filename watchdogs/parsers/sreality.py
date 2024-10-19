import requests
from bs4 import BeautifulSoup

DOMAIN = "www.sreality.cz"
SOURCE_WEB_URL = f"https://{DOMAIN}/hledani"
SOURCE_API_URL = f"https://{DOMAIN}/api/v1/estates/search"


def fetch_single_page_api(query: str = "/?") -> list[str]:
    # Not stable
    response = requests.get(f"{SOURCE_API_URL}{query}")
    return [str(item["hash_id"]) for item in response.json()["results"]]


def fetch_single_page_web(query: str = "/?") -> list[str]:
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
    # print(
    #     fetch_single_page_api(
    #         "?locality_country_id=112&locality_search_name=Hole%C5%A1ov&locality_entity_type=municipality&locality_entity_id=3125&locality_radius=25&limit=20&sort=-date&include_broker_tip=false&include_region_tip=false&include_project_tip=false"
    #     )
    # )
    print(
        fetch_single_page_web(
            "?region=Hole%C5%A1ov&region-id=3125&region-typ=municipality&vzdalenost=25"
        )
    )
