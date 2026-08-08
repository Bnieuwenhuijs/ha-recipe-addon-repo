"""
Artikelnamen die Bring! zelf kent. Zet je zo'n naam in de titel van een
todo-item, dan toont Bring het bijbehorende icoon. Recepten gebruiken
vaak een andere schrijfwijze ("hüttenkäse", "bosuien"), daarom staat er
naast de catalogus een synoniemenlijst die naar de canonieke naam wijst.
"""

CATALOG = [
    # Groente en fruit
    "Aardappelen", "Aardbeien", "Abrikozen", "Ananas", "Appels", "Artisjokken",
    "Asperges", "Aubergine", "Avocado", "Bananen", "Basilicum", "Bessen",
    "Bieslook", "Blauwe bessen", "Bloemkool", "Bonen", "Bosui / Lente-ui",
    "Broccoli", "Champignons", "Cherrytomaten", "Chillipeper", "Citroen",
    "Courgette", "Cranberry", "Dadels", "Druiven", "Erwten", "Frambozen",
    "Fruit", "Gember", "Grapefruit", "Groenten", "Kersen", "Kiwi", "Knoflook",
    "Komkommer", "Kool", "Koolrabi", "Koriander", "Kruiden", "Limoen", "Maïs",
    "Mandarijnen", "Mango", "Meloen", "Munt", "Nectarine", "Olijven", "Paprika",
    "Passiefruit", "Peren", "Perzik", "Peterselie", "Pompoen", "Prei",
    "Pruimen", "Rabarber", "Radijzen", "Rode biet", "Rucola", "Salie",
    "Selderij", "Sinaasappelen", "Sla", "Sperziebonen", "Spinazie", "Tijm",
    "Tomaten", "Uien", "Venkel", "Vijgen", "Watermeloen", "Witlof", "Wortelen",
    "Zoete aardappelen", "Zwarte bessen",
    # Brood en gebak
    "Amerikaans Broodje", "Bagels", "Bladerdeeg", "Brood", "Croissant",
    "Donuts", "Gesneden brood", "Kadetje", "Muffins", "Pannenkoeken",
    "Pastei / Hartige taart", "Pizza deeg", "Pompoentaart", "Stokbrood",
    "Toast", "Tortillas", "Wafels", "Zoete broodjes",
    # Zuivel en eieren
    "Blauwe kaas", "Boter", "Cheddar", "Creme fraiche", "Eieren", "Feta",
    "Geraspte kaas", "Gorgonzola", "Huttenkaas", "Kaas", "Margarine",
    "Mascarpone", "Melk", "Mozzarella", "Parmezaanse Kaas", "Room", "Roomkaas",
    "Smeerkaas", "Soja melk", "Vla", "Yoghurt", "Zure Room",
    # Vlees en vis
    "Anchovis", "Bitterballen", "Braadworst", "Filet Americain", "Frikadel",
    "Garnalen", "Gehakt", "Gesneden Rundvlees", "Ham", "Hot Dog", "Kalfsvlees",
    "Kalkoen", "Kip", "Kreeft", "Kroket", "Lam", "Mosselen", "Oesters",
    "Prosciutto", "Rundvlees", "Salami", "Spek", "Steak", "Tonijn",
    "Varkensvlees", "Vis", "Vlees", "Vleeswaren", "Worst", "Worsten", "Zalm",
    # Voorraadkast
    "Aardappelpuree", "Ahornstroop", "Amandelen", "Appelmoes", "Augurk",
    "Azijn", "Bakpoeder", "Balsamico Azijn", "BBQ Saus", "Bouillon",
    "Britse bruine saus", "Chutney", "Dip", "Gist", "Hazelnoten", "Jus",
    "Kaneel", "Ketchup", "Kokosmelk", "Linzen", "Mayonaise", "Mosterd",
    "Noten", "Olie", "Olijfolie", "Oregano", "Paneermeel", "Paprikapoeder",
    "Pasta saus", "Peperkorrels", "Pijnboompitten", "Pikante Saus",
    "Pindakaas", "Poedersuiker", "Rozemarijn", "Salade dressing", "Soja saus",
    "Suiker", "Tomatenblokjes", "Tomatenpuree", "Tomatensaus", "Vanillesuiker",
    "Veenbessen saus", "Walnoten", "Witte bonen", "Zetmeel", "Zout",
    # Diepvries en kant-en-klaar
    "Burrito", "Chinees", "Dumplings", "Frieten", "Ijs", "Indische maaltijden",
    "Ingevroren groenten", "Italiaanse maaltijden", "Kippenvleugels",
    "Lasagna", "Mexicaanse maaltijden", "Pizza", "Soep", "Thaise maaltijden",
    "Vissticks", "Witte bonen met tomaat",
    # Granen en pasta
    "Basmati rijst", "Bloem", "Cornflakes", "Couscous", "Cruesli", "Griesmeel",
    "Havermout", "Kikkererwten", "Muesli", "Noedels", "Pasta", "Penne",
    "Rijst", "Risotto rijst", "Spaghetti", "Tofu",
    # Snacks en zoet
    "Chips", "Chocolade", "Crackers", "Dessert", "Gedroogd fruit", "Gelei",
    "Hagelslag", "Honing", "Jam", "Kauwgum", "Kerstkransjes", "Koekjes",
    "Kroepoek", "Mueslireep", "Ontbijtkoek", "Pindanoten", "Popcorn",
    "Pralinécreme", "Snacks", "Stroopwafels", "Taart", "Tortilla Chips",
    "Vanille saus", "Zoetigheid", "Zoute krakeling",
    # Dranken
    "Appelsap", "Bier", "Champagne", "Cider", "Cola", "Drank", "Energiedrank",
    "Fruitsap", "Gemberbier", "Gin", "IJsthee", "Koffie", "Limonade",
    "Mineraalwater", "Prosecco", "Rode wijn", "Rum", "Sinaasappelsap",
    "Smoothie", "Sportdrank", "Sterke drank", "Thee", "Tonic",
    "Warme chocomelk", "Water", "Whisky", "Witte wijn", "Wodka",
    # Huishouden
    "Afwasmiddel", "Aluminium Folie", "Bakpapier", "Batterijen", "Bloemen",
    "Glasreiniger", "Gloeilampen", "Houtskool", "Kaarsen", "Keukenrol",
    "Schoonmaakmiddelen", "Servetten", "Spons", "Vaatwasser tabletten",
    "Vershoudfolie", "Vuilniszakken", "Waspoeder", "Wasverzachter",
]

