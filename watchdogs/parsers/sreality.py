import requests

SOURCE_URL = "https://www.sreality.cz/api/v1/estates/search"


def fetch_single_page(query: str = "/?") -> list[str]:
    response = requests.get(f"{SOURCE_URL}{query}")
    return [item["hash_id"] for item in response.json()["results"]]


if __name__ == "__main__":
    print(fetch_single_page())
