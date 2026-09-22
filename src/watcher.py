import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup


SOURCE_URL = os.environ.get("SOURCE_URL")
TIMEOUT = 30
STATE_FILE = Path("state/state.json")


def normalize_url(url):
    parts = urlsplit(url)

    # El parámetro sid cambia entre sesiones y no identifica
    # de forma única el tema del foro.
    query_parts = []

    for parameter in parts.query.split("&"):
        if not parameter:
            continue

        key = parameter.split("=", 1)[0].lower()

        if key == "sid":
            continue

        query_parts.append(parameter)

    query = "&".join(query_parts)

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path.rstrip("/"),
        query,
        "",
    ))


def load_state():
    if not STATE_FILE.exists():
        return {"seen": []}

    try:
        state = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        return {"seen": []}

    seen = state.get("seen", [])

    # Normalizar y eliminar duplicados antiguos.
    normalized_seen = sorted({
        normalize_url(url)
        for url in seen
    })

    return {
        "seen": normalized_seen
    }


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
    found_urls = set()

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)

        if "lakers" not in title.lower():
            continue

        url = normalize_url(
            urljoin(SOURCE_URL, link["href"])
        )

        # Evitar que el mismo enlace aparezca varias veces
        # en la página.
        if url in found_urls:
            continue

        found_urls.add(url)

        results.append({
            "title": title,
            "url": url,
        })

    return results


def main():
    print("=== Gasolina Watcher ===")

    state = load_state()
    seen = set(state["seen"])

    items = find_lakers_items()

    print(f"Entradas Lakers encontradas: {len(items)}")
    print(f"Entradas ya registradas: {len(seen)}")

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

    # Incorporamos las entradas actuales al estado.
    # El set garantiza que nunca haya duplicados.
    for item in items:
        seen.add(item["url"])

    state["seen"] = sorted(seen)

    save_state(state)

    print()
    print("Estado guardado correctamente.")
    print(f"Total de URLs almacenadas: {len(state['seen'])}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
