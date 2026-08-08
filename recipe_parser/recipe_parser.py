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

import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Elk ingrediënt kost een aparte todo.add_item-call, en Home Assistant geeft
# die service pas terug als Bring het item in de cloud heeft opgeslagen (~1
# seconde per stuk). Achter elkaar duurt een recept van 11 ingrediënten
# daardoor ruim 10 seconden, dus voeren we ze in kleine groepjes tegelijk uit.
# Bewust bescheiden: elk item is een eigen schrijfactie naar Bring, en met een
# paar tegelijk halen we vrijwel de hele winst zonder Bring te overvragen.
MAX_PARALLEL_ADDS = 5

# requests.Session is niet gegarandeerd thread-safe, dus krijgt elke thread
# zijn eigen sessie. Binnen een thread blijft de verbinding hergebruikt.
_local = threading.local()


def _session() -> requests.Session:
    session = getattr(_local, "session", None)
    if session is None:
        session = _local.session = requests.Session()
    return session


# Eén vaste pool voor de hele add-on: de threads (en dus hun verbindingen naar
# de Supervisor) blijven bestaan tussen recepten door, en het aantal gelijktijdige
# schrijfacties richting Bring blijft begrensd, ook als er meerdere tabbladen open staan.
_add_pool = ThreadPoolExecutor(
    max_workers=MAX_PARALLEL_ADDS, thread_name_prefix="todo-add"
)


