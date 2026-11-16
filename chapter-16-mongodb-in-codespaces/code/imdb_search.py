"""A small Streamlit page: search IMDb titles and show the work MongoDB did.

Run from this folder with MONGODB_URI set:
    streamlit run imdb_search.py
"""
import streamlit as st

import imdb_queries as queries

st.set_page_config(page_title="IMDb on MongoDB", layout="wide")
st.title("IMDb on MongoDB")


@st.cache_resource
def database():
    client, db = queries.connect()
    return db


try:
    db = database()
except Exception as error:
    st.error(f"Cannot reach MongoDB: {error}")
    st.stop()

with st.sidebar:
    st.header("Title index")
    if queries.has_title_index(db):
        st.write("The index on primary_title exists.")
        if st.button("Drop the index"):
            queries.drop_title_index(db)
            st.rerun()
    else:
        st.write("No index on primary_title.")
        if st.button("Create the index"):
            with st.spinner("Building the index"):
                queries.create_title_index(db)
            st.rerun()

with st.form("search"):
    left, middle, right = st.columns(3)
    title = left.text_input("Exact title", placeholder="The Godfather")
    title_type = middle.selectbox("Type", ["", "movie", "short", "tvSeries", "tvEpisode"])
    year = right.number_input("Year (0 for any)", min_value=0, max_value=2100, value=0)
    submitted = st.form_submit_button("Search")

if submitted:
    query = queries.build_filter(title, title_type, year)
    if not query:
        st.info("Enter at least one condition.")
    else:
        rows, work = queries.search(db, query)
        st.subheader("The work MongoDB did")
        a, b, c, d = st.columns(4)
        a.metric("Plan", work["plan"])
        b.metric("Documents examined", f"{work['docs_examined']:,}")
        c.metric("Returned", f"{work['returned']:,}")
        d.metric("Server time (ms)", work["millis"])
        st.subheader("Results (first 20)")
        st.dataframe(
            [
                {
                    "Title": r.get("primary_title"),
                    "Type": r.get("title_type"),
                    "Year": r.get("start_year"),
                    "Rating": r.get("average_rating"),
                    "Votes": r.get("num_votes"),
                    "ID": r["_id"],
                }
                for r in rows
            ],
            hide_index=True,
        )
