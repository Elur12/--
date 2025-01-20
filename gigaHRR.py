from langchain.schema import HumanMessage, SystemMessage
#from langchain.chat_models.gigachat import GigaChat
from langchain_gigachat import GigaChat
import csv
import json


class GigaHR():
    messages = None
    response = None
    def __init__(self):
        self.messages = [
                    SystemMessage(
                        content='Ты HR организатор мероприятия и тебе надо сделать табличку, с задачами организаторов во время мероприятия и вернуть её в формате JSON. С такими полями: "org" - массив хэш-таблиц организаторов("id" - число(начина с 0), "telegram" - профиль человека, "name", "depart" - отдел). Далее в таблице оформи время начала и конца задачи, её название и id организатора, кто это будет делать, если в задаче два человека, то создай задачу для каждого. Используй как пример:"tasks": [{"start_time": "10:00","end_time": "10:15","task_name": "<Название общего задания>","organizer_id": [0,1,2,3]},{"start_time": "10:15","end_time": "10:30","task_name": "<Название личного задания>","organizer_id": [0]},{"start_time": "11:00","end_time": "12:00","task_name": "<Название задания на какое-то количество человек>","organizer_id": [2,3]},{"start_time": "14:00","end_time": "15:00","task_name": "<Название3>","organizer_id": [1,2]},{"start_time": "15:00","end_time": "16:00","task_name": "<Название личного задания>","organizer_id": [0]}]\nВ поле date формат ты пишешь формат в котором ты записал время в json ответе для Python библиотека datetime'
                    )
                    ]
    def __call__(self, user_input, chat: GigaChat):
        self.messages.append(HumanMessage(content=user_input))
        res = chat.invoke(self.messages)
        self.messages.append(res)
        self.response = json.loads(" ".join(res.content[8:len(res.content) - 4].split('\n')))

    def save_to_csv(self, file):
        with open(file, 'w') as csvfile:
            fieldnames = ['id', 'name', 'telegram', 'depart']
            for i in self.response['tasks']:
                fieldnames.append(i['start_time'] + ' ' + i['end_time'])
            self.table = csv.DictWriter(csvfile, fieldnames=fieldnames)
            self.table.writeheader()

            for i in self.response['org']:
                for j in self.response['tasks']:
                    if(i['id'] in j['organizer_id']):
                        i[j['start_time'] + ' ' + j['end_time']] = j['task_name']
                self.table.writerow(i)
    
    def get_table(self):
        fieldnames = ['id', 'name', 'telegram', 'depart']
        data = []
        for i in self.response['tasks']:
            fieldnames.append(i['start_time'] + ' ' + i['end_time'])
        for i in self.response['org']:
                for j in fieldnames[4:len(fieldnames)]:
                     i[j] = ' '
                for j in self.response['tasks']:
                    if(i['id'] in j['organizer_id']):
                        i[j['start_time'] + ' ' + j['end_time']] = j['task_name']
                data.append(i)
        return data, fieldnames
    
def run(TOKEN):
        chat = GigaChat(credentials=TOKEN, verify_ssl_certs=False, streaming=True, model="GigaChat")
        return chat

