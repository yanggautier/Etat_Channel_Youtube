import re
import string 
import numpy as np
import pandas as pd 
from wordcloud import WordCloud
from pymongo import MongoClient
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer

def get_similarity_by_theme(theme):
    tfidf2 = TfidfVec.transform([theme])
    vals = cosine_similarity(tfidf2, tfidf)
    idx=vals.argsort()[0][0]
    flat = vals.flatten()
    flat.sort()
    req_tfidf = flat[0]
    return req_tfidf

def channel_tags_to_wordcloud(df):
    # Remove punctuation
    df['paper_text_processed'] = df['videoTags'].map(lambda x: re.sub('[,\.!?]', '', x))
    # Convert the titles to lowercase
    df['paper_text_processed'] = df['paper_text_processed'].map(lambda x: x.lower())

    # Join the different processed titles together.
    long_string = ','.join(list(df['paper_text_processed'].values))
    # Create a WordCloud object
    wordcloud = WordCloud(background_color="white", max_words=50, contour_width=3, contour_color='steelblue')
    # Generate a word cloud
    wordcloud.generate(long_string)
    # Visualize the word cloud
    wordcloud.to_file('app/static/img/channel_wordcloud.png')

def most_common_8_words(df):
    stopWords = stopwords.words('french')
    count_vectorizer = CountVectorizer(stop_words=stopWords)
    count_data = count_vectorizer.fit_transform(df['videoTags'])
    words = count_vectorizer.get_feature_names()
    total_counts = np.zeros(len(words))
    for t in count_data:
        total_counts+=t.toarray()[0]
    
    count_dict = (zip(words, total_counts))
    count_dict = sorted(count_dict, key=lambda x:x[1], reverse=True)[0:8]
    words = [w[0] for w in count_dict]
    counts = [int(w[1]) for w in count_dict]
    x_pos = np.arange(len(words)) 
    
    return words,counts

if __name__ == '__main__':    
    print("hello")
    # similarities = [get_similarity_by_theme(theme) for theme in themes]
    client = MongoClient('localhost', 27017)
    db = client.youtube
    collection = db.videos
    videos_in_db = collection.find({'channelId': "UCmpptkXu8iIFe6kfDK5o7VQ"})
    df =  pd.DataFrame(list(videos_in_db))
    # channel_tags_to_wordcloud(df)
    # Fit and transform the processed titles

    # Visualise the 10 most common words
    words,counts = most_common_8_words(df)
    print(words)
    print(counts)
