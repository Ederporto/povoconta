# -*- coding: utf-8 -*-
#
# This file is part of the "Povo Conta" wikitool
#
# Copyright (C) 2020 Éder Porto and contributors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Some functions, particular to the login part, are derived directly from
# Wikidata Art Depiction Explorer tool, available at
# <https://github.com/EdwardBetts/depicts>, under GPL-3 license.

import requests
import os
import yaml
import mwoauth
import roman
from math import ceil
from flask_thumbnails import Thumbnail
from requests_oauthlib import OAuth1Session
import wikidata_oauth
from flask import Flask, render_template, flash, request, redirect, url_for, session, g
from flask_babel import Babel, gettext
from povoconta.validate import *


__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))
BABEL = Babel(app)
thumb = Thumbnail(app)
consumer_token = mwoauth.ConsumerToken(
    app.config['CONSUMER_KEY'],
    app.config['CONSUMER_SECRET'])
WIKIDATA_API_ENDPOINT = 'https://www.wikidata.org/w/api.php'


############################################################################
# LOGIN                                                                    #
############################################################################
@app.before_request
def init_profile():
    g.profiling = []


@app.before_request
def global_user():
    g.user = wikidata_oauth.get_username()


@app.route('/login')
def login():
    next_page = request.args.get('next')
    if next_page:
        session['after_login'] = next_page

    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']
    base_url = 'https://www.wikidata.org/w/index.php'
    request_token_url = base_url + '?title=Special%3aOAuth%2finitiate'

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          callback_uri='oob')
    fetch_response = oauth.fetch_request_token(request_token_url)

    session['owner_key'] = fetch_response.get('oauth_token')
    session['owner_secret'] = fetch_response.get('oauth_token_secret')

    base_authorization_url = 'https://www.wikidata.org/wiki/Special:OAuth/authorize'
    authorization_url = oauth.authorization_url(base_authorization_url,
                                                oauth_consumer_key=client_key)
    return redirect(authorization_url)


@app.route("/oauth-callback", methods=["GET"])
def oauth_callback():
    base_url = 'https://www.wikidata.org/w/index.php'
    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'])

    oauth_response = oauth.parse_authorization_response(request.url)
    verifier = oauth_response.get('oauth_verifier')
    access_token_url = base_url + '?title=Special%3aOAuth%2ftoken'
    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'],
                          verifier=verifier)

    oauth_tokens = oauth.fetch_access_token(access_token_url)
    session['owner_key'] = oauth_tokens.get('oauth_token')
    session['owner_secret'] = oauth_tokens.get('oauth_token_secret')

    next_page = session.get('after_login')
    return redirect(next_page)


@app.route('/logout')
def logout():
    next_page = request.args.get('next')
    if next_page:
        session['after_logout'] = next_page

    for key in 'owner_key', 'owner_secret', 'username', 'after_login':
        if key in session:
            del session[key]
    next_page = session.get('after_logout')
    return redirect(next_page)


############################################################################
# MUSEU DO IPIRANGA                                                        #
############################################################################
@app.route('/', methods=['GET'])
def museudoipiranga():
    username = wikidata_oauth.get_username()
    return render_template("museudoipiranga.html", username=username)


@app.route('/about', methods=['GET'])
@app.route('/sobre', methods=['GET'])
def sobre():
    username = wikidata_oauth.get_username()
    return render_template("sobre.html", username=username)


@app.route('/tutorial', methods=['GET'])
def tutorial():
    username = wikidata_oauth.get_username()
    return render_template("tutorial.html", username=username)


@app.route('/p195', methods=['GET'])
@app.route('/collections', methods=['GET'])
@app.route('/coleções', methods=['GET'])
def show_per_collection():
    username = wikidata_oauth.get_username()
    json = per_collection()
    collections = []
    for result in json["results"]["bindings"]:
        collections.append({
            "qid": result["collection"]["value"].split("/")[-1],
            "label": result["collection_label"]["value"],
            "quantity": result["num_works"]["value"]})
    return render_template("per_collection.html", collections=collections, username=username)


