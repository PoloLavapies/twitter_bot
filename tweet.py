# coding: utf-8

import os
import random
import tweepy

# Twitter API    
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('ACCESS_SECRET')

# ツイートを作成する
def get_tweet_random():
    file_path = "pieces.tsv"
    lines = open(file_path, encoding="utf-8").readlines()
    line = lines[random.randint(0, len(lines) - 1)]
    line = line.split("\t")

    sentence = line[3]
    if sentence[-1] == "\n":
        sentence = sentence[:-1]
    tweet = "{0} / {1}\n{2}\n{3}".format(line[0], line[1], line[2], sentence)
    if (check_over_140(tweet)):
        return get_tweet_random()

    return tweet

# 140字越えチェック
def check_over_140(tweet):
    if len(tweet) > 140:
        return True

client = tweepy.Client(
	bearer_token = BEARER_TOKEN,
	consumer_key = CONSUMER_KEY,
	consumer_secret = CONSUMER_SECRET,
	access_token = ACCESS_TOKEN,
	access_token_secret = ACCESS_SECRET
)

# ツイートを作成
tweet = get_tweet_random()
print("以下のツイートを投稿します。")
print(tweet)
client.create_tweet(text = tweet)
print("投稿しました。")