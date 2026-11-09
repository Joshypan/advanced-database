import os
import streamlit as st
import database

st.set_page_config(page_title='IMDb dashboard: basics', layout='wide')
st.title('IMDb dashboard: basics')
if not os.environ.get('DATABASE_URL'):
    st.error('Set DATABASE_URL before starting the app.')
    st.stop()
votes = st.slider('Minimum votes', min_value=0, value=3500000, step=100)
minimum_movie_length = st.sidebar.number_input(
'Minimum movie length (minutes)',
min_value=0, value=0, step=10,
)
maximum_movie_length = st.sidebar.number_input(
'Maximum movie length (minutes)',
min_value=0, value=300, step=10,
)

if maximum_movie_length < minimum_movie_length:
    st.error('Maximum movie length must be at least the minimum.')
    st.stop()
if st.sidebar.button('Refresh query results'):
    st.cache_data.clear()
@st.cache_data(ttl=60)
def search(text, votes):
    return database.search_titles(text, votes)
@st.cache_data(ttl=60)
def summary(votes, minimum_movie_length, maximum_movie_length):
    return database.yearly_summary(votes, minimum_movie_length,maximum_movie_length)
try:
    first, second = st.tabs(['Search', 'By year'])
    with first:
        text = st.text_input('Title contains', '')
        st.dataframe(search(text, votes), hide_index=True)
    with second:
        rows = summary(votes, minimum_movie_length, maximum_movie_length)
        #rows = summary(votes)
        st.dataframe(rows, hide_index=True)
        if rows:
            st.line_chart(rows, x='start_year', y='movies')
        st.caption('Counts reflect this sample and vote threshold; ratings give each title equal weight.')
except Exception:
    st.error('Query failed. Verify the server, connection and imported tables.')
