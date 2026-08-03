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
ingrediëntenlijst uit de HTML haalt en als JSON teruggeeft.

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

### Gebruik vanuit Home Assistant

De bedoeling is dat Home Assistant dit endpoint aanroept via een
`rest_command`, en de ingrediënten vervolgens één voor één via
`todo.add_item` toevoegt aan een Bring!-boodschappenlijst (via de
Home Assistant Bring-integratie).

```yaml
# configuration.yaml
rest_command:
  parse_recipe:
    url: "http://localhost:5001/parse?url={{ recipe_url }}"
    method: GET
```

Een script kan de response van `rest_command.parse_recipe` uitlezen en
per ingrediënt `todo.add_item` aanroepen op bijvoorbeeld `todo.thuis`.

### Lokaal testen

De extractielogica (`extract_ingredients()`) kan los van Home Assistant
getest worden met de meegeleverde HTML-fixtures (afkomstig van live
recepten):

```bash
cd recipe_parser
python -m unittest test_parser.py -v
```

Zo hoeft de add-on niet steeds herbouwd te worden in Home Assistant om
een wijziging in de parser te verifiëren.

### Bekende beperking

De parser is afgestemd op de HTML-structuur van voedingscentrum.nl.
Wijzigt die site haar opmaak, dan kan `/parse` een 422 teruggeven totdat
`extract_ingredients()` is bijgewerkt (zie `recipe_parser/CHANGELOG.md`
voor de historie hiervan).