@app.route('/p195/<qid>', methods=['GET'])
@app.route('/collection/<qid>', methods=['GET'])
@app.route('/coleção/<qid>', methods=['GET'])
def show_works_in_collection(qid):
    username = wikidata_oauth.get_username()
    json = works_in_collection(qid)
    collection = []
    collection_data_ = collection_data(qid)

    for result in json["results"]["bindings"]:
        collection.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"],
            "image": result["image"]["value"]+"?width=200px"})

    coll_data = {
        "collection_label": collection_data_["results"]["bindings"][0]["collection_label"]["value"],
        "total": collection_data_["results"]["bindings"][0]["total"]["value"],
        "total_scope": len(collection),
        "collection_article": collection_data_["results"]["bindings"][0]["collection_article"]["value"] if "collection_article" in collection_data_["results"]["bindings"][0] else "",
        "collection_category": collection_data_["results"]["bindings"][0]["collection_category"]["value"] if "collection_category" in collection_data_["results"]["bindings"][0] else "",
        "named_after": collection_data_["results"]["bindings"][0]["named_after"]["value"] if "named_after" in collection_data_["results"]["bindings"][0] else "",
        "named_after_label": collection_data_["results"]["bindings"][0]["named_after_label"]["value"] if "named_after_label" in collection_data_["results"]["bindings"][0] else "",
        "named_after_article": collection_data_["results"]["bindings"][0]["named_after_article"]["value"] if "named_after_article " in collection_data_["results"]["bindings"][0] else ""
    }

    return render_template("per_collection.html",
                           collection=collection,
                           qid=qid,
                           username=username,
                           collection_data=coll_data,
                           goback="museudoipiranga")


@app.route('/p170', methods=['GET'])
@app.route('/creators', methods=['GET'])
@app.route('/criadores', methods=['GET'])
def show_per_creator():
    username = wikidata_oauth.get_username()
    json = per_creator()
    creators = []
    for result in json["results"]["bindings"]:
        creators.append({
            "qid": result["creator"]["value"].split("/")[-1],
            "label": result["creator_label"]["value"],
            "quantity": result["total"]["value"]})
    return render_template("per_creator.html", creators=creators, username=username)


@app.route('/p170/<qid>', methods=['GET'])
@app.route('/creator/<qid>', methods=['GET'])
@app.route('/criador/<qid>', methods=['GET'])
def show_works_of_creator(qid):
    username = wikidata_oauth.get_username()
    json = works_of_creator(qid)
    creator = []
    creator_data_ = creator_data(qid)

    for result in json["results"]["bindings"]:
        creator.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"],
            "image": result["image"]["value"] + "?width=200px"})

    creator_data_aux = {
        "creator_article": creator_data_["results"]["bindings"][0]["creator_article"]["value"] if "creator_article" in creator_data_["results"]["bindings"][0] else "",
        "creator_label": creator_data_["results"]["bindings"][0]["creator_label"]["value"],
        "total": creator_data_["results"]["bindings"][0]["total"]["value"],
        "total_scope": len(creator),
    }

    return render_template("per_creator.html",
                           creator=creator,
                           qid=qid,
                           username=username,
                           creator_data=creator_data_aux,
                           goback="museudoipiranga")


@app.route('/p571', methods=['GET'])
@app.route('/decades', methods=['GET'])
@app.route('/décadas', methods=['GET'])
def show_per_decade():
    username = wikidata_oauth.get_username()
    json = per_decade()
    decades = []
    for result in json["results"]["bindings"]:
        decades.append({"label": result["decade"]["value"]})
    return render_template("per_decade.html", decades=decades, username=username)


@app.route('/p571/<decade>', methods=['GET'])
@app.route('/decade/<decade>', methods=['GET'])
@app.route('/década/<decade>', methods=['GET'])
def show_works_of_decade(decade):
    username = wikidata_oauth.get_username()
    json = works_of_decade(decade)
    decade_ = []

    for result in json["results"]["bindings"]:
        decade_.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"],
            "image": result["image"]["value"] + "?width=200px"})

    return render_template("per_decade.html",
                           decade=decade,
                           indeterminate="Década indeterminada",
                           username=username,
                           decade_data=decade_,
                           goback="museudoipiranga")


@app.route('/p31', methods=['GET'])
@app.route('/instances', methods=['GET'])
@app.route('/tipos', methods=['GET'])
def show_per_instance():
    username = wikidata_oauth.get_username()
    json = per_instance()
    instances = []
    for result in json["results"]["bindings"]:
        instances.append({"qid": result["instance"]["value"].split("/")[-1],
                          "label": result["instance_label"]["value"]})
    return render_template("per_instance.html", instances=instances, username=username)


@app.route('/p31/<qid>', methods=['GET'])
@app.route('/instance/<qid>', methods=['GET'])
@app.route('/tipo/<qid>', methods=['GET'])
def show_works_of_instance(qid):
    username = wikidata_oauth.get_username()
    json = works_of_instance(qid)
    instance = []

    for result in json["results"]["bindings"]:
        instance.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"],
            "image": result["image"]["value"] + "?width=200px"})

    instance_data = {"instance_label": get_name(qid),
                     "total_scope": len(instance)}

    return render_template("per_instance.html",
                           instance=instance,
                           qid=qid,
                           username=username,
                           instance_data=instance_data,
                           goback="museudoipiranga")


