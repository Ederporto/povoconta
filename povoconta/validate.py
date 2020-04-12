import requests

SESSION = requests.Session()
WIKIDATA_API_ENDPOINT = 'https://www.wikidata.org/w/api.php'
COMMONS_API_ENDPOINT = 'https://commons.wikimedia.org/w/api.php'


def get_p18(qid):
    """ Get qid P18 """
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims",
        "format": "json"
        
    }

    result = SESSION.get(url=WIKIDATA_API_ENDPOINT, params=params)
    data = result.json()

    try:
        image_name = data["entities"][qid]["claims"]["P18"][0]["mainsnak"]["datavalue"]["value"]
        image = get_image_url(image_name)
    except:
        image = ""

    return image


def get_image_url(filename):
    params = {
        'action': 'query',
        'prop': 'imageinfo',
        'iiprop': 'url',
        'titles': 'File:'+filename,
        "format": "json"
    }

    result = SESSION.get(url=COMMONS_API_ENDPOINT, params=params)
    data = result.json()
    for key in data["query"]["pages"]:
        image_url = data["query"]["pages"][key]["imageinfo"][0]["url"]

    return image_url


def get_p180(qid, lang):
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims|labels",
        "format": "json"
    }

    result = SESSION.get(url=WIKIDATA_API_ENDPOINT, params=params)
    data = result.json()
    depicts = []
    show_validate = False
    try:
        p180s = data["entities"][qid]["claims"]["P180"]
        for p180 in p180s:
            quantity, show_validate = get_p1114(p180)
            qid = p180["mainsnak"]["datavalue"]["value"]["id"]
            id = p180["id"]
            name = get_name(qid, lang)
            depict = {"qid": qid, "id":id, "name": name, "quantity": quantity}
            depicts.append(depict)
    except:
        pass

    return depicts, show_validate


def get_p1114(snak):
    if "qualifiers" in snak and "P1114" in snak["qualifiers"]:
        return int(snak["qualifiers"]["P1114"][0]["datavalue"]["value"]["amount"]), True
    else:
        return 0, False


def get_name(qid, lang):
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "labels",
        "format": "json"
    }
    result = SESSION.get(url=WIKIDATA_API_ENDPOINT, params=params)
    data = result.json()
    name = ""
    try:
        labels = data["entities"][qid]["labels"]

        if lang in labels:
            name = labels[lang]["value"]
        elif "pt-br" in labels:\
            name = labels["pt-br"]["value"]
        elif "pt" in labels:\
            name = labels["pt"]["value"]
        elif "en" in labels:\
            name = labels["en"]["value"]
    except:
        pass

    return name


def search(term, lang):
    params = {
        "action": "wbsearchentities",
        "search": term,
        "language": lang,
        "type": "item",
        "format": "json"
    }

    result = SESSION.get(url=WIKIDATA_API_ENDPOINT, params=params)
    data = result.json()

    possible_terms = []

    for item in data["search"]:
        qid = item["id"]
        label = item["label"]
        description = item["description"]
        possible_terms.append({"qid": qid, "label": label, "description": description})

    return possible_terms


def query_wikidata(query):
    url = "https://query.wikidata.org/sparql"
    params = {
        "query": query,
        "format": "json"
    }
    result = SESSION.post(url=url, params=params)
    data = result.json()
    return data


def per_collection(lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?collection ?collection_label (COUNT(?work) AS ?num_works) WHERE { ?work wdt:P195 wd:Q56677470, ?collection; wdt:P18 ?image; wdt:P180 ?depicts. ?collection rdfs:label ?collection_label. FILTER((LANG(?collection_label)) = '"+lang+"') } GROUP BY ?collection ?collection_label ORDER BY DESC (?num_works)")
    return data


def works_in_collection(qid_collection, mode="validate", lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label WHERE { ?work wdt:P195 wd:Q56677470, wd:"+qid_collection+"; wdt:P18 ?imagem; wdt:P180 ?depicts; rdfs:label ?work_label. FILTER((LANG(?work_label)) = '"+lang+"') }")
    return data


def post_to_wikidata():
    return 0