def add_ingredient_to_todo(entity_id: str, item: str, description: str = ""):
    payload = {"entity_id": entity_id, "item": item}
    if description:
        payload["description"] = description
    resp = _session().post(
        f"{HA_API_BASE}/services/todo/add_item",
        headers={
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()


def add_ingredients_to_todo(entity_id: str, items):
    """
    Zet alle ingrediënten op de lijst en geef terug hoeveel er gelukt zijn en
    welke niet. Mislukte items worden niet opnieuw geprobeerd: todo.add_item
    is niet idempotent, dus een retry na een timeout kan een dubbel item
    opleveren. Liever eerlijk melden wat er misging.
    """
    if not items:
        return 0, []

    failed = {}
    futures = {
        _add_pool.submit(add_ingredient_to_todo, entity_id, title, description): index
        for index, (title, description) in enumerate(items)
    }
    for future in as_completed(futures):
        index = futures[future]
        try:
            future.result()
        except requests.RequestException:
            failed[index] = items[index][0]

    # Mislukte items in receptvolgorde, niet in de volgorde waarin ze terugkwamen.
    return len(items) - len(failed), [failed[i] for i in sorted(failed)]


FRACTIONS = "½¼¾⅓⅔⅛⅜⅝⅞"
UNITS = (
    "gram|gr|g|kilogram|kilo|kg|milliliter|ml|liter|l|cm|"
    "eetlepels|eetlepel|el|theelepels|theelepel|tl|"
    "takjes|takje|takken|tak|blaadjes|blaadje|"
    "teentjes|teentje|tenen|teen|stengels|stengel|"
    "snufjes|snufje|snuf|mespuntjes|mespuntje|mespunt|"
    "scheutjes|scheutje|scheuten|scheut|"
    "blikjes|blikje|blikken|blik|blokjes|blokje|"
    "pakjes|pakje|pakken|pak|zakjes|zakje|zakken|zak|"
    "bosjes|bosje|bossen|bos|bollen|bol|kroppen|krop|"
    "stuks|stuk|plakjes|plakje|plakken|plak|sneetjes|sneetje|"
    "bolletjes|bolletje|handjes|handje|handvol|"
    "potjes|potje|potten|pot|flesjes|flesje|kopjes|kopje|kop"
)

# Woorden die iets zeggen over het product, maar niet het product zelf zijn.
# Alleen gebruikt als de hele naam nergens op matcht: "biologische volkorenorzo"
# levert dan de titel "Volkorenorzo" op in plaats van de hele zin.
QUALIFIER_WORDS = {
    "biologisch", "biologische", "bio", "verse", "vers", "diepvries",
    "gerookte", "gerookt", "gedroogde", "gedroogd", "gezouten", "ongezouten",
    "geroosterde", "geroosterd", "gepelde", "gepeld", "rauwe", "rauw",
    "milde", "mild", "pittige", "pittig", "donkere", "donker", "lichte",
    "magere", "mager", "halfvolle", "volle", "kleine", "grote", "fijne",
    "grove", "eetrijpe", "griekse", "italiaanse", "verspakket", "extra",
    "mini", "jonge", "oude", "zoete", "verpakte", "voorgesneden",
}

# Keukengerei dat sommige sites tussen de ingrediënten zet (leukerecepten.nl
# noemt bijvoorbeeld een staafmixer). Dat hoort niet op een boodschappenlijst.
KITCHEN_EQUIPMENT = {
    "staafmixer", "blender", "keukenmachine", "foodprocessor", "hakmolen",
    "oven", "koekenpan", "hapjespan", "wok", "bakvorm", "springvorm",
    "ovenschaal", "garde", "spatel", "pollepel", "snijplank", "mandoline",
    "vergiet", "rasp", "deegroller", "airfryer", "barbecue", "bbq",
}

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


def _build_matchers():
    """
    Compileer alle zoektermen één keer. Dit moet vooraf: er zijn meer termen
    dan de regex-cache van de standaardbibliotheek aankan, dus re.search()
    zou anders bij elk ingrediënt élk patroon opnieuw compileren.
    """
    matchers = []
    for term, canonical in LOOKUP.items():
        # Term moet aan het begin van een woord staan. Korte termen ('sla',
        # 'kip') moeten een heel woord zijn, anders matchen ze in 'slagroom'.
        pattern = r"(?<![a-z0-9])" + re.escape(term)
        if len(term) < 4:
            pattern += r"(?![a-z0-9])"
        matchers.append((re.compile(pattern), term, canonical))
    return matchers


MATCHERS = _build_matchers()


def match_bring_item(name: str):
    """
    Zoek de Bring-artikelnaam die bij deze ingrediëntnaam hoort. Geeft de
    Bring-naam terug plus het woord waarop hij gevonden is. Bij meerdere
    treffers wint de term die het vroegst in de tekst begint (het kernwoord
    staat vooraan: 'sojasaus met minder zout' is sojasaus, geen zout), en bij
    gelijke positie de langste term.
    """
    norm = _normalize(name)
    best_key = None
    best = (None, None)

    for pattern, term, canonical in MATCHERS:
        match = pattern.search(norm)
        if match:
            key = (match.start(), -len(term))
            if best_key is None or key < best_key:
                best_key, best = key, (canonical, term)

    return best


def _title_forms(title: str):
    """Schrijfwijzen waarin de titel in de omschrijving terug kan komen."""
    norm = _normalize(title)
    # Zonder leestekens, zodat "pinda's" en "pindas" hetzelfde opleveren.
    candidates = [re.sub(r"[^a-z0-9]", "", norm)]
    candidates += [
        re.sub(r"[^a-z0-9]", "", part) for part in re.split(r"[\s/-]+", norm)
    ]

    forms = set()
    for candidate in candidates:
        if not candidate:
            continue
        # Zowel korter als langer: "limoen" moet ook "limoenen" afvangen, en
        # "uien" ook "ui". Niet of/of, want dan valt één kant weg.
        forms.add(candidate)
        forms.add(candidate + "en")
        forms.add(candidate + "s")
        if candidate.endswith("en") and len(candidate) > 3:
            forms.add(candidate[:-2])
        elif candidate.endswith("s") and len(candidate) > 3:
            forms.add(candidate[:-1])
    return forms


def _is_same_product(term: str, title: str) -> bool:
    """
    Is dit hetzelfde artikel als de titel, alleen anders geschreven
    ('bosuien' bij 'Bosui / Lente-ui', 'hüttenkäse' bij 'Huttenkaas')? Zo ja,
    dan is het woord overbodig in de omschrijving. Iets specifiekers
    ('tagliatelle' bij 'Pasta', 'kipfilet' bij 'Kip') blijft juist staan.
    """
    left = re.sub(r"[\s/-]", "", _normalize(term))
    right = re.sub(r"[\s/-]", "", _normalize(title))
    if left == right:
        return True
    shared = len(os.path.commonprefix([left, right]))
    return shared >= 4 and min(len(left), len(right)) >= 4


def _without_title_words(text: str, title: str, term: str) -> str:
    """
    Haal uit de omschrijving weg wat de titel al zegt, zodat er geen
    "Groenten / 200 gram groenten" ontstaat. Woorden die wél iets toevoegen
    ("verse", "halfvolle", "vloeibare") blijven staan.
    """
    forms = _title_forms(title)
    if term and _is_same_product(term, title):
        forms.update(_title_forms(term))

    kept = []
    for word in text.split():
        # Leestekens weg, zodat "(olijf)olie" ook als "olijfolie" herkend wordt.
        bare = re.sub(r"[^a-z0-9]", "", _normalize(word))
        if bare and bare in forms:
            continue
        kept.append(word)
    return " ".join(kept)


def _without_leading_qualifiers(name: str) -> str:
    """Haal beschrijvende woorden vooraan weg: 'biologische volkorenorzo'."""
    words = name.split()
    while len(words) > 1 and _normalize(words[0]).strip("().,;:") in QUALIFIER_WORDS:
        words = words[1:]
    return " ".join(words)


def is_kitchen_equipment(text: str) -> bool:
    """Keukengerei hoort niet op de boodschappenlijst."""
    bare = re.sub(r"[^a-z0-9 ]", "", _normalize(text)).strip()
    return bare in KITCHEN_EQUIPMENT


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

    matched, term = match_bring_item(head)
    core = head
    if not matched:
        # Niets herkend: probeer het nog eens zonder de bijvoeglijke woorden
        # vooraan. Dat gebeurt pas nu, zodat catalogusnamen die er zelf mee
        # beginnen ("Zoete aardappelen", "Witte bonen") ongemoeid blijven.
        core = _without_leading_qualifiers(head)
        if core != head:
            matched, term = match_bring_item(core)

    # De titel komt van de kale naam, maar de omschrijving houdt de
    # weggelaten woorden ("biologische", "verse") gewoon vast.
    title = matched or (core[:1].upper() + core[1:])

    if _normalize(title) == _normalize(head):
        parts = [quantity, tail]
    else:
        # De Bring-naam wijkt af van wat het recept schrijft ('Pasta' voor
        # tagliatelle), dus de oorspronkelijke tekst hoort in de omschrijving -
        # maar zonder de woorden die de titel al zegt.
        parts = [quantity, _without_title_words(head, title, term), tail]

    description = " ".join(p for p in parts if p)
    description = re.sub(r"\s+([,;])", r"\1", description).strip(" ,;-")
    return title, description


def _ingredients_from_json_ld(soup):
    """
    Haal recipeIngredient uit schema.org JSON-LD. Leukerecepten.nl en ah.nl
    zetten hun recept zo op de pagina (en veel andere receptsites ook), soms
    verstopt in een @graph of een lijst met meerdere blokken.
    """
    ingredients = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue  # niet elke site levert geldige JSON

        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                values = node.get("recipeIngredient")
                if isinstance(values, list):
                    ingredients.extend(
                        str(v).strip() for v in values if str(v).strip()
                    )
                stack.extend(node.values())
    return ingredients


def extract_ingredients(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Voedingscentrum.nl markeert elk ingrediënt met de schema.org-attribuut
    # itemprop="recipeIngredient", ook als de lijst over meerdere <ul>-kolommen
    # verdeeld is (div.columns.group). Geverifieerd tegen meerdere live
    # recepten - dit is robuuster dan op de koptekst "Ingrediënten" te zoeken.
    items = soup.find_all(attrs={"itemprop": "recipeIngredient"})
    ingredients = [text for i in items if (text := i.get_text(strip=True))]
    if ingredients:
        return _drop_equipment(ingredients)

    # Dezelfde schema.org-gegevens, maar als JSON-LD in een <script>.
    ingredients = _ingredients_from_json_ld(soup)
    if ingredients:
        return _drop_equipment(ingredients)

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
    return _drop_equipment(ingredients)


def _drop_equipment(ingredients):
    return [i for i in ingredients if not is_kitchen_equipment(i)]


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
                    added, failed = add_ingredients_to_todo(entity_id, items)
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
