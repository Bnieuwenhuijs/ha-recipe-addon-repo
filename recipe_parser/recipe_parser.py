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

import os

from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (HomeAssistant recipe-parser)"}

# Beschikbaar zodra de add-on draait met homeassistant_api: true in config.yaml.
# Ontbreekt bij lokaal draaien buiten Home Assistant (bewust geen fallback -
# dat maakt lokaal testen van het formulier mogelijk zonder HA-verbinding).
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_API_BASE = "http://supervisor/core/api"
DEFAULT_TODO_ENTITY = "todo.thuis"


def add_ingredient_to_todo(entity_id: str, item: str):
    resp = requests.post(
        f"{HA_API_BASE}/services/todo/add_item",
        headers={
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"entity_id": entity_id, "item": item},
        timeout=10,
    )
    resp.raise_for_status()


def extract_ingredients(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Voedingscentrum.nl markeert elk ingrediënt met de schema.org-attribuut
    # itemprop="recipeIngredient", ook als de lijst over meerdere <ul>-kolommen
    # verdeeld is (div.columns.group). Geverifieerd tegen meerdere live
    # recepten - dit is robuuster dan op de koptekst "Ingrediënten" te zoeken.
    items = soup.find_all(attrs={"itemprop": "recipeIngredient"})
    ingredients = [text for i in items if (text := i.get_text(strip=True))]
    if ingredients:
        return ingredients

    # Fallback voor pagina's zonder itemprop-markering: zoek de kop
    # "Ingrediënten" (h2/h3) en loop door alle volgende elementen in
    # document-volgorde (dus ook geneste <ul>'s in kolommen) tot de
    # volgende kop (bijv. "Bereiding").
    heading = soup.find(
        lambda tag: tag.name in ("h2", "h3")
        and "ingredi" in tag.get_text(strip=True).lower()
    )
    if not heading:
        return []

    for elem in heading.find_all_next():
        if elem.name in ("h2", "h3"):
            break
        if elem.name == "li":
            text = elem.get_text(strip=True)
            if text:
                ingredients.append(text)
    return ingredients


@app.route("/", methods=["GET", "POST"])
def index():
    ingredients = None
    message = None
    message_class = None
    url = ""
    entity_id = DEFAULT_TODO_ENTITY

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        entity_id = request.form.get("entity_id", "").strip() or DEFAULT_TODO_ENTITY

        if not url:
            message, message_class = "Vul een recept-URL in.", "error"
        else:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                resp.raise_for_status()
            except requests.RequestException as e:
                message, message_class = f"Kon pagina niet ophalen: {e}", "error"
            else:
                ingredients = extract_ingredients(resp.text)
                if not ingredients:
                    message, message_class = (
                        "Geen ingrediënten gevonden - paginastructuur kan gewijzigd zijn.",
                        "error",
                    )
                elif not SUPERVISOR_TOKEN:
                    message, message_class = (
                        "Ingrediënten gevonden, maar niet toegevoegd: geen SUPERVISOR_TOKEN "
                        "beschikbaar (draai je dit lokaal buiten Home Assistant?).",
                        "warning",
                    )
                else:
                    added, failed = 0, []
                    for ingredient in ingredients:
                        try:
                            add_ingredient_to_todo(entity_id, ingredient)
                            added += 1
                        except requests.RequestException:
                            failed.append(ingredient)
                    if failed:
                        message, message_class = (
                            f"{added}/{len(ingredients)} ingrediënten toegevoegd aan "
                            f"{entity_id}. Mislukt: {', '.join(failed)}",
                            "warning",
                        )
                    else:
                        message, message_class = (
                            f"Alle {added} ingrediënten toegevoegd aan {entity_id}.",
                            "success",
                        )

    return render_template(
        "index.html",
        ingredients=ingredients,
        message=message,
        message_class=message_class,
        url=url,
        entity_id=entity_id,
    )


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


@app.route("/debug", methods=["GET"])
def debug():
    """
    Diagnose-endpoint om via de browser te checken of de Home Assistant
    API bereikbaar is, zonder dat daarvoor terminal/SSH-toegang nodig is.
    """
    info = {"supervisor_token_present": bool(SUPERVISOR_TOKEN)}

    if SUPERVISOR_TOKEN:
        try:
            resp = requests.get(
                f"{HA_API_BASE}/",
                headers={"Authorization": f"Bearer {SUPERVISOR_TOKEN}"},
                timeout=10,
            )
            info["ha_api_reachable"] = True
            info["ha_api_status_code"] = resp.status_code
            info["ha_api_response"] = resp.text[:200]
        except requests.RequestException as e:
            info["ha_api_reachable"] = False
            info["ha_api_error"] = str(e)

    return jsonify(info)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
