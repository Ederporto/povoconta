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
    entities = []
    entity = {}
    try:
        p180s = data["entities"][qid]["claims"]["P180"]
        for p180 in p180s:
            quantidade = get_p1114(p180)
            qid = p180["mainsnak"]["datavalue"]["value"]["id"]
            name = get_name(qid, lang)
            entity = {"qid": qid, "name": name, "quantity": quantidade}
            entities.append(entity)
    except:
        pass

    return entities


def get_p1114(snak):
    if "qualifiers" in snak and "P1114" in snak["qualifiers"]:
        return int(snak["qualifiers"]["P1114"][0]["datavalue"]["value"]["amount"])
    else:
        return 0


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


def post_to_wikidata():
    return 0