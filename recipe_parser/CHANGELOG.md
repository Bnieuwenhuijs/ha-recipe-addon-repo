# Changelog

## 1.11.0

De voorraadkast en de synoniemenlijst zijn flink uitgebreid, op basis van wat
er daadwerkelijk in de kast staat (vier bestellingen bij De Kruidenbaron).

- **96 voorraadartikelen** in plaats van 44. Erbij: kruidnagel, sumak,
  karwijzaad, venkelzaad, korianderzaad, uienpoeder, knoflookpoeder,
  gemberpoeder, nootmuskaat, foelie, piment, steranijs, saffraan, maanzaad,
  nigellazaad, kokosrasp, kerrie, ras el hanout, tandoori, vijfkruidenpoeder,
  Italiaanse en Provençaalse kruiden, nasi kruiden, sambal, harissa, tahin,
  vanille, cacao, thee, koffie en kraanwater.
- **Gedroogde kruiden staan nu gewoon in de kast.** Basilicum, peterselie,
  dille, bieslook, koriander en munt gelden als voorraad, want die staan er
  gedroogd. Vraagt een recept om het verse product, dan gaat het alsnog op de
  lijst - en dat wordt nu ook herkend zonder het woord "verse", aan maten die
  alleen bij vers horen: "1 bosje", "3 takjes", "een handje", "2 blaadjes".
- **Poeder is niet hetzelfde als het verse product.** Knoflookpoeder,
  uienpoeder, gemberpoeder, venkelzaad en korianderpoeder werden eerder
  aangezien voor knoflook, ui, gember, venkel en een bosje koriander - en
  verdwenen daarmee naar de verkeerde groep. Die hebben nu hun eigen naam.
- **249 synoniemen** in plaats van 130. Naast de specerijen ook gewone
  boodschappen: sjalotten en zilveruitjes worden Uien, winterpeen en bospeen
  worden Wortelen, kidney-, borlotti- en cannellinibonen worden Bonen,
  ijsbergsla en little gem worden Sla, kastanjechampignons worden
  Champignons, slagroom en kookroom worden Room, spekjes en pancetta worden
  Spek, geitenkaas en halloumi worden Kaas, zalmfilet wordt Zalm.

Op de vijf uitgeschreven recepten scheelt dat 20 van de 51 artikelen: die
gaan niet meer naar Bring tenzij je ze aantikt.

## 1.10.0

Artikelen die je vrijwel altijd in huis hebt gaan niet meer vanzelf mee.

- Olie, azijn, sauzen, bloem, suiker, zout, peper en de gemalen specerijen
  (kaneel, kurkuma, garam masala, laos, kardemom, chilipoeder, bouillon en
  meer) komen in een aparte groep **Waarschijnlijk in huis**, onderaan het
  overzicht en standaard uitgevinkt. Ze verdwijnen dus niet: je ziet nog wel
  dat een recept erom vraagt, en tikt ze aan als je fles bijna leeg is.
- **Verse kruiden zijn een uitzondering.** "5 g verse basilicum" hoort gewoon
  op de boodschappenlijst, "1 tsp gedroogde oregano" niet. Zonder dat verschil
  zou een bosje koriander stilletjes van je lijst verdwijnen.
- Blaadjeskruiden (basilicum, peterselie, munt, koriander, bieslook, dille)
  gelden alleen als voorraad wanneer het recept expliciet "gedroogd" zegt.
  Vraagt het ene recept om verse en het andere om gedroogde, dan wint kopen.
- "Vers gemalen zwarte peper" telt als voorraad: dat woordje "vers" gaat
  daar over de molen, niet over iets wat je moet halen.

De lijst staat in `recipe_parser/bring_catalog.py` onder `PANTRY` en
`DRIED_ONLY_PANTRY`.

## 1.9.0

Nieuwe vormgeving, in de stijl van Bubble Card.

- Alles is nu een capsule met veel ronding, geen randen en een rond icoon
  links, met een vette titel en een kleine grijze regel eronder.
- Een aangevinkt recept is een **groen gevulde** capsule, een uitgevinkt
  blijft grijs, en een link die niet lukte is roodgetint. Je tikt ergens op
  de rij om hem aan of uit te zetten - de hele capsule is het label, dus dat
  werkt ook zonder JavaScript.
- Knop **Alles aanvinken / uitvinken**, handig als je een maand aan berichten
  plakt en er maar een paar wil koken. Het opschrift volgt de stand.
- Per recept een **inklapbaar lijstje** met de ingrediënten, zodat je kunt
  kijken wat erin zit voordat je toevoegt. Gebruikt `<details>`, dus ook dit
  werkt zonder JavaScript.
- **Donker thema** via `prefers-color-scheme`: staat je telefoon of Home
  Assistant 's avonds donker, dan is het paneel geen lichtbak meer.
- De iconen zijn inline SVG. Geen externe fonts of CDN, dus het paneel laadt
  ook zonder internet en er lekt niets naar buiten.

## 1.8.0

Recepten die als tekst geplakt worden, zonder link erbij.

