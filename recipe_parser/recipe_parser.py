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
import re
import unicodedata

from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup

from bring_catalog import CATALOG, SYNONYMS

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (HomeAssistant recipe-parser)"}

# Beschikbaar zodra de add-on draait met homeassistant_api: true in config.yaml.
# Ontbreekt bij lokaal draaien buiten Home Assistant (bewust geen fallback -
# dat maakt lokaal testen van het formulier mogelijk zonder HA-verbinding).
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_API_BASE = "http://supervisor/core/api"
DEFAULT_TODO_ENTITY = "todo.thuis"

# Eén hergebruikte sessie voor de todo.add_item-calls naar de Supervisor,
# zodat de TCP-connectie hergebruikt wordt in plaats van er per ingrediënt
# (tot wel 17x per recept) een nieuwe op te zetten.
http_session = requests.Session()


def add_ingredient_to_todo(entity_id: str, item: str, description: str = ""):
    payload = {"entity_id": entity_id, "item": item}
    if description:
        payload["description"] = description
    resp = http_session.post(
        f"{HA_API_BASE}/services/todo/add_item",
        headers={
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()


FRACTIONS = "½¼¾⅓⅔⅛⅜⅝⅞"
UNITS = (
    "gram|gr|g|kilogram|kilo|kg|milliliter|ml|liter|l|"
    "eetlepels|eetlepel|el|theelepels|theelepel|tl|"
    "takjes|takje|blaadjes|blaadje|teentjes|teentje|"
    "snufjes|snufje|mespuntjes|mespuntje|mespunt|scheutjes|scheutje|"
    "blikjes|blikje|blikken|blik|pakjes|pakje|pakken|pak|"
    "bosjes|bosje|bossen|bos|stuks|stuk|plakjes|plakje|plakken|plak|"
    "bolletjes|bolletje|handjes|handje|handvol|zakjes|zakje|"
    "potjes|potje|flesjes|flesje|kopjes|kopje|kop"
)

# Voorloop met hoeveelheid en/of maat: "200 gram", "1 teentje", "½", "2 eetlepels".
QUANTITY_RE = re.compile(
    rf"^\s*(?:(?:\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?|[{FRACTIONS}])\s*)?"
    rf"(?:(?:{UNITS})\b\s*)?",
    re.IGNORECASE,
)

# Alles hierna is een toelichting op het artikel, niet de artikelnaam zelf:
# "sojasaus met minder zout", "rauwkost, zoals rodekool", "kaas (geraspt)".
QUALIFIER_RE = re.compile(
    r"\s*(?:[,;(]|\bmet\b|\bzonder\b|\bof\b|\bzoals\b|\bnaar smaak\b)",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Kleine letters zonder accenten, zodat 'tempé' en 'tempe' gelijk zijn."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _build_lookup():
    """Zoektabel van genormaliseerde term -> canonieke Bring-naam."""
    table = {}

    def add(term, canonical):
        term = _normalize(term).strip()
        if len(term) >= 3:
            table.setdefault(term, canonical)

    for name in CATALOG:
        for variant in name.split("/"):
            variant = variant.strip()
            add(variant, name)
            # Simpele enkelvoud/meervoud-varianten, alleen als ze lang genoeg
            # zijn om niet per ongeluk in een ander woord te matchen.
            norm = _normalize(variant)
            if len(norm) >= 5:
                if norm.endswith("en"):
                    add(norm[:-2], name)
                elif norm.endswith("s"):
                    add(norm[:-1], name)
                else:
                    add(norm + "en", name)
                    add(norm + "s", name)

    # Synoniemen winnen van afgeleide varianten.
    for alias, canonical in SYNONYMS.items():
        table[_normalize(alias).strip()] = canonical

    return table


LOOKUP = _build_lookup()


def match_bring_item(name: str):
    """
    Zoek de Bring-artikelnaam die bij deze ingrediëntnaam hoort. Bij meerdere
    treffers wint de term die het vroegst in de tekst begint (het kernwoord
    staat vooraan: 'sojasaus met minder zout' is sojasaus, geen zout), en bij
    gelijke positie de langste term.
    """
    norm = _normalize(name)
    best_key = None
    best_name = None

    for term, canonical in LOOKUP.items():
        # Term moet aan het begin van een woord staan. Korte termen ('sla',
        # 'kip') moeten een heel woord zijn, anders matchen ze in 'slagroom'.
        pattern = r"(?<![a-z0-9])" + re.escape(term)
        if len(term) < 4:
            pattern += r"(?![a-z0-9])"
        match = re.search(pattern, norm)
        if match:
            key = (match.start(), -len(term))
            if best_key is None or key < best_key:
                best_key, best_name = key, canonical

    return best_name


def split_ingredient(text: str):
    """
    Splits "400 gram prei" in ("Prei", "400 gram"): de artikelnaam als titel
    zodat Bring het juiste icoon toont, de rest als omschrijving.
    """
    text = " ".join(text.split())

    quantity = QUANTITY_RE.match(text).group().strip()
    name_part = text[len(QUANTITY_RE.match(text).group()):].strip()
    if not name_part:  # bijv. alleen "peper" - dan is er geen hoeveelheid
        quantity, name_part = "", text

    qualifier = QUALIFIER_RE.search(name_part, pos=1)
    head = name_part[: qualifier.start()].strip() if qualifier else name_part
    tail = name_part[qualifier.start():].strip() if qualifier else ""

    title = match_bring_item(head) or (head[:1].upper() + head[1:])

    if _normalize(title) == _normalize(head):
        parts = [quantity, tail]
    else:
        # De Bring-naam wijkt af van wat het recept schrijft ('Pasta' voor
        # tagliatelle), dus de oorspronkelijke tekst hoort in de omschrijving.
        parts = [quantity, head, tail]

    description = " ".join(p for p in parts if p)
    description = re.sub(r"\s+([,;])", r"\1", description).strip(" ,;-")
    return title, description


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
    items = []
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
                items = [split_ingredient(i) for i in ingredients]
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
                    for title, description in items:
                        try:
                            add_ingredient_to_todo(entity_id, title, description)
                            added += 1
                        except requests.RequestException:
                            failed.append(title)
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
        items=items,
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

    return jsonify(
        {
            "ingredients": ingredients,
            # Zelfde ingrediënten, maar gesplitst in een Bring-artikelnaam en
            # de bijbehorende hoeveelheid - handig voor todo.add_item.
            "items": [
                {"title": title, "description": description}
                for title, description in (split_ingredient(i) for i in ingredients)
            ],
            "source_url": url,
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/debug", methods=["GET"])
def debug():
    """
    Diagnose-endpoint om via de browser te checken of de Home Assistant
    API bereikbaar is, zonder dat daarvoor terminal/SSH-toegang nodig is.
    """
    info = {
        "supervisor_token_present": bool(SUPERVISOR_TOKEN),
        # Alleen namen, geen waarden - zodat we kunnen zien wat de
        # container daadwerkelijk aan omgevingsvariabelen heeft gekregen
        # zonder geheimen bloot te leggen.
        "env_var_names": sorted(os.environ.keys()),
    }

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
