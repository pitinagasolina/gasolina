import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE_URL = os.environ.get("SOURCE_URL")
TIMEOUT = 30
STATE_FILE = Path("state/state.json")


def load_state():
    if not STATE_FILE.exists():
        return {"seen": []}

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"seen": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    STATE_FILE.write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8",
    )


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

        url = urljoin(SOURCE_URL, link["href"])

        results.append({
            "title": title,
            "url": url,
        })

    return results


def main():
    print("=== Gasolina Watcher ===")

    state = load_state()
    seen = set(state.get("seen", []))

    items = find_lakers_items()

    print(f"Entradas Lakers encontradas: {len(items)}")
    print(f"Entradas Lakers ya conocidas: {len(seen)}")

    new_items = []

    for item in items:
        if item["url"] not in seen:
            new_items.append(item)

    print(f"Entradas Lakers NUEVAS: {len(new_items)}")

    if new_items:
        print()
        print("=== NUEVAS ENTRADAS ===")

        for item in new_items:
            print()
            print(f"Título: {item['title']}")
            print(f"URL: {item['url']}")

            seen.add(item["url"])

    # Guardamos como conocidas las entradas que hemos visto.
    state["seen"] = sorted(seen)

    save_state(state)

    print()
    print("Estado guardado correctamente.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
