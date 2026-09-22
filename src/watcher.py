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
    """
    Normaliza una URL para que pequeñas diferencias no creen
    entradas duplicadas.

    El parámetro sid es una sesión del foro y no identifica
    de forma única una entrada.
    """

    parts = urlsplit(url)

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

def login_720pier():
    username = os.environ.get("FORUM_USERNAME")
    password = os.environ.get("FORUM_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "Faltan FORUM_USERNAME o FORUM_PASSWORD"
        )

    session = requests.Session()

    session.headers.update({
        "User-Agent": "GasolinaWatcher/1.0"
    })

    login_url = "https://720pier.ru/ucp.php?mode=login"

    # 1. Obtener el formulario y los tokens dinámicos.
    response = session.get(
        login_url,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    login_form = None

    for form in soup.find_all("form"):
        username_field = form.find(
            "input",
            {"name": "username"}
        )

        password_field = form.find(
            "input",
            {"name": "password"}
        )

        if username_field and password_field:
            login_form = form
            break

    if login_form is None:
        raise RuntimeError(
            "No se encontró el formulario de login"
        )

    data = {}

    for field in login_form.find_all("input"):
        name = field.get("name")

        if not name:
            continue

        input_type = field.get("type", "").lower()

        if input_type in ("submit", "button"):
            continue

        if input_type in ("checkbox", "radio"):
            if field.has_attr("checked"):
                data[name] = field.get("value", "on")
            continue

        data[name] = field.get("value", "")

    data["username"] = username
    data["password"] = password
    data["login"] = "Вход"

    action = login_form.get("action")

    if not action:
        action = login_url

    action_url = urljoin(
        response.url,
        action
    )

    # 2. Enviar login usando la misma sesión.
    login_response = session.post(
        action_url,
        data=data,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    login_response.raise_for_status()

    print("Login enviado correctamente.")
    print("URL después del login:", login_response.url)

    return session

def test_download_torrent(session):
    torrent_url = "https://720pier.ru/download/torrent?id=74907"
    topic_url = "https://720pier.ru/viewtopic.php?t=75712"

    print("=== DIAGNÓSTICO SESIÓN ===")

    # No mostramos los valores de las cookies por seguridad.
    print("Cookies después del login:")

    for cookie in session.cookies:
        print(
            f"  {cookie.name} "
            f"(domain={cookie.domain}, path={cookie.path})"
        )

    # Primero visitamos la entrada usando LA MISMA sesión.
    print("Consultando entrada:", topic_url)

    topic_response = session.get(
        topic_url,
        timeout=TIMEOUT,
        headers={
            "Referer": "https://720pier.ru/"
        },
        allow_redirects=True,
    )

    print("Status entrada:", topic_response.status_code)
    print("URL entrada:", topic_response.url)

    topic_response.raise_for_status()

    # Ahora intentamos el torrent desde esa misma sesión.
    print("Descargando torrent:", torrent_url)

    torrent_response = session.get(
        torrent_url,
        timeout=TIMEOUT,
        headers={
            "Referer": topic_response.url,
        },
        allow_redirects=True,
    )

    print("Status torrent:", torrent_response.status_code)
    print("URL final torrent:", torrent_response.url)
    print(
        "Content-Type torrent:",
        torrent_response.headers.get("Content-Type")
    )
    print(
        "Bytes recibidos:",
        len(torrent_response.content)
    )

    if torrent_response.status_code != 200:
        print(
            "Respuesta del servidor:",
            torrent_response.text[:500]
        )

    torrent_response.raise_for_status()

    output_dir = Path("downloads")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "test-74907.torrent"
    output_file.write_bytes(torrent_response.content)

    print(f"Torrent guardado en: {output_file}")

def find_lakers_items(session=None):
    if session is None:
        session = requests.Session()

        session.headers.update({
            "User-Agent": "GasolinaWatcher/1.0"
        })

    print(f"Consultando: {SOURCE_URL}")

    response = session.get(
        SOURCE_URL,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    print(f"URL final: {response.url}")
    print(f"Status HTTP: {response.status_code}")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Diagnóstico: si el foro nos manda al login,
    # podremos verlo directamente en el log.
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    print(f"Título de la página: {page_title}")

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

    session = login_720pier()

    test_download_torrent(session)

    items = find_lakers_items(session)


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
