import os
import re
# import sys
import string
import requests
import numpy as np
import pandas as pd
from cred import get_API_key
from pymongo import MongoClient
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

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
    # if df.shape[0] >0:
    client.close()
    return json['items'][0]
    # else:
    #     collection.insert_one({'channelTitle':json['items'][0]['snippet']['title'], 'channelId':channel_id})
    #     client.close()
    #     return json['items'][0]

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

def get_recommand_channels(current_channel_id,nb_channels):
    '''
    This function can retourn recommends channels using cosine_similarity
    '''
    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.channels
    channels_in_db = collection.find({ 'channelId':{ '$ne': current_channel_id}})
    channels_data = pd.DataFrame(list(channels_in_db))
    channels_data = channels_data[['channelId','channelTitle','tagsToken']]
    current_channel = collection.find({ 'channelId': current_channel_id})
    current_channel = pd.DataFrame(list(current_channel))
    current_channel = current_channel[['channelId','channelTitle','tagsToken']]
    client.close()
    all_datas = channels_data.append(current_channel)
    TfidfVec = TfidfVectorizer()
    tfidf = TfidfVec.fit_transform(all_datas['tagsToken'])
    all_datas['similarity'] = cosine_similarity(tfidf[-1], tfidf)[0]
    response = all_datas[:-1].sort_values(by='similarity', ascending=False)[:3]
    response_dicte = response[['channelId','channelTitle']].to_dict('records') 
    return response_dicte

if __name__ == '__main__':
    API_key = get_API_key(0)
    info = get_general_info("UCj_iGliGCkLcHSZ8eqVNPDQ", API_key)
    print(info)
    # df = get_all_channels()
    # print(type(df[0]))
    # response = get_recommand_channels(3)
    # print(response)
    