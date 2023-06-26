class User:
    def __init__(self, username=None, chat_id=None, lpna=None, name=None, minutes=5):
        self.username = username
        self.chat_id = chat_id
        self.lpna = lpna
        self.name = name
        self.minutes = minutes
    def create_from_dict(self, dict):
        self.username = dict['username']
        self.chat_id = dict['chat_id']
        self.lpna = dict['lpna']
        self.name = dict['name']
        self.minutes = dict['minutes']
        