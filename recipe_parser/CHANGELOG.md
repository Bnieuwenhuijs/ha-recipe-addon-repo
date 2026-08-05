# Changelog

## 1.2.1

- Fix: `bring_catalog.py` werd niet naar het container-image gekopieerd,
  waardoor 1.2.0 crashte met `ModuleNotFoundError: No module named
  'bring_catalog'` en de add-on in een herstartlus belandde. De Dockerfile
  kopieert nu alle modules ineens.
- Toegevoegd: `test_packaging.py`, die faalt zodra een geïmporteerde module
  niet door een `COPY` in de Dockerfile gedekt wordt.

## 1.2.0

- Ingrediënten worden nu gesplitst in een artikelnaam als titel en de
  hoeveelheid als omschrijving ("400 gram prei" wordt "Prei" met
  omschrijving "400 gram"), zoals gebruikelijk in Home Assistant en Bring.
- De artikelnaam wordt gematcht tegen de artikelen die Bring zelf kent
  (`bring_catalog.py`), inclusief synoniemen en enkelvoud/meervoud, zodat
  Bring het juiste icoon toont: "hüttenkäse" wordt "Huttenkaas",
  "2 bosuien" wordt "Bosui / Lente-ui", "1 tomaat" wordt "Tomaten".
- Bij het matchen wint het woord dat vooraan staat, zodat "sojasaus met
  minder zout" als "Soja saus" wordt herkend en niet als "Zout".
- `GET /parse` geeft naast `ingredients` nu ook `items` terug met per
  ingrediënt een `title` en `description`. Het bestaande `ingredients`-veld
  is ongewijzigd.

## 1.1.4

- De 17 (of hoeveel dan ook) `todo.add_item`-calls per recept hergebruiken
  nu één `requests.Session()` in plaats van voor elk ingrediënt een nieuwe
  TCP-verbinding naar de Supervisor op te zetten. Verhelpt merkbare
  traagheid bij het toevoegen aan de todo-lijst binnen Home Assistant.

## 1.1.3

- Root cause gevonden voor de ontbrekende `SUPERVISOR_TOKEN`: `run.sh`
  gebruikte het gewone `#!/usr/bin/env bash` shebang, waardoor het op de
  s6-overlay-gebaseerde HA-images een gesaneerd environment kreeg (alleen
  `PATH`/`PWD`/`OLDPWD`/`SHLVL`, bevestigd via `/debug`'s env_var_names).
  `run.sh` gebruikt nu `#!/usr/bin/with-contenv bashio`, de standaard voor
  HA add-ons, waarmee het script wel toegang krijgt tot de echte
  container-omgevingsvariabelen zoals `SUPERVISOR_TOKEN`.

## 1.1.2

- `/debug` toont nu ook alle namen (niet de waarden) van omgevingsvariabelen
  die de container daadwerkelijk heeft gekregen. Nodig om te achterhalen
  waarom `SUPERVISOR_TOKEN` ontbrak ondanks `homeassistant_api: true` en
  een volledige herinstallatie van de add-on.

## 1.1.1

- Nieuw: `GET /debug` endpoint dat meldt of `SUPERVISOR_TOKEN` aanwezig is
  en of de Home Assistant API bereikbaar is, zodat dit vanuit de browser
  te controleren is zonder terminal/SSH-toegang tot de host.

## 1.1.0

- Nieuw: ingress-webformulier (verschijnt als paneel in de HA-sidebar) om
  een recept-URL en todo-entity in te vullen. De gevonden ingrediënten
  worden direct via de Home Assistant API (`todo.add_item`) toegevoegd,
  zonder tussenkomst van een `rest_command` of script.
- Vereist `homeassistant_api: true` (toegevoegd aan `config.yaml`) voor
  toegang tot de HA API via `SUPERVISOR_TOKEN`.
- Draait het formulier lokaal buiten Home Assistant (geen
  `SUPERVISOR_TOKEN` aanwezig), dan worden de ingrediënten getoond met
  een waarschuwing in plaats van te worden toegevoegd - zo blijft lokaal
  testen mogelijk.
- Toegevoegd: `test_app.py` met gemockte HTTP-calls voor de nieuwe route.

## 1.0.1

- Ingrediënten worden nu primair via het `itemprop="recipeIngredient"`
  attribuut geëxtraheerd in plaats van via de koptekst "Ingrediënten" te
  zoeken. Voedingscentrum.nl toont ingrediënten in twee `<ul>`-kolommen
  naast elkaar, wat bij sommige recepten leidde tot een 422-fout
  ("geen ingrediënten gevonden").
- Toegevoegd: `test_parser.py` met HTML-fixtures van live recepten, zodat
  de extractielogica lokaal getest kan worden zonder de add-on opnieuw
  te hoeven bouwen.

## 1.0.0

- Eerste versie.