- Een geplakt recept met een kopje `INGREDIENTS` (of `Ingrediënten`) en
  daaronder de ingrediënten wordt herkend als recept. De titel is de eerste
  regel, de lijst loopt tot `STEPS`, `Bereiding`, `NOTES` of een lege regel.
  Bulletpoints met •, - of * worden weggehaald.
- Zulke recepten staan gewoon tussen de links in het overzicht, met hun
  datum uit het WhatsApp-bericht en de vermelding "uit tekst". Je kunt dus
  in één keer links én tekstrecepten plakken.
- Hoeveelheden in deze recepten hebben een eigen schrijfwijze, die nu
  begrepen wordt: gemengde breuken (`44 1/3 ml`, `1 1/4 ml`) en Engelse
  maten (`tbsp`, `tsp`, `pinch`, `cup`, `clove`, `oz`).
- Een woord dat de titel al zegt in een andere portievorm wordt niet meer
  herhaald: "3 knoflookteentjes" wordt "Knoflook - 3", en
  "200 g bloemkoolroosjes" wordt "Bloemkool - 200 g". Een woord dat iets
  ánders betekent blijft wel staan, dus "citroensap" en "kipfilet" gaan niet
  verloren.
- Beschrijvende woorden achteraan tellen niet meer mee voor de titel, zodat
  "komijnzaad gemalen" en "komijnzaad" op één regel samenkomen.
- "uit blik" hoort bij de hoeveelheid, niet bij de naam: "kidneybonen uit
  blik" wordt de titel "Kidneybonen".
- Fixes: mosterdzaad belandde onder Mosterd en sesamzaad onder Sesam;
  tarwenoedels en mie worden nu Noedels.

## 1.7.0

Getoetst aan een volledige WhatsApp-export met 224 unieke receptlinks over
33 sites. Daarvan werken er nu **205 (91%)**; dat waren er 149.

- **Korte Albert Heijn-links werken nu.** De deelknop van de AH-app maakt
  links als `ah.nl/r/1196876`, die zelf een 404 geven. Hetzelfde nummer
  werkt wél als `ah.nl/allerhande/recept/R-R1196876`, en dat herschrijven we
  nu. Dit redt 49 links - eerder stond in deze changelog dat ze niet op te
  halen waren, dat klopte niet.
- **Doorstuurlinks** (`share.google`, 44 stuks in de export) worden gevolgd
  naar de echte receptsite.
- JSON-LD met een letterlijke regelovergang in een tekst wordt nu toch
  gelezen. Strikt genomen is dat ongeldige JSON, maar de ingrediënten
  kloppen wel (savorysweets.nl).
- Ook `type="application/ld+json; charset=utf-8"` telt nu mee.
- De oude schema.org-sleutel `ingredients` wordt gelezen naast
  `recipeIngredient`, maar alleen binnen een blok dat zichzelf een Recipe
  noemt (libelle-lekker.be).
- De kop-fallback voor sites zonder schema.org-gegevens kijkt nu naar h1
  t/m h6 in plaats van alleen h2 en h3, en laat zich niet meer afkappen
  door een tussenkop als "Voor 2 personen" (24baby.nl). Lijstjes in
  navigatie, zijbalk of voettekst tellen niet mee, en hele alinea's ook
  niet - dat is bereidingstekst, geen ingrediënt.
- De add-on meldt zich als een gewone browser; een deel van de sites gaf
  een onbekende client een 403 of een lege pagina.
- Een verwijderd recept meldt nu "recept bestaat niet meer" in plaats van
  "geen ingrediënten gevonden". Voedingscentrum stuurt zulke pagina's door
  naar een 404-pagina maar meldt gewoon HTTP 200.

Wat niet werkt, en waarom:

| Link | Reden |
|---|---|
| instagram.com | een reel, geen receptpagina |
| miljuschka.nl | blokkeert niet-browsers (403) |
| overzichtspagina's ("5x de lekkerste curry's") | geen los recept |
| eerstkoken.blogspot.com | recept staat als lopende tekst, geen lijst |
| verwijderde recepten | de pagina bestaat niet meer |

## 1.6.0

Meerdere recepten in één keer, bedoeld voor de gewoonte om recepten in een
WhatsApp-groep te delen en ze pas bij het boodschappen doen te verwerken.

- Het invoerveld accepteert nu geplakte tekst in plaats van één URL. Alle
  links worden eruit gevist, ook als ze middenin een zin staan of op een
  eigen regel onder het bericht. Eén losse link plakken werkt gewoon nog.
- De datum uit het WhatsApp-bericht (`[12/07, 12:40]`) komt bij het recept
  te staan, zodat je bij een maand aan berichten ziet wat oud is.
- Je krijgt eerst een overzicht van de gevonden recepten met hun naam en
  aantal ingrediënten, en vinkt aan wat mee moet. Pas daarna gaat er iets
  naar de lijst.
