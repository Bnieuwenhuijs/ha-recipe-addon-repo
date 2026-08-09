"""
Kleine microservice die receptpagina's ophaalt, de ingrediënten eruit haalt
en ze in een Home Assistant todo-lijst (bijv. Bring) zet.

Het formulier accepteert geplakte tekst met meerdere links erin - bijvoorbeeld
een stuk WhatsApp-geschiedenis waarin recepten zijn gedeeld. Alle links worden
opgehaald, je kiest welke recepten mee moeten, en artikelen die in meerdere
recepten voorkomen worden tot één regel samengevoegd.

Endpoint voor automatisering:
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

from bring_catalog import CATALOG, SYNONYMS, PANTRY, DRIED_ONLY_PANTRY

app = Flask(__name__)

# Een gewone browser-User-Agent: een deel van de receptsites geeft een
# onbekende client een 403 of een lege pagina.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

# De deelknop van de Albert Heijn-app maakt links als ah.nl/r/1196876. Die
# geven zelf een 404, maar hetzelfde nummer werkt wel als recept-URL, die
# daarna doorstuurt naar de volledige pagina.
AH_SHORT_RE = re.compile(r"^https?://(?:www\.)?ah\.nl/r/(\d+)/?$", re.IGNORECASE)


def normalize_url(url: str) -> str:
    """Herschrijf linkvormen die zelf niet op te halen zijn."""
    match = AH_SHORT_RE.match(url.strip())
    if match:
        return f"https://www.ah.nl/allerhande/recept/R-R{match.group(1)}"
    return url

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

# Aparte pool voor het ophalen van receptpagina's, zodat een lijst van vijf
# recepten in ongeveer de tijd van één opgehaald is. Los van de pool hierboven,
# zodat ophalen en toevoegen elkaar niet in de weg zitten.
MAX_PARALLEL_FETCHES = 5
_fetch_pool = ThreadPoolExecutor(
    max_workers=MAX_PARALLEL_FETCHES, thread_name_prefix="recipe-fetch"
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
    "potjes|potje|potten|pot|flesjes|flesje|kopjes|kopje|kop|"
    # Engelse maten, zoals in recepten die met Claude gemaakt zijn
    "tablespoons|tablespoon|tbsp|tbs|teaspoons|teaspoon|tsp|"
    "pinches|pinch|cups|cup|cloves|clove|ounces|ounce|oz|pounds|pound|lb"
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
    "dunne", "dikke", "gemalen", "geraspte", "gehakte", "gesnipperde",
}

# Keukengerei dat sommige sites tussen de ingrediënten zet (leukerecepten.nl
# noemt bijvoorbeeld een staafmixer). Dat hoort niet op een boodschappenlijst.
KITCHEN_EQUIPMENT = {
    "staafmixer", "blender", "keukenmachine", "foodprocessor", "hakmolen",
    "oven", "koekenpan", "hapjespan", "wok", "bakvorm", "springvorm",
    "ovenschaal", "garde", "spatel", "pollepel", "snijplank", "mandoline",
    "vergiet", "rasp", "deegroller", "airfryer", "barbecue", "bbq",
}

# Voorloop met hoeveelheid en/of maat: "200 gram", "1 teentje", "½",
# "2 eetlepels", "3 tbsp", en gemengde breuken als "44 1/3 ml" en "1 1/4 ml".
# De gemengde breuk moet vooraan staan, anders pakt hij alleen het hele getal.
AMOUNT = (
    rf"\d+\s+\d+\s*/\s*\d+"      # 44 1/3
    rf"|\d+\s*/\s*\d+"           # 1/2
    rf"|\d+(?:[.,]\d+)?"         # 400  of  4.9
    rf"|[{FRACTIONS}]"           # ½
)
QUANTITY_RE = re.compile(
    rf"^\s*(?:(?:{AMOUNT})\s*)?(?:(?:{UNITS})\b\s*)?",
    re.IGNORECASE,
)

# Alles hierna is een toelichting op het artikel, niet de artikelnaam zelf:
# "sojasaus met minder zout", "rauwkost, zoals rodekool", "kaas (geraspt)".
QUALIFIER_RE = re.compile(
    r"\s*(?:[,;(]|\bmet\b|\bzonder\b|\bof\b|\bzoals\b|\buit\b|\bnaar smaak\b)",
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


# Woorden die alleen zeggen in welke vorm je het product krijgt. Staan ze
# vast aan de productnaam ("knoflookteentjes", "bloemkoolroosjes"), dan is dat
# een schrijfwijze van hetzelfde artikel en niet iets anders.
PORTION_SUFFIXES = {
    "teentje", "teentjes", "teen", "tenen", "blokje", "blokjes",
    "roosje", "roosjes", "reepje", "reepjes", "ring", "ringen",
    "partje", "partjes", "stukje", "stukjes", "plakje", "plakjes",
    "blaadje", "blaadjes", "takje", "takjes", "sneetje", "sneetjes",
    "bolletje", "bolletjes", "staafje", "staafjes",
}


def _is_same_product(term: str, title: str) -> bool:
    """
    Is dit hetzelfde artikel als de titel, alleen anders geschreven
    ('bosuien' bij 'Bosui / Lente-ui', 'hüttenkäse' bij 'Huttenkaas')? Zo ja,
    dan is het woord overbodig in de omschrijving. Iets specifiekers
    ('tagliatelle' bij 'Pasta', 'kipfilet' bij 'Kip') blijft juist staan.
    """
    left = re.sub(r"[\s/-]", "", _normalize(term))
    # Een titel als "Bosui / Lente-ui" bestaat uit meerdere schrijfwijzen;
    # het volstaat als de term met één daarvan overeenkomt.
    for part in [title] + re.split(r"\s*/\s*", title):
        right = re.sub(r"[\s/-]", "", _normalize(part))
        if not right:
            continue
        if left == right:
            return True
        shared = len(os.path.commonprefix([left, right]))
        if shared >= 4 and min(len(left), len(right)) >= 4:
            return True
    return False


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
        if bare and (bare in forms or _is_portion_of(bare, forms)):
            continue
        kept.append(word)
    return " ".join(kept)


def _is_portion_of(word: str, forms) -> bool:
    """'knoflookteentjes' is knoflook, 'citroensap' is iets anders."""
    for form in forms:
        if len(form) >= 4 and word.startswith(form):
            if word[len(form):] in PORTION_SUFFIXES:
                return True
    return False


def _without_qualifier_words(name: str) -> str:
    """
    Haal beschrijvende woorden aan de randen weg: 'biologische volkorenorzo'
    wordt 'volkorenorzo', 'komijnzaad gemalen' wordt 'komijnzaad'. Zo krijgen
    twee recepten die hetzelfde anders opschrijven dezelfde titel.
    """
    words = name.split()

    def is_qualifier(word):
        return _normalize(word).strip("().,;:") in QUALIFIER_WORDS

    while len(words) > 1 and is_qualifier(words[0]):
        words = words[1:]
    while len(words) > 1 and is_qualifier(words[-1]):
        words = words[:-1]
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

    if head.endswith("-"):
        # "zonnebloem- of arachideolie": het product staat pas na het streepje,
        # dus hier valt niets af te splitsen.
        head, tail = name_part, ""

    matched, term = match_bring_item(head)
    core = head
    if not matched:
        # Niets herkend: probeer het nog eens zonder de beschrijvende woorden
        # eromheen. Dat gebeurt pas nu, zodat catalogusnamen die er zelf mee
        # beginnen ("Zoete aardappelen", "Witte bonen") ongemoeid blijven.
        core = _without_qualifier_words(head)
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


def _json_ld_blocks(soup):
    """
    Alle JSON-LD-blokken als Python-gegevens. Het type-attribuut wordt los
    vergeleken (sommige sites schrijven "application/ld+json; charset=utf-8"),
    en strict=False laat losse regeleindes binnen teksten toe - zonder dat
    laatste sneuvelt bijvoorbeeld savorysweets.nl op één afbreking.
    """
    blocks = []
    for tag in soup.find_all(
        "script", type=lambda value: value and "ld+json" in value.lower()
    ):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            blocks.append(json.loads(raw, strict=False))
        except (ValueError, TypeError):
            continue  # niet elke site levert bruikbare JSON
    return blocks


def _walk_json_ld(blocks, key):
    """Zoek een sleutel in geneste JSON-LD (vaak verstopt in een @graph)."""
    for block in blocks:
        stack = [block]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                if key in node:
                    yield node
                stack.extend(node.values())


def _as_ingredient_list(values):
    if isinstance(values, list):
        return [str(v).strip() for v in values if str(v).strip()]
    if isinstance(values, str) and values.strip():
        return [values.strip()]
    return []


def _is_recipe_node(node) -> bool:
    types = node.get("@type", "")
    if isinstance(types, list):
        return any("recipe" in str(t).lower() for t in types)
    return "recipe" in str(types).lower()


def _ingredients_from_json_ld(soup):
    """
    Haal de ingrediënten uit schema.org JSON-LD. De meeste receptsites zetten
    hun recept zo op de pagina.
    """
    blocks = _json_ld_blocks(soup)

    ingredients = []
    for node in _walk_json_ld(blocks, "recipeIngredient"):
        ingredients.extend(_as_ingredient_list(node.get("recipeIngredient")))
    if ingredients:
        return ingredients

    # Oudere schema.org-versie gebruikte "ingredients" (libelle-lekker.be doet
    # dat nog). Dat woord is te algemeen om zomaar te vertrouwen, dus alleen
    # binnen een node die zichzelf een Recipe noemt.
    for node in _walk_json_ld(blocks, "ingredients"):
        if _is_recipe_node(node):
            ingredients.extend(_as_ingredient_list(node.get("ingredients")))
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

    # Laatste redmiddel voor pagina's zonder schema.org-gegevens: zoek de kop
    # "Ingrediënten" en verzamel de lijstitems die erop volgen.
    return _drop_equipment(_ingredients_after_heading(soup))


HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

# Koppen die de ingrediëntenlijst onderverdelen in plaats van afsluiten:
# "Voor 2 personen", "Voor de saus", "Ingrediënten deeg".
SUBHEADING_RE = re.compile(r"^\s*(voor\b|ingredi)", re.IGNORECASE)

# Lijstitems hier binnen zijn navigatie of "lees ook", geen ingrediënten.
NON_CONTENT_PARENTS = ("nav", "aside", "footer", "header", "form")


def _ingredients_after_heading(soup):
    heading = soup.find(
        lambda tag: tag.name in HEADING_TAGS
        and "ingredi" in tag.get_text(strip=True).lower()
    )
    if not heading:
        return []

    ingredients = []
    for elem in heading.find_all_next():
        if elem.name in HEADING_TAGS:
            # Voor het eerste ingrediënt kan er nog een tussenkop staan
            # ("Voor 2 personen"); die sluit de lijst niet af.
            if ingredients and not SUBHEADING_RE.match(elem.get_text(strip=True)):
                break
            continue
        if elem.name != "li":
            continue
        if elem.find_parent(NON_CONTENT_PARENTS):
            continue
        text = elem.get_text(strip=True)
        # Hele alinea's zijn geen ingrediënt maar bereidingstekst of een tip.
        if text and len(text) <= 200:
            ingredients.append(text)
    return ingredients


def _drop_equipment(ingredients):
    return [i for i in ingredients if not is_kitchen_equipment(i)]


# Links uit geplakte tekst. Sluit afsluitende leestekens uit, want in
# "kijk hier: https://site.nl/recept." hoort de punt niet bij de link.
URL_RE = re.compile(r"https?://[^\s<>\"']+")

# WhatsApp zet voor elk bericht "[05/07, 13:43] Naam: ". De link staat soms op
# een volgende regel, dus onthouden we de laatst geziene datum.
WHATSAPP_LINE_RE = re.compile(r"^\[(\d{1,2}[/-]\d{1,2})[^\]]*\]")


def find_recipe_links(text: str):
    """
    Haal de links uit geplakte tekst (bijv. een stuk WhatsApp-geschiedenis),
    met de datum van het bericht waar ze in stonden. Dubbele links vallen weg.
    """
    links = []
    seen = set()
    date = ""

    for line in text.splitlines():
        stamp = WHATSAPP_LINE_RE.match(line.strip())
        if stamp:
            date = stamp.group(1)
        for url in URL_RE.findall(line):
            url = url.rstrip(".,;:!?)")
            if url not in seen:
                seen.add(url)
                links.append({"url": url, "date": date})
    return links


# Een bericht in een WhatsApp-export: "[19/07, 16:44] Naam: eerste regel".
WHATSAPP_MESSAGE_RE = re.compile(r"^\[(\d{1,2}[/-]\d{1,2})[^\]]*\]\s*[^:]{1,60}?:\s?(.*)$")

# Recepten die als tekst geplakt worden (bijv. gemaakt met Claude) hebben een
# kopje boven de ingrediënten en daarna een kopje voor de bereiding.
INGREDIENTS_HEADING_RE = re.compile(
    r"^\s*(?:ingredi[eë]nt(?:en|s)?|ingredients)\s*:?\s*$", re.IGNORECASE
)
NEXT_SECTION_RE = re.compile(
    r"^\s*(?:steps?|stappen|bereiding(?:swijze)?|instructions?|method|"
    r"notes?|notities|opmerkingen|tips?|voorbereiding)\s*:?\s*$",
    re.IGNORECASE,
)
BULLET_RE = re.compile(r"^\s*[-*•‣▪●⁃·]\s*")


def _split_messages(text: str):
    """Deel geplakte tekst op in losse berichten, met hun datum."""
    messages = []
    for line in text.splitlines():
        match = WHATSAPP_MESSAGE_RE.match(line)
        if match:
            messages.append({"date": match.group(1), "lines": [match.group(2)]})
        elif messages:
            messages[-1]["lines"].append(line)
        else:
            # Tekst zonder WhatsApp-kopregel, bijv. één recept geplakt.
            messages.append({"date": "", "lines": [line]})
    return messages


def _ingredients_from_lines(lines):
    """De regels tussen het kopje 'Ingredients' en het volgende kopje."""
    start = None
    for index, line in enumerate(lines):
        if INGREDIENTS_HEADING_RE.match(line):
            start = index + 1
            break
    if start is None:
        return []

    ingredients = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            # Een lege regel sluit de lijst af, maar niet vóór het begin.
            if ingredients:
                break
            continue
        if NEXT_SECTION_RE.match(stripped):
            break
        ingredients.append(BULLET_RE.sub("", stripped).strip())
    return [i for i in ingredients if i]


def find_text_recipes(text: str):
    """
    Recepten die als tekst geplakt zijn in plaats van als link. De titel is de
    eerste regel van het bericht; de ingrediënten staan onder een kopje.
    """
    recipes = []
    for index, message in enumerate(_split_messages(text)):
        ingredients = _ingredients_from_lines(message["lines"])
        if not ingredients:
            continue
        title = next((l.strip() for l in message["lines"] if l.strip()), "Recept")
        recipes.append({
            "index": index,
            "title": title,
            "date": message["date"],
            "ingredients": _drop_equipment(ingredients),
        })
    return recipes


def extract_title(soup, fallback: str = "") -> str:
    """Naam van het recept, zodat je in het overzicht ziet wat je aanvinkt."""
    blocks = _json_ld_blocks(soup)
    for key in ("recipeIngredient", "ingredients"):
        for node in _walk_json_ld(blocks, key):
            name = node.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

    for candidate in (soup.find("h1"), soup.find("title")):
        if candidate:
            name = candidate.get_text(strip=True)
            if name:
                return name
    return fallback


# Voedingscentrum stuurt een verwijderd recept door naar /nl/404.aspx, maar
# meldt gewoon HTTP 200. Dan is "recept bestaat niet meer" een duidelijker
# antwoord dan "geen ingrediënten gevonden".
MISSING_PAGE_RE = re.compile(r"/404|niet gevonden|not found", re.IGNORECASE)


def _looks_like_a_missing_page(resp) -> bool:
    if MISSING_PAGE_RE.search(resp.url or ""):
        return True
    title = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.S | re.I)
    return bool(title and MISSING_PAGE_RE.search(title.group(1)))


def fetch_recipe(link):
    """Haal één recept op. Fouten komen terug in het resultaat, niet als crash."""
    url = link["url"]
    result = {"value": url, "url": url, "date": link.get("date", ""),
              "title": url, "items": [], "error": ""}
    try:
        # Doorstuurlinks (share.google) volgt requests zelf; de korte
        # AH-vorm moet eerst herschreven worden.
        resp = requests.get(normalize_url(url), headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        result["error"] = f"kon pagina niet ophalen ({e.__class__.__name__})"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    result["title"] = extract_title(soup, fallback=url)
    ingredients = extract_ingredients(resp.text)
    if not ingredients:
        result["error"] = (
            "recept bestaat niet meer" if _looks_like_a_missing_page(resp)
            else "geen ingrediënten gevonden op deze pagina"
        )
        return result

    result["items"] = [split_ingredient(i) for i in ingredients]
    return result


def fetch_recipes(links):
    """Alle recepten tegelijk ophalen, in de volgorde waarin ze geplakt zijn."""
    if not links:
        return []
    return list(_fetch_pool.map(fetch_recipe, links))


# Aanvinkwaarde voor een recept dat als tekst geplakt is; links gebruiken
# hun eigen URL. Zo weet stap 2 waar elk aangevinkt recept vandaan komt.
TEXT_RECIPE_PREFIX = "tekst:"


def collect_recipes(text: str):
    """
    Alles wat in de geplakte tekst staat: recepten achter een link én
    recepten die als tekst zijn meegestuurd, in de volgorde van de tekst.
    """
    recipes = fetch_recipes(find_recipe_links(text))
    for recipe in find_text_recipes(text):
        recipes.append({
            "value": f"{TEXT_RECIPE_PREFIX}{recipe['index']}",
            "url": "",
            "date": recipe["date"],
            "title": recipe["title"],
            "items": [split_ingredient(i) for i in recipe["ingredients"]],
            "error": "",
        })
    return recipes


def recipes_for_values(text: str, values):
    """De aangevinkte recepten opnieuw opbouwen uit de oorspronkelijke tekst."""
    wanted = set(values)
    links = [{"url": v} for v in values if not v.startswith(TEXT_RECIPE_PREFIX)]
    chosen = fetch_recipes(links)

    for recipe in find_text_recipes(text):
        if f"{TEXT_RECIPE_PREFIX}{recipe['index']}" in wanted:
            chosen.append({
                "value": f"{TEXT_RECIPE_PREFIX}{recipe['index']}",
                "url": "",
                "date": recipe["date"],
                "title": recipe["title"],
                "items": [split_ingredient(i) for i in recipe["ingredients"]],
                "error": "",
            })
    return chosen


def merge_items(item_lists):
    """
    Voeg dezelfde artikelen uit meerdere recepten samen tot één regel. De
    hoeveelheden komen achter elkaar te staan ("2 tenen + 1 teentje") in
    plaats van opgeteld: eenheden uit vrije tekst optellen gaat een keer mis,
    en dan koop je de verkeerde hoeveelheid.
    """
    merged = {}
    for items in item_lists:
        for title, description in items:
            if title not in merged:
                merged[title] = []
            if description:
                # Niet ontdubbelen: drie keer "1" betekent drie uien.
                merged[title].append(description)
    return [(title, " + ".join(parts)) for title, parts in merged.items()]


# "verse basilicum" wil je kopen, maar "vers gemalen peper" zegt alleen iets
# over de pepermolen - dat is nog steeds de peper uit je eigen kastje.
FRESH_RE = re.compile(r"\bvers(e|se)?\b(?!\s+gemalen)", re.IGNORECASE)
DRIED_RE = re.compile(r"\bgedroogd(e)?\b", re.IGNORECASE)


def is_pantry_item(title: str, description: str = "") -> bool:
    """
    Heb je dit vrijwel zeker al in huis? Zout en kaneel wel, maar een bosje
    verse koriander niet - dat woordje "verse" is het verschil tussen iets
    uit je kastje en iets uit het schap.
    """
    fresh = bool(FRESH_RE.search(description))
    if title in DRIED_ONLY_PANTRY:
        # Alleen voorraad als het recept expliciet gedroogd zegt. Vraagt een
        # ander recept om hetzelfde kruid vers, dan wint kopen.
        return bool(DRIED_RE.search(description)) and not fresh
    if title not in PANTRY:
        return False
    return not fresh


def split_pantry(items):
    """Splits de lijst in wat je moet kopen en wat waarschijnlijk in huis is."""
    shopping, pantry = [], []
    for title, description in items:
        target = pantry if is_pantry_item(title, description) else shopping
        target.append((title, description))
    return shopping, pantry


@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    entity_id = DEFAULT_TODO_ENTITY
    recipes = []       # gevonden recepten om aan te vinken (stap 1)
    merged = []        # wat er naar de lijst gaat
    pantry = []        # wat je waarschijnlijk al in huis hebt
    message = message_class = None

    if request.method == "POST":
        entity_id = request.form.get("entity_id", "").strip() or DEFAULT_TODO_ENTITY

        if request.form.get("action") == "add":
            # Stap 2: de aangevinkte recepten opnieuw opbouwen en toevoegen.
            gekozen = request.form.getlist("recipe")
            text = request.form.get("text", "")
            if not gekozen:
                message, message_class = "Vink minstens één recept aan.", "error"
            else:
                fetched = recipes_for_values(text, gekozen)
                alles = merge_items([r["items"] for r in fetched if not r["error"]])
                mislukt = [r for r in fetched if r["error"]]

                # Voorraadartikelen gaan alleen mee als ze zijn aangevinkt.
                shopping, staples = split_pantry(alles)
                aangevinkt = set(request.form.getlist("pantry"))
                merged = shopping + [i for i in staples if i[0] in aangevinkt]

                if not merged:
                    message, message_class = (
                        "Geen ingrediënten om toe te voegen.", "error")
                elif not SUPERVISOR_TOKEN:
                    message, message_class = (
                        "Ingrediënten gevonden, maar niet toegevoegd: geen "
                        "SUPERVISOR_TOKEN beschikbaar (draai je dit lokaal buiten "
                        "Home Assistant?).", "warning")
                else:
                    added, failed = add_ingredients_to_todo(entity_id, merged)
                    deel = (f"{added}/{len(merged)}" if failed else f"Alle {added}")
                    tekst = f"{deel} artikelen toegevoegd aan {entity_id}."
                    if failed:
                        tekst += f" Mislukt: {', '.join(failed)}."
                    if mislukt:
                        tekst += (" Niet opgehaald: "
                                  + ", ".join(r["url"] for r in mislukt) + ".")
                    message = tekst
                    message_class = "warning" if (failed or mislukt) else "success"
        else:
            # Stap 1: recepten uit de geplakte tekst halen (links én tekst).
            text = request.form.get("text", "").strip()
            if not text:
                message, message_class = "Plak eerst een recept-link of tekst.", "error"
            else:
                recipes = collect_recipes(text)
                merged, pantry = split_pantry(
                    merge_items([r["items"] for r in recipes if not r["error"]])
                )
                if not recipes:
                    message, message_class = (
                        "Geen recepten gevonden: plak een link, of een recept met "
                        "een kopje 'Ingredients' boven de ingrediënten.", "error")
                elif all(r["error"] for r in recipes):
                    message, message_class = (
                        "Geen van de recepten leverde ingrediënten op.", "error")

    return render_template(
        "index.html",
        text=text,
        recipes=recipes,
        merged=merged,
        pantry=pantry,
        message=message,
        message_class=message_class,
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
