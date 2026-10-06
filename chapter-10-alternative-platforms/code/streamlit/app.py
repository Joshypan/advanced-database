"""Run with: streamlit run app.py"""
import streamlit as st
import database

st.set_page_config(page_title="Pets", layout="wide")
database.initialize()
st.title("Pets and Owners")

# Carry a success message across the rerun that refreshes the tables.
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

#saving operating
def save(operation, message):
    """Report a data error, or refresh the page after a successful write."""
    try:
        operation()
    except ValueError as error:
        st.error(str(error))
    except database.ConstraintError:
        st.error("The change conflicts with a database rule. "
                 "An owner with pets cannot be deleted; a pet needs an existing owner.")
    else:
        st.session_state["notice"] = message
        st.rerun()


def pet_form(pet=None):
    owners = database.get_owners()
    if not owners:
        st.info("Add an owner before adding a pet.")
        return
    pet = pet or {"name": "", "age": 0, "type": "", "food": "",
                  "owner_id": owners[0]["id"]}
    owner_names = {owner["id"]: owner["name"] for owner in owners}
    owner_ids = list(owner_names)
    current = pet["owner_id"]
    if current not in owner_ids:
        st.warning("The owner list changed. Refresh the page.")
        return
    # Including the record id keeps one pet's widget state separate from another's.
    prefix = "pet_" + str(pet.get("id", "new"))
    with st.form(prefix):
        name = st.text_input("Pet name", value=pet["name"], key=prefix + "_name")
        age = st.number_input("Age", min_value=0, value=pet["age"], step=1,
                              key=prefix + "_age")
        kind = st.text_input("Type", value=pet["type"], key=prefix + "_type")
        food = st.text_input("Food", value=pet["food"] or "", key=prefix + "_food")
        owner_id = st.selectbox("Owner", owner_ids, index=owner_ids.index(current),
                               format_func=lambda id: owner_names[id] + " (#" + str(id) + ")",
                               key=prefix + "_owner")
        submitted = st.form_submit_button("Save pet")
    if submitted:
        data = {"name": name, "age": age, "type": kind, "food": food, "owner_id": owner_id}
        if "id" in pet:
            save(lambda: database.update_pet(pet["id"], data), "Pet updated.")
        else:
            save(lambda: database.create_pet(data), "Pet added.")


def owner_form(owner=None):
    owner = owner or {"name": "", "city": "", "type_of_home": ""}
    prefix = "owner_" + str(owner.get("id", "new"))
    with st.form(prefix):
        name = st.text_input("Owner name", value=owner["name"], key=prefix + "_name")
        city = st.text_input("City", value=owner["city"] or "", key=prefix + "_city")
        home = st.text_input("Type of home", value=owner["type_of_home"] or "",
                             key=prefix + "_home")
        submitted = st.form_submit_button("Save owner")
    if submitted:
        data = {"name": name, "city": city, "type_of_home": home}
        if "id" in owner:
            save(lambda: database.update_owner(owner["id"], data), "Owner updated.")
        else:
            save(lambda: database.create_owner(data), "Owner added.")

#sidebar options
page = st.sidebar.radio("Manage", ["Pets", "Owners", "Foods"])
#actions for forms
action = st.sidebar.radio("Action", ["List", "Add", "Edit", "Delete"])
#decides what to display
if page == "Pets": 
    records = database.get_pets() 
elif page == "Owners":
    records = database.get_owners()
else:
    records = database.get_foods()

st.header(page)
if records:
    st.dataframe(records, hide_index=True, width="stretch")
elif action == "List":
    st.info("No records yet.")

#will shos owner form for food since we have not created a food form yet
if action == "Add":
    pet_form() if page == "Pets" else owner_form()
elif action in ("Edit", "Delete"):
    if records:
        choices = {record["id"]: record for record in records}
        selected = st.selectbox("Choose a record", list(choices),
                                format_func=lambda id: choices[id]["name"] + " (#" + str(id) + ")",
                                key=page + "_selected")
        record = choices[selected]
        if action == "Edit":
            pet_form(record) if page == "Pets" else owner_form(record)
        else:
            # Confirmation belongs to the selected record, not the entire page.
            confirmed = st.checkbox("Confirm deletion of " + record["name"],
                                    key=page + "_delete_" + str(selected))
            if st.button("Delete record", disabled=not confirmed):
                operation = database.delete_pet if page == "Pets" else database.delete_owner
                save(lambda: operation(selected), "Record deleted.")
    else:
        st.info("Add a record first.")
