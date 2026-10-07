import re

import pytest

import app as webapp
import database


@pytest.fixture
def client():
    database.setup_database("pytest_ci", client_factory=database.MongitaClientMemory)
    database.owners_collection.delete_many({})
    database.pets_collection.delete_many({})

    with webapp.app.test_client() as test_client:
        yield test_client

    database.close_connection()


def create_owner(client, name="greg", city="Portland", type_of_home="condo"):
    response = client.post(
        "/owner/create",
        data={"name": name, "city": city, "type_of_home": type_of_home},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/owners")


def get_owner_ids():
    owners = database.get_owners()
    return {owner["name"]: owner["id"] for owner in owners}


def extract_first_pet_id(body):
    match = re.search(r"/update/([0-9a-f]{24})", body)
    assert match is not None
    return match.group(1)


def test_health_route(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_owner_crud_flow(client):
    create_owner(client, name="greg", city="Portland", type_of_home="condo")

    response = client.get("/owners")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "greg" in body
    assert "Portland" in body

    owner_id = get_owner_ids()["greg"]

    response = client.get(f"/owner/update/{owner_id}")
    assert response.status_code == 200
    assert "greg" in response.get_data(as_text=True)

    response = client.post(
        f"/owner/update/{owner_id}",
        data={"name": "gregory", "city": "Salem", "type_of_home": "cabin"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/owners")

    updated_owner = database.get_owner(owner_id)
    assert updated_owner is not None
    assert updated_owner["name"] == "gregory"
    assert updated_owner["city"] == "Salem"
    assert updated_owner["type_of_home"] == "cabin"


def test_pet_crud_flow(client):
    create_owner(client, name="greg", city="Portland", type_of_home="condo")
    create_owner(client, name="david", city="Seattle", type_of_home="farm")
    owner_ids = get_owner_ids()

    response = client.post(
        "/create",
        data={
            "name": "walter",
            "age": "2",
            "type": "mouse",
            "owner_id": owner_ids["greg"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/list")

    response = client.get("/list")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "walter" in body
    assert owner_ids["greg"] in body

    pet_id = extract_first_pet_id(body)

    response = client.get(f"/update/{pet_id}")
    assert response.status_code == 200
    assert "walter" in response.get_data(as_text=True)

    response = client.post(
        f"/update/{pet_id}",
        data={
            "name": "updated",
            "age": "8",
            "type": "dog",
            "owner_id": owner_ids["david"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/list")

    updated_pet = database.get_pet(pet_id)
    assert updated_pet is not None
    assert updated_pet["name"] == "updated"
    assert updated_pet["age"] == 8
    assert updated_pet["type"] == "dog"
    assert updated_pet["owner_id"] == owner_ids["david"]

    response = client.get(f"/delete/{pet_id}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/list")
    assert database.get_pet(pet_id) is None


def test_pet_create_rejects_unknown_owner(client):
    response = client.post(
        "/create",
        data={
            "name": "ghost",
            "age": "1",
            "type": "cat",
            "owner_id": "000000000000000000000000",
        },
    )
    assert response.status_code == 400
    assert "owner_id" in response.get_data(as_text=True)


def test_owner_delete_is_restricted_by_pets(client):
    create_owner(client, name="greg", city="Portland", type_of_home="condo")
    owner_id = get_owner_ids()["greg"]

    client.post(
        "/create",
        data={
            "name": "dorothy",
            "age": "9",
            "type": "dog",
            "owner_id": owner_id,
        },
    )

    response = client.get(f"/owner/delete/{owner_id}")
    assert response.status_code == 400
    assert "have pets" in response.get_data(as_text=True)

    pet = database.get_pets()[0]
    client.get(f"/delete/{pet['id']}")

    response = client.get(f"/owner/delete/{owner_id}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/owners")
    assert database.get_owner(owner_id) is None


def test_create_and_update_owner_validation(client):
    response = client.post("/owner/create", data={"name": "", "city": "x", "type_of_home": "y"})
    assert response.status_code == 400
    assert "name is required" in response.get_data(as_text=True)

    create_owner(client, name="greg", city="Portland", type_of_home="condo")
    owner_id = get_owner_ids()["greg"]

    response = client.post(
        f"/owner/update/{owner_id}",
        data={"name": "", "city": "x", "type_of_home": "y"},
    )
    assert response.status_code == 400
    assert "name is required" in response.get_data(as_text=True)


def test_disk_identifiers_and_reopen(tmp_path):
    from bson.objectid import ObjectId

    database.setup_database("pets", data_dir=tmp_path / "mongita")
    try:
        owner_id = database.create_owner({"name": "Alex"})
        pet_id = database.create_pet({
            "name": "Casey", "type": "dog", "age": "3", "owner_id": owner_id,
        })
        assert isinstance(pet_id, str) and len(pet_id) == 24
        stored = database.pets_collection.find_one({"_id": ObjectId(pet_id)})
        assert stored["owner_id"] == ObjectId(owner_id)
        assert isinstance(stored["_id"], ObjectId)
        database.close_connection()
        database.setup_database("pets", data_dir=tmp_path / "mongita")
        assert database.get_pet(pet_id)["owner_id"] == owner_id
        database.update_pet(pet_id, {
            "name": "Casey", "type": "dog", "age": "4", "owner_id": owner_id,
        })
        assert database.get_pet(pet_id)["age"] == 4
        database.delete_pet(pet_id)
        assert database.get_pet(pet_id) is None
    finally:
        database.close_connection()


def test_id_routes_reject_bad_and_missing_ids(client):
    assert client.get("/update/not-an-id").status_code == 400
    assert client.get("/update/000000000000000000000000").status_code == 404


@pytest.mark.parametrize("age", ["-5", "abc"])
def test_invalid_pet_age_create_and_update(client, age):
    create_owner(client)
    owner_id = get_owner_ids()["greg"]
    data = {"name": "Casey", "type": "dog", "age": age, "owner_id": owner_id}
    response = client.post("/create", data=data)
    assert response.status_code == 400
    assert database.get_pets() == []
    pet_id = database.create_pet(dict(data, age="3"))
    response = client.post(f"/update/{pet_id}", data=data)
    assert response.status_code == 400
    assert database.get_pet(pet_id)["age"] == 3


@pytest.mark.parametrize("age", [None, "", "  ", "0", "3"])
def test_valid_pet_age_defaults_and_conversion(client, age):
    create_owner(client)
    owner_id = get_owner_ids()["greg"]
    pet_id = database.create_pet({"name": "Casey", "type": "dog", "age": age, "owner_id": owner_id})
    assert database.get_pet(pet_id)["age"] == (3 if age == "3" else 0)
