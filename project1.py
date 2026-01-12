import asyncio
import logging
import os
import json
import re
import io
import sys
import time
from typing import Dict, Any, List, Union, Set, Optional

import aiosqlite
import aiohttp
from openpyxl import Workbook
from dotenv import load_dotenv
from cryptography.fernet import Fernet

from aiogram import Bot, Dispatcher, Router, F, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError


load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
try:
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
except:
    ADMIN_IDS = []
    
AI_API_URL = os.getenv('AI_API_URL')
AI_API_KEY = os.getenv('AI_API_KEY')
AI_MODEL = os.getenv('AI_MODEL')
DB_PATH = "robust_results_v2.db"
CIPHER_KEY = os.getenv('CIPHER_KEY')

if not CIPHER_KEY:
    key = Fernet.generate_key()
    print(f"\n[ВАЖНО] КЛЮЧ ШИФРОВАНИЯ: {key.decode()}")
    CIPHER_KEY = key.decode()

cipher = Fernet(CIPHER_KEY.encode())
logging.basicConfig(level=logging.ERROR, stream=sys.stdout)


class Txt:
    LVS = {1: "Репродуктивный (Низкий)", 2: "Частично-поисковый (Средний)", 3: "Творчески-исследовательский (Высокий)"}
    INTRO = """Здравствуйте, коллега! 👋
Рады видеть вас в чат-боте для диагностики вашей исследовательской культуры.

Почему это важно? Современный педагог — это не только наставник, но и исследователь, способный анализировать, проектировать и постоянно развивать свою практику. Эта диагностика поможет вам оценить свою готовность к этой роли.

Что оцениваем? Всего три ключевых аспекта:
1. Ценностное отношение к новшествам и поиску.
2. Технологическая готовность — знание методологии и умение применять исследовательские приемы.
3. Творческая активность и стремление к саморазвитию.

Как это проходит? Вам предстоит ответить на серию небольших вопросов и разобрать несколько кейс-ситуаций. Отвечайте быстро, исходя из вашего опыта.
Время: около 25–40 минут.

Готовы начать и увидеть свою траекторию роста?
👉 Нажмите «Начать диагностику» или напишите «Начать»."""
    
    GR = {
        1: "<b>Уровень: РЕПРОДУКТИВНЫЙ (Начальный)</b>\nРекомендации: Начните с посещения семинаров, ведите педагогический дневник, освойте базовые методы диагностики.",
        2: "<b>Уровень: ЧАСТИЧНО-ПОИСКОВЫЙ (Средний)</b>\nРекомендации: Участвуйте в дебатах, реализуйте исследовательский проект, опубликуйте статью.",
        3: "<b>Уровень: ТВОРЧЕСКИ-ИССЛЕДОВАТЕЛЬСКИЙ (Высокий)</b>\nРекомендации: Транслируйте свою концепцию, создавайте авторские методики, выступайте на конференциях."
    }


    M1_S = {1:1, 2:1, 3:1, 4:0, 5:1, 6:1, 7:1, 8:0, 9:0, 10:0, 11:1}
    M1_T = {
        1: "Потребность в изменении пед. действительности", 2: "Совершенствование практики", 3: "Осуществление инноваций", 
        4: "Удовлетворение амбиций", 5: "Глубокое познание явлений", 6: "Потребность в самореализации", 
        7: "Проф. саморазвитие", 8: "Самоутверждение", 9: "Потребность в контактах", 
        10: "Обогащение опыта", 11: "Ценностное отношение к познанию"
    }


    M2_Q = [
        ("Какая характеристика Вам подходит?", [("Целеустремленный", 3), ("Трудолюбивый", 2), ("Дисциплинированный", 1)]), 
        ("За что вас ценят коллеги?", [("Ответственность", 2), ("Принципиальность", 1), ("Эрудиция", 3)]), 
        ("Отношение к исследованию?", [("Трата времени", 1), ("Не вникал", 2), ("Положительно", 3)]), 
        ("Что мешает самосовершенствоваться?", [("Время", 3), ("Условия", 2), ("Воля", 1)]), 
        ("Затруднения в исследовании?", [("Не анализировал", 2), ("Нет", 3), ("Не знаю", 1)]), 
        ("Характеристика (2)?", [("Требовательный", 3), ("Настойчивый", 2), ("Снисходительный", 1)]), 
        ("Характеристика (3)?", [("Решительный", 2), ("Сообразительный", 3), ("Любознательный", 1)]), 
        ("Позиция в деятельности?", [("Генератор идей", 3), ("Критик", 2), ("Организатор", 1)]), 
        ("Сильные качества?", [("Сила воли", 2), ("Упорство", 3), ("Обязательность", 1)]), 
        ("Свободное время?", [("Любимое дело", 2), ("Читаю", 3), ("С друзьями", 1)]), 
        ("Интерес сейчас?", [("Методика", 1), ("Психология", 2), ("Инновации", 3)]), 
        ("Где реализовать себя?", [("Практика", 1), ("Проект", 3), ("Не знаю", 2)]), 
        ("Мнение друзей?", [("Справедливый", 3), ("Доброжелательный", 2), ("Отзывчивый", 1)]), 
        ("Принцип жизни?", [("Как хочешь", 1), ("Развитие", 3), ("Творчество", 2)]), 
        ("Идеал?", [("Исполнительный", 1), ("Независимый", 3), ("Творческий", 2)]), 
        ("Добьетесь мечты?", [("Да", 3), ("Скорее всего", 2), ("Как повезет", 1)]), 
        ("Что привлекает в исследовании?", [("Одобрение", 2), ("Не знаю", 1), ("Новые возможности", 3)]), 
        ("Выбор?", [("Путешествия", 2), ("Новая школа", 3), ("Удовольствие", 1)])
    ]

    M3_S = {1:0, 2:1, 3:0, 4:0, 5:0, 6:1, 7:0, 8:1, 9:0, 10:0, 11:0, 12:0, 13:1}
    M3_T = {
        1:"Недостаточность результатов", 2:"Высокий уровень притязаний", 3:"Потребность в контактах", 4:"Создать школу", 
        5:"Новизна", 6:"Лидерство", 7:"Поиск", 8:"Самовыражение", 9:"Инновации", 10:"Проверить знания", 
        11:"Риск", 12:"Деньги", 13:"Оценка"
    }

    M4_P = [
        "Для меня педагогическое исследование – это…", "Знание методологии педагогического исследования необходимо, чтобы…", 
        "Когда я сталкиваюсь с новой педагогической проблемой, я…", "Научная литература для меня – это…", 
        "Анализ данных в исследовании позволяет мне…", "Умение выдвигать гипотезу в моей работе…", 
        "Изучать что-то новое в педагогике меня побуждает…", "Без владения методами научного познания педагог…"
    ]

    M4_Q_S = [
        {"t":"s", "q":"Педагогическое исследование – это:", "o":[("Эксперименты", 0), ("Новые знания", 1), ("Системный процесс", 2)]}, 
        {"t":"m", "q":"Компоненты исследования:", "o":["Методы", "Задачи", "Продукт", "Ресурсы", "Объект", "Критерии", "Предмет", "Планирование", "Гипотеза"], "c":{0, 1, 4, 6, 7, 8}, "w":0.5}, 
        {"t":"s", "q":"Цель исследования – это:", "o":[("Результат", 1), ("Вопрос", 0), ("Ответ", 0)]},
        {"t":"s", "q":"Гипотеза – это:", "o":[("Вопрос", 0), ("Предположительный ответ", 1), ("Сфера поиска", 0)]},
        {"t":"s", "q":"Методы – это:", "o":[("Замысел", 0), ("Задачи", 0), ("Способы познания", 1)]},
        {"t":"m", "q":"Теоретические методы:", "o":["Моделирование", "Наблюдение", "Обработка", "Тесты", "Беседа", "Прогнозирование", "Анализ лит-ры", "Сравн. анализ", "Эксперимент", "Анализ продуктов"], "c":{0, 5, 6, 7}, "w":0.5},
        {"t":"m", "q":"Эмпирические методы:", "o":["Моделирование", "Наблюдение", "Обработка", "Тесты", "Беседа", "Прогнозирование", "Анализ лит-ры", "Сравн. анализ", "Эксперимент", "Анализ продуктов"], "c":{1, 2, 3, 4, 8, 9}, "w":0.5}
    ]

    M5_S = {1:1, 2:1, 3:1, 4:1, 5:0, 6:0, 7:1, 8:1, 9:0, 10:1, 11:1, 12:0, 13:0}
    M5_T = {
        1:"Видеть проблему", 2:"Анализировать причины", 3:"Прогнозировать", 4:"Выдвигать гипотезу", 
        5:"Перспектива ученика", 6:"Решать теоретически", 7:"Проектировать", 8:"Планировать", 
        9:"Атмосфера", 10:"Оценка деятельности", 11:"Рефлексия", 12:"Культ. различия", 13:"Оценивать учебную"
    }


    M6_Q = [
        ("ВПР низкий. Действия:", [("РНО", 1), ("Задания", 2), ("Изучить лит.", 3)]), 
        ("Нет гипотезы. Действия:", [("Образцы", 1), ("Уроки-исследования", 2), ("Анализ", 3)]), 
        ("Условие для ест-науч. грамотности:", [("Рекомендации", 1), ("Внеурочка", 2), ("Интеграция", 3)]),
        ("Гипотеза об интервальном повторении:", [("Диктанты", 1), ("Карточки", 2), ("Цифровые сервисы", 3)]),
        ("Сложности с методологией:", [("Продолжить", 1), ("Выяснить причину", 2), ("Изменить план", 3)]),
        ("Прогноз профориентации:", [("Диагностика", 1), ("Проект", 2), ("Профпроба", 3)]),
        ("Ценность Родины (низкая):", [("Рекомендации", 1), ("Обмен опытом", 2), ("Новые формы", 3)]),
        ("Не понимают проекты:", [("Анализ причин", 1), ("Опыт", 2), ("Сообщество", 3)])
    ]

    GT = {
        'm7':[("Мир может быть улучшен:", [("Да", 3), ("Нет", 1), ("Кое в чем", 2)]), ("Сможете участвовать:", [("Да", 3), ("Нет", 1), ("Иногда", 2)]), 
              ("Ваши идеи принесут прогресс:", [("Да", 3), ("При условиях", 1), ("В степени", 2)]), ("Изменить будущее:", [("Да", 3), ("Маловероятно", 1), ("Возможно", 2)]),
              ("Осуществите начинание:", [("Да", 3), ("Думаю, смогу", 1), ("Часто", 2)]), ("Новое дело:", [("Привлекает", 3), ("Нет", 1), ("Зависит", 2)]),
              ("Совершенство в новом:", [("Да", 3), ("Нет", 1), ("Если нравится", 2)]), ("Знать все о деле:", [("Да", 3), ("Нет", 1), ("Любопытство", 2)]),
              ("При неудаче:", [("Упорствую", 3), ("Бросаю", 1), ("Продолжаю", 2)]), ("Выбор профессии:", [("Возможности", 3), ("Стабильность", 1), ("Преимущества", 2)]),
              ("Ориентир на маршруте:", [("Да", 3), ("Нет", 1), ("Где понравилось", 2)]), ("Вспомнить беседу:", [("Да", 3), ("Нет", 1), ("Интересное", 2)]),
              ("Слово на языке:", [("Да", 3), ("Нет", 1), ("Не совсем", 2)]), ("Свободное время:", [("Наедине", 3), ("В компании", 1), ("Все равно", 2)]),
              ("Прекратить занятие:", [("Выполнено", 3), ("Более-менее", 1), ("Не все удалось", 2)]), ("Когда одни:", [("Мечтаю", 3), ("Ищу дело", 1), ("О работе", 2)]),
              ("Идея захватывает:", [("Всегда", 3), ("Наедине", 1), ("В тишине", 2)]), ("Отстаиваете идею:", [("Могу отказаться", 3), ("Останусь", 1), ("Изменю", 2)])],
        'm8':[("Следите за опытом?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]), ("Самообразование?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]), 
              ("Пед. идеи?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]), ("Научные консультанты?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]),
              ("Прогноз деятельности?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]), ("Открыты новому?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)])],
        'm10':[("Руководитель исследований?", [("Да", 2), ("Раздумываю", 1), ("Нет", 0)]), ("Обобщаете опыт?", [("Да", 2), ("Понимаю, но нет", 1), ("Нет", 0)]), 
               ("Форма обобщения?", [("Доклад", 1), ("Нет", 0), ("Другое", 0)]), ("Статьи (кол-во):", [("0", 0), ("1-3", 1), ("Более 3", 2)]),
               ("Мастер-классы?", [("Да", 2), ("Обдумываю", 1), ("Нет", 0)]), ("Курсы повышения?", [("Раз в 3 г", 1), ("Ежегодно", 2), ("Часто", 3)]),
               ("Инициатор курсов?", [("Сам (дефициты)", 2), ("Сам (надо)", 1), ("Админ", 0)]), ("Курсы по иссл. культуре?", [("Да", 2), ("Возможно", 1), ("Нет", 0)]),
               ("Неформальное повышение?", [("Да", 2), ("Желал бы", 1), ("Нет", 0)])]
    }

