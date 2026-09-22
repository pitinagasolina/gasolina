import os
import sys
import requests
from bs4 import BeautifulSoup


SOURCE_URL = os.environ.get("SOURCE_URL")
TIMEOUT = 30


def check_source():
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

    print(f"Página recibida correctamente.")
    print(f"Título: {soup.title.get_text(strip=True) if soup.title else '(sin título)'}")


def main():
    print("=== Gasolina Watcher ===")
    check_source()
    print("Comprobación terminada correctamente.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
