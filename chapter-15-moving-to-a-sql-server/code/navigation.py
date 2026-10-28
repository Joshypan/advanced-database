import streamlit as st

def choose_page():
    requested=st.query_params.get('page','Search')
    if requested=='Transactions':requested='Notes'
    if requested not in ['Search','Notes','Reports']:requested='Search'
    if st.session_state.get('_query_page')!=requested:
        st.session_state['page_navigation']=requested
        st.session_state['_query_page']=requested
    def navigate():
        chosen=st.session_state['page_navigation']
        st.query_params['page']=chosen
        st.session_state['_query_page']=chosen
    return st.sidebar.radio('Page',['Search','Notes','Reports'],key='page_navigation',on_change=navigate)

def linked_movies(rows):
    from urllib.parse import urlencode
    output=[]
    for row in rows:
        title_id=row.get('title_id',row.get('_id'))
        item=dict(row)
        item['movie_notes']='?'+urlencode({'page':'Notes','title_id':title_id,'title':row['primary_title']})
        output.append(item)
    return output

def show_movies(rows):
    if not rows:
        st.info('No matching movies with the current filters.')
        return
    columns=[c for c in ['primary_title','movie_notes','start_year','average_rating','num_votes','runtime_minutes','genres'] if c=='movie_notes' or (rows and c in rows[0])]
    st.dataframe(linked_movies(rows),hide_index=True,column_order=columns,column_config={'primary_title':st.column_config.TextColumn('Movie'),'movie_notes':st.column_config.LinkColumn('Notes',display_text=':material/note_alt:',help='Open movie notes'),'title_id':None,'_id':None,'start_year':'Year','average_rating':'Rating','num_votes':'Votes','runtime_minutes':'Runtime','genres':'Genres','year_rank':'Rank'})
