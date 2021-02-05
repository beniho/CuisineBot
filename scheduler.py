from flask import Flask, request, abort
import os

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
from linebot.models import (
   CarouselColumn, CarouselTemplate, FollowEvent,
   LocationMessage, MessageEvent, TemplateSendMessage,
   TextMessage, TextSendMessage, UnfollowEvent, URITemplateAction
)
import psycopg2
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "<botのChannel access token>"
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

#接続情報取得
def get_connection():
    dsn = "host=＜Host＞ port=5432 dbname=＜Database＞ user=＜User＞ password=＜Password＞"
    return psycopg2.connect(dsn)

def main():

    #料理リスト
    list = []

    #クックパッドで検索
    url = "https://cookpad.com/search/" + "豚肉" + "?order="

    #検索結果取得
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    #レシピタイトル
    title = soup.find_all(class_="recipe-title")

    #レシピ画像
    image = soup.find_all(class_="recipe-image")

    #レシピ内容
    memo = soup.find_all(class_="recipe_description")

    #5つのレシピを料理リストに追加
    i=0
    for each in title[:5]:
        result_dict = {
                "thumbnail_image_url": image[i].find('img').get('src'),
                "title": title[i].get_text(),
                "text": memo[i].get_text().strip('\n'),
                "actions": {
                    "label": "料理を見る",
                    "uri": "https://cookpad.com" + each.get('href')
                }
        }
        list.append(result_dict)
        i+=1

    #カルーセルに渡す形に変換
    columns = [
        CarouselColumn(
            thumbnail_image_url=column["thumbnail_image_url"],
            title=column["title"],
            text=column["text"],
            actions=[
                URITemplateAction(
                    label=column["actions"]["label"],
                    uri=column["actions"]["uri"],
                )
            ]
        )
        for column in list
    ]

    #メッセージ作成
    messages = TemplateSendMessage(alt_text="料理について提案しました。",template=CarouselTemplate(columns=columns))

    #DBに登録されている友達分送信する
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM Users")
            for each in cur:
                line_bot_api.push_message(each[0], messages=messages)
    

if __name__ == "__main__":
    main()