class ST(StatesGroup):
    wait_fio = State()
    wait_m4 = State()

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit=0.5):
        self.limit = limit
        self.cache = {}
    async def __call__(self, handler, event, data):
        user = data.get('event_from_user')
        if user:
            now = time.time()
            if user.id in self.cache and now - self.cache[user.id] < self.limit: return
            self.cache[user.id] = now
        return await handler(event, data)

class DB:
    def __init__(self):
        self.lock = asyncio.Lock()
    def e(self, d): return cipher.encrypt(d.encode()) if d else None
    def d(self, d): return cipher.decrypt(d).decode() if d else None

    async def init(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS u (
                    id INTEGER PRIMARY KEY, f BLOB,
                    c1 BLOB, c1s REAL, c1l INTEGER,
                    c2 BLOB, c2s REAL, c2l INTEGER,
                    c3 BLOB, c3s REAL, c3l INTEGER,
                    tr BLOB, trs REAL, trl INTEGER,
                    det BLOB
                )
            """)
            await db.commit()

    async def gf(self, uid):
        async with self.lock:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT f FROM u WHERE id=?", (uid,)) as c:
                    r = await c.fetchone()
                    return self.d(r[0]) if r and r[0] else None

    async def sf(self, uid, f):
        ef = self.e(f)
        async with self.lock:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT OR IGNORE INTO u (id) VALUES (?)", (uid,))
                await db.execute("UPDATE u SET f=? WHERE id=?", (ef, uid))
                await db.commit()

    async def gr(self, uid):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM u WHERE id=?", (uid,)) as c:
                r = await c.fetchone()
                if not r: return {}
                d = dict(r)
                for k in ['f', 'c1', 'c2', 'c3', 'tr']:
                    if d.get(k): d[k] = self.d(d[k])
                return d

    async def sr(self, uid, k, t, s, l=0, det=None):
        et = self.e(t)
        ed = self.e(json.dumps(det, ensure_ascii=False)) if det else None
        q = f"UPDATE u SET {k}=?, {k}s=?, {k}l=?" + (", det=?" if det else "") + " WHERE id=?"
        p = [et, s, l]
        if det: p.append(ed)
        p.append(uid)
        async with self.lock:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT OR IGNORE INTO u (id) VALUES (?)", (uid,))
                await db.execute(q, tuple(p))
                await db.commit()

    async def dump(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM u") as c:
                return await c.fetchall()

db = DB()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.message.middleware(ThrottlingMiddleware())
dp.callback_query.middleware(ThrottlingMiddleware())
r = Router()
dp.include_router(r)

async def req_ai(qa):
    p = "\n".join([f"Q: {q}\nA: {a}" for q, a in qa])
    sp = "Ты эксперт-методист. Оцени ответы на незаконченные предложения (1-3 балла). Верни JSON: {\"score\": <сумма>, \"level_id\": <1-3>, \"text\": \"<подробный вывод>\"}"
    pl = {"model": AI_MODEL, "messages": [{"role": "system", "content": sp}, {"role": "user", "content": p}]}
    for _ in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(AI_API_URL, json=pl, headers={"Authorization": f"Bearer {AI_API_KEY}"}, timeout=25) as rs:
                    if rs.status == 200:
                        d = await rs.json()
                        c = re.sub(r'```json\s*|\s*```', '', d['choices'][0]['message']['content']).strip()
                        j = json.loads(c)
                        return j['text'], float(j['score']), int(j['level_id'])
        except: await asyncio.sleep(1)
    return "ИИ не ответил", 0.0, 1

def clc(s, l, h): return 1 if s <= l else (2 if s <= h else 3)

def xls(rw):
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "FIO", "C1", "C2", "C3", "TR"])
    for x in rw:
        d = dict(x)
        f = db.d(d['f']) if d['f'] else ""
        ws.append([d['id'], f, d['c1s'], d['c2s'], d['c3s'], db.d(d['tr'])])
    b = io.BytesIO()
    wb.save(b)
    b.seek(0)
    return b.getvalue()

@r.message(Command("start"))
async def cmd_s(m: types.Message, state: FSMContext):
    try:
        f = await db.gf(m.chat.id)
        await m.answer(Txt.INTRO, parse_mode="HTML")
        if not f:
            await m.answer("Введите ФИО:")
            await state.set_state(ST.wait_fio)
        else:
            await m.answer(f"Привет, {f}!"); await mn(m)
    except: pass

@r.message(ST.wait_fio)
async def cmd_f(m: types.Message, state: FSMContext):
    if len(m.text) < 5: return await m.answer("Введите полное ФИО.")
    await db.sf(m.chat.id, m.text); await state.clear(); await mn(m)

async def mn(m: types.Message):
    r = await db.gr(m.chat.id)
    b = InlineKeyboardBuilder()
    c1, c2, c3 = r.get('c1'), r.get('c2'), r.get('c3')
    b.button(text=f"{'✅ ' if c1 else ''}Часть 1 (Ценности)", callback_data="s_c1")
    b.button(text=f"{'✅ ' if c2 else ''}Часть 2 (Технологии)", callback_data="s_c2")
    b.button(text=f"{'✅ ' if c3 else ''}Часть 3 (Творчество)", callback_data="s_c3")
    b.button(text="Мои результаты", callback_data="s_res")
    b.button(text="ИТОГОВЫЙ ОТЧЕТ", callback_data="s_fin")
    b.adjust(1)
    await m.answer("Меню:", reply_markup=b.as_markup())

@r.callback_query(F.data == "mn")
async def cb_mn(c: types.CallbackQuery): await mn(c.message); await c.answer()

@r.callback_query(F.data == "s_res")
async def cb_res(c: types.CallbackQuery):
    r = await db.gr(c.message.chat.id)
    t = "\n\n".join(filter(None, [r.get('c1'), r.get('c2'), r.get('c3'), r.get('tr')])) or "Нет данных."
    await c.message.answer(t, parse_mode="HTML"); await c.answer()

@r.callback_query(F.data == "s_fin")
async def cb_fin(c: types.CallbackQuery):
    r = await db.gr(c.message.chat.id)
    if not (r.get('c1') and r.get('c2') and r.get('c3')): return await c.answer("Сначала пройдите все тесты!", show_alert=True)
    l = (r.get('c1l',0) + r.get('c2l',0) + r.get('c3l',0)) / 3.0
    fl = 1 if l < 1.6 else (2 if l < 2.5 else 3)
    s = r.get('c1s',0) + r.get('c2s',0) + r.get('c3s',0)
    t = f"🏆 <b>ОБЩИЙ ВЫВОД</b>\n\n{Txt.GR[fl]}\n\nСуммарный балл: {s}"
    await db.sr(c.message.chat.id, 'tr', t, s, fl)
    await c.message.answer(t, parse_mode="HTML"); await c.answer()

@r.callback_query(F.data == "s_c1")
async def s_c1(c: types.CallbackQuery, state: FSMContext):
    r = await db.gr(c.message.chat.id)
    if r.get('c1'): return await c.answer("Пройдено.")
    await state.update_data(d={'m1':set(), 'm2':[], 'm3':set()})
    await rc(c, "c1m1", Txt.M1_T, set(), "М.1 Ценности", "n_c1m1")

@r.callback_query(F.data.startswith("c1m1_") | (F.data == "n_c1m1"))
async def p_c1m1(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    if c.data == "n_c1m1": await rq(c, "c1m2", Txt.M2_Q, 0, "М.2 Саморазвитие")
    else:
        s = d['d']['m1']; i = int(c.data.split("_")[1])
        s.remove(i) if i in s else s.add(i)
        await state.update_data(d=d['d'])
        await rc(c, "c1m1", Txt.M1_T, s, "М.1 Ценности", "n_c1m1")

@r.callback_query(F.data.startswith("c1m2_"))
async def p_c1m2(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data(); dt = d['d']
    if "a" in c.data:
        dt['m2'].append(int(c.data.split("_")[-1]))
        await state.update_data(d=dt)
        await rq(c, "c1m2", Txt.M2_Q, len(dt['m2']), "М.2 Саморазвитие")
    elif "n" in c.data: await rc(c, "c1m3", Txt.M3_T, set(), "М.3 Мотивация", "n_c1m3")

@r.callback_query(F.data.startswith("c1m3_") | (F.data == "n_c1m3"))
async def p_c1m3(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    if c.data == "n_c1m3":
        await state.set_state(ST.wait_m4); await state.update_data(i=0, a=[])
        await c.message.answer(f"1. {Txt.M4_P[0]}")
        try: await c.message.delete()
        except: pass
    else:
        s = d['d']['m3']; i = int(c.data.split("_")[1])
        s.remove(i) if i in s else s.add(i)
        await state.update_data(d=d['d'])
        await rc(c, "c1m3", Txt.M3_T, s, "М.3 Мотивация", "n_c1m3")

@r.message(ST.wait_m4)
async def p_c1m4(m: types.Message, state: FSMContext):
    d = await state.get_data(); i = d['i']
    d['a'].append((Txt.M4_P[i], m.text))
    i += 1
    if i >= len(Txt.M4_P):
        await m.answer("⏳ Анализирую...")
        at, asc, al = await req_ai(d['a'])
        dt = d['d']
        if isinstance(dt.get('m1'), set): dt['m1'] = list(dt['m1'])
        if isinstance(dt.get('m3'), set): dt['m3'] = list(dt['m3'])

        s1 = sum(Txt.M1_S[k] for k in dt['m1'])
        s2 = sum(dt['m2']) 
        s3 = sum(Txt.M3_S[k] for k in dt['m3'])
        
        l1 = clc(s1, 3, 5)
        l2 = clc(s2, 28, 42)
        l3 = clc(s3, 1, 2)
        
        avg = (l1+l2+l3+al)/4.0
        final_lvl = 1 if avg < 1.6 else (2 if avg < 2.5 else 3)
        ts = s1 + s2 + s3 + asc
        
        rt = f"📊 <b>C1 (Аксиологический)</b>\nБаллы: {ts}\n\n• Ценности: {s1} ({Txt.LVS[l1]})\n• Саморазвитие: {s2} ({Txt.LVS[l2]})\n• Мотивация: {s3} ({Txt.LVS[l3]})\n• ИИ Анализ: {asc} (Ур. {al})\n\n💬 <b>ИИ:</b>\n<i>{at}</i>\n\n🏆 Уровень: {Txt.LVS[final_lvl]}"
        await db.sr(m.chat.id, 'c1', rt, ts, final_lvl, {'raw': dt, 'ai': d['a']})
        await m.answer(rt, parse_mode="HTML"); await state.clear(); await mn(m)
    else:
        await state.update_data(i=i, a=d['a']); await m.answer(f"{i+1}. {Txt.M4_P[i]}")

@r.callback_query(F.data == "s_c2")
async def s_c2(c: types.CallbackQuery, state: FSMContext):
    r = await db.gr(c.message.chat.id)
    if r.get('c2'): return await c.answer("Пройдено.")
    await state.update_data(d={'m5':set(), 'm6':[], 'm4s':0})
    await rq_m4(c, 0, set())

async def rq_m4(c, i, ts):
    if i >= len(Txt.M4_Q_S): await rc(c, "c2m5", Txt.M5_T, set(), "М.5 Методология", "n_c2m5"); return
    q = Txt.M4_Q_S[i]; b = InlineKeyboardBuilder()
    txt = f"<b>М.4 ({i+1})</b>\n{q['q']}\n\n"
    if q['t'] == 's':
        for x, o in enumerate(q['o']): txt += f"{x+1}. {o[0]}\n"; b.button(text=f"{x+1}", callback_data=f"c2m4_s_{o[1]}")
    else:
        for x, o in enumerate(q['o']):
            mk = "✅" if x in ts else ""; txt += f"{x+1}. {o} {mk}\n"
            b.button(text=f"{x+1} {mk}", callback_data=f"c2m4_m_{x}")
        b.button(text="OK", callback_data="c2m4_ok")
    b.adjust(3); await c.message.edit_text(txt, reply_markup=b.as_markup(), parse_mode="HTML")

@r.callback_query(F.data.startswith("c2m4_"))
async def p_c2m4(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data(); dt = d.get('d', {}); i = d.get('i', 0); ts = set(d.get('ts', []))
    if "s_" in c.data:
        dt['m4s'] += float(c.data.split("_")[-1]); i += 1; ts = set()
    elif "m_" in c.data:
        x = int(c.data.split("_")[-1]); ts.remove(x) if x in ts else ts.add(x)
    elif "ok" in c.data:
        q = Txt.M4_Q_S[i]; dt['m4s'] += len(ts.intersection(q['c'])) * q['w']; i += 1; ts = set()
    await state.update_data(d=dt, i=i, ts=list(ts))
    if "m_" in c.data: await rq_m4(c, i, ts)
    else: await rq_m4(c, i, set())

@r.callback_query(F.data.startswith("c2m5_") | (F.data == "n_c2m5"))
async def p_c2m5(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    if c.data == "n_c2m5": await rq(c, "c2m6", Txt.M6_Q, 0, "М.6 Задачи")
    else:
        s = d['d']['m5']; i = int(c.data.split("_")[1])
        s.remove(i) if i in s else s.add(i)
        await state.update_data(d=d['d'])
        await rc(c, "c2m5", Txt.M5_T, s, "М.5 Методология", "n_c2m5")

@r.callback_query(F.data.startswith("c2m6_"))
async def p_c2m6(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data(); dt = d['d']
    if "a" in c.data:
        dt['m6'].append(int(c.data.split("_")[-1]))
        await state.update_data(d=dt)
        await rq(c, "c2m6", Txt.M6_Q, len(dt['m6']), "М.6 Задачи")
    elif "n" in c.data:
        if isinstance(dt.get('m5'), set): dt['m5'] = list(dt['m5'])
        s4, s5, s6 = dt['m4s'], sum(Txt.M5_S[k] for k in dt['m5']), sum(dt['m6'])
        ts = s4 + s5 + s6
        l = clc(ts, 18, 30) 
        rt = f"📊 C2: {ts}\nУровень: {Txt.LVS[l]}"
        await db.sr(c.message.chat.id, 'c2', rt, ts, l, dt); await c.message.answer(rt); await mn(c.message)

@r.callback_query(F.data == "s_c3")
async def s_c3(c: types.CallbackQuery, state: FSMContext):
    r = await db.gr(c.message.chat.id)
    if r.get('c3'): return await c.answer("Пройдено.")
    await state.update_data(d={'m7':[], 'm8':[], 'm10':[]})
    await rq(c, "c3m7", Txt.GT['m7'], 0, "М.7")

@r.callback_query(F.data.startswith("c3"))
async def p_c3(c: types.CallbackQuery, state: FSMContext):
    d = await state.get_data(); dt = d['d']; p = c.data.split("_"); k = p[0].replace("c3","")
    if "a" in c.data:
        dt[k].append(int(p[-1]))
        await state.update_data(d=dt)
        await rq(c, f"c3{k}", Txt.GT[k], len(dt[k]), k.upper())
    elif "n" in c.data:
        nk = "m8" if k == "m7" else ("m10" if k == "m8" else None)
        if nk: await rq(c, f"c3{nk}", Txt.GT[nk], 0, nk.upper())
        else:
            s7, s8, s10 = sum(dt['m7']), sum(dt['m8']), sum(dt['m10'])
            s = s7 + s8 + s10
            l = clc(s, 40, 65) 
            rt = f"📊 C3: {s}\nУровень: {Txt.LVS[l]}"
            await db.sr(c.message.chat.id, 'c3', rt, s, l, dt); await c.message.answer(rt); await mn(c.message)

@r.message(Command("admin"))
async def adm(m: types.Message):
    if m.from_user.id in ADMIN_IDS:
        rw = await db.dump(); f = xls(rw)
        await m.answer_document(BufferedInputFile(f, filename="res.xlsx"))

async def rc(c, p, i, s, t, n):
    b = InlineKeyboardBuilder(); txt = f"<b>{t}</b>\n\n"
    for k, v in i.items(): mk = "✅" if k in s else ""; txt += f"{k}. {v} {mk}\n"; b.button(text=f"{k} {mk}", callback_data=f"{p}_{k}")
    txt += "\nВыберите номера (можно несколько):"; b.button(text="Далее", callback_data=n); b.adjust(5)
    await c.message.edit_text(txt, reply_markup=b.as_markup(), parse_mode="HTML")

async def rq(c, p, q, i, t):
    if i >= len(q): b = InlineKeyboardBuilder(); b.button(text="Далее", callback_data=f"{p}_n"); await c.message.edit_text(f"{t} завершен.", reply_markup=b.as_markup()); return
    d = q[i]; b = InlineKeyboardBuilder()
    for x, o in enumerate(d[1]): b.button(text=f"{x+1}", callback_data=f"{p}_a_{o[1]}")
    ot = "\n".join([f"{x+1}. {z[0]}" for x, z in enumerate(d[1])])
    await c.message.edit_text(f"<b>{t} {i+1}/{len(q)}</b>\n{d[0]}\n\n{ot}", reply_markup=b.as_markup(), parse_mode="HTML")

async def main():
    await db.init()
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен!")
    while True:
        try: await dp.start_polling(bot)
        except Exception as e: print(f"ERR: {e}"); await asyncio.sleep(5)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
