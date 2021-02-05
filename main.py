from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, LocationMessage
)
from linebot.exceptions import LineBotApiError
from linebot.models import (
   CarouselColumn, CarouselTemplate, FollowEvent,
   LocationMessage, MessageEvent, TemplateSendMessage,
   TextMessage, TextSendMessage, UnfollowEvent, URITemplateAction
)
import os
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
DATABASE_URL = os.environ['DATABASE_URL']

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

import psycopg2

#接続情報取得
def get_connection():
    dsn = "host=＜Host＞ port=5432 dbname=＜Database＞ user=＜User＞ password=＜Password＞"
    return psycopg2.connect(dsn)

#友達追加時のイベント
@handler.add(FollowEvent)
def handle_follow(event):

    #友達追加時DBにユーザーIDを登録する
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                profile = line_bot_api.get_profile(event.source.user_id)
                s = 'INSERT INTO Users VALUES (%s)' % ("'" + str(profile.user_id) + "'")
                cur.execute(s)
                conn.commit()
            except:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text='exception')
                )

#WebhookからURLにイベントが送られるようにする
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

#テキストメッセージが送られてきた場合
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    #テキスト保持
    text = event.message.text
    
    #料理リスト
    list = []
    
    #クックパッドで検索
    url = "https://cookpad.com/search/" + text + "?order="

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

    #送信する
    try:
        line_bot_api.reply_message(event.reply_token, messages=messages)
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, messages=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)