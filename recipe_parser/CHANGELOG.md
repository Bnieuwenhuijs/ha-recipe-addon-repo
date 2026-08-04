# Changelog

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
