import os

import dataset
from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, OperationalError

# SQLite ignores foreign keys unless each connection asks for them.
DATABASE_URL = os.environ.get("PETS_DATABASE_URL", "sqlite:///pets.db")
db = dataset.connect(DATABASE_URL, on_connect_statements=["PRAGMA foreign_keys=ON"])

app = Flask(__name__)


def error_page(message, status=400):
    return message, status, {"Content-Type": "text/plain; charset=utf-8"}


def text(data, key):
    return (data.get(key) or "").strip()


def check_pet_form(data):
    """Return a message for a bad pet form, or None when the form is usable."""
    if text(data, "name") == "":
        return "Error: name is required."
    if not text(data, "age").isdigit():
        return "Error: age must be a whole number, zero or more."
    if text(data, "owner") == "":
        return "Error: owner is required."
    if not text(data, "kind_id").isdigit():
        return "Error: choose a kind."
    return None


def check_kind_form(data):
    for key in ("kind_name", "food", "noise"):
        if text(data, key) == "":
            return f"Error: {key} is required."
    return None


def pet_values(data):
    return {
        "name": text(data, "name"),
        "age": int(text(data, "age")),
        "owner": text(data, "owner"),
        "kind_id": int(text(data, "kind_id")),
    }


@app.route("/")
@app.route("/list")
def get_list():
    # One query with a join, instead of one lookup per pet.
    pets = list(db.query(
        "select pets.id, pets.name, pets.age, pets.owner, "
        "kind.kind_name, kind.food, kind.noise "
        "from pets join kind on kind.id = pets.kind_id "
        "order by pets.id"
    ))
    return render_template("list.html", pets=pets)


@app.route("/create", methods=["GET", "POST"])
def get_post_create():
    if request.method == "GET":
        return render_template("create.html", kinds=db["kind"].all())

    problem = check_pet_form(request.form)
    if problem:
        return error_page(problem)
    try:
        db["pets"].insert(pet_values(request.form))
    except IntegrityError as error:
        return error_page(f"Constraint error creating pet: {error.orig}")
    return redirect(url_for("get_list"))


@app.route("/update/<int:id>", methods=["GET", "POST"])
def get_post_update(id):
    pet = db["pets"].find_one(id=id)
    if pet is None:
        return error_page("Error: pet not found.", 404)

    if request.method == "GET":
        return render_template("update.html", pet=pet, kinds=db["kind"].all())

    problem = check_pet_form(request.form)
    if problem:
        return error_page(problem)
    try:
        db["pets"].update({"id": id, **pet_values(request.form)}, ["id"])
    except IntegrityError as error:
        return error_page(f"Constraint error updating pet: {error.orig}")
    return redirect(url_for("get_list"))


@app.route("/delete/<int:id>")
def get_delete(id):
    db["pets"].delete(id=id)
    return redirect(url_for("get_list"))


@app.route("/kind/list")
def list_kinds():
    return render_template("kind_list.html", kinds=db["kind"].all())


@app.route("/kind/create", methods=["GET", "POST"])
def create_kind():
    if request.method == "GET":
        return render_template("kind_create.html")

    problem = check_kind_form(request.form)
    if problem:
        return error_page(problem)
    db["kind"].insert({key: text(request.form, key) for key in ("kind_name", "food", "noise")})
    return redirect(url_for("list_kinds"))


@app.route("/kind/update/<int:id>", methods=["GET", "POST"])
def update_kind(id):
    kind = db["kind"].find_one(id=id)
    if kind is None:
        return error_page("Error: kind not found.", 404)

    if request.method == "GET":
        return render_template("kind_update.html", kind=kind)

    problem = check_kind_form(request.form)
    if problem:
        return error_page(problem)
    values = {key: text(request.form, key) for key in ("kind_name", "food", "noise")}
    db["kind"].update({"id": id, **values}, ["id"])
    return redirect(url_for("list_kinds"))


@app.route("/kind/delete/<int:id>")
def delete_kind(id):
    try:
        db["kind"].delete(id=id)
    except IntegrityError:
        message = "Cannot delete this kind because pets use it. Delete or change those pets first."
        return render_template("kind_list.html", kinds=db["kind"].all(), error_message=message), 400
    return redirect(url_for("list_kinds"))


@app.route("/health")
def health():
    try:
        foreign_keys = list(db.query("pragma foreign_keys"))[0]["foreign_keys"]
    except OperationalError as error:
        return error_page(f"Error checking health: {error}", 500)
    if foreign_keys != 1:
        return error_page("Error: foreign key constraints are NOT active.", 500)
    return error_page("ok", 200)


if __name__ == "__main__":
    app.run(debug=True)
