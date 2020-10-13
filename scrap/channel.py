import os
import re
# import sys
import nltk
import string
import requests
import unidecode
import numpy as np
import pandas as pd
from cred import get_API_key
from pymongo import MongoClient
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
nltk.download('punkt')

# root_folder = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append("/mnt/c/Users/yangg/project/cred.py")

def get_general_info(channel_id, API_key):
    '''
    This function get all general information about the channel which has the API_Key giving
    '''
    request = "https://www.googleapis.com/youtube/v3/channels?id={}&part=statistics,id,snippet&key={}".format(channel_id,API_key)
    response = requests.get(request)
    json = response.json()

    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.channels
    channels_in_db = collection.find({'channelId':channel_id})  
    df =  pd.DataFrame(list(channels_in_db))
    if df.shape[0] >0:
        client.close()
        return json['items'][0]
    else:
        collection.insert_one({'channelTitle':json['items'][0]['snippet']['title'], 'channelId':channel_id})
        client.close()
        return json['items'][0]

def get_all_channels():
    '''
    This function get all channels in mongodb
    '''
    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.channels
    channels = collection.find()
    array_channels =  [ele for ele in channels]
    client.close()
    return array_channels

def nettoyage(texte):

    '''
    This function remove all punctions and french stop words, replace accent letters, and replace words by stemming words
    '''
    stemmer = SnowballStemmer("french")
    tex=[]
    
    sw_nltk = stopwords.words('french')+['vais','dont','tres'+'the'+'in'+'this','they','you','if','else']
    sw_nltk=[unidecode.unidecode(elem) for elem in sw_nltk]
    
    remove_punct_dict = dict((ord(punct), None) for punct in string.punctuation)
    texte=unidecode.unidecode(texte.lower().translate(remove_punct_dict))
    
    p="([a-z]+)"
    for elem in re.findall(p,texte):
        if elem in sw_nltk or elem==' ':
            continue
        else:
            tex.append(stemmer.stem(elem))
    return ' '.join(tex)


def get_recommand_channels(current_channel_id,nb_channels):
    '''
    This function can retourn recommends channels using cosine_similarity
    '''
    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.videos

    videos_in_db = collection.find({ 'channelId':{ '$ne': current_channel_id}})
    videos_data = pd.DataFrame(list(videos_in_db))
    videos_data = videos_data[['channelId','channelTitle','videoTags']]
    videos_data['videoTags'] = videos_data.groupby(['channelId'])['videoTags'].transform(lambda x : ' '.join(x))
    videos_data = videos_data.drop_duplicates(subset=['videoTags'])

    current_video = collection.find({ 'channelId': current_channel_id})
    current_video = pd.DataFrame(list(current_video))
    current_video = current_video[['channelId','channelTitle','videoTags']]
    current_video['videoTags'] = current_video.groupby(['channelId'])['videoTags'].transform(lambda x : ' '.join(x))
    current_video = current_video.drop_duplicates()

    all_datas = videos_data.append(current_video)
    all_datas['videoTags'] = all_datas['videoTags'].apply(nettoyage)
    TfidfVec = TfidfVectorizer()
    tfidf = TfidfVec.fit_transform(all_datas['videoTags'])
    all_datas['similarity'] = cosine_similarity(tfidf[-1], tfidf)[0]

    response = all_datas[:-1].sort_values(by='similarity', ascending=False)[:nb_channels]
    client.close()

    response_dicte = response[['channelId','channelTitle']].to_dict('records') 
    return response_dicte


if __name__ == '__main__':
    # API_key = get_API_key(0)
    # info = get_general_info("UCj_iGliGCkLcHSZ8eqVNPDQ", API_key)
    # print(info['snippet'])
    # df = get_all_channels()
    # print(type(df[0]))
    response = get_recommand_channels(3)
    print(response)
    