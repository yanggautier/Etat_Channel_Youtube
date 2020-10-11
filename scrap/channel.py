import requests
from cred import get_API_key
import os
import pandas as pd
import sys

root_folder = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append("/mnt/c/Users/yangg/project/cred.py")


def get_general_info(channel_id, API_key):
    '''
    This function get all general information about the channel which has the API_Key giving
    '''
    request = "https://www.googleapis.com/youtube/v3/channels?id={}&part=statistics,id,snippet&key={}".format(channel_id,API_key)
    response = requests.get(request)
    json = response.json()
    return json['items'][0]

def get_all_channels():
    df = pd.read_csv("../data/channel/youtubers.csv", index_col=0)


if __name__ == '__main__':
    API_key = get_API_key(0)
    info = get_general_info("UCH0XvUpYcxn4V0iZGnZXMnQ", API_key)
    print(info['snippet']['title'])