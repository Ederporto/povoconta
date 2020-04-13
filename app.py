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
import mwapi
from requests_oauthlib import OAuth1Session
import wikidata_oauth
from flask import Flask, render_template, flash, request, redirect, url_for, session, g
from flask_babel import Babel, gettext
from povoconta.validate import get_p18, get_p180, per_collection, works_in_collection


__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))
BABEL = Babel(app)
consumer_token = mwoauth.ConsumerToken(
    app.config['CONSUMER_KEY'],
    app.config['CONSUMER_SECRET'])
WIKIDATA_API_ENDPOINT = 'https://www.wikidata.org/w/api.php'

@app.template_global()
def current_url():
    args = request.view_args.copy()
    args.update(request.args)
    return url_for(request.endpoint, **args)


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
# MUSEU PAULISTA                                                           #
############################################################################
@app.route('/', methods=['GET'])
@app.route('/museupaulista', methods=['GET'])
def museupaulista():
    username = wikidata_oauth.get_username()
    return render_template("museupaulista.html", username=username)


@app.route('/museupaulista/<url_prefix>/<qid>', methods=['GET', 'POST'])
def view_work_museupaulista(url_prefix, qid):
    username = wikidata_oauth.get_username()
    depicts = get_p180(qid, "pt-br")
    image = get_p18(qid)
    if request.method == "POST":
        if "confirmation" in request.form:
            edit = request.form["confirmation"].split(";")
            result = post_to_wikidata(edit[0], edit[1])
            return result
        else:
            print(request.form["confirmation_quantity"])
            print(request.form["quantity_statement"])
    return render_template("item.html",
                           entity=qid,
                           url_prefix=url_prefix,
                           depicts=depicts,
                           image=image,
                           username=username)


def post_to_wikidata(claim, qualifier):
    params = {
        "action": "wbremovequalifiers",
        "claim": claim,
        "qualifiers": qualifier
    }

    result = wikidata_oauth.api_post_request(params)
    return result


@app.route('/save_validation', methods=['POST'])
def save_validation():
    confirmation = request.form['confirmation']
    return confirmation

@app.route('/museupaulista/P195s', methods=['GET'])
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


@app.route('/museupaulista/P195/<qid>', methods=['GET'])
def show_works_in_collection(qid):
    username = wikidata_oauth.get_username()
    json = works_in_collection(qid)
    collection = []
    for result in json["results"]["bindings"]:
        collection.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"]})
    return render_template("per_collection.html", collection=collection, qid=qid, username=username)


if __name__ == "__main__":
    app.run()