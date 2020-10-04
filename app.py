# %%
import streamlit as st
import pandas as pd
import numpy as np
from channels.channel import *
from channels.video import *
from comments.comments import *
from cred import get_API_key

API_KEY = get_API_key(2)

st.title("Channel analytics")

st.subheader("HELLO")

# data_load_state = st.text('Loading data...')
# training_set = load_data()
# data_load_state.text('Loading data...done!')

user_input = st.sidebar.text_input("Veuillez entrer le nom de channel que vous voulez analyser","" )

if len(user_input)> 3 :
	channel_id, channel_title = get_id_by_search(user_input, API_KEY)

	info = get_general_info(channel_id,API_KEY)
	video_ids = get_all_video_in_channel_with_id(channel_id,channel_title, API_KEY)
	data_videos = get_videos_with_stastic(channel_id, channel_title, video_ids, API_KEY)

	st.write(data_videos)

	st.image(info["snippet"]['thumbnails']['default']['url']) 

	st.write("Nom de channel: " + info["snippet"]['title'])
	# st.write(info)
	st.write("Description: " + info["snippet"]['description'])
	st.write("Crée le : " + info["snippet"]['publishedAt'])
	st.write("Pays : " + info["snippet"]['country'])
	st.warning("Statistiques")
	st.write("Nombre de vue totale: " + info['statistics']['viewCount'])
	st.write("Nombre d'abonné total: " + info['statistics']['subscriberCount'])
	st.write("Nombre de vidéo total: " + info['statistics']['videoCount'])

	comments_data = get_comments_by_video("Gx5JhyUwvWo",limit=20)
	st.write(comments_data.head())



# classe = st.sidebar.selectbox("La classe de la personne",[1,2,3])
# try channel_id:


# age = st.sidebar.slider("L'âge de la personne", 0, 100 )


# montant_nb_frere_soeur = st.sidebar.slider("Le nombre de frères et soeurs", 1, 30 )

# nb_enfant = st.sidebar.slider("Le nombre d'enfants", 1, 30 )

# porte_embarquement = st.sidebar.selectbox("La porte que la personne a embarqué ",['C','Q','S'])
