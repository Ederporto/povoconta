import requests
from flask import Flask, render_template, flash, request, redirect, url_for
from flask_babel import Babel, gettext
from povoconta.login import start_client_login
from povoconta.validate import get_p18, get_p180, post_to_wikidata

APP = Flask(__name__)
APP.config.from_pyfile('config.py')
BABEL = Babel(APP)


@APP.route("/login", methods=['GET', 'POST'])
def show_form():
    """ Render form template and handle form submission request """

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        start_client_login(username, password)

    return render_template('clientlogin_form.html')


@APP.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@APP.route("/validate", methods=['GET', 'POST'])
def validate():
    if request.method == "POST":
        return redirect(url_for("validate_item", qid=request.form["qid"]))
    else:
        return render_template("validate.html", show=True)


@APP.route("/validate/<qid>", methods=['GET', 'POST'])
def validate_item(qid):
    image = get_p18(qid)
    entities = get_p180(qid, "pt")
    show = True if entities else False
    return render_template("validate.html", image=image, entities=entities, show=show, item=qid)


@APP.route("/wikidatify", methods=['GET', 'POST'])
def wikidatify():
    if request.method == "POST":
        return redirect(url_for("wikidatify_item", qid=request.form["qid"]))
    else:
        return render_template("wikidatify.html", show=True)


@APP.route("/wikidatify/<qid>", methods=['GET', 'POST'])
def wikidatify_item(qid):
    image = get_p18(qid)
    if request.method == "POST":
        try:
            post_to_wikidata()
            flash("Insira outra entidade")
        except:
            pass
        return render_template("wikidatify.html", show=True, image=image, item=qid)
    else:
        return render_template("wikidatify.html", show=True, image=image, item=qid)


if __name__ == "__main__":
    APP.run()