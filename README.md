# Bart's Home Assistant Add-ons

Home Assistant add-on repository met daarin één add-on: **Recipe Parser**.

## Toevoegen aan Home Assistant

1. Ga in Home Assistant naar **Instellingen → Add-ons → Add-on Store**.
2. Klik rechtsboven op de drie puntjes → **Repositories**.
3. Voeg deze URL toe: `https://github.com/Bnieuwenhuijs/ha-recipe-addon-repo`
4. De add-on **Recipe Parser** verschijnt in de store en kan worden geïnstalleerd.
5. Nieuwe versies komen daarna gewoon binnen via **Check for updates**, zonder handmatig bestanden te hoeven kopiëren.

## Recipe Parser

Een kleine Flask-microservice die een receptpagina-URL (voornamelijk
[voedingscentrum.nl](https://www.voedingscentrum.nl)) ophaalt, de
ingrediëntenlijst uit de HTML haalt, en via een webformulier of REST
endpoint kan doorzetten naar een Home Assistant todo-lijst (bijv. Bring).

### Webformulier (ingress)

De add-on verschijnt na installatie als paneel in de HA-sidebar (via
[ingress](https://developers.home-assistant.io/docs/add-ons/presentation/#ingress)).
Daar vul je een recept-URL en een todo-entity in (standaard `todo.thuis`)
en de gevonden ingrediënten worden direct via de Home Assistant API
(`todo.add_item`) aan die lijst toegevoegd - geen aparte `rest_command`
of script nodig.

### Endpoint

```
GET /parse?url=<recept-url>
```

**Succes (200):**

```json
{
  "ingredients": ["200 gram volkoren tagliatelle", "100 gram prei", "..."],
  "source_url": "https://www.voedingscentrum.nl/recepten/gezond-recept/..."
}
```

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