- Artikelen die in meerdere recepten voorkomen worden één regel, met de
  hoeveelheden achter elkaar: "Knoflook - 2 tenen + 1 teentje + 2 teentjes".
  Er wordt niet opgeteld; eenheden uit vrije tekst optellen gaat een keer
  mis en dan koop je de verkeerde hoeveelheid. Gelijke hoeveelheden blijven
  ook staan, want drie keer "1" betekent drie uien.
- Een link die niet opgehaald kan worden, wordt bij dat recept gemeld en
  houdt de rest niet tegen.
- De recepten worden tegelijk opgehaald: vijf stuks in ongeveer 3 seconden.

Let op: links van de deelknop in de Albert Heijn-app (`ah.nl/r/...`) werken
niet. Die geven ook in een gewone browser "pagina niet gevonden"; het volledige
adres (`ah.nl/allerhande/recept/...`) werkt wel.

## 1.5.0

Naast voedingscentrum.nl werken nu ook **leukerecepten.nl** en **ah.nl**.

- Die twee zetten hun recept niet in de HTML maar in een schema.org
  JSON-LD-blok, dat nu ook gelezen wordt. Omdat dit een standaard is en geen
  maatwerk per site, werken veel andere receptsites hoogstwaarschijnlijk ook.
  Voedingscentrum blijft via zijn eigen microdata werken.
- Eenheden uit die sites herkend: `gr`, `g`, `el`, `tl`, `blokje`, `zak`,
  `snuf`, `teen`, `krop`, `bol`, `sneetje`, `stengel`, `cm`, `pot`.
- Staat er niets herkenbaars in de naam, dan worden beschrijvende woorden
  vooraan alsnog overgeslagen: "300 g biologische volkorenorzo" wordt
  "Pasta" in plaats van de hele zin als titel. Catalogusnamen die er zelf
  mee beginnen ("Zoete aardappelen", "Witte bonen") blijven heel.
- Keukengerei dat leukerecepten.nl tussen de ingrediënten zet (staafmixer,
  blender, oven) belandt niet meer op de boodschappenlijst.
- Betere matches: orzo/fusilli/farfalle en andere pastavormen worden Pasta,
  rijstnoedels worden Noedels (niet Rijst), biefstuk wordt Steak,
  cottagecheese wordt Huttenkaas, maïzena wordt Zetmeel.
- "peper en zout" blijft één regel in plaats van een item "Zout" met een
  losse "peper en" in de omschrijving.
- Fix: meervouden werkten maar één kant op, waardoor "2 biologische
  limoenen" onder de titel "Limoen" toch nog "limoenen" herhaalde.

## 1.4.0

- De omschrijving herhaalt de titel niet meer: "200 gram groenten" onder de
  titel "Groenten" wordt nu gewoon "200 gram", en "1 appel" onder "Appels"
  wordt "1". Dat geldt ook als het recept het anders schrijft dan Bring
  ("hüttenkäse" bij "Huttenkaas", "pinda's" bij "Pindanoten").
- Woorden die wél iets toevoegen blijven staan, want die heb je nodig in de
  winkel: "5 gram verse", "3 eetlepels halfvolle", "1 eetlepel vloeibare".
- Een specifieker product wordt nooit weggegooid: "200 gram kipfilet" blijft
  onder de titel "Kip" staan, en "volkoren tagliatelle" onder "Pasta".
- Fix: "(olijf)olie" belandde onder Olijven in plaats van Olijfolie, en
  "(groente)bouillontablet" onder Groenten in plaats van Bouillon. Bij dit
  soort haakjes vooraan wint nu het juiste artikel.

## 1.3.0

Een recept van 11 ingrediënten toevoegen duurde ongeveer 12 seconden, met
een stil scherm tot alles klaar was. Opgemeten waar die tijd heen ging:

| onderdeel                  | 1.2.1  | nu     |
|----------------------------|--------|--------|
| receptpagina ophalen       | 0,20 s | 0,20 s |
| HTML parsen                | 0,06 s | 0,06 s |
| ingrediënten splitsen (11x)| 0,60 s | 0,003 s|
| toevoegen aan de lijst     | ~11 s  | ~3 s   |

- De zoektermen voor het matchen op Bring-artikelen worden nu één keer
  gecompileerd. Er zijn er meer (772) dan in de regex-cache van Python
  passen (512), waardoor élk patroon bij ieder ingrediënt opnieuw werd
  gecompileerd. Dit deel is nu ~180x sneller.
- Ingrediënten worden nu in groepjes van maximaal 5 tegelijk toegevoegd.
  Home Assistant geeft `todo.add_item` pas terug als Bring het item in de
  cloud heeft opgeslagen (~1 seconde per stuk), dus achter elkaar wachten
  was de grootste kostenpost. Mislukte items worden nog steeds per stuk
  gemeld, in receptvolgorde, en worden bewust niet opnieuw geprobeerd:
  `todo.add_item` is niet idempotent, dus een retry na een timeout kan een
  dubbel item opleveren.
- Het formulier laat nu meteen "Bezig met ophalen en toevoegen…" zien, in
  plaats van een stil scherm tot alles klaar is.

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
