import requests
from random import random

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
    try:
        p180s = data["entities"][qid]["claims"]["P180"]
        for p180 in p180s:
            quantity, quantity_hash, show_validate = get_p1114(p180)
            qid = p180["mainsnak"]["datavalue"]["value"]["id"]
            id_ = p180["id"]
            name = get_name(qid, lang)
            depict = {"depict_qid": qid, "depict_id": id_, "depict_label": name, "quantity_value": quantity, "quantity_hash": quantity_hash}
            depicts.append(depict)
    except:
        pass

    return depicts


def get_p1114(snak):
    if "qualifiers" in snak and "P1114" in snak["qualifiers"]:
        return int(snak["qualifiers"]["P1114"][0]["datavalue"]["value"]["amount"]), snak["qualifiers"]["P1114"][0]["hash"], True
    else:
        return 0, "", False


def get_name(qid, lang="pt-br"):
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
        else:
            name = qid
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
    data = query_wikidata("SELECT DISTINCT ?collection ?collection_label (COUNT(?work) AS ?num_works) WHERE {?work wdt:P195 wd:Q56677470, ?collection; wdt:P18 ?image; wdt:P180 ?depicts. FILTER(?collection!=wd:Q56677470) ?collection rdfs:label ?collection_label_aux. FILTER((LANG(?collection_label_aux)) = \""+lang+"\") BIND(STRAFTER(?collection_label_aux, \" \") AS ?collection_label)} GROUP BY ?collection ?collection_label ORDER BY ?num_works")
    return data


