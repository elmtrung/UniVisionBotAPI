from flask import Flask, request, jsonify
from poe_api_wrapper import AsyncPoeApi
import asyncio

app = Flask(__name__)

tokens = {
    'p-b': 'ToDAkUbHxfsHWu1fGpz_cA%3D%3D',
    'p-lat': 'afGkUC17qGhaRPWctFWPOT7Ryg7nPvCemYA8iICo7g%3D%3D',
}

async def send_message_to_bot(message, chatId=None, chatCode=None):
    client = await AsyncPoeApi(tokens=tokens).create()
    response = ""
    async for chunk in client.send_message(bot="univisionbot", message=message, chatId=chatId, chatCode=chatCode):
        response += chunk["response"]
        chatId = chunk.get("chatId", chatId)
        chatCode = chunk.get("chatCode", chatCode)
    return response, chatId, chatCode

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message')
    chatId = data.get('chatId')
    chatCode = data.get('chatCode')
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response, chatId, chatCode = loop.run_until_complete(send_message_to_bot(message, chatId, chatCode))
    
    return jsonify({
        'response': response,
        'chatId': chatId,
        'chatCode': chatCode
    })

if __name__ == '__main__':
    app.run(debug=True)