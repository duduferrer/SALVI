import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import logging

test_mode = False
if test_mode:
    collection = "usersTESTE"
else:
    collection = 'users'

def db_conn():
    cred = credentials.Certificate('credentials_db.json')
    app = firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Connected to DB")
    return db

def db_upd_time(chat_id, minutes):
    doc = db.collection(collection).document(chat_id)
    doc.update({"minutes": minutes})
    return True

def db_search_by_chat_id(chat_id):
    doc_ref = db.collection(collection).document(chat_id)
    doc = doc_ref.get()
    return doc

def db_delete_user(chat_id):
    doc = db.collection(collection).document(chat_id)
    doc.delete()
    return True

def db_create_user(user):
    doc_ref = db.collection(collection).document(user.chat_id)
    doc_ref.set({"username": user.username, "chat_id": user.chat_id, "lpna": user.lpna, "name": user.name, "minutes":user.minutes})
    logging.info(f"{user.lpna} created on DB")

def db_time_search(name):
    doc = db.collection(collection).where("name", "==", name).get()
    if not doc:
        mins = None
        return mins
    mins = doc[0].get('minutes')
    return mins


def db_chat_id_search(name):
    doc = db.collection(collection).where("name", "==", name).get()
    chat_id = doc[0].get('chat_id')
    return chat_id

db = db_conn()
    
