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

import requests
import os
import yaml
import mwoauth
import mwapi
import requests_oauthlib
from flask import Flask, render_template, flash, request, redirect, url_for, session
from flask_babel import Babel, gettext
from povoconta.validate import get_p18, get_p180, post_to_wikidata, per_collection, works_in_collection


__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))
BABEL = Babel(app)
consumer_token = mwoauth.ConsumerToken(
    app.config['CONSUMER_KEY'],
    app.config['CONSUMER_SECRET'])


############################################################################
# LOGIN                                                                    #
############################################################################
@app.route('/login')
def login():
    consumer_token = mwoauth.ConsumerToken(app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'])
    try:
        redirect_, request_token = mwoauth.initiate(app.config['OAUTH_MWURI'], consumer_token)
    except Exception:
        app.logger.exception('mwoauth.initiate failed')
        return redirect(url_for('museupaulista'))
    else:
        session['request_token'] = dict(zip(request_token._fields, request_token))
        return redirect(redirect_)


@app.route('/oauth-callback')
def oauth_callback():
    if 'request_token' not in session:
        flash('OAuth callback failed. Are cookies disabled?')
        return redirect(url_for('museupaulista'))

    consumer_token = mwoauth.ConsumerToken(app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'])

    try:
        access_token = mwoauth.complete(
            app.config['OAUTH_MWURI'],
            consumer_token,
            mwoauth.RequestToken(**session['request_token']),
            request.query_string)

        identity = mwoauth.identify(app.config['OAUTH_MWURI'], consumer_token, access_token)
    except Exception:
        app.logger.exception('OAuth authentication failed')

    else:
        session['access_token'] = dict(zip(access_token._fields, access_token))
        session['username'] = identity['username']

    return redirect(url_for('museupaulista'))


@app.route('/logout')
def logout():
    """Log the user out by clearing their session."""
    session.clear()
    return redirect(url_for('museupaulista'))


############################################################################
# MUSEU PAULISTA                                                           #
############################################################################
@app.route('/', methods=['GET'])
@app.route('/museupaulista', methods=['GET'])
def museupaulista():
    return render_template("museupaulista.html")


@app.route('/museupaulista/<url_prefix>/<qid>', methods=['GET'])
def view_work_museupaulista(url_prefix, qid):
    depicts = get_p180(qid, "pt-br")
    image = get_p18(qid)
    print(depicts)
    return render_template("item.html", depicts=depicts, image=image)


@app.route('/museupaulista/P195s', methods=['GET'])
def show_per_collection():
    json = per_collection()
    collections = []
    for result in json["results"]["bindings"]:
        collections.append({
            "qid": result["collection"]["value"].split("/")[-1],
            "label": result["collection_label"]["value"],
            "quantity": result["num_works"]["value"]})
    return render_template("per_collection.html", collections=collections)


@app.route('/museupaulista/P195/<qid>', methods=['GET'])
def show_works_in_collection(qid):
    json = works_in_collection(qid)
    collection = []
    for result in json["results"]["bindings"]:
        collection.append({
            "qid": result["work"]["value"].split("/")[-1],
            "label": result["work_label"]["value"]})
    return render_template("per_collection.html", collection=collection, qid=qid)


if __name__ == "__main__":
    app.run()