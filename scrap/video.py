
# from selenium import webdriver
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.options import Options
import os
import os.path
import sys
from cred import get_API_key
from scrap.channel import get_general_info
import json
import requests
import pandas as pd
from apiclient.discovery import build
from pymongo import MongoClient
import datetime

# def get_channel_ID(youtube_channel_url):
#     '''
#     This function can get return the ID of the channel by that URL that we giving,
#     It was passed at the website 'https://commentpicker.com/youtube-channel-id.php'
#     And we get the ID of the channel at return from the website
#     '''
#     chrome_options=Options()
#     chrome_options.add_argument('--headless')
#     driver = webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options)

#     driver.get('https://commentpicker.com/youtube-channel-id.php')
#     try:
#         accept_cookie_button = driver.find_element_by_id('ez-accept-all')
#         accept_cookie_button.click()
#     except:
#         pass

#     input_url_youtube = driver.find_element_by_id("js-youtube-url")
#     input_url_youtube.send_keys(youtube_channel_url)
#     button_valid_url = driver.find_element_by_id("get-channel-id")
#     button_valid_url.click()
#     driver.implicitly_wait(3)
#     channel_result = driver.find_element_by_class_name("channel-result")
#     channelId = (channel_result.find_element_by_tag_name("p").text.split())[-1]
#     driver.close()
#     return channelId

def scrap_youtubers_list():
    '''
    With this function, we can get a list of youtubers in France et the category of their channel, and save all this in a csv file.
    '''
    response = requests.get("https://us.youtubers.me/france/all/top-1000-youtube-channels-in-france")
    content = response.content
    parser = BeautifulSoup(content,'html.parser')
    table = parser.find('div',{"class":"top-charts-box"})
    data_channels = pd.DataFrame(columns=['youtuber','category'])
    trs = table.find_all('tr')
    for i in range(1, len(trs)):
        tds = trs[i].find_all('td')
        youtuber = tds[1].text.strip()
        category = tds[5].text.strip()
        data_channels = data_channels.append({"youtuber": youtuber, "category":category}, ignore_index=True)
    return data_channels

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


def get_channel_videos_ids(channel_id,channel_title, API_KEY):
    '''
    This function can get all videos in a Youtube channel with the the id of channel.
    '''

    PATH="data/video/"+ channel_title +"/VideoIds.csv"

    if os.path.isfile(PATH) :
        df = pd.read_csv(PATH, index_col=0)
        return df['videoId']
        
    else:
        api_key = API_KEY

        base_search_url = 'https://www.googleapis.com/youtube/v3/search?'

        first_url = base_search_url +'key={}&channelId={}&part=snippet,id&order=date&maxResults=50'.format(api_key, channel_id)

        videos = []
        url = first_url
        while True:
            inp = requests.get(url)
            resp = inp.json()

            videos += resp['items']

            try:
                next_page_token = resp['nextPageToken']
                url = first_url + '&pageToken={}'.format(next_page_token)
            except:
                break

        videos_ids = pd.DataFrame(columns=['videoId'])
        for video in videos:
            if "videoId" in video['id']:
                videoId = video['id']['videoId']
                videos_ids = videos_ids.append({'videoId':videoId}, ignore_index=True)

        outdir = "data/video/"+ channel_title
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        videos_ids.to_csv(PATH)
    return videos_ids['videoId']


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

def get_videos_with_stastic(channelId, video_ids, API_key): 

    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.videos

    # PATH='data/video/' + channelTitle + "/Statistics.csv"

    # if os.path.isfile(PATH):
    #     print("File already existed")
    videos_in_db = collection.find({'channelId': channelId})
    df =  pd.DataFrame(list(videos_in_db))  
    
    if df.shape[0] > 0:
        client.close()
        return df

    else:
        length = len(video_ids)
        videos_with_stastic = []
        nb = length//50
        for i in range(nb):
            ids = ",".join(video_ids[i*50:(i+1)*50])
            request = "https://www.googleapis.com/youtube/v3/videos?part=snippet,id,statistics&key={}&id={}".format(API_key,ids)
            response = requests.get(request)
            json = response.json()
            videos_with_stastic +=json['items']

        if length%50>0:
            ids = ",".join(video_ids[-(length-nb*50):])
            request = "https://www.googleapis.com/youtube/v3/videos?part=snippet,id,statistics&key={}&id={}".format(API_key,ids)
            response = requests.get(request)
            json = response.json()
            videos_with_stastic += json['items']
        
        # data = save_videos_to_mongodb(videos_with_stastic)
        # data.to_csv(PATH)
        df = save_videos_to_mongodb(videos_with_stastic)
        return df

    # data = pd.read_csv(PATH, index_col=0)

def save_videos_to_mongodb(list_video):
    '''
    This function can save the list of information videos with youtube api v3 to mongodb databse, 
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

        videoDate = datetime.datetime.strptime(videoDate,"%Y-%m-%dT%H:%M:%SZ")
        new_format = "%Y-%m-%d"
        videoDate = videoDate.strftime(new_format)

        videoDescription = video['snippet']['description'].replace("\n","")
        
        categoryId = video['snippet']['categoryId']
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

        collection.insert_one(video_info)
        # videos_complete_data = videos_complete_data.append(video_info,ignore_index=True)

    print("Save to mongodb with success! ")
    videos_in_db = collection.find({"channelId": channelId})
    df_videos = pd.DataFrame(list(videos_in_db))
    client.close()
    return df_videos
    # return videos_info

if __name__ == '__main__':
    API_key = get_API_key(1)
    # channel_id, _ = get_id_by_search("Machine Learnia", API_key)
    channel_id = "UCmpptkXu8iIFe6kfDK5o7VQ"
    channel_info = get_general_info(channel_id, API_key)
    channel_title = channel_info['snippet']['title']
    video_ids = get_channel_videos_ids_apiclient(channel_id, channel_title, API_key)
    videos = get_videos_with_stastic( channel_id, channel_title, video_ids, API_key)
    print(videos['commentCount'].sum())
