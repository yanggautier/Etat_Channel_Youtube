from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
from transformers import pipeline
from pymongo import MongoClient
import pandas as pd
import random

def sentiment_analysis(comments_data, model, tokenizer):
    '''
    This function take in mongodb all comments with the video_id that we give, and use nlp to give us the sentiment
    '''
    # import weights that trained with allocine dataset by Camember tokenizer

    nlp = pipeline('sentiment-analysis', model=model, tokenizer=tokenizer)

    if comments_data.shape[0] <= 100:
        n = comments_data.shape[0]
    else:
        n = 100
    random_df = comments_data['text'].sample(n=n, random_state=1)
    sentiments = [nlp(com[:512])[0]['label'] for com in random_df]
    
    positive_nb = sentiments.count("POSITIVE")
    negative_nb = sentiments.count("NEGATIVE")

    return positive_nb, negative_nb

if __name__ == '__main__':
    comments_df = get_comments_by_video("MGg318fNSDI", limit=5000)
    positive_nb, negative_nb = sentiment_analysis(comments_df)
    print(positive_nb, negative_nb)