@app.route('/p180', methods=['GET'])
@app.route('/depicts', methods=['GET'])
@app.route('/descritores', methods=['GET'])
def show_per_depict():
    username = wikidata_oauth.get_username()
    json = per_depict()
    depicts = []
    for result in json["results"]["bindings"]:
        depicts.append({"qid": result["depict"]["value"].split("/")[-1],
                        "label": result["depict_label"]["value"]})
    return render_template("per_depict.html", depicts=depicts, username=username)


@app.route('/p180/<qid>', methods=['GET'])
@app.route('/depict/<qid>', methods=['GET'])
@app.route('/descritor/<qid>', methods=['GET'])
def show_works_of_depict(qid):
    username = wikidata_oauth.get_username()
    json = works_of_depict(qid)
    depict = []

    for result in json["results"]["bindings"]:
        depict.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"],
            "image": result["image"]["value"] + "?width=200px"})

    depict_data = {"depict_label": get_name(qid),
                   "total_scope": len(depict)}

    return render_template("per_depict.html",
                           depict=depict,
                           qid=qid,
                           username=username,
                           depict_data=depict_data,
                           goback="museudoipiranga")


@app.route('/qid/<qid>', methods=['GET'])
def view_work_museudoipiranga(qid):
    username = wikidata_oauth.get_username()
    if "goback" in request.args:
        goback = request.args["goback"]
        if goback == "museudoipiranga":
            goback = qid
            first = True
        elif goback == "":
            return redirect(url_for("museudoipiranga"))
        else:
            goback = goback
            first = False
    else:
        goback = "museudoipiranga"
        first = True

    work_data_ = get_work_data(qid)
    work_depicts_ = get_p180(qid, "pt-br")

    if work_data_:
        return render_template("item.html",
                               entity=qid,
                               work_depicts=work_depicts_,
                               work_data=work_data_,
                               username=username,
                               back=goback,
                               skip=get_next_qid(qid),
                               first=first)
    else:
        return redirect(url_for("erro"))


@app.route('/save/<qid>', methods=['POST'])
def save_quantities(qid):
    form = request.form
    if form and form.__len__() > 0:
        for action in form:
            statement_, hash = action.split(";")
            quantity, continue_ = validate_quantity(form[action])
            if continue_:
                if hash:
                    try:
                        change_qualifier(statement_, hash, quantity)
                    except:
                        pass
                else:
                    try:
                        add_qualifier(statement_, quantity)
                    except:
                        pass
    next_qid = get_next_qid(qid)
    return redirect(url_for("view_work_museudoipiranga", qid=next_qid, goback=qid))


def validate_quantity(quantity):
    if quantity == "" or quantity == "0":
        return "", False
    else:
        try:
            return int(quantity), True
        except ValueError:
            return "", False


def get_work_depicts(qid):
    depicts_work = work_depicts(qid)
    work_depicts_ = []
    for result in depicts_work["results"]["bindings"]:
        depicts_id = result["depicts_"]["value"].split("/")[-1]
        depicts_qid = result["depicts"]["value"].split("/")[-1]
        if "depicts_label_ptbr" in result:
            depicts_label = result["depicts_label_ptbr"]["value"]
        elif "depicts_label_pt" in result:
            depicts_label = result["depicts_label_pt"]["value"]
        else:
            depicts_label = ""
        if "depicts_desc_ptbr" in result:
            depicts_desc = result["depicts_desc_ptbr"]["value"]
        elif "depicts_desc_pt" in result:
            depicts_desc = result["depicts_desc_pt"]["value"]
        else:
            depicts_desc = ""
        quantity_hash = result["quantity_"]["value"] if "quantity_" in result else ""
        quantity_value = result["quantity"]["value"] if "quantity" in result else 0

        work_depicts_.append({"depict_id": depicts_id,
                              "depict_qid": depicts_qid,
                              "depict_label": depicts_label,
                              "depict_desc": depicts_desc,
                              "quantity_hash": quantity_hash,
                              "quantity_value": quantity_value})
    return work_depicts_


