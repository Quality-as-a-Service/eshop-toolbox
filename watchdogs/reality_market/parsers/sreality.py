import requests

SOURCE_URL = "https://www.sreality.cz/api/cs/v2/estates"


def fetch_single_page(query: str = "/?") -> list[str]:
    response = requests.get(f"{SOURCE_URL}{query}")
    return [
        item["_links"]["self"]["href"]
        for item in response.json()["_embedded"]["estates"]
    ]


if __name__ == "__main__":
    print(fetch_single_page())