# Woorden zoals recepten ze schrijven -> naam zoals Bring hem kent.
# Deze winnen van de automatisch afgeleide enkelvoud/meervoud-varianten.
SYNONYMS = {
    # Groente en fruit
    "ui": "Uien",
    "rode ui": "Uien",
    "bosui": "Bosui / Lente-ui",
    "bosuien": "Bosui / Lente-ui",
    "lente-ui": "Bosui / Lente-ui",
    "lenteui": "Bosui / Lente-ui",
    "tomaat": "Tomaten",
    "cherrytomaatjes": "Cherrytomaten",
    "wortel": "Wortelen",
    "winterwortel": "Wortelen",
    "peen": "Wortelen",
    "appel": "Appels",
    "peer": "Peren",
    "sinaasappel": "Sinaasappelen",
    "mandarijn": "Mandarijnen",
    "aardappel": "Aardappelen",
    "zoete aardappel": "Zoete aardappelen",
    "champignon": "Champignons",
    "chinese kool": "Kool",
    "witte kool": "Kool",
    "rode kool": "Kool",
    "rodekool": "Kool",
    "spitskool": "Kool",
    "paksoi": "Kool",
    "sperzieboon": "Sperziebonen",
    "radijs": "Radijzen",
    # Voedingscentrum schrijft olijfolie als "(olijf)olie"; zonder deze regel
    # wint "olijf" en belandt de olie onder Olijven.
    "(olijf)olie": "Olijfolie",
    "verse munt": "Munt",
    "verse koriander": "Koriander",
    "verse basilicum": "Basilicum",
    "rode peper": "Chillipeper",
    "chilipeper": "Chillipeper",
    "chilivlokken": "Chillipeper",
    # Zuivel
    "hüttenkäse": "Huttenkaas",
    "huttenkase": "Huttenkaas",
    "cottage cheese": "Huttenkaas",
    "oude kaas": "Kaas",
    "jonge kaas": "Kaas",
    "belegen kaas": "Kaas",
    "parmezaan": "Parmezaanse Kaas",
    "crème fraîche": "Creme fraiche",
    "griekse yoghurt": "Yoghurt",
    "ei": "Eieren",
    "vloeibare margarine": "Margarine",
    "ricotta": "Roomkaas",
    # Granen en pasta
    "tagliatelle": "Pasta",
    "macaroni": "Pasta",
    "volkoren pasta": "Pasta",
    "lasagnebladen": "Lasagna",
    "zilvervliesrijst": "Rijst",
    "basmatirijst": "Basmati rijst",
    # Voorraadkast
    "sojasaus": "Soja saus",
    "ketjap": "Soja saus",
    "ketjap manis": "Soja saus",
    "zonnebloemolie": "Olie",
    "sesamolie": "Olie",
    "bakolie": "Olie",
    "bouillontablet": "Bouillon",
    "bouillonblokje": "Bouillon",
    "groentebouillon": "Bouillon",
    # Ook hier zet Voedingscentrum een deel tussen haakjes vooraan, waardoor
    # anders "(groente)" wint en het tablet onder Groenten belandt.
    "(groente)bouillontablet": "Bouillon",
    "(groente)bouillonblokje": "Bouillon",
    "(groente)bouillon": "Bouillon",
    "gedroogde linzen": "Linzen",
    "kikkererwt": "Kikkererwten",
    "pinda": "Pindanoten",
    "pinda's": "Pindanoten",
    "pindas": "Pindanoten",
    "walnoot": "Walnoten",
    "hazelnoot": "Hazelnoten",
    "amandel": "Amandelen",
    # Vlees, vis en vega
    "kipfilet": "Kip",
    "kipdijfilet": "Kip",
    "gerookte zalm": "Zalm",
    "vegetarisch gehakt": "Gehakt",
    "vegetarische gehakt": "Gehakt",
}
