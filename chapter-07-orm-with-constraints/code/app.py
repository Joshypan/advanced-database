from flask import Flask, redirect, render_template, request, url_for
from peewee import IntegrityError, OperationalError

import database

# remember to $ pip install flask
# remember to $ pip install peewee

database.initialize("pets.db")

app = Flask(__name__)


def error_page(message, status=400):
    return message, status, {"Content-Type": "text/plain; charset=utf-8"}


def check_pet_form(data):
    """Return a message for a bad pet form, or None when the form is usable."""
    if (data.get("name") or "").strip() == "":
        return "Error: name is required."
    if (data.get("type") or "").strip() == "":
        return "Error: type is required."
    age = (data.get("age") or "").strip()
    if age != "" and not age.isdigit():
        return "Error: age must be a whole number, zero or more."
    owner_id = (data.get("owner_id") or "").strip()
    if owner_id == "":
        return "Error: You must select an owner for the pet."
    if not owner_id.isdigit():
        return "Error: owner_id must be a number."
    return None


@app.route("/", methods=["GET"])
@app.route("/list", methods=["GET"])
def get_list():
    try:
        pets = database.get_pets()
        return render_template("list.html", pets=pets)
    except OperationalError as e:
        return error_page(f"Database error while listing pets: {e}", 500)


@app.route("/create", methods=["GET"])
def get_create():
    try:
        owners = database.get_owners()
        return render_template("create.html", owners=owners)
    except OperationalError as e:
        return error_page(f"Database error while loading owners: {e}", 500)


@app.route("/create", methods=["POST"])
def post_create():
    data = dict(request.form)

    problem = check_pet_form(data)
    if problem:
        return error_page(problem, 400)

    try:
        database.create_pet(data)
        return redirect(url_for("get_list"))
    except IntegrityError as e:
        return error_page(f"Constraint error creating pet: {e}", 400)
    except OperationalError as e:
        return error_page(f"Database operational error creating pet: {e}", 500)
    except ValueError as e:
        return error_page(f"Bad input creating pet: {e}", 400)
    except Exception as e:
        return error_page(f"Unexpected error creating pet: {e}", 500)


@app.route("/delete/<id>", methods=["GET"])
def get_delete(id):
    try:
        int(id)
    except ValueError:
        return error_page("Error: pet id must be an integer.", 400)

    try:
        database.delete_pet(id)
        return redirect(url_for("get_list"))
    except IntegrityError as e:
        return error_page(f"Constraint error deleting pet: {e}", 400)
    except OperationalError as e:
        return error_page(f"Database operational error deleting pet: {e}", 500)
    except Exception as e:
        return error_page(f"Unexpected error deleting pet: {e}", 500)


@app.route("/update/<id>", methods=["GET"])
def get_update(id):
    try:
        int(id)
    except ValueError:
        return error_page("Error: pet id must be an integer.", 400)

    try:
        data = database.get_pet(id)
        if data is None:
            return error_page("Error: pet not found.", 404)
        owners = database.get_owners()
        return render_template("update.html", data=data, owners=owners)
    except OperationalError as e:
        return error_page(f"Database error loading pet for update: {e}", 500)


@app.route("/update/<id>", methods=["POST"])
def post_update(id):
    try:
        int(id)
    except ValueError:
        return error_page("Error: pet id must be an integer.", 400)

    data = dict(request.form)

    problem = check_pet_form(data)
    if problem:
        return error_page(problem, 400)

    try:
        database.update_pet(id, data)
        return redirect(url_for("get_list"))
    except IntegrityError as e:
        return error_page(f"Constraint error updating pet: {e}", 400)
    except OperationalError as e:
        return error_page(f"Database operational error updating pet: {e}", 500)
    except ValueError as e:
        return error_page(f"Bad input updating pet: {e}", 400)
    except Exception as e:
        return error_page(f"Unexpected error updating pet: {e}", 500)


@app.route("/owners", methods=["GET"])
def get_owners_list():
    try:
        owners = database.get_owners()
        return render_template("owner_list.html", owners=owners)
    except OperationalError as e:
        return error_page(f"Database error while listing owners: {e}", 500)


@app.route("/owner/create", methods=["GET"])
def get_owner_create():
    return render_template("owner_create.html")


@app.route("/owner/create", methods=["POST"])
def post_owner_create():
    data = dict(request.form)
    name = (data.get("name") or "").strip()
    if name == "":
        return error_page("Error: owner name is required.", 400)

    try:
        database.create_owner(data)
        return redirect(url_for("get_owners_list"))
    except IntegrityError as e:
        return error_page(f"Constraint error creating owner: {e}", 400)
    except OperationalError as e:
        return error_page(f"Database operational error creating owner: {e}", 500)
    except ValueError as e:
        return error_page(f"Bad input creating owner: {e}", 400)
    except Exception as e:
        return error_page(f"Unexpected error creating owner: {e}", 500)


@app.route("/owner/delete/<id>", methods=["GET"])
def get_owner_delete(id):
    try:
        int(id)
    except ValueError:
        return error_page("Error: owner id must be an integer.", 400)

    try:
        database.delete_owner(id)
        return redirect(url_for("get_owners_list"))
    except IntegrityError as e:
        return error_page(
            "Error: Cannot delete this owner because they have pets. "
            "Please delete their pets first.\n"
            f"(details: {e})",
            400,
        )
    except OperationalError as e:
        return error_page(f"Database operational error deleting owner: {e}", 500)
    except Exception as e:
        return error_page(f"Unexpected error deleting owner: {e}", 500)


@app.route("/owner/update/<id>", methods=["GET"])
def get_owner_update(id):
    try:
        int(id)
    except ValueError:
        return error_page("Error: owner id must be an integer.", 400)

    try:
        data = database.get_owner(id)
        if data is None:
            return error_page("Error: owner not found.", 404)
        return render_template("owner_update.html", data=data)
    except OperationalError as e:
        return error_page(f"Database error loading owner for update: {e}", 500)


@app.route("/owner/update/<id>", methods=["POST"])
def post_owner_update(id):
    try:
        int(id)
    except ValueError:
        return error_page("Error: owner id must be an integer.", 400)

    data = dict(request.form)
    name = (data.get("name") or "").strip()
    if name == "":
        return error_page("Error: owner name is required.", 400)

    try:
        database.update_owner(id, data)
        return redirect(url_for("get_owners_list"))
    except IntegrityError as e:
        return error_page(f"Constraint error updating owner: {e}", 400)
    except OperationalError as e:
        return error_page(f"Database operational error updating owner: {e}", 500)
    except ValueError as e:
        return error_page(f"Bad input updating owner: {e}", 400)
    except Exception as e:
        return error_page(f"Unexpected error updating owner: {e}", 500)


@app.route("/health", methods=["GET"])
def health():
    try:
        fk = database.db.execute_sql("PRAGMA foreign_keys").fetchone()[0]
        if fk != 1:
            return error_page("Error: foreign key constraints are NOT active.", 500)
        return error_page("ok", 200)
    except Exception as e:
        return error_page(f"Error checking health: {e}", 500)
