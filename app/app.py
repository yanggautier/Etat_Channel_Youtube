from flask import Flask, url_for, redirect, render_template, request
from scrap.video import *
from scrap.comments import *
from scrap.channel import *
from cred import get_API_key
from models.channel_analyse import *
from models.video_analyse import *
# from model.predict_stock import *
import json
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from cachetools import cached, TTLCache


API_key = get_API_key(2)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
cache = TTLCache(maxsize=100, ttl=60)

@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@cached(cache)
def read_tokenize_model():
    tokenizer = AutoTokenizer.from_pretrained("tblard/tf-allocine")
    model = TFAutoModelForSequenceClassification.from_pretrained("tblard/tf-allocine")

    return tokenizer, model

@app.route('/',  methods=['GET'])
def index():
    # Load sentiment-analysis models

    channel_id = request.args.get('channel_id')
    channels = get_all_channels()

    if channel_id:
  
        df = get_general_info(channel_id, API_key)

        categories = {
            2: "Autos et véhicules",
            1: "Film et animation",
            10: "Musique",
            15: "Animal de compagnie & Animaux",
            17: "Sports",
            18: "Courts métrages",
            19: "Voyages et événements",
            20: "Jeux",
            21: "Videoblogging",
            22: "People & Blogs",
            23: "Comédie",
            24: "Divertissement",
            25: "Actualités et politique",
            26: "Mode d'emploi et style",
            27: "Éducation",
            28: "Science et technologie",
            29: "Organisations à but non lucratif et activisme",
            30: "Films",
            31: "Anime / Animation",
            32: "Action / Aventure",
            33: "Classiques",
            34: "Comédie",
            35: "Documentaire",
            36: "Drame",
            37: "Famille",
            38: "étranger",
            39: "Horreur",
            40: "Science-fiction / Fantaisie",
            41: "Thriller",
            42: "Shorts",
            43: "Spectacles",
            44: "Bande-annonces",
            }

        countries = {
            'JP': 'Japon',
            'US': 'Etats-Unis',
            'FR': 'France',
            'EN': 'Royaume-Unis',
            'SP': 'Espagnol',
            'IT': 'Italie',
            'GE': 'Germany',
            'CN': 'Chine',
            'AU': 'Australie',
            'CA': 'Canada'
        }

        channel_title = df['snippet']['title']
        # get the list of all video IDs in the channel, we use that to get below all informations about their videos
        video_ids = get_channel_videos_ids_apiclient(channel_id, API_key)
        # get the list all informations of videos
        videos = get_videos_with_stastic(channel_id, video_ids, API_key)
        # save wordcloud image to app/static/img/channel_wordcloud.png
        channel_tags_to_wordcloud(videos)

        videos['categoryId'] = videos['categoryId'].astype(int).replace(categories)
        try:
            viewCount = int(df['statistics']['viewCount'])
        except:
            viewCount = 0

        try:    
            subscriberCount = int(df['statistics']['subscriberCount'])
        except:
            subscriberCount = 0

        try:    
            videoCount = int(df['statistics']['videoCount'])
        except:
            videoCount = 0

        commentCount = videos['commentCount'].astype(int).sum()
        likeCount = videos['likeCount'].astype(int).sum()
        dislikeCount = videos['dislikeCount'].astype(int).sum()
        categories = videos['categoryId'].value_counts()
        try: 
            country = countries[df['snippet']['country']]
        except:
            country = ""
        try:
            language = df['snippet']['defaultLanguage']
        except:
            language = ""

        # get 8 must common words and frequencies , this is used to tag cards 
        channel_tag_words,channel_tag_counts = most_common_8_words(videos)

        # This is used to display videos
        videoInfo = [{'id': video_ids[i],'title':videos['videoTitle'][i]} for i in range(len(video_ids))]

        # We take their variables to display in web page
        results = { 'id': channel_id,
                    'title': channel_title,
                    'description': df['snippet']['description'],
                    'viewCount':  f'{viewCount:,}',
                    'subscriberCount': f'{subscriberCount:,}',
                    'videoCount': f'{videoCount:,}',
                    'image': df['snippet']['thumbnails']['default']['url'],
                    'country': country,
                    'language': language,
                    'commentCount': f'{commentCount:,}',
                    'likeCount': f'{likeCount:,}',
                    'dislikeCount':f'{dislikeCount:,}',
                    'dateArray': videos['videoDate'][::-1],
                    'viewCountArray': videos['viewCount'][::-1],
                    'commentCountArray': videos['commentCount'],
                    'categories':list(categories.keys()),
                    'categorieNbs':list(categories.values),
                    'channel_tag_words':channel_tag_words,
                    'channel_tag_counts':channel_tag_counts,
                    'videoInfo': videoInfo,
        }

        recommend_channels= ""
        
        # get value of request variable 'video_id'
        video_id = request.args.get('video_id')
        if video_id is None:
            return render_template("index.html", results=results, channels=channels, recommend_channels=recommend_channels)
        else:
            
            comments_df = get_comments_by_video(video_id)
            tokenizer, model = read_tokenize_model()
            positive_nb, negative_nb = sentiment_analysis(comments_df, model, tokenizer)
 
            video_results={
                'id': video_id,
                'sentiments': [positive_nb,negative_nb]
            }
            print(video_results)
            return render_template("index.html", results=results, video_results=video_results, channels=channels, recommend_channels=recommend_channels)

    return render_template("index.html", channels=channels)
if __name__ == '__main__':
    app.run(debug=True)
