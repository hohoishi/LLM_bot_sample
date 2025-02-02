import sys
import configparser

# Azure OpenAI
import os
from openai import AzureOpenAI

# Azure Speech
import azure.cognitiveservices.speech as speechsdk
import librosa

from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

#Config Parser
config = configparser.ConfigParser()
config.read('config.ini')


# Azure OpenAI Key
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["KEY"],
    api_version=config["AzureOpenAI"]["VERSION"],
    azure_endpoint=config["AzureOpenAI"]["BASE"],
)

# Azure OpenAI Key
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["KEY"],
    api_version=config["AzureOpenAI"]["VERSION"],
    azure_endpoint=config["AzureOpenAI"]["BASE"],
)

app = Flask(__name__)

channel_access_token = config['Line']['CHANNEL_ACCESS_TOKEN']
channel_secret = config['Line']['CHANNEL_SECRET']
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

handler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    azure_openai_result = azure_openai(event.message.text)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=azure_openai_result)]
            )
        )

def azure_openai(user_input):
    message_text = [
        {
            "role": "system",
            "content": "",
        },
        {"role": "user", "content": user_input},
    ]

    message_text[0]["content"] = """
    妳是一個很有幽默感的人，很會講笑話。
    請一律用繁體中文回答。
    """
    message_text[1]["content"] = "請用這個關鍵字「"
    message_text[1]["content"] += user_input
    message_text[1]["content"] += "」來說一個笑話。不超過300字。"

    

    completion = client.chat.completions.create(
        model=config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT35"],
        # model=config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4_32K"],
        # model=config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
        messages=message_text,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )
    print(completion)
    return completion.choices[0].message.content

if __name__ == "__main__":
    app.debug = True
    app.run()