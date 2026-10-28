import os
import streamlit as st
import database

st.set_page_config(page_title='IMDb dashboard: basics', layout='wide')
st.title('IMDb dashboard: basics')
if not os.environ.get('DATABASE_URL'):
    st.error('Set DATABASE_URL before starting the app.')
    st.stop()
votes = st.sidebar.number_input('Minimum votes', min_value=0, value=1000, step=100)
if st.sidebar.button('Refresh query results'):
    st.cache_data.clear()
@st.cache_data(ttl=60)
def search(text, votes):
    return database.search_titles(text, votes)
@st.cache_data(ttl=60)
def summary(votes):
    return database.yearly_summary(votes)
try:
    first, second = st.tabs(['Search', 'By year'])
    with first:
        text = st.text_input('Title contains', '')
        st.dataframe(search(text, votes), hide_index=True)
    with second:
        rows = summary(votes)
        st.dataframe(rows, hide_index=True)
        if rows:
            st.bar_chart(rows, x='start_year', y='movies')
        st.caption('Counts reflect this sample and vote threshold; ratings give each title equal weight.')
except Exception:
    st.error('Query failed. Verify the server, connection and imported tables.')
