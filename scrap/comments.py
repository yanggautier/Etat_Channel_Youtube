import io
import json
import os
import sys
import time
import pandas as pd
import argparse
import lxml.html
import requests
from cred import get_API_key
from lxml.cssselect import CSSSelector
from pymongo import MongoClient

YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v={youtube_id}'
YOUTUBE_COMMENTS_AJAX_URL_OLD = 'https://www.youtube.com/comment_ajax'
YOUTUBE_COMMENTS_AJAX_URL_NEW = 'https://www.youtube.com/comment_service_ajax'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'


def find_value(html, key, num_chars=2, separator='"'):
    pos_begin = html.find(key) + len(key) + num_chars
    pos_end = html.find(separator, pos_begin)
    return html[pos_begin: pos_end]


def ajax_request(session, url, params=None, data=None, headers=None, retries=5, sleep=20):
    for _ in range(retries):
        response = session.post(url, params=params, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        if response.status_code in [403, 413]:
            return {}
        else:
            time.sleep(sleep)


def download_comments(youtube_id, sleep=.1):
    if r'\"isLiveContent\":true' in requests.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)).text:
        print('Live stream detected! Not all comments may be downloaded.')
        return download_comments_new_api(youtube_id, sleep)
    return download_comments_old_api(youtube_id, sleep)


def download_comments_new_api(youtube_id, sleep=1):
    # Use the new youtube API to download some comments
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))
    html = response.text
    session_token = find_value(html, 'XSRF_TOKEN', 3)

    data = json.loads(find_value(html, 'window["ytInitialData"] = ', 0, '\n').rstrip(';'))
    for renderer in search_dict(data, 'itemSectionRenderer'):
        ncd = next(search_dict(renderer, 'nextContinuationData'), None)
        if ncd:
            break
    continuations = [(ncd['continuation'], ncd['clickTrackingParams'])]

    while continuations:
        continuation, itct = continuations.pop()
        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_NEW,
                                params={'action_get_comments': 1,
                                        'pbj': 1,
                                        'ctoken': continuation,
                                        'continuation': continuation,
                                        'itct': itct},
                                data={'session_token': session_token},
                                headers={'X-YouTube-Client-Name': '1',
                                         'X-YouTube-Client-Version': '2.20200207.03.01'})

        if not response:
            break
        if list(search_dict(response, 'externalErrorMessage')):
            raise RuntimeError('Error returned from server: ' + next(search_dict(response, 'externalErrorMessage')))

        # Ordering matters. The newest continuations should go first.
        continuations = [(ncd['continuation'], ncd['clickTrackingParams'])
                         for ncd in search_dict(response, 'nextContinuationData')] + continuations

        for comment in search_dict(response, 'commentRenderer'):
            yield {'cid': comment['commentId'],
                   'text': ''.join([c['text'] for c in comment['contentText']['runs']]),
                   'votes': comment.get('voteCount', {}).get('simpleText', '0')
                   }

        time.sleep(sleep)


def search_dict(partial, key):
    if isinstance(partial, dict):
        for k, v in partial.items():
            if k == key:
                yield v
            else:
                for o in search_dict(v, key):
                    yield o
    elif isinstance(partial, list):
        for i in partial:
            for o in search_dict(i, key):
                yield o


def download_comments_old_api(youtube_id, sleep=1):
    # Use the old youtube API to download all comments (does not work for live streams)
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    # Get Youtube page with initial comments
    response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))
    html = response.text

    reply_cids = extract_reply_cids(html)

    ret_cids = []
    for comment in extract_comments(html):
        ret_cids.append(comment['cid'])
        yield comment

    page_token = find_value(html, 'data-token')
    session_token = find_value(html, 'XSRF_TOKEN', 3)

    first_iteration = True

    # Get remaining comments (the same as pressing the 'Show more' button)
    while page_token:
        data = {'video_id': youtube_id,
                'session_token': session_token}

        params = {'action_load_comments': 1,
                  'order_by_time': True,
                  'filter': youtube_id}

        if first_iteration:
            params['order_menu'] = True
        else:
            data['page_token'] = page_token

        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_OLD, params, data)
        if not response:
            break

        page_token, html = response.get('page_token', None), response['html_content']

        reply_cids += extract_reply_cids(html)
        for comment in extract_comments(html):
            if comment['cid'] not in ret_cids:
                ret_cids.append(comment['cid'])
                yield comment

        first_iteration = False
        time.sleep(sleep)

    # Get replies (the same as pressing the 'View all X replies' link)
    for cid in reply_cids:
        data = {'comment_id': cid,
                'video_id': youtube_id,
                'can_reply': 1,
                'session_token': session_token}

        params = {'action_load_replies': 1,
                  'order_by_time': True,
                  'filter': youtube_id,
                  'tab': 'inbox'}

        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_OLD, params, data)
        if not response:
            break

        html = response['html_content']

        for comment in extract_comments(html):
            if comment['cid'] not in ret_cids:
                ret_cids.append(comment['cid'])
                yield comment
        time.sleep(sleep)


def extract_comments(html):

    tree = lxml.html.fromstring(html)
    item_sel = CSSSelector('.comment-item')
    text_sel = CSSSelector('.comment-text-content')
    vote_sel = CSSSelector('.like-count.off')

    for item in item_sel(tree):
        yield {'cid': item.get('data-cid'),
               'text': text_sel(item)[0].text_content(),
               'votes': vote_sel(item)[0].text_content() if len(vote_sel(item)) > 0 else 0,
               }

