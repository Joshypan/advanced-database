"""Small notes page shared by the two classroom applications."""
import streamlit as st
import notes_store

def render():
    st.subheader('Movie notes')
    st.caption('Create, read, update and delete course notes. Imported IMDb records remain read-only.')
    try:
        rows=notes_store.list_notes()
    except Exception:
        st.info('Run the account setup and configure the notes connection. Search can still run without write access.')
        return
    selected_id=st.query_params.get('title_id','')
    selected_title=st.query_params.get('title','')
    if selected_id:
        movie=notes_store.get_movie(selected_id)
        if movie:
            selected_title=movie['primary_title']
            st.markdown('### '+selected_title)
            st.caption(selected_id)
        else:
            st.error('This movie is not in the loaded selection.')
            return
    else:
        st.markdown('[Find a movie](?page=Search)')
    with st.form('create_note',clear_on_submit=True):
        title_id=st.text_input('IMDb title identifier',value=selected_id,disabled=bool(selected_id))
        note=st.text_area('New note',max_chars=2000)
        create=st.form_submit_button('Create note')
    if create:
        try:
            notes_store.create_note(title_id,note)
            st.rerun()
        except Exception as error:
            st.error(str(error))
    if not rows:
        if not selected_id:
            st.info('Open a movie from Search to add a note.')
        return
    ids=[row['title_id'] for row in rows]
    names={row['title_id']:row['primary_title'] for row in rows}
    selected=st.selectbox('Note to edit',ids,index=ids.index(selected_id) if selected_id in ids else 0,format_func=lambda value:names[value])
    current=next(row for row in rows if row['title_id']==selected)
    with st.form('edit_note'):
        changed=st.text_area('Edited note',value=current['note'],max_chars=2000,key='edit_'+selected)
        update=st.form_submit_button('Update note')
    if update:
        try:
            notes_store.update_note(selected,changed);st.rerun()
        except Exception as error:st.error(str(error))
    confirmed=st.checkbox('Confirm deletion of this note')
    if st.button('Delete note',disabled=not confirmed):
        try:
            notes_store.delete_note(selected);st.rerun()
        except Exception as error:st.error(str(error))

    st.subheader('Existing notes')
    st.dataframe(rows,hide_index=True,column_order=['primary_title','note'],column_config={'primary_title':'Movie','note':'Note','title_id':None})
