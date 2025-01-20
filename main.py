from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import token
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from html import escape
import asyncio
import logging

# Создаем объект бота и диспетчер
bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(force=True, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import csv
import pickle
import gigaHRR
import dataclasses
from datetime import datetime
import base64
import googleshet
import threading
import time
from config import token, token_giga
MESSAGECONFIG = {
    'welcome':"Привет, давай начнём процесс твоей регистрации"
}

giga_chat = None
google_id = None

@dataclasses.dataclass
class UserJoined:
    chat_id: int
    name: str
    user_name: str
    event_id_now: str

@dataclasses.dataclass
class User:
    register: bool
    chat_id: int
    name: str
    user_name: str
    depart: str
    time_tag: list[tuple]
    time_task: list[str]
    data = None

class EventTable:
    google_sheet: str = None
    users: dict[User]
    data: list[dict]
    code_start_time: str = None
    code_stop_time: str = None
    code_separator: str = None
    frame: list[str]
    frame_date: list[tuple] = []

    def __init__(self, google_sheet):
        self.google_sheet = google_sheet
    def __call__(self, lenght):
        self.data = googleshet.extract_data_from_sheet_var_2(googleshet.get_table_by_url(google_id, self.google_sheet), "НаМесте")[:lenght - 1]
        self.users = {}
        self.frame = list(self.data[0].keys())
        self.frame.remove("id")
        self.frame.remove("name")
        self.frame.remove("telegram")
        self.frame.remove("depart")
        for i in self.data:
            self.users[i['telegram'] if i['telegram'][0] == "@" else "@" + i['telegram']] = User(False if self.users.get(i['telegram'] if i['telegram'][0] == "@" else "@" + i['telegram'], None) == None else True, i['id'], i['name'], i['telegram'] if i['telegram'][0] == "@" else i['telegram'] + "@", i["depart"], [], [])
    def set_code(self, date: datetime, start = None, stop = None, separator = None):
        if(start != None):
            self.code_start_time = start
        if(stop != None):
            self.code_stop_time = stop
        if(separator != None):
            self.code_separator = separator

        for i in range(len(self.frame)):
            j = self.frame[i].split(self.code_separator)
            self.frame_date.append((datetime.strptime(j[0] + ' ' + date.strftime('%d.%m.%Y'), self.code_start_time + ' %d.%m.%Y'), datetime.strptime(j[1] + ' ' + date.strftime('%d.%m.%Y'), self.code_stop_time + ' %d.%m.%Y')))
        for i in self.users.keys():
            self.users[i].time_tag = self.frame_date.copy()
        for i in self.data:
            k = []
            for j in self.users[i['telegram'] if i['telegram'][0] == "@" else "@" + i['telegram']].time_tag:
                k.append(i[j[0].strftime(self.code_start_time) + self.code_separator + j[1].strftime(self.code_stop_time)])
            self.users[i['telegram'] if i['telegram'][0] == "@" else "@" + i['telegram']].time_task = k.copy()
            k.clear()
            


@dataclasses.dataclass
class Event:
    created: bool
    event_id: str
    name: str
    date: datetime
    manager_id: int
    google_sheet: str
    event_table: EventTable
    giga_gen: gigaHRR.GigaHR

@dataclasses.dataclass
class Manager:
    chat_id: int
    name: str
    tag: str
    events: dict[Event]
    event_count: int
    pro_event_count: int
    pro_giga_gen_count: int
    grade_gen: list[int] 


managers: dict[Manager] = dict()
users: dict[User] = dict()
feed = []

class Form(StatesGroup):
    wait = State()
    choose_role = State()
    enter_promo_code = State()
    gen_schedule_giga = State()
    my_events = State()
    save_name = State()
    feedback = State()
    enter_join_code = State()
    save_date = State()
    test_sheet = State()
    generate_event = State()
    grade_gen = State()
    continue_gen = State()
    my_events_menu = State()
    read_table = State()
    read_table_end = State()
    change_date = State()
    delete_event = State()
    check_user = State()

def save_to_pickle(name, data):
    with open("" + name, 'wb') as f:
        pickle.dump(data, f)

def load_from_pickle(name):
    with open("" + name, 'rb') as f:
        return pickle.load(f)

def encode_to_base64(name, chat_id):
    encode = base64.b64encode((name + "|" + chat_id).encode('utf-8'))
    return encode

def decode_from_base64(text):
    decode = base64.b64decode(text).decode('utf-8')
    return decode.split("|")[0], decode.split("|")[1]

def promo_code_check(promo_code):
    roww = ["null", 0, 0, "null"]
    rows = []
    with open('promo.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == promo_code:
                roww = row
            else:
                rows.append(row)
    with open('promo.csv', 'w') as file:
        writer = csv.writer(file)
        for i in rows:
            writer.writerow(i)

    return roww

@dp.message(CommandStart())
async def welcome(message: Message, state: FSMContext):
    chat_id = message.chat.id

    # Проверка роли пользователя
    if managers.get(chat_id):
        kb_list = [
        [KeyboardButton(text="Мои мероприятия"),
        KeyboardButton(text="Создать мероприятие")],
        [KeyboardButton(text="Сгенерировать расписание(beta)")],
        [KeyboardButton(text="Отзыв")]
        ]
        
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

        manager = managers[chat_id]
        await bot.send_message(
            chat_id,
            f"Добро пожаловать в меню\n"
            f"Количество ваших мероприятий: {manager.event_count}\n"
            f"Количество доступных вам мероприятий: {manager.pro_event_count}\n"
            f"Количество вам доступных запросов к ИИ для генерации мероприятий: {manager.pro_giga_gen_count}",
            reply_markup=markup
        )
        await state.set_state(Form.wait)
    elif users.get(chat_id):
        kb_list= [[
        KeyboardButton(text = "Моё расписание"),
        KeyboardButton(text = "Следующая задача")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)


        await bot.send_message(chat_id, "Добро пожаловать в меню", reply_markup=markup)
        await state.set_state(Form.wait)
    else:
        kb_list= [[
        KeyboardButton(text = "Я руководитель"),
        KeyboardButton(text = "Я сотрудник")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

        await bot.send_message(
            chat_id, 
            MESSAGECONFIG['welcome'], 
            parse_mode='HTML', 
            reply_markup=markup
        )
        # Сохранение следующего шага
        await state.set_state(Form.choose_role)

# Хендлер для выбора роли
@dp.message(Form.choose_role)
async def choose_role(message: Message, state: FSMContext):
    chat_id = message.chat.id
    if message.text == "Я руководитель":
        managers[chat_id] = Manager(
            chat_id=chat_id,
            name=message.from_user.first_name,
            tag=message.from_user.username,
            events={},
            event_count=0,
            pro_event_count=0,
            pro_giga_gen_count=0,
            grade_gen=[]
        )

        kb_list= [[
        KeyboardButton(text = "У меня нет промокода")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

        await bot.send_message(chat_id, "Введите ваш промокод для Pro функций", reply_markup=markup)
        await state.set_state(Form.enter_promo_code)
    elif message.text == "Я сотрудник":
        await bot.send_message(chat_id, "Введите код присоединения")
        await state.set_state(Form.enter_join_code)

@dp.message(Form.enter_join_code)
async def JoinCode(message: Message, state: FSMContext):
    try:
        nameEvent, chat_id = decode_from_base64(message.text)
        event = managers[int(chat_id)].events[message.text.encode("utf-8")]
        event.event_table.users["@" + message.from_user.username].register = True
        event.event_table.users["@" + message.from_user.username].chat_id = message.chat.id
        await bot.send_message(message.chat.id, f"Вы присоединились к мероприятию {nameEvent} и {event.name}")
        users[message.chat.id] = UserJoined(message.chat.id, event.event_table.users["@" + message.from_user.username].name, message.from_user.username, event.event_id)
        save_to_pickle("users.pickle", users)
        save_to_pickle("managers.pickle", managers)
        await welcome(message, state)
    except:
        await bot.send_message(message.chat.id, "Неверный код присоединения")
        await welcome(message, state)
        return 
    ##bot.register_next_step_handler(message, JoinCodeCheck)
#
@dp.message(Form.enter_promo_code)
async def PromoCode(message: Message, state: FSMContext):
    kb_list = [
    [KeyboardButton(text="Мои мероприятия"),
    KeyboardButton(text="Создать мероприятие")],
    [KeyboardButton(text="Сгенерировать расписание(beta)")],
    [KeyboardButton(text="Отзыв")]
    ]
    
    markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

    manager = managers[message.chat.id]
    if manager.chat_id == message.chat.id:
        if(message.text == "У меня нет промокода"):
            await bot.send_message(message.chat.id, "Спасибо за регистрацию", reply_markup=markup)
        else:
            promo = promo_code_check(message.text)
            if promo[0] == "null":
                await bot.send_message(message.chat.id, "Промокод не найден")
            else:
                manager.pro_event_count = int(promo[1])
                manager.pro_giga_gen_count = int(promo[2])
                await bot.send_message(message.chat.id, f"Промокод найден\n{promo[1]} - вам доступно событий\n{promo[2]} - вам доступно генераций при помощи нейросети(beta)", reply_markup=markup)
        save_to_pickle("managers.pickle", managers)
        await welcome(message, state)


@dp.message(F.text, Form.wait)
async def gen_schedule(message: Message, state: FSMContext):
    if(managers.get(message.chat.id) == None and users.get(message.chat.id) == None):
        await bot.send_message(message.chat.id, "Вы не зарегистрированы")
        await welcome(message, state)
        return
    elif(managers.get(message.chat.id) != None):
        
        if(message.text == "Сгенерировать расписание(beta)"):
            kb_list = []
            for event in managers[message.chat.id].events.keys():
                kb_list.append([KeyboardButton(text = managers[message.chat.id].events[event].name)])
            markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
            await bot.send_message(message.chat.id, "Добро Пожаловать в генератор расписаний, для начала давайте выберем мероприятие для которое будем генерировать", reply_markup=markup)
            await state.set_state(Form.gen_schedule_giga)
        elif(message.text == "Мои мероприятия"):
            kb_list = []
            for event in managers[message.chat.id].events.keys():
                kb_list.append([KeyboardButton(text = managers[message.chat.id].events[event].name)])
            markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
            await bot.send_message(message.chat.id, "Ваши мероприятия", reply_markup=markup)
            await state.set_state(Form.my_events)
        elif(message.text == "Создать мероприятие"):
            kb_list= [[
            KeyboardButton(text = "Отменить создание")
            ]]
            markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
            await bot.send_message(message.chat.id, "Создание мероприятия, для доступа к вашим таблицам добавьте id-342@onplace-441311.iam.gserviceaccount.com как редатора ваших таблиц в Google\nВведите название вашего мероприятия: ", reply_markup=markup)
            await state.set_state(Form.save_name)
        elif(message.text == "Отзыв"):
            await bot.send_message(message.chat.id, "Введите ваш отзыв")
            await state.set_state(Form.feedback)
    else:
        if(message.text == "Моё расписание"):
            name, chat_id = decode_from_base64(users[message.chat.id].event_id_now)
            time = managers[int(chat_id)].events[users[message.chat.id].event_id_now].event_table.users["@" + message.from_user.username]
            lisr = ""
            for i in range(len(time.time_tag)):
                lisr += time.time_tag[i][0].strftime("%X %x") + "-" + time.time_tag[i][1].strftime("%X %x") + ": " + time.time_task[i] + "\n"
            await bot.send_message(message.chat.id, lisr, reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text, Form.feedback)
async def feedback(message: Message, state: FSMContext):
    try:
        feed = load_from_pickle("feedback.pickle")
    except:
        pass
    feed.append(message)
    save_to_pickle("feedback.pickle", feed)
    await bot.send_message(message.chat_id, "Спасибо за ваш отзыв!!!")

@dp.message(F.text, Form.my_events)
async def my_events(message: Message, state: FSMContext):
    manager = managers.get(message.chat.id, None)
    if(manager != None):
        try:
            event: Event = manager.events[encode_to_base64(message.text, str(message.chat.id))]
            event.event_id
        except:
            await welcome(message, state)
        kb_list= [[
        KeyboardButton(text = "Считать расписание из таблицы"),
        KeyboardButton(text = "Запустить мероприятие сейчас")
        ],
        [
        KeyboardButton(text = "Изменить дату мероприятия"),
        KeyboardButton(text = "Удалить мероприятие")
        ],
        [
        KeyboardButton(text = "Проверить статус организаторов мероприятия"),
        KeyboardButton(text = "Выйти в меню")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

        await bot.send_message(message.chat.id, f"Ваше мероприятие:\nТаблица со всеми данными о мероприятии, которая сейчас сохранена: {event.google_sheet}\nДата, когда мероприятие будет запущено автоматически: {event.date.strftime('%d.%m.%Y')}", reply_markup=markup)
        await state.update_data(event = event)
        await state.set_state(Form.my_events_menu)
#!!!!!!!!!!!!!!!!!!
@dp.message(Form.my_events_menu)
async def my_events_menu(message: Message, state: FSMContext):
    event = (await state.get_data())["event"]
    manager = managers.get(message.chat.id, None)
    if(message.text == "Выйти в меню"):
        await welcome(message, state)
        return
    elif(message.text == "Считать расписание из таблицы"):
        kb_list= [[
        KeyboardButton(text = "Выйти в меню мероприятия")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
        await bot.send_message(message.chat.id, "Проверьте вашу таблицу и лист с названием \"НаМесте\", чтобы она совпадала с правилами: \n1. Столбец A - содержит номер человека(можно оставить пустым)\n2. Cтолбец B - содержит имена сотрудников\n3. Столбец C - содержит username человека в TG\n4. Столбец D - содержит отдел человека\n5. первая строка в столбцах A, B, C, D - должан иметь такие названия: id, telegram, name, depart\n6. столбцы E, F и т.д. - 2 и последующие строки содержат задачи которые должен делать человек в это время, а 1 - строка содержит временные рамки для задачи по примеру: 15:00 16:00\n \n \nА в слудующем сообщении напишиет номер строки, где сделана последняя запись об организаторе, либо нажмите кнопку выхода в меню", reply_markup=markup)
        await state.set_state(Form.read_table)
    elif(message.text == "Запустить мероприятие сейчас"):
        event.date = datetime.now()
        event.event_table.set_code(event.date)
        await bot.send_message(message.chat.id, "Мероприятие запущено")
        start_event(event)
    elif(message.text == "Изменить дату мероприятия"):
        kb_list= [[
        KeyboardButton(text = "Выйти в меню мероприятия")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
        await bot.send_message(message.chat.id, "Введите дату вашего мероприятия в формате ДД:ММ:ГГГГ: \nНапример 03:12:2005", reply_markup=markup)
        await state.set_state(Form.change_date)
        save_to_pickle("managers.pickle", managers)
    elif(message.text == "Удалить мероприятие"):
        kb_list= [[
        KeyboardButton(text = "Выйти в меню мероприятия"),
        KeyboardButton(text="Удалить мероприятие")
        ]]
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
        await bot.send_message(message.chat.id, "Вы уверены?", reply_markup=markup)
        await state.set_state(Form.delete_event)
    elif(message.text == "Проверить статус организаторов мероприятия"):
        if(event.event_table != None):
            markup = types.ReplyKeyboardMarkup()
            lisr = ""
            for i in event.event_table.users.keys():
                markup.add(types.KeyboardButton(event.event_table.users[i].name + "|" + event.event_table.users[i].user_name))
                lisr += event.event_table.users[i].name + "\nTG: " + event.event_table.users[i].user_name + "\nОтдел: " + event.event_table.users[i].depart + "\n" + ("Не в " if event.event_table.users[i].register == False else "В ") + "системе" + "\n\n"
            markup.add(types.KeyboardButton("Выйти в меню мероприятия"))
            await bot.send_message(message.chat.id, "Выберите организатора: " + lisr, reply_markup=markup)
            await state.set_state(Form.check_user)
        else:
            await welcome(message, state)
    else:
        await welcome(message, state)

async def send_mes_to_users(user: User):
    user.time_tag.sort(key=lambda x: x[0].timestamp())
    for i in range(len(user.time_tag)):
        while(user.time_tag[i][0].timestamp() > datetime.now().timestamp()):
            time.sleep(10)
        await bot.send_message(user.chat_id, f"Ваша задача {user.time_task[i]}\nДо: {user.time_tag[i][1].strftime('%X')}")

async def start_event(event: Event):
    await bot.send_message(event.manager_id, f"Ваше мероприятие {event.name} было запущено")
    event_table = event.event_table
    for i in event_table.users.keys():
        if(event_table.users[i].register):
            threading.Thread(target=lambda: send_mes_to_users(event_table.users[i])).start()

@dp.message(Form.change_date)
async def change_date(message: Message, state: FSMContext):
    event = (await state.get_data())["event"]
    if(message.text == "Выйти в меню мероприятия"):
        await welcome(message, state)
        return
    else:
        try:
            event.date = datetime.strptime(message.text, '%d:%m:%Y')
            await bot.send_message(message.chat.id, f"Ваша мероприятие пройдёт {event.date.strftime('%d.%m.%Y')}")
        except:
            await bot.send_message(message.chat.id, "Неверный формат даты, попробуйте ещё раз")
        await welcome(message, state)

@dp.message(Form.delete_event)
async def delete_event(message: Message, state: FSMContext):
    event = (await state.get_data())["event"]
    manager = managers.get(message.chat.id, None)
    if(message.text == "Выйти в меню мероприятия"):
        await welcome(message, state)
        return
    elif(message.text == "Удалить мероприятие"):
        manager.events.pop(encode_to_base64(event.name, str(message.chat.id)))
        await bot.send_message(message.chat.id, "Мероприятие удалено")
        save_to_pickle("managers.pickle", managers)
        await welcome(message, state)
        
@dp.message(Form.check_user)
async def check_user(message: Message, state: FSMContext):
    event = (await state.get_data())["event"]
    manager = managers.get(message.chat.id, None)
    if(message.text == "Выйти в меню мероприятия"):
        await welcome(message, state)
        return
    kb_list= [[
    KeyboardButton(text = "Выйти в меню мероприятия")
    ]]
    markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
    await bot.send_message(message.chat.id, "Ваш код приглашения: " + event.event_id.decode('utf-8'), reply_markup=markup)
    await welcome(message, state)

@dp.message(Form.read_table)
async def read_table(message: Message, state: FSMContext):
    event = (await state.get_data())["event"]
    manager = managers.get(message.chat.id, None)
    if(message.text == "Выйти в меню мероприятия"):
        my_events(message)
        return
    try:
        num = int(message.text)
    except:
        await bot.send_message(message.chat.id, "Введите число")
        return
    
    if(event.event_table == None):
        event.event_table = EventTable(event.google_sheet)
    event.event_table(num)
    kb_list= [[
    KeyboardButton(text = "Выйти в меню мероприятия"),
    KeyboardButton(text = "%H:%M; ;%H:%M")
    ]]
    markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
        
    await bot.send_message(message.chat.id, "Таблица успешно считана\nТеперь вам надо указать данные для считывания времени, если вы используете данные по умолчанию (Например, 15:00 16:00), то нажмите на кнопку снизу, если у вас свой макет, то введите свой принцип сепарации\n\n\n\n%d	День месяца [01,31]\n%H	Час (24-часовой формат) [00,23]\n%I	Час (12-часовой формат) [01,12]\n%j	День года [001,366]\n%m	Номер месяца [01,12]\n%M	Число минут [00,59]\n%p	До полудня или после (при 12-часовом формате)\n%S	Число секунд [00,61]\n%U	Номер недели в году (нулевая неделя начинается с воскресенья) [00,53]\n%w	Номер дня недели [0(Sunday),6]\n%W	Номер недели в году (нулевая неделя начинается с понедельника) [00,53]\n%x	Дата\n%X	Время\n%y	Год без века [00,99]\n%Y	Год с веком\n%Z	Временная зона\n%%	Знак '%'\n\nСначала введите формат для времяни начала;Потом введите что является сепаратором;Потом введите формат для времени конца задачи\n\nНапример: 15:00 16:00 - %H:%M; ;%H:%M", reply_markup=markup)
    save_to_pickle("managers.pickle", managers)
    await state.set_state(Form.read_table_end)


@dp.message(Form.read_table_end)
async def read_table_end(message: Message, state: FSMContext):
    event = (await state.get_data())["event"]
    manager = managers.get(message.chat, None)
    if(message.text == "Выйти в меню мероприятия"):
        await welcome(message, state)
        return
    j = message.text.split(";")
    if(len(j) != 3):
        await bot.send_message(message.chat.id, "Введите правильный формат")
        return
    event.event_table.set_code(event.date, j[0], j[2], j[1])
    await bot.send_message(message.chat.id, f"Таблица для мероприятия {event.name} успешно считана")
    save_to_pickle("managers.pickle", managers)
    await welcome(message, state)

@dp.message(Form.save_name)
async def save_name(message: Message, state: FSMContext):
    if(message.text == "Отменить создание"):
        await bot.send_message(message.chat.id, "Создание отменено")
        await welcome(message, state)
        return
    kb_list= [[
    KeyboardButton(text = "Отменить создание")
    ]]
    markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
        
    
    manager = managers.get(message.chat.id, None)
    if(manager != None):
        if(manager.pro_event_count <= 0):
            await bot.send_message(message.chat.id, "Вы достигли лимита мероприятий")
            await welcome(message, state)
            return
        encode = encode_to_base64(message.text, str(message.chat.id))
        if(manager.events.get(encode, None) != None or message.text.count("/") > 0):
            await bot.send_message(message.chat.id, "Мероприятие с таким именем уже существует")
            return
        manager.events[encode] = Event(False ,encode, message.text, datetime(2012,12,3,23,59,59), message.chat.id, "null", None, gigaHRR.GigaHR())
        await bot.send_message(message.chat.id, f"Мероприятие {message.text}\nВведите дату вашего мероприятия в формате ДД:ММ:ГГГГ: \nНапример 03:12:2005", reply_markup=markup)

        await state.set_state(Form.save_date)
    else:
        await bot.send_message(message.chat.id, "Создание отменено")
        await welcome(message, state)

@dp.message(Form.save_date)
async def save_date(message: Message, state: FSMContext):
    if(message.text == "Отменить создание"):
        await bot.send_message(message.chat.id, "Создание отменено")
        await welcome(message, state)
        return
    manager = managers.get(message.chat.id, None)
    encode = "--"
    if(manager != None):
        for i in manager.events.items():
            if(i[1].created == False):
                encode = i[1].event_id
                break
        if(message.text == "Отменить создание"):
            await bot.send_message(message.chat.id, "Создание отменено")
            await welcome(message, state)
            manager.events.pop(encode)
            return
        try:
            manager.events[encode].date = datetime.strptime(message.text, '%d:%m:%Y')
            await bot.send_message(message.chat.id, f"Ваша мероприятие пройдёт {manager.events[encode].date.strftime('%d.%m.%Y')}\nДалее вам надо создать таблицу в Google Sheets и добавить в качестве редактора нашего бота id-342@onplace-441311.iam.gserviceaccount.com\nОн автоматически создаст там новый лист с названием 'НаМесте' и вам надо будет заполнить данные в нём для продолжения работы в следующем формате:\n1. Cтолбец B - содержит имена сотрудников\n2. Столбец C - содержит username человека в TG\n3. Столбец D - содержит отдел человека\n4. первая строка в столбцах A, B, C, D - может иметь любые данные\n5. столбцы E, F и т.д. - 2 и последующие строки содержат задачи которые должен делать человек в это время, а 1 - строка содержит временные рамки для задачи по примеру: 15:00 16:00\nЕсли все условия выполнены, то отправляйте ссылку на таблицу")
            await state.set_state(Form.test_sheet)
        except:
            await bot.send_message(message.chat.id, "Неверный формат даты, попробуйте ещё раз")
            await state.set_state(Form.save_date)
    else:
        for i in manager.events.items():
            if(i[1].created == False):
                encode = i[1].event_id
                break
        manager.events.pop(encode)
        await bot.send_message(message.chat.id, "Создание отменено")

@dp.message(Form.test_sheet)
async def test_sheet(message: Message, state: FSMContext):
    if(googleshet.get_table_by_url(google_id, message.text) == None):
        await bot.send_message(message.chat.id, "Таблица не найдена")
    else:
        manager = managers.get(message.chat.id, None)
        encode = "--"
        if(manager != None):
            for i in manager.events.items():
                if(i[1].created == False):
                    encode = i[1].event_id
                    break
            manager.events[encode].google_sheet = message.text
            try:
                googleshet.create_worksheet(googleshet.get_table_by_url(google_id, message.text), "НаМесте", 100, 100)
                await bot.send_message(message.chat.id, "Таблица успешно сохранена")
                manager.events[encode].created = True
                manager.event_count += 1
                manager.pro_event_count -= 1
            except:
                manager.events.pop(encode)
                await bot.send_message(message.chat.id, "Не удалось создать таблицу. Возможно у вас есть ")
            save_to_pickle("managers.pickle", managers)
            await welcome(message, state)

@dp.message(Form.gen_schedule_giga)
async def gen_schedule_giga(message: Message, state: FSMContext):
    if(managers[message.chat.id].pro_giga_gen_count <= 0):
        await bot.send_message(message.chat.id, "Вы не можете генерировать при помощи нейросети")
        await welcome(message, state)
        return
    encode = encode_to_base64(message.text, str(message.chat.id))

    await bot.send_message(message.chat.id, "Теперь введите ваш запрос для ИИ, чтобы она сгенирировала вам мероприятие")
    await state.update_data(encode=encode)
    await state.set_state(Form.generate_event)

@dp.message(Form.generate_event)
async def generate_event(message: Message, state: FSMContext):
    data = await state.get_data()
    encode = data['encode']
    manager = managers.get(message.chat.id, None)
    try:
        manager.events[encode].giga_gen(message.text, giga_chat)
    except:
        await bot.send_message(message.chat.id, "Не удалось сгенерировать мероприятие")
        await welcome(message, state)
        return
    data, frame = manager.events[encode].giga_gen.get_table()
    googleshet.add_data_to_worksheet_var_1(googleshet.get_table_by_url(google_id, manager.events[encode].google_sheet), "НаМесте", data, 1)

    #Написать InLine
    builder = ReplyKeyboardBuilder()
    builder.button(text='5', callback_data='5')
    builder.button(text='4', callback_data='4')
    builder.button(text='3', callback_data='3')
    builder.button(text='2', callback_data='2')
    builder.button(text='1', callback_data='1')
    builder.adjust(5)

    manager.pro_giga_gen_count -= 1
    await bot.send_message(message.chat.id, "Ваше мероприятие сгенерировано\nВас устраивает генерация?", reply_markup=builder.as_markup())
    save_to_pickle("managers.pickle", managers)
    await state.set_state(Form.grade_gen)

@dp.message(Form.grade_gen)
async def grade_gen(message: Message, state: FSMContext):
    manager: Manager = managers.get(message.chat.id, None)
    try:
        grade = int(message.text)
        if(grade < 1 or grade > 5):
            await bot.send_message(message.chat.id, "Вы ввели неверное число")
            return
        manager.grade_gen.append(grade)
        await bot.send_message(message.chat.id, "Спасибо за оценку")
    except:
        await bot.send_message(message.chat.id, "Вы ввели неверное число")


    kb_list= [[
    KeyboardButton(text = "Продолжить генерацию"),
    KeyboardButton(text = "Выйти в меню")
    ]]
    markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
    

    await bot.send_message(message.chat.id, "Ваше мероприятие сгенерировано\nВас устраивает генерация?", reply_markup=markup)
    save_to_pickle("managers.pickle", managers)
    await state.set_state(Form.continue_gen)

@dp.message(Form.continue_gen)
async def continue_gen(message: Message, state: FSMContext):
    manager: Manager = managers.get(message.chat.id, None)
    if(message.text == "Выйти в меню"):
        await welcome(message, state)
    elif(message.text == "Продолжить генерацию"):
        kb_list= [
        ]
        for event in managers[message.chat.id].events.keys():
            kb_list.append([types.KeyboardButton(managers[message.chat.id].events[event].name)])
        markup = ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)
        await bot.send_message(message.chat.id, "Добро Пожаловать в генератор расписаний, для начала давайте выберем мероприятие для которое будем генерировать", reply_markup=markup)
        await state.set_state(Form.gen_schedule_giga)

async def start_bot():
    commands = [BotCommand(command='com1', description='Команда1'),
                BotCommand(command='com2', description='Команда2')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

async def main(): #Основная асинхронная функция, которая будет запускаться при старте бота.
    dp.startup.register(start_bot)
    try:
      print("Бот запущен...")
      await bot.delete_webhook(drop_pending_updates=True)
      await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()) #апускаем бота в режиме опроса (polling). Бот начинает непрерывно запрашивать обновления с сервера Telegram и обрабатывать их
    finally:
      await bot.session.close()
      print("Бот остановлен")

if __name__ == '__main__':
    try:
        feed = load_from_pickle("feedback.pickle")
    except:
        pass
    save_to_pickle("feedback.pickle", feed)
    try:
        managers: dict[Manager] = load_from_pickle("managers.pickle")
        users: dict[User] = load_from_pickle("users.pickle")
    except:
        save_to_pickle("managers.pickle", {})
        save_to_pickle("users.pickle", {})
    managers: dict[Manager] = load_from_pickle("managers.pickle")
    users: dict[User] = load_from_pickle("users.pickle")
    giga_chat = gigaHRR.run(token_giga)
    google_id = googleshet.client_init_json()
    asyncio.run(main())