def extract_reply_cids(html):
    tree = lxml.html.fromstring(html)
    sel = CSSSelector('.comment-replies-header > .load-comments')
    return [i.get('data-cid') for i in sel(tree)]

# def get_comments_by_video(video_id, limit=500):

#     try:
#         if not video_id:
#             raise ValueError('L\'id de channel n\'est pas valide. ')

#         client = MongoClient('localhost', 27017)
#         db = client.youtube
#         collection = db.comments

#         comments_in_db = collection.find({"video_id": video_id})
#         df =  pd.DataFrame(list(comments_in_db))
        
#         if df.shape[0] >0:
#             return df
#             client.close()
#         else:
#             print('Téléchargement de commentaire de vidéo: ', video_id)
            
#             client = MongoClient('localhost', 27017)
#             db = client.youtube
#             collection = db.comments

#             count = 0

#             start_time = time.time()
#             for comment in download_comments(video_id):
                
#                 comment_df = {'video_id':video_id,'comment_id':comment['cid'], 'text':comment['text'],'votes':comment['votes']}

#                 if collection.count_documents({'comment_id': comment['cid']}) > 0:
#                     pass
#                 else:
#                     collection.insert_one(comment_df)

#                 count += 1

#                 print('Downloaded %d comment(s)\r' % count)
#                 if limit and count >= limit:
#                     break
            
#             print('\n[{:.2f} seconds] Done!'.format(time.time() - start_time))

#             comments_in_db = collection.find({"video_id": video_id})
#             comments_data = pd.DataFrame(list(comments_in_db)) 
#             client.close()
#             return comments_data

#     except Exception as e:
#         print('Error:', str(e))
#         sys.exit(1)

def get_comments_by_video(video_id, limit, API_Key):
    '''
    This function can get comments by videos, if limit is smaller ou equal to 500 it use Youtu APi to get comments, else we use ajax to scrap comments
    '''
    try:
        if not video_id:
            raise ValueError('L\'id de channel n\'est pas valide. ')

        client = MongoClient('localhost', 27017)
        db = client.youtube
        collection = db.comments

        comments_in_db = collection.find({"video_id": video_id})
        df =  pd.DataFrame(list(comments_in_db))
        
        if df.shape[0] >0:
            return df
            client.close()
        else:
            client = MongoClient('localhost', 27017)
            db = client.youtube
            collection = db.comments

            if limit <= 500:
                # request = "https://www.googleapis.com/youtube/v3/commentThreads?key={}&textFormat=plainText&part=id,snippet&videoId={}&maxResults=50".format(API_Key, video_id)
                # response = requests.get(request)
                # json = response.json()
                # comments = json['items']

                # try:
                #     nextPageToken = json['nextPageToken']
                # except:
                #     nexPageToken = None

                # while nextPageToken is not None and len(comments)< limit:
                #     request = "https://www.googleapis.com/youtube/v3/commentThreads?key={}&textFormat=plainText&part=id,snippet&videoId={}&maxResults=50&nextPageToken={}".format(API_Key,video_id, nextPageToken)
                #     response = requests.get(request)
                #     json = response.json()
                #     comments += json['items']
                #     try:
                #         nextPageToken = json['nextPageToken']
                #     except:
                #         nexPageToken = None
                comments = []
                next_page_token = None

                while 1:
                    res = "https://www.googleapis.com/youtube/v3/commentThreads?key={}&textFormat=plainText&part=id,snippet&videoId={}&maxResults=50&nextPageToken={}".format(API_Key,video_id, next_page_token)

                    comments += res['items']
                    next_page_token = res.get('nextPageToken')

                    if next_page_token is None:
                        break   
                
                for comment in comments:
                    comment_id = comment['id']
                    comment_vote = comment['snippet']['topLevelComment']['snippet']['textOriginal']
                    comment_text = comment['snippet']['topLevelComment']['snippet'][ 'likeCount']
                    comment_df = {'video_id':video_id,'comment_id':comment_id, 'text':comment_vote,'votes':comment_text}
                    collection.insert_one(comment_df)
                
            else:    
                print('Téléchargement de commentaire de vidéo: ', video_id)
                
                client = MongoClient('localhost', 27017)
                db = client.youtube
                collection = db.comments

                count = 0

                start_time = time.time()
                for comment in download_comments(video_id):
                    
                    comment_df = {'video_id':video_id,'comment_id':comment['cid'], 'text':comment['text'],'votes':comment['votes']}

                    if collection.count_documents({'comment_id': comment['cid']}) > 0:
                        pass
                    else:
                        collection.insert_one(comment_df)

                    count += 1

                    print('Downloaded %d comment(s)\r' % count)
                    if limit and count >= limit:
                        break
                
                print('\n[{:.2f} seconds] Done!'.format(time.time() - start_time))

            comments_in_db = collection.find({"video_id": video_id})
            comments_data = pd.DataFrame(list(comments_in_db)) 
            client.close()
            return comments_data

    except Exception as e:
        print('Error:', str(e))
        sys.exit(1)

if __name__ == '__main__':
    API_key = get_API_key(1)
    comments_df = get_comments_by_video("MGg318fNSDI", 500, API_key)
    positive_nb, negative_nb = sentiment_analysis(comments_df)
    print(positive_nb, negative_nb)
