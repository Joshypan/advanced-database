from flask import Flask, render_template, request, redirect, url_for

import database

app = Flask(__name__)
database.setup_database("pets.db")


@app.route("/", methods=["GET"])
@app.route("/hello", methods=["GET"])
@app.route("/hello/<name>", methods=["GET"])
def get_hello(name="world"):
    return render_template("hello.html", name=name)


@app.route("/bye", methods=["GET"])
def get_bye():
    return "Bye!"


@app.route("/pets", methods=["GET"])
@app.route("/list", methods=["GET"])
def get_pets():
    return render_template("list.html", pets=database.get_pets())


@app.route("/create", methods=["GET"])
def get_create():
    return render_template("create.html")


@app.route("/create", methods=["POST"])
def post_create():
    database.create_pet(dict(request.form))
    return redirect(url_for("get_pets"))


@app.route("/update", methods=["GET"])
@app.route("/update/<int:id>", methods=["GET"])
def get_update(id=None):
    if id is None:
        return render_template("error.html", error_message="No ID was provided."), 400
    data = database.get_pet(id)
    if data is None:
        return render_template("error.html", error_message="Data not found."), 404
    return render_template("update.html", data=data)


@app.route("/update", methods=["POST"])
@app.route("/update/<int:id>", methods=["POST"])
def post_update(id=None):
    if id is None:
        return render_template("error.html", error_message="No ID was provided."), 400
    if database.get_pet(id) is None:
        return render_template("error.html", error_message="Data not found."), 404
    database.update_pet(id, dict(request.form))
    return redirect(url_for("get_pets"))


@app.route("/delete/<int:id>", methods=["GET"])
def get_delete(id):
    database.delete_pet(id)
    return redirect(url_for("get_pets"))
