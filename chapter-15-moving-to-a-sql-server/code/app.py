import os
import streamlit as st
import database
from navigation import choose_page, show_movies


def yearly_chart(data, field, mark):
    # No scale-bound selection: page gestures must not pan or zoom the chart.
    st.vega_lite_chart(data, {
        'mark': mark,
        'encoding': {
            'x': {'field': 'Year', 'type': 'ordinal'},
            'y': {'field': field, 'type': 'quantitative'},
            'tooltip': [{'field': 'Year', 'type': 'ordinal'},
                        {'field': field, 'type': 'quantitative'}],
        },
    }, use_container_width=True)

st.set_page_config(page_title='IMDb on PostgreSQL', layout='wide')
st.title('IMDb on PostgreSQL')
if not os.environ.get('DATABASE_URL'):
    st.error('Set DATABASE_URL before starting the app.'); st.stop()
page=choose_page()
if page=='Notes':
    import notes_page
    notes_page.render()
else:
    votes=st.sidebar.number_input('Minimum votes',min_value=0,value=1000,step=100)
    if st.sidebar.button('Refresh results'):st.cache_data.clear()
    @st.cache_data(ttl=60)
    def read(view,*args):
        return getattr(database,view)(*args)
    try:
        if page=='Search':
            sample=read('sample_summary')
            st.caption(f"{sample['titles']:,} movies, {sample['first_year']}-{sample['last_year']}. Results respect Minimum votes; each list shows up to 100 movies.")
            name,year,rating=st.tabs(['By Name','By Year','By Rating'])
            with name:
                text=st.text_input('Movie name',placeholder='Jurassic Park or The Matrix')
                rows=read('search_titles',text,votes)
                if rows:show_movies(rows)
                else:st.info('No matching movies with the current vote filter.')
            with year:
                chosen=st.selectbox('Year',read('available_years'),index=0)
                rows=read('movies_by_year',chosen,votes)
                if rows:show_movies(rows)
                else:st.info('No matching movies with the current vote filter.')
            with rating:
                low,high=st.slider('Rating range',0.0,10.0,(7.0,9.0),0.1)
                rows=read('movies_by_rating',low,high,votes)
                if rows:show_movies(rows)
                else:st.info('No matching movies in this rating range.')
        else:
            st.header('Reports')
            summary=read('yearly_summary',votes)
            if not summary:st.info('No movies meet the current vote filter.')
            else:
                data=[{'Year':str(r['start_year']),'Movies':int(r['movies']),'Rating':float(r['mean_rating'])} for r in summary]
                st.subheader('Average rating by year')
                yearly_chart(data,'Rating','line')
                st.caption('Each movie has equal weight in the yearly average. Minimum votes determines which movies qualify.')
                st.subheader('Movies by year')
                yearly_chart(data,'Movies','bar')
                changes=read('year_changes',votes)
                totals=[{'Year':str(r['start_year']),'Movies':int(r['running_total'])} for r in changes]
                st.subheader('Cumulative movie count')
                yearly_chart(totals,'Movies','area')
                st.caption('The running total adds each year to all earlier years in the loaded selection.')
                st.subheader('Yearly change in movie count')
                differences=[{'Year':str(r['start_year']),'Difference':int(r['change']) if r['change'] is not None else None} for r in changes]
                yearly_chart(differences,'Difference','bar')
                st.caption('Each bar compares the movie count with the preceding available year. The first year has no comparison.')
    except Exception:
        st.error('Could not load this view. Check the database connection and imported data.')