def get_work_data(qid):
    data_work = work_data(qid)
    if data_work["results"]["bindings"].__len__()>0:
        if "work_label_" in data_work["results"]["bindings"][0]:
            work_label = data_work["results"]["bindings"][0]["work_label_"]["value"]
        else:
            work_label = ""
        if "image" in data_work["results"]["bindings"][0]:
            image = data_work["results"]["bindings"][0]["image"]["value"] + "?width=1000px"
        else:
            image = ""
        if "date" in data_work["results"]["bindings"][0]:
            date_aux = data_work["results"]["bindings"][0]["date"]["value"]
            if date_aux.startswith("Século"):
                date = "Século "+str(roman.toRoman(ceil(int(date_aux.replace("Século ", ""))/100)))
            else:
                date = date_aux
        else:
            date = ""
        if "instances" in data_work["results"]["bindings"][0]:
            instances_ = data_work["results"]["bindings"][0]["instances"]["value"].split(";")
        else:
            instances_ = []
        if "instance_labels" in data_work["results"]["bindings"][0]:
            instance_labels_ = data_work["results"]["bindings"][0]["instance_labels"]["value"].split(";")
        else:
            instance_labels_ = []
        if "creators" in data_work["results"]["bindings"][0]:
            creators_ = data_work["results"]["bindings"][0]["creators"]["value"].split(";")
        else:
            creators_ = []
        if "creators_labels" in data_work["results"]["bindings"][0]:
            creators_labels_ = data_work["results"]["bindings"][0]["creators_labels"]["value"].split(";")
        else:
            creators_labels_ = []
        if "materials" in data_work["results"]["bindings"][0]:
            materials_ = data_work["results"]["bindings"][0]["materials"]["value"].split(";")
        else:
            materials_ = []
        if "materials_labels" in data_work["results"]["bindings"][0]:
            materials_labels_ = data_work["results"]["bindings"][0]["materials_labels"]["value"].split(";")
        else:
            materials_labels_ = []
        if "commissioners" in data_work["results"]["bindings"][0]:
            commissioners_ = data_work["results"]["bindings"][0]["commissioners"]["value"].split(";")
        else:
            commissioners_ = []
        if "commissioners_labels" in data_work["results"]["bindings"][0]:
            commissioners_labels_ = data_work["results"]["bindings"][0]["commissioners_labels"]["value"].split(";")
        else:
            commissioners_labels_ = []

        instances = []
        if instances_ and instance_labels_ and len(instances_)==len(instance_labels_) and instances!=[""]:
            for i in range(len(instances_)):
                instances.append({"qid": instances_[i].split("/")[-1],
                                  "label": instance_labels_[i]})
        creators = []
        if creators_ and creators_labels_ and len(creators_) == len(creators_labels_) and creators_!=[""]:
            for i in range(len(creators_)):
                creators.append({"qid": creators_[i].split("/")[-1],
                                  "label": creators_labels_[i]})
        materials = []
        if materials_ and materials_labels_ and len(materials_) == len(materials_labels_) and materials_!=[""]:
            for i in range(len(materials_)):
                materials.append({"qid": materials_[i].split("/")[-1],
                                  "label": materials_labels_[i]})
        commissioners = []
        if commissioners_ and commissioners_labels_ and len(commissioners_) == len(commissioners_labels_) and commissioners_!=[""]:
            for i in range(len(commissioners_)):
                commissioners.append({"qid": commissioners_[i].split("/")[-1],
                                      "label": commissioners_labels_[i]})

        work_data_ = {"work_label": work_label,
                      "image": image,
                      "date": date,
                      "instances": instances,
                      "creators": creators,
                      "materials": materials,
                      "commissioners": commissioners}

        return work_data_
    else:
        return ""


############################################################################
# REQUESTS TO WIKIDATA                                                     #
############################################################################
def add_qualifier(claim, quantity):
    token = wikidata_oauth.get_token()
    params = {
        "action": "wbsetqualifier",
        "claim": claim,
        "property": "P1114",
        "value": "{\"amount\":\"+"+str(quantity)+"\", \"unit\": \"1\"}",
        "snaktype": "value",
        "token": token
    }

    wikidata_oauth.api_post_request(params)


def change_qualifier(claim, hash, quantity):
    token = wikidata_oauth.get_token()
    params = {
        "action": "wbsetqualifier",
        "claim": claim,
        "property": "P1114",
        "value": "{\"amount\": \"+" + str(quantity) + "\", \"unit\": \"1\"}",
        "snaktype": "value",
        "snakhash": hash,
        "token": token
    }

    wikidata_oauth.api_post_request(params)
    flash(_("Qualificador alterado com sucesso"), "success")


def remove_qualifier(claim, qualifier):
    token = wikidata_oauth.get_token()
    params = {
        "action": "wbremovequalifiers",
        "claim": claim,
        "qualifiers": qualifier,
        "token": token
    }

    wikidata_oauth.api_post_request(params)
    flash(_("Qualificador removido com sucesso"), "success")


############################################################################
# RUN THE APP                                                              #
############################################################################
if __name__ == "__main__":
    app.run()