def works_in_collection(qid_collection, lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label ?image (COUNT(DISTINCT(?depicts_p)) AS ?count_depicts) WHERE {?work wdt:P195 wd:Q56677470, wd:"+qid_collection+";wdt:P18 ?image;wdt:P180 ?depicts;rdfs:label ?work_label. OPTIONAL {?work p:P180 ?depicts_p. ?depicts_p pq:P1114 ?depicts_quantity.} FILTER((LANG(?work_label)) = \""+lang+"\")} GROUP BY ?work ?work_label ?image ORDER BY ?count_depicts")
    return data


def collection_data(qid_collection, lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?collection ?collection_label ?collection_category ?collection_article ?named_after ?named_after_label ?named_after_article (COUNT(?work) AS ?total) (COUNT(?work_scope) AS ?total_scope) WHERE { BIND(wd:"+qid_collection+" AS ?collection) OPTIONAL {?commons_collection schema:about ?collection; schema:name ?collection_category; schema:isPartOf <https://commons.wikimedia.org/>.} OPTIONAL {?article_collection schema:about ?collection; schema:name ?collection_article; schema:isPartOf <https://pt.wikipedia.org/>.} ?collection rdfs:label ?collection_label. FILTER(LANG(?collection_label)=\""+lang+"\") OPTIONAL {?collection wdt:P138 ?named_after. ?named_after rdfs:label ?named_after_label. FILTER(LANG(?named_after_label)=\""+lang+"\") OPTIONAL{?article schema:about ?named_after; schema:name ?named_after_article; schema:isPartOf <https://pt.wikipedia.org/>.}} ?work wdt:P195 ?collection. OPTIONAL {?work wdt:P18 ?image; wdt:P180 ?depic. BIND(1 AS ?work_scope)}} GROUP BY ?named_after ?named_after_label ?named_after_article ?collection ?collection_label ?collection_category ?collection_article")
    return data


def per_artist(lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?artist ?artist_label (COUNT(?work) AS ?total) WHERE {?work wdt:P195 wd:Q56677470. {?work wdt:P18 ?image. ?work wdt:P180 ?depict. ?work wdt:P170 ?artist.} UNION {?work_ wdt:P170 ?artist. ?work wdt:P195 ?work_. ?work wdt:P18 ?image. ?work wdt:P180 ?depict.} ?artist rdfs:label ?artist_label. FILTER(LANG(?artist_label)=\""+lang+"\").} GROUP BY ?artist ?artist_label ORDER BY ?total")
    return data


def works_of_artist(qid_artist, lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label ?image (COUNT(?depict) AS ?total) WHERE {BIND(wd:"+qid_artist+" AS ?artist) ?work wdt:P195 wd:Q56677470. {?work wdt:P18 ?image. ?work wdt:P180 ?depict. ?work wdt:P170 ?artist.} UNION {?work_ wdt:P170 ?artist. ?work wdt:P195 ?work_. ?work wdt:P18 ?image. ?work wdt:P180 ?depict.} ?work rdfs:label ?work_label. FILTER(LANG(?work_label)=\""+lang+"\").} GROUP BY ?work ?work_label ?image ORDER BY ?total")
    return data


def artist_data(qid_artist, lang="pt-br", lang_fallback="pt"):
    data = query_wikidata("SELECT DISTINCT ?creator ?artist_article ?artist_label (COUNT(?work) AS ?total) (COUNT(?work_scope) AS ?total_scope) WHERE {BIND(wd:"+qid_artist+" AS ?creator) OPTIONAL {?article_ schema:about ?creator; schema:inLanguage 'pt'; schema:name ?artist_article.} OPTIONAL {?creator rdfs:label ?artist_label_ptbr. FILTER(LANG(?artist_label_ptbr)=\""+lang+"\").} OPTIONAL {?creator rdfs:label ?artist_label_pt. FILTER(LANG(?artist_label_pt)=\""+lang_fallback+"\").} BIND(IF(BOUND(?artist_label_ptbr),?artist_label_ptbr,IF(BOUND(?artist_label_pt),?artist_label_pt,'')) AS ?artist_label) ?work wdt:P195 wd:Q56677470. {?work wdt:P170 ?creator} UNION {?work_ wdt:P170 ?creator. ?work wdt:P195 ?work_.} OPTIONAL {?work wdt:P18 ?image;wdt:P180 ?depict.BIND(1 AS ?work_scope)}} GROUP BY ?creator ?artist_article ?artist_label")
    return data


def per_decade(indeterminate="Década indeterminada"):
    data = query_wikidata("SELECT DISTINCT ?decade WHERE {?work wdt:P195 wd:Q56677470; wdt:P18 ?image; wdt:P180 ?depicts. ?work p:P571 ?decade_aux. ?decade_aux psv:P571 ?decade_. ?decade_ wikibase:timeValue ?value. ?decade_ wikibase:timePrecision ?precision. BIND(IF(?precision = 7,CONCAT('"+indeterminate+"'), STR(10*FLOOR(YEAR(?value)/10))) AS ?decade)} ORDER BY ?decade")
    return data


def works_of_decade(decade, lang="pt-br", indeterminate="Década indeterminada"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label ?image (COUNT(?depicts) AS ?total) WHERE {?work wdt:P195 wd:Q56677470; wdt:P18 ?image; wdt:P180 ?depicts. ?work p:P571 ?decade_aux. ?decade_aux psv:P571 ?decade_. ?decade_ wikibase:timeValue ?value. ?decade_ wikibase:timePrecision ?precision. ?work rdfs:label ?work_label. FILTER((LANG(?work_label)) = \""+lang+"\") BIND(IF(?precision = 7,CONCAT('"+indeterminate+"'), STR(10*FLOOR(YEAR(?value)/10))) AS ?decade) FILTER(?decade=\""+decade+"\")} GROUP BY ?work ?work_label ?image ORDER BY ?total")
    return data


def per_instance(lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?instance ?instance_label (COUNT(DISTINCT(?work)) AS ?total) WHERE {?work wdt:P195 wd:Q56677470; wdt:P18 ?image; wdt:P180 ?depicts; wdt:P31 ?instance. ?instance rdfs:label ?instance_label.FILTER(LANG(?instance_label)=\""+lang+"\") FILTER(?instance!=wd:Q18593264)} GROUP BY ?instance ?instance_label ORDER BY ?total")
    return data


def works_of_instance(qid_instance, lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label ?image (COUNT(DISTINCT(?depict)) AS ?total) WHERE {BIND(wd:"+qid_instance+" AS ?instance) ?work wdt:P195 wd:Q56677470. {?work wdt:P18 ?image; wdt:P180 ?depict; wdt:P31 ?instance.} UNION {?work_ wdt:P31 ?instance. ?work wdt:P195 ?work_; wdt:P18 ?image; wdt:P180 ?depict.} ?work rdfs:label ?work_label. FILTER((LANG(?work_label)) = \""+lang+"\")} GROUP BY ?work ?work_label ?image ORDER BY ?total")
    return data


def per_depict(lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?depict ?depict_label (COUNT(?work) AS ?total) WHERE { ?work wdt:P195 wd:Q56677470; wdt:P18 ?image; wdt:P180 ?depict. ?depict rdfs:label ?depict_label. FILTER((LANG(?depict_label)) = \""+lang+"\")} GROUP BY ?depict ?depict_label ORDER BY (?total)")
    return data


def works_of_depict(qid_depict, lang="pt-br"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label ?image (COUNT(DISTINCT(?depict)) AS ?total) WHERE {BIND(wd:"+qid_depict+" AS ?depict_) ?work wdt:P195 wd:Q56677470. {?work wdt:P18 ?image; wdt:P180 ?depict; wdt:P180 ?depict_.} UNION {?work_ wdt:P180 ?depict_. ?work wdt:P195 ?work_; wdt:P18 ?image; wdt:P180 ?depict.} ?work rdfs:label ?work_label. FILTER((LANG(?work_label)) = \""+lang+"\")} GROUP BY ?work ?work_label ?image ORDER BY ?total")
    return data


def work_data(qid_work, lang="pt-br", lang_fallback="pt"):
    data = query_wikidata("SELECT DISTINCT ?work ?work_label_ ?date (SAMPLE(?image) AS ?image) (GROUP_CONCAT(DISTINCT(?instance);separator=';') AS ?instances) (GROUP_CONCAT(DISTINCT(?instance_label_);separator=';') AS ?instance_labels) (GROUP_CONCAT(DISTINCT(?artist);separator=';') AS ?artists) (GROUP_CONCAT(DISTINCT(?artist_label_);separator=';') AS ?artists_labels) (GROUP_CONCAT(DISTINCT(?material);separator=';') AS ?materials) (GROUP_CONCAT(DISTINCT(?material_label_);separator=';') AS ?materials_labels) (GROUP_CONCAT(DISTINCT(?commissioned);separator=';') AS ?commissioners) (GROUP_CONCAT(DISTINCT(?commissioned_label_);separator=';') AS ?commissioners_labels) WHERE {BIND(wd:"+qid_work+" AS ?work) ?work wdt:P18 ?image. OPTIONAL {?work wdt:P31 ?instance. OPTIONAL {?instance rdfs:label ?instance_label_ptbr. FILTER(LANG(?instance_label_ptbr)='"+lang+"')} OPTIONAL {?instance rdfs:label ?instance_label_pt. FILTER(LANG(?instance_label_pt)='"+lang_fallback+"')} BIND(IF(BOUND(?instance_label_ptbr),?instance_label_ptbr,IF(BOUND(?instance_label_pt),?instance_label_pt,'')) AS ?instance_label_)} OPTIONAL {?work wdt:P170 ?artist. OPTIONAL {?artist rdfs:label ?artist_label_ptbr. FILTER(LANG(?artist_label_ptbr)='"+lang+"')} OPTIONAL {?artist rdfs:label ?artist_label_pt. FILTER(LANG(?artist_label_pt)='"+lang_fallback+"')} BIND(IF(BOUND(?artist_label_ptbr),?artist_label_ptbr,IF(BOUND(?artist_label_pt),?artist_label_pt,'')) AS ?artist_label_)} OPTIONAL {?work wdt:P186 ?material. OPTIONAL {?material rdfs:label ?material_label_ptbr. FILTER(LANG(?material_label_ptbr)='"+lang+"')} OPTIONAL {?material rdfs:label ?material_label_pt. FILTER(LANG(?material_label_pt)='"+lang_fallback+"')} BIND(IF(BOUND(?material_label_ptbr),?material_label_ptbr,IF(BOUND(?material_label_pt),?material_label_pt,'')) AS ?material_label_)} OPTIONAL {?work wdt:P88 ?commissioned. OPTIONAL {?commissioned rdfs:label ?commissioned_label_ptbr. FILTER(LANG(?commissioned_label_ptbr)='"+lang+"')} OPTIONAL {?commissioned rdfs:label ?commissioned_label_pt. FILTER(LANG(?commissioned_label_pt)='"+lang_fallback+"')} BIND(IF(BOUND(?commissioned_label_ptbr),?commissioned_label_ptbr,IF(BOUND(?commissioned_label_pt),?commissioned_label_pt,'')) AS ?commissioned_label_)} OPTIONAL {?work rdfs:label ?work_label_ptbr. FILTER(LANG(?work_label_ptbr)='"+lang+"')} OPTIONAL {?work rdfs:label ?work_label_pt. FILTER(LANG(?work_label_pt)='"+lang_fallback+"')} BIND(IF(BOUND(?work_label_ptbr),?work_label_ptbr,IF(BOUND(?work_label_pt),?work_label_pt,'')) AS ?work_label_) OPTIONAL {?work p:P571/psv:P571 ?date_. ?date_ wikibase:timePrecision ?date_precision. ?date_ wikibase:timeValue ?date_value. BIND(IF(?date_precision=7,CONCAT('Século ',STR(YEAR(?date_value))),IF(?date_precision=8,CONCAT('Década de ',STR(YEAR(?date_value))),IF(?date_precision>8,STR(YEAR(?date_value)),''))) AS ?date)}} GROUP BY ?work ?work_label_ ?date")
    return data


def work_depicts(qid_work, lang="pt-br", lang_fallback="pt"):
    data = query_wikidata("SELECT DISTINCT ?depicts_ ?depicts ?depicts_label_ptbr ?depicts_desc_ptbr ?depicts_label_pt ?depicts_desc_pt ?quantity_ ?quantity  WHERE {BIND(wd:"+qid_work+" AS ?work) ?work p:P180 ?depicts_. ?depicts_ ps:P180 ?depicts. OPTIONAL {?depicts_ pq:P1114 ?quantity. ?depicts_ pqv:P1114 ?quantity_.} OPTIONAL {?depicts rdfs:label ?depicts_label_ptbr. FILTER((LANG(?depicts_label_ptbr)) = \""+lang+"\")} OPTIONAL {?depicts rdfs:label ?depicts_label_pt. FILTER((LANG(?depicts_label_pt)) = \""+lang_fallback+"\")} OPTIONAL {?depicts schema:description ?depicts_desc_ptbr. FILTER((LANG(?depicts_desc_ptbr)) = \""+lang+"\")} OPTIONAL {?depicts schema:description ?depicts_desc_pt. FILTER((LANG(?depicts_desc_pt)) = \""+lang_fallback+"\")}}")
    return data


def get_next_qid(qid_from):
    data = query_wikidata("SELECT DISTINCT ?work (MD5(CONCAT(str("+str(random())+"*RAND()),str(?work))) AS ?random_hash) WHERE {?work wdt:P195 wd:Q56677470; wdt:P18 ?image; wdt:P180 ?depicts. MINUS{VALUES ?work {wd:"+qid_from+"}}} ORDER BY ?random_hash LIMIT 1")
    return data["results"]["bindings"][0]["work"]["value"].split("/")[-1]
