from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
from poe_api_wrapper import AsyncPoeApi
import asyncio
import requests
app = Flask(__name__)
CORS(app)

client = MongoClient('mongodb://localhost:27017/')
db = client['UniVisionBot']
pending_conversations = db['PendingConversation']
conversations = db['Conversation']
messages = db['Message']
visitor_collection = db['Visitor']
app_users = db['appUsers']

tokens = {
    'p-b': 'ToDAkUbHxfsHWu1fGpz_cA%3D%3D',
    'p-lat': 'afGkUC17qGhaRPWctFWPOT7Ryg7nPvCemYA8iICo7g%3D%3D',
}

# tokens = {
#     'p-b': 'iOVFeQwIx-o_FJ81yRbYGw%3D%3D',
#     'p-lat': 'xJgVOZVXrN4b0HCALLUzvi22WVBQovclTR0SuhqnXw%3D%3D',
# }
# tokens = {
#     'p-b': 'ToDAkUbHxfsHWu1fGpz_cA%3D%3D',
#     'p-lat': 'UknZG4i92rDKkkVbSSwnQSUReu2yW%2FoRlee73XKn8g%3D%3D',
# }



async def send_message_to_bot(message, chatId=None, chatCode=None):
    client = await AsyncPoeApi(tokens=tokens).create()
    response = ""
    async for chunk in client.send_message(bot="univisionbot", message=message, chatId=chatId, chatCode=chatCode):
        response += chunk["response"]
        chatId = chunk.get("chatId", chatId)
        chatCode = chunk.get("chatCode", chatCode)
    return response, chatId, chatCode

def add_conversation(user_Id):
    now = datetime.utcnow()
    microseconds = now.microsecond
    microseconds = f"{microseconds:06d}"  
    microseconds = microseconds + '7'
    conversation = {
        "consultant_Id": '672214299c167656b2dc0d5b',
        "user_Id": user_Id,
        "created_at": now.strftime(f"%Y-%m-%dT%H:%M:%S.{microseconds}Z")
    }
    result = conversations.insert_one(conversation)
    return result.inserted_id

def add_pending_conversation(status, user_Id, fullName):
    now = datetime.utcnow()
    microseconds = now.microsecond
    microseconds = f"{microseconds:06d}"  
    microseconds = microseconds + '7'
    pending_conversation = {
        "conversationId": add_conversation(user_Id),
        "status": "Pending",
        "fullName": fullName,
        "created_at": now.strftime(f"%Y-%m-%dT%H:%M:%S.{microseconds}Z")
    }
    pending_conversations.insert_one(pending_conversation)
    return pending_conversation["conversationId"]

def add_message(conversation_Id, message, sender ,receiver):
    now = datetime.utcnow()
    microseconds = now.microsecond
    microseconds = f"{microseconds:06d}"  
    microseconds = microseconds + '7'
    message_doc = {
        "status": 0,
        "message": message,
        "conversation_id": conversation_Id,
        "sender": sender,
        "receiver": receiver,
        "create_at": now.strftime(f"%Y-%m-%dT%H:%M:%S.{microseconds}Z")
    }
    messages.insert_one(message_doc)

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

@app.route('/add_pending_conversation', methods=['POST'])
def api_add_pending_conversation():
    data = request.json
    conversation_id = add_pending_conversation(data['status'], data['user_Id'], data['fullName'])
    consultant_id = '675461fbf87f485f45b118a6'  
    external_api_url = f'https://localhost:7230/api/conversations/notify'
    payload = {
        'conversationId': str(conversation_id), 
        'consultantId': consultant_id
    }
    try:
        response = requests.post(external_api_url, json=payload, verify=False)  # Disable SSL verification
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        external_api_response = response.json()
    except requests.exceptions.HTTPError as http_err:
        external_api_response = {'error': f'HTTP error occurred: {http_err}', 'status_code': response.status_code, 'response_text': response.text}
    except Exception as err:
        external_api_response = {'error': f'Other error occurred: {err}'}

    return jsonify({
        "conversation_Id": str(conversation_id),
        "external_api_response": external_api_response
    })

@app.route('/add_message', methods=['POST'])
def api_add_message():
    data = request.json
    print("data:", data)
    add_message(data['conversationId'], data['message'], data['sender'], data['receiverId'])
    return jsonify({"status": "success"})

@app.route('/visitor-count', methods=['GET'])
def get_visitor_count():
    visitor = visitor_collection.find_one()
    if visitor:
        return jsonify({'Count_Visitor': visitor['Count_Visitor']})
    else:
        return jsonify({'Count_Visitor': 0})

@app.route('/update-visitor-count', methods=['POST'])
def update_visitor_count():
    visitor = visitor_collection.find_one()
    if visitor:
        new_count = visitor['Count_Visitor'] + 1
        visitor_collection.update_one({}, {'$set': {'Count_Visitor': new_count}})
    else:
        new_count = 1
        visitor_collection.insert_one({'Count_Visitor': new_count})
    return jsonify({'Count_Visitor': new_count})

@app.route('/user-count', methods=['GET'])
def get_user_count():
    user_count = app_users.count_documents({})
    return jsonify({'total_user' : user_count, 'total_users_last_30_days': user_count})

@app.route('/new-user-count', methods=['GET'])
def get_new_user_count():
    days = request.args.get('days', default=30, type=int)
    n_days_ago = datetime.utcnow() - timedelta(days=days)
    new_user_count = app_users.count_documents({
        "CreatedOn": {
            "$gte": n_days_ago.isoformat() + "Z"
        }
    })
    return jsonify({'new_users_last_n_days': new_user_count})

@app.route('/get-ad-click', methods=['GET'])
def get_ad_click():
    visitor = visitor_collection.find_one()
    if visitor and 'AD_Click' in visitor:
        return jsonify({'AD_Click': visitor['AD_Click']})
    else:
        return jsonify({'AD_Click': 0})

@app.route('/set-ad-click', methods=['POST'])
def set_ad_click():
    visitor = visitor_collection.find_one()
    if visitor and 'AD_Click' in visitor:
        new_ad_click_count = visitor['AD_Click'] + 1
        visitor_collection.update_one({}, {'$set': {'AD_Click': new_ad_click_count}})
    else:
        new_ad_click_count = 1
        visitor_collection.insert_one({'AD_Click': new_ad_click_count})
    return jsonify({'AD_Click': new_ad_click_count})

if __name__ == '__main__':
    app.run(debug=True)
