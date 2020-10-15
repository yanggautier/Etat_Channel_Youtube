import os
import nltk
import sys
import unidecode
import re
import os.path
from cred import get_API_key
from scrap.channel import get_general_info
import json
import requests
import string
import pandas as pd
from apiclient.discovery import build
from pymongo import MongoClient
import datetime
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
nltk.download('punkt')

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

def get_id_by_search(channel_title, API_KEY):
    '''
    This function can get all videos in a Youtube channel with the the title of channel.
    '''

    url = 'https://www.googleapis.com/youtube/v3/search?type=channel&part=id,snippet&q={}&key={}&regionCode=FR'.format(channel_title,API_KEY)

    inp = requests.get(url)
    resp = inp.json()
    print(resp)
    channel_id = resp['items'][0]['snippet']['channelId']
    channel_title = resp['items'][0]['snippet']['title']
    return channel_id,channel_title

def get_channel_videos_ids_apiclient(channel_id, API_key):
    '''
    This function can get all videos in a Youtube channel with .
    '''
    youtube = build('youtube','v3', developerKey=API_key)
    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    playlistId=res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    videos = []
    next_page_token = None

    while 1:
        res = youtube.playlistItems().list(playlistId=playlistId,
                                    part='snippet,id',
                                    maxResults=50,
                                    pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')

        if next_page_token is None:
            break
    videos_ids = [video['snippet']['resourceId']['videoId'] for video in videos]

    return videos_ids

def get_videos_with_stastic(channelId, video_ids, videoCount, API_key): 
    '''
    This function get all statistics of channel with just channelId
    '''
    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.videos
    df_videos = collection.find({"channelId":  channelId})
    df_videos = pd.DataFrame(list(df_videos))

    difference_len = videoCount - df_videos.shape[0]

    video_ids2 = video_ids[:difference_len]

    
    if len(video_ids2) == 0:
        videos_in_db = collection.find({'channelId': channelId})
        df =  pd.DataFrame(list(videos_in_db))

        # df['corpus'] = df['channelTitle']  + " " + df['videoTitle'] + " " + df['videoTags']
        # client = MongoClient('localhost', 27017)

        # collection_channels = db.channels
        # current_channel = collection_channels.find({'channelId':channelId})
        # df_current_channel = pd.DataFrame(list(current_channel))
        
        # if df_current_channel.shape[0] > 0:
        #     pass
        # else:
        #     corpus = "".join(df['corpus'])
        #     corpusClean = nettoyage(corpus)
            
        #     if len(corpusClean) == 0:
        #         corpusClean = ""

        #     print("corpusClean: {}".format(corpusClean))
        #     dicte = {'channelId': channelId,'channelTitle':df['channelTitle'][0],'tagsToken':corpusClean}

        #     print("dicte: {}".format(dicte))
        #     collection_channels.insert_one(dicte)

        client.close()
        return df
    else:
        client.close()
        length = len(video_ids2)
        videos_with_stastic = []
        nb = length//50
        for i in range(nb):
            ids = ",".join(video_ids2[i*50:(i+1)*50])
            request = "https://www.googleapis.com/youtube/v3/videos?part=snippet,id,statistics&key={}&id={}".format(API_key,ids)
            response = requests.get(request)
            json = response.json()
            videos_with_stastic +=json['items']

        if length%50>0:
            ids = ",".join(video_ids2[-(length-nb*50):])
            request = "https://www.googleapis.com/youtube/v3/videos?part=snippet,id,statistics&key={}&id={}".format(API_key,ids)
            response = requests.get(request)
            json = response.json()
            videos_with_stastic += json['items']

        save_videos_to_mongodb(videos_with_stastic)
        client = MongoClient('localhost', 27017)
        db = client.youtube
        collection = db.videos
        videos_in_db = collection.find({"channelId": channelId})
        client.close()
        df_videos = pd.DataFrame(list(videos_in_db))
        #todo @bug à corriger,ne les tags nettoyés n'a pas de 
        
        df_videos['corpus'] = df_videos['channelTitle']  + " " + df_videos['videoTitle'] + " " + df_videos['videoTags']
        client = MongoClient('localhost', 27017)

        collection_channels = db.channels
        current_channel = collection_channels.find({'channelId':channelId})
        df_current_channel = pd.DataFrame(list(current_channel))
        
        if df_current_channel.shape[0] > 0:
            pass
        else:
            corpus = "".join(df_videos['corpus'])
            corpusClean = nettoyage(corpus)
            
            if len(corpusClean) == 0:
                corpusClean = ""

            print("corpusClean: {}".format(corpusClean))
            dicte = {'channelId': channelId,'channelTitle':channelTitle,'tagsToken':corpusClean}

            print("dicte: {}".format(dicte))
            collection_channels.insert_one(dicte)
        client.close()
        return df_videos


def save_videos_to_mongodb(list_video):
    '''
    This function can save the list of information videos with youtube api v3 to collection videos mongodb , save ID, channel, and token in to collection channels in mongodb.
    in each row we have all information about "videoId","channelId", "channelTitle","videoTitle", "videoDate", "videoDescription","categoryId","videoTags", "defaultLanguage","defaultAudioLanguage", "viewCount","dislikeCount","favoriteCount","commentCount"
    '''

    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.videos

    for video in  list_video:
        videoId = video['id']
        channelId = video['snippet']['channelId']
        channelTitle = video['snippet']['channelTitle']
        videoTitle = video['snippet']['title']
        videoDate = video['snippet']['publishedAt']
        # videoTags = video['snippet']['topLevelComment']['snippet']['textOriginal']

        videoDate = datetime.datetime.strptime(videoDate,"%Y-%m-%dT%H:%M:%SZ")
        new_format = "%Y-%m-%d"
        videoDate = videoDate.strftime(new_format)

        categoryId = video['snippet']['categoryId']
        try:
            videoDescription  = video['snippet']['description'].replace("\n","")
        except:
            videoDescription = ""

        try:
            videoTags = " ".join(video['snippet']['tags'])
        except:
            videoTags = ""
        try:   
            defaultLanguage = video['snippet']['defaultLanguage']
        except:
            defaultLanguage = ""
        try:   
            defaultAudioLanguage = video['snippet']['defaultAudioLanguage']
        except:
            defaultAudioLanguage =""
        try:  
            viewCount = video['statistics']['viewCount']
        except:
            viewCount = 0
        try:
            likeCount = video['statistics']['likeCount']
        except:
            likeCount = 0
        try:
            dislikeCount = video['statistics']['dislikeCount']
        except:
            dislikeCount = 0
        try:
            favoriteCount = video['statistics']['favoriteCount']
        except:
            favoriteCount = 0
        try:
            commentCount = video['statistics']['commentCount']
        except:
            commentCount = 0        

        video_info ={"videoId":videoId,
                    "channelId":channelId,
                    "channelTitle":channelTitle,
                    "videoTitle":videoTitle, 
                    "videoDate": videoDate,
                    "videoDescription":videoDescription,
                    "videoTags":videoTags,
                    "categoryId":categoryId,
                    "defaultLanguage":defaultLanguage,
                    "defaultAudioLanguage":defaultAudioLanguage,
                    "viewCount":viewCount,
                    "likeCount":likeCount,
                    "dislikeCount":dislikeCount,
                    "favoriteCount":favoriteCount,
                    "commentCount":commentCount
                    }

        video_in_base = collection.find({"videoId": videoId})
        video_def = pd.DataFrame(list(video_in_base))

        if video_def.shape[0] > 0:
            pass
        else:
            collection.insert_one(video_info)
            # videos_complete_data = videos_complete_data.append(video_info,ignore_index=True)
    client.close()
    print("Save to mongodb with success! ")
    
    # return videos_info

if __name__ == '__main__':
    API_key = get_API_key(1)
    # channel_id, _ = get_id_by_search("Machine Learnia", API_key)
    channel_id = "UCUe6ZpY6TJ0no8jI4l2iLxw"
    channel_info = get_general_info(channel_id, API_key)
    channel_title = channel_info['snippet']['title']
    video_ids = get_channel_videos_ids_apiclient(channel_id, API_key)
    
    # videos = get_videos_with_stastic( channel_id, channel_title, video_ids, API_key)
    # print(len(video_ids))
