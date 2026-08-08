# Bart's Home Assistant Add-ons

Home Assistant add-on repository met daarin één add-on: **Recipe Parser**.

## Toevoegen aan Home Assistant

1. Ga in Home Assistant naar **Instellingen → Add-ons → Add-on Store**.
2. Klik rechtsboven op de drie puntjes → **Repositories**.
3. Voeg deze URL toe: `https://github.com/Bnieuwenhuijs/ha-recipe-addon-repo`
4. De add-on **Recipe Parser** verschijnt in de store en kan worden geïnstalleerd.
5. Nieuwe versies komen daarna gewoon binnen via **Check for updates**, zonder handmatig bestanden te hoeven kopiëren.

## Recipe Parser

Een kleine Flask-microservice die een receptpagina-URL ophaalt, de
ingrediëntenlijst eruit haalt, en via een webformulier of REST endpoint kan
doorzetten naar een Home Assistant todo-lijst (bijv. Bring).

### Ondersteunde receptsites

Er is geen lijst met toegestane sites: de ingrediënten komen uit de
[schema.org](https://schema.org/Recipe)-gegevens die vrijwel elke receptsite
meestuurt, als microdata of als JSON-LD. Daardoor werken ook sites die nooit
apart zijn ingebouwd.

Getoetst aan een WhatsApp-export met 224 receptlinks over 33 sites: **205
daarvan (91%) leveren hun ingrediënten**, waaronder voedingscentrum.nl (ook
`mobiel.`), ah.nl, leukerecepten.nl, jumbo.com, dekamarkt.nl, 24kitchen.nl,
libelle-lekker.be, recipetineats.com, lassie.nl, en een reeks foodblogs.

Twee soorten links worden eerst omgezet:

- **Korte Albert Heijn-links** uit de deelknop van de app (`ah.nl/r/1196876`)
  geven zelf een 404, maar hetzelfde nummer werkt als
  `ah.nl/allerhande/recept/R-R1196876`. Dat gebeurt automatisch.
- **Doorstuurlinks** zoals `share.google/...` worden gevolgd naar de site
  waar ze heen wijzen.

**Wat niet lukt**, en waarom: een Instagram-reel of een overzichtspagina
("5x de lekkerste curry's") bevat geen los recept; een enkele site blokkeert
alles wat geen browser is; en een blog dat het recept als lopende tekst
schrijft heeft geen lijst om uit te lezen. Zulke links worden per stuk
gemeld en houden de rest niet tegen.

### Webformulier (ingress)

De add-on verschijnt na installatie als paneel in de HA-sidebar (via
[ingress](https://developers.home-assistant.io/docs/add-ons/presentation/#ingress)).
Daar plak je een recept-link - of gewoon een stuk tekst met links erin,
bijvoorbeeld een kopie uit een WhatsApp-groep waarin jullie recepten delen:

```
[05/07, 13:55] Bart: Ik kook vandaag dit!
https://www.voedingscentrum.nl/recepten/gezond-recept/aardappel-knolselderijgratin.aspx
[12/07, 12:40] Bart: https://www.leukerecepten.nl/recepten/kikkererwten-curry/
```

Alle links worden eruit gevist en tegelijk opgehaald. Je krijgt een overzicht
met de naam van elk recept, de datum uit het bericht en het aantal
ingrediënten, en vinkt aan welke mee moeten. Pas daarna gaan ze via de Home
Assistant API (`todo.add_item`) naar de lijst - geen aparte `rest_command`
of script nodig.

Artikelen die in meerdere recepten voorkomen worden één regel, met de
hoeveelheden achter elkaar: **Knoflook** met omschrijving
*2 tenen + 1 teentje + 2 teentjes*. Er wordt bewust niet opgeteld, want
eenheden uit vrije tekst optellen gaat een keer mis - en dan koop je de
verkeerde hoeveelheid.

Elk ingrediënt wordt gesplitst in een artikelnaam (de titel) en de
hoeveelheid (de omschrijving), dus "400 gram prei" wordt een taak **Prei**
met omschrijving *400 gram*. De artikelnaam wordt daarbij gematcht tegen
de artikelen die Bring zelf kent (zie `recipe_parser/bring_catalog.py`),
zodat Bring het juiste icoon toont - ook als het recept een andere
schrijfwijze gebruikt ("hüttenkäse" wordt "Huttenkaas").

### Endpoint

```
GET /parse?url=<recept-url>
```

**Succes (200):**

```json
{
  "ingredients": ["200 gram volkoren tagliatelle", "100 gram prei", "..."],
  "items": [
    {"title": "Pasta", "description": "200 gram volkoren tagliatelle"},
    {"title": "Prei", "description": "100 gram"}
  ],
  "source_url": "https://www.voedingscentrum.nl/recepten/gezond-recept/..."
}
```

`items` bevat dezelfde ingrediënten, maar gesplitst in een Bring-artikelnaam
en de hoeveelheid - direct bruikbaar als `item` en `description` voor
`todo.add_item`.

**Fouten:**

| Status | Betekenis |
|---|---|
| 400 | `url`-parameter ontbreekt |
| 422 | pagina opgehaald, maar geen ingrediënten gevonden (paginastructuur gewijzigd?) |
| 502 | pagina kon niet opgehaald worden |

Daarnaast is er een `GET /health` endpoint dat `{"status": "ok"}` teruggeeft.

### Gebruik vanuit een Home Assistant automation/script

Naast het formulier blijft `/parse` bruikbaar voor automatisering, bijv.
via een `rest_command` gevolgd door een script dat zelf `todo.add_item`
per ingrediënt aanroept:

```yaml
# configuration.yaml
rest_command:
  parse_recipe:
    url: "http://localhost:5001/parse?url={{ recipe_url }}"
    method: GET
```

### Lokaal testen

**Unit tests** — de extractielogica en het formulier kunnen los van Home
Assistant getest worden met de meegeleverde HTML-fixtures (afkomstig van
live recepten) en gemockte HTTP-calls:

```bash
cd recipe_parser
pip install -r requirements.txt
python -m unittest test_parser.py test_app.py -v
```

**Het formulier zelf proberen** — start de app lokaal en open
`http://localhost:5001/` in je browser:

```bash
cd recipe_parser
python recipe_parser.py
```

Zonder `SUPERVISOR_TOKEN` (die alleen bestaat als de add-on binnen Home
Assistant draait) worden de gevonden ingrediënten getoond met een
waarschuwing dat ze niet zijn toegevoegd - zo kan de parser en het
formulier volledig lokaal getest worden zonder Home Assistant nodig te
hebben, en zonder de add-on steeds te hoeven herbouwen.

### Bekende beperking

De parser is afgestemd op de HTML-structuur van voedingscentrum.nl.
Wijzigt die site haar opmaak, dan kan `/parse` een 422 teruggeven totdat
`extract_ingredients()` is bijgewerkt (zie `recipe_parser/CHANGELOG.md`
voor de historie hiervan).
