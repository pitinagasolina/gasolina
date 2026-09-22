import os
import sys

import requests
from bs4 import BeautifulSoup


SOURCE_URL = os.environ.get("SOURCE_URL")
TIMEOUT = 30


def find_lakers_items():
    if not SOURCE_URL:
        raise RuntimeError("No se ha configurado SOURCE_URL")

    print(f"Consultando: {SOURCE_URL}")

    response = requests.get(
        SOURCE_URL,
        timeout=TIMEOUT,
        headers={
            "User-Agent": "GasolinaWatcher/1.0"
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)

        if "lakers" not in title.lower():
            continue

        results.append({
            "title": title,
            "url": link["href"],
        })

    return results


def main():
    print("=== Gasolina Watcher ===")

    items = find_lakers_items()

    if not items:
        print("No se encontraron elementos que mencionen Lakers.")
        return

    print(f"Encontrados: {len(items)}")

    for item in items:
        print()
        print(f"Título: {item['title']}")
        print(f"URL: {item['url']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
