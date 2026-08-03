"""
Kleine microservice die recept-URL's (met focus op voedingscentrum.nl)
ophaalt en de ingrediëntenlijst als JSON teruggeeft, zodat Home Assistant
dit via rest_command kan aanroepen en doorzetten naar Bring.

Endpoint:
    GET /parse?url=<recept-url>

Response:
    { "ingredients": ["200 gram volkoren tagliatelle", ...], "source_url": "..." }
    of bij een fout: { "error": "..." }
"""

from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (HomeAssistant recipe-parser)"}


def extract_ingredients(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Zoek de kop "Ingrediënten" (h2/h3).
    heading = soup.find(
        lambda tag: tag.name in ("h2", "h3")
        and "ingredi" in tag.get_text(strip=True).lower()
    )
    if not heading:
        return []

    # Loop door ALLE volgende elementen in document-volgorde (dus ook
    # geneste elementen, zoals meerdere <ul>'s naast elkaar in kolommen
    # binnen een omliggende <div>), tot de volgende kop (bijv. "Bereiding").
    ingredients = []
    for elem in heading.find_all_next():
        if elem.name in ("h2", "h3"):
            break
        if elem.name == "li":
            text = elem.get_text(strip=True)
            if text:
                ingredients.append(text)
    return ingredients


@app.route("/parse", methods=["GET"])
def parse_recipe():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "missing 'url' query parameter"}), 400

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": f"kon pagina niet ophalen: {e}"}), 502

    ingredients = extract_ingredients(resp.text)

    if not ingredients:
        return jsonify(
            {"error": "geen ingrediënten gevonden - paginastructuur kan gewijzigd zijn"}
        ), 422

    return jsonify({"ingredients": ingredients, "source_url": url})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
