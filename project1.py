import asyncio, logging, os, json, re, io, sys
from typing import Dict, Any, List, Tuple, Set
import aiosqlite, aiohttp
from openpyxl import Workbook
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from aiogram import Bot, Dispatcher, Router, F, types, BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()
TK=os.getenv('API_TOKEN'); AD=[int(x) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip()]
UR=os.getenv('AI_API_URL'); KY=os.getenv('AI_API_KEY'); MD=os.getenv('AI_MODEL')
DB="results.db"; CK=os.getenv('CIPHER_KEY')
fr=Fernet(CK.encode()) if CK else Fernet(Fernet.generate_key())
logging.basicConfig(level=logging.ERROR, handlers=[logging.StreamHandler(sys.stdout)])

class St(StatesGroup): wf=State(); pc1=State()

class Txt:
    LVS={1:"Репродуктивный (Низкий)", 2:"Частично-поисковый (Средний)", 3:"Творчески-исследовательский (Высокий)"}
    FD={'c1':{1:"Вы не проявляете интерес к познанию педагогических явлений и овладению средствами научного познания. Исследовательская деятельность не является для Вас ценностью.", 2:"Вы проявляете частичный интерес к познанию педагогических явлений. Вы понимаете значимость исследовательской деятельности, но не всегда готовы заниматься ею систематически.", 3:"Вам свойственен устойчивый интерес к познанию педагогических явлений. Исследовательская деятельность является для Вас одной из приоритетных ценностей, способствующей профессиональному росту."}, 'c2':{1:"Ваши методологические знания фрагментарны. Вы слабо владеете методами научного познания и испытываете затруднения в их применении на практике.", 2:"Вы владеете основными понятиями методологии педагогического исследования. Вы способны применять отдельные методы научного познания, но испытываете трудности в системном проектировании исследования.", 3:"Ваши методологические знания носят системный характер; вы уверенно используете методы научного познания для решения профессиональных задач и проектирования педагогического процесса."}, 'c3':{1:"Вы строите свою деятельность по заранее отработанной схеме, не проявляя творчества. Вы предпочитаете действовать по образцу и избегаете инноваций.", 2:"Вы демонстрируете стремление усовершенствовать собственную педагогическую практику. Вы открыты новому, но внедряете инновации осторожно.", 3:"Вы демонстрируете высокую творческую активность и инициативность. Вы постоянно стремитесь к саморазвитию, создаете авторские продукты и активно внедряете инновации."}}
    INT=("Здравствуйте, коллега! 👋\nРады видеть вас в чат-боте для диагностики вашей <b>исследовательской культуры</b>.\n\n<b>Почему это важно?</b> Современный педагог — это не только наставник, но и исследователь, способный анализировать, проектировать и постоянно развивать свою практику. Эта диагностика поможет вам оценить свою готовность к этой роли.\n\n<b>Что оцениваем?</b> Всего три ключевых аспекта:\n1. Ценностное отношение к новшествам и поиску.\n2. Технологическая готовность — знание методологии и умение применять исследовательские приемы.\n3. Творческая активность и стремление к саморазвитию.\n\n<b>Как это проходит?</b> Вам предстоит ответить на серию небольших вопросов и разобрать несколько кейс-ситуаций. Отвечайте быстро, исходя из вашего опыта.\n<b>Время:</b> около 25–40 минут.")
    CIN={'c1':"<b>Часть 1. Аксиологический критерий исследовательской культуры педагога.</b>\n\nОн позволит выявить вашу внутреннюю мотивацию: насколько вы стремитесь к новшествам и познанию педагогических явлений.", 'c2':"<b>Часть 2. Технологический критерий исследовательской культуры педагога.</b>\n\nОн позволит определить ваш уровень знаний методологии педагогического исследования и уровень владения приемами решения профессиональных задач.", 'c3':"<b>Часть 3. Личностно-творческий критерий исследовательской культуры педагога.</b>\n\nОн позволит определить вашу творческую активность и стремление к самореализации и личностному саморазвитию."}
    MIN={'tm1':"<b>Методика 1.</b> Анкета по выявлению у педагога ценностного отношения.\n\n<b>Задание:</b> определите важные для Вас ценности, отметьте все подходящие ответы.", 'tm2':"<b>Методика 2.</b> Тест «Рефлексия на саморазвитие».\n\n<b>Задание:</b> ответьте на вопросы, выбирая только один из предложенных вариантов ответа.", 'tm3':"<b>Методика 3.</b> Анкета «Мотивационная готовность».\n\n<b>Задание:</b> выберите не более трех ответов.", 'tm4':"<b>Методика 4.</b> Метод незаконченных предложений.\n\n<b>Задание:</b> завершите каждое предложение (не более 5 слов).", 'tm5':"<b>Методика 5.</b> Тест «Знание методологии».\n\n<b>Задание:</b> ответьте на вопросы.", 'tm6':"<b>Методика 6.</b> Умения педагога-исследователя.\n\n<b>Задание:</b> выберите необходимые умения.", 'tm7':"<b>Методика 7.</b> Решение педагогических задач.", 'tm8':"<b>Методика 8.</b> Тест «Творческий потенциал».", 'tm9':"<b>Методика 9.</b> Анкета «Восприимчивость к новшествам».", 'tm10':"<b>Методика 10.</b> Стремление к самосовершенствованию."}
    GR={1:"<b>Ваш уровень — РЕПРОДУКТИВНЫЙ (Начальный)</b>\n\nРекомендации:\n1. Начните с малого. Посетите семинар «Зачем учителю исследовать?».\n2. Освойте один метод диагностики.\n3. Подключитесь к проф. сообществу как наблюдатель.", 2:"<b>Ваш уровень — ЧАСТИЧНО-ПОИСКОВЫЙ (Средний)</b>\n\nРекомендации:\n1. Переходите от наблюдения к участию.\n2. Реализуйте небольшой исследовательский проект.\n3. Представьте результаты в формате стендового доклада.", 3:"<b>Ваш уровень — ТВОРЧЕСКИ-ИССЛЕДОВАТЕЛЬСКИЙ (Высокий)</b>\n\nРекомендации:\n1. Транслируйте свою концепцию.\n2. Разрабатывайте нестандартные методики.\n3. Выступите инициатором конференции."}
    M1I={1:1, 2:1, 3:1, 4:0, 5:1, 6:1, 7:1, 8:0, 9:0, 10:0, 11:1}
    M1T={1:"Потребность в изменении", 2:"Совершенствование практики", 3:"Осуществление инноваций", 4:"Удовлетворение амбиций", 5:"Глубокое познание", 6:"Потребность в самореализации", 7:"Проф. саморазвитие", 8:"Самоутверждение", 9:"Потребность в контактах", 10:"Обогащение опыта", 11:"Ценностное отношение"}
    M2Q=[("Характеристика:", [("Целеустремленный", 3), ("Трудолюбивый", 2), ("Дисциплинированный", 1)]), ("За что ценят:", [("Ответственность", 2), ("Принципиальность", 1), ("Эрудиция", 3)]), ("Отношение к исследованию:", [("Трата времени", 1), ("Не вникал", 2), ("Положительно", 3)]), ("Что мешает:", [("Время", 3), ("Условия", 2), ("Воля", 1)]), ("Затруднения:", [("Не анализировал", 2), ("Нет", 3), ("Не знаю", 1)])]
    M3I={1:0, 2:1, 3:0, 4:0, 5:0, 6:1, 7:0, 8:1, 9:0, 10:0, 11:0, 12:0, 13:1}
    M3T={1:"Недостаточность результатов", 2:"Высокий уровень притязаний", 3:"Потребность в контактах", 4:"Создать школу", 5:"Новизна", 6:"Лидерство", 7:"Поиск", 8:"Самовыражение", 9:"Инновации", 10:"Проверить знания", 11:"Риск", 12:"Деньги", 13:"Оценка"}
    M4P=["Для меня педагогическое исследование – это…", "Знание методологии педагогического исследования необходимо, чтобы…", "Когда я сталкиваюсь с новой педагогической проблемой, я…", "Научная литература для меня – это…", "Анализ данных в исследовании позволяет мне…", "Умение выдвигать гипотезу в моей работе…", "Изучать что-то новое в педагогике меня побуждает…", "Без владения методами научного познания педагог…"]
    M4Q=[{"t":"s", "q":"Педагогическое исследование – это:", "o":[("Эксперименты", 0), ("Новые знания", 1), ("Системный процесс", 2)]}, {"t":"m", "q":"Компоненты исследования:", "o":["Методы", "Задачи", "Продукт", "Ресурсы", "Объект", "Критерии", "Предмет", "Планирование", "Гипотеза"], "c":{0, 1, 4, 6, 7, 8}, "w":0.5}, {"t":"s", "q":"Цель исследования – это:", "o":[("Результат", 1), ("Вопрос", 0), ("Ответ", 0)]}]
    M5I={1:1, 2:1, 3:1, 4:1, 5:0, 6:0, 7:1, 8:1, 9:0, 10:1, 11:1, 12:0, 13:0}
    M5T={1:"Видеть проблему", 2:"Анализировать причины", 3:"Прогнозировать", 4:"Выдвигать гипотезу", 5:"Перспектива ученика", 6:"Решать теоретически", 7:"Проектировать", 8:"Планировать", 9:"Атмосфера", 10:"Оценка деятельности", 11:"Рефлексия", 12:"Культ. различия", 13:"Оценивать учебную"}
    M6Q=[("Анализ ВПР показал низкий уровень. Действия:", [("РНО", 1), ("Задания", 2), ("Изучить лит.", 3)]), ("Затруднения с гипотезой. Действия:", [("Образцы", 1), ("Уроки-исследования", 2), ("Анализ", 3)]), ("Условие для ест-науч. грамотности:", [("Рекомендации", 1), ("Внеурочка", 2), ("Интеграция", 3)])]
    GT={'m7':[("Мир может быть улучшен:", [("Да", 3), ("Нет", 1), ("Кое в чем", 2)]), ("Сможете участвовать в изменениях:", [("Да", 3), ("Нет", 1), ("Иногда", 2)]), ("Ваши идеи принесли бы прогресс:", [("Да", 3), ("При условиях", 1), ("В степени", 2)])], 'm8':[("Следите за опытом?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]), ("Самообразование?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)]), ("Пед. идеи?", [("Всегда", 3), ("Иногда", 2), ("Никогда", 1)])], 'm10':[("Руководитель исследований?", [("Да", 2), ("Раздумываю", 1), ("Нет", 0)]), ("Обобщаете опыт?", [("Да", 2), ("Понимаю, но нет", 1), ("Нет", 0)]), ("Форма обобщения?", [("Доклад", 1), ("Нет", 0), ("Другое", 0)])]}

class Bz:
    def __init__(self,nm): self.nm=nm; self.lk=asyncio.Lock()
    def _e(self,d): return fr.encrypt(d.encode()) if d else None
    def _d(self,d): return fr.decrypt(d).decode() if d else None
    async def ini(self):
        async with aiosqlite.connect(self.nm) as db:
            await db.execute("PRAGMA journal_mode=WAL;"); await db.execute("PRAGMA synchronous=NORMAL;"); await db.execute("PRAGMA cache_size=-64000;")
            await db.execute('CREATE TABLE IF NOT EXISTS res (u INTEGER PRIMARY KEY, f BLOB, c1 BLOB, c1s REAL, c1l INTEGER, c1d BLOB, c2 BLOB, c2s REAL, c2l INTEGER, c2d BLOB, c3 BLOB, c3s REAL, c3l INTEGER, c3d BLOB, tr BLOB)'); await db.commit()
    async def gf(self,u):
        async with aiosqlite.connect(self.nm) as db:
            async with db.execute("SELECT f FROM res WHERE u = ?", (u,)) as cur: r=await cur.fetchone(); return self._d(r[0]) if r and r[0] else None
    async def sf(self,u,f):
        eb=self._e(f)
        async with self.lk:
            async with aiosqlite.connect(self.nm) as db: await db.execute("INSERT OR IGNORE INTO res (u) VALUES (?)", (u,)); await db.execute("UPDATE res SET f = ? WHERE u = ?", (eb, u)); await db.commit()
    async def gr(self,u):
        async with aiosqlite.connect(self.nm) as db:
            db.row_factory=aiosqlite.Row
            async with db.execute("SELECT * FROM res WHERE u = ?", (u,)) as cur:
                r=await cur.fetchone(); 
                if not r: return {}
                d=dict(r)
                for k in ['c1','c2','c3','tr','c1d','c2d','c3d']: 
                    if d.get(k): d[k]=self._d(d[k])
                return d
    async def gar(self):
        async with aiosqlite.connect(self.nm) as db:
            db.row_factory=aiosqlite.Row
            async with db.execute("SELECT * FROM res") as cur:
                rs=await cur.fetchall(); out=[]
                for r in rs:
                    d=dict(r)
                    for k in ['f','c1','c2','c3','tr','c1d','c2d','c3d']: 
                        if d.get(k): d[k]=self._d(d[k])
                    out.append(d)
                return out
    async def sr(self,u,c,t,s,l=0,dt=None):
        ct=f"{c}"; cs=f"{c}s" if c!='tr' else None; cl=f"{c}l" if c!='tr' else None; cd=f"{c}d" if c!='tr' else None; dj=json.dumps(dt, ensure_ascii=False) if dt else None
        et=self._e(t); ed=self._e(dj)
        async with self.lk:
            async with aiosqlite.connect(self.nm) as db:
                await db.execute("INSERT OR IGNORE INTO res (u) VALUES (?)", (u,))
                if cs: await db.execute(f"UPDATE res SET {ct}=?, {cs}=?, {cl}=?, {cd}=? WHERE u=?", (et,s,l,ed,u))
                else: await db.execute(f"UPDATE res SET {ct}=? WHERE u=?", (et,u))
                await db.commit()

class Mid(BaseMiddleware):
    def __init__(self,l=0.5): self.l=l; self.lr={}
    async def __call__(self,h,e,d):
        u=d.get("event_from_user")
        if u:
            n=asyncio.get_running_loop().time(); lr=self.lr.get(u.id,0)
            if n-lr<self.l: return 
            self.lr[u.id]=n
        return await h(e,d)

class Sess:
    s=None
    @classmethod
    async def gs(cls): 
        if cls.s is None: cls.s=aiohttp.ClientSession()
        return cls.s
    @classmethod
    async def cl(cls): 
        if cls.s: await cls.s.close()

bz=Bz(DB); bt=Bot(token=TK); st=MemoryStorage(); dp=Dispatcher(storage=st); r=Router(); dp.include_router(r); dp.update.middleware(Mid(limit=0.3)); txt=Txt()

async def ai(qa):
    qt="\n".join([f"Q: {q}\nA: {a}" for q,a in qa])
    sp="Ты методист-психолог. Оцени ответы (1-3 балла). 1 (Репродуктивный), 2 (Частично-поисковый), 3 (Творческий). Верни JSON: {\"score\": <sum>, \"level_id\": <1-3>, \"text\": \"<вывод>\"}"
    try:
        s=await Sess.gs(); pl={"model":MD, "messages":[{"role":"system", "content":sp}, {"role":"user", "content":qt}]}
        async with s.post(UR, json=pl, headers={"Authorization":f"Bearer {KY}"}) as rp:
            dt=await rp.json(); c=dt['choices'][0]['message']['content']; cl=re.sub(r'```json\s*|\s*```','',c).strip(); p=json.loads(cl); return p['text'], float(p['score']), int(p['level_id'])
    except: return "Ошибка AI.", 0.0, 1

def clc(s,lm,mm):
    if s<=lm: return 1
    if s<=mm: return 2
    return 3

async def xls(rw):
    wb=Workbook(); ws=wb.active; ws.title="R"; ws.append(["ID", "FIO", "C1 S", "C1 L", "C2 S", "C2 L", "C3 S", "C3 L", "T"])
    for x in rw: ws.append([x['u'], x['f'], x['c1s'], x['c1l'], x['c2s'], x['c2l'], x['c3s'], x['c3l'], x['tr']])
    b=io.BytesIO(); wb.save(b); b.seek(0); return b.getvalue()

@r.message(Command("start"))
async def nch(m:types.Message, s:FSMContext):
    f=await bz.gf(m.chat.id); await m.answer(txt.INT, parse_mode="HTML")
    if not f: await m.answer("Введите ФИО:"); await s.set_state(St.wf)
    else: await m.answer(f"Привет, {f}!"); await mn(m)

@r.message(St.wf)
async def fio(m:types.Message, s:FSMContext):
    if len(m.text)<5: return await m.answer("ФИО полностью.")
    await bz.sf(m.chat.id, m.text); await m.answer("Сохранено."); await s.clear(); await mn(m)

async def mn(m:types.Message):
    r=await bz.gr(m.chat.id); b=InlineKeyboardBuilder()
    for i in range(1,4): d="✅ " if r.get(f'c{i}') else ""; b.button(text=f"{d}Критерий {i}", callback_data=f"sc{i}")
    b.button(text="Мои результаты", callback_data="sr"); b.button(text="ОБЩИЙ ВЫВОД", callback_data="gr"); b.adjust(1); await m.answer("Меню:", reply_markup=b.as_markup())

@r.callback_query(F.data=="men")
async def cbm(c:types.CallbackQuery): await c.answer(); await mn(c.message)

@r.callback_query(F.data=="sr")
async def cbs(c:types.CallbackQuery):
    r=await bz.gr(c.message.chat.id); t="\n\n".join(filter(None, [r.get(f'c{i}') for i in range(1,4)]+[r.get('tr')])) or "Нет данных."
    await c.message.answer(t, parse_mode="HTML"); await c.answer()

@r.callback_query(F.data=="gr")
async def cbg(c:types.CallbackQuery):
    r=await bz.gr(c.message.chat.id)
    if not all(r.get(f'c{i}') for i in range(1,4)): return await c.answer("Пройдите все!", show_alert=True)
    la=sum(r.get(f'c{i}l',0) for i in range(1,4))/3.0; fl=1 if la<1.6 else (2 if la<2.5 else 3); ts=sum(r.get(f'c{i}s',0) for i in range(1,4))
    t=f"🏆 <b>ОБЩИЙ ВЫВОД</b>\n\n{txt.GR[fl]}\n\nСумма: {ts}"; await bz.sr(c.message.chat.id, 'tr', t, ts); await c.message.answer(t, parse_mode="HTML"); await c.answer()

@r.message(Command("admin"))
async def adm(m:types.Message):
    if m.from_user.id not in AD: return
    b=InlineKeyboardBuilder(); b.button(text="Excel", callback_data="ex"); await m.answer("Adm", reply_markup=b.as_markup())

@r.callback_query(F.data=="ex")
async def cbx(c:types.CallbackQuery):
    if c.from_user.id not in AD: return
    await c.answer("Wait..."); r=await bz.gar(); fd=await asyncio.to_thread(xls, r); await c.message.answer_document(BufferedInputFile(fd, filename="r.xlsx"))

@r.callback_query(F.data.startswith("sc"))
async def csc(c:types.CallbackQuery, s:FSMContext):
    n=int(c.data[-1]); r=await bz.gr(c.message.chat.id)
    if r.get(f'c{n}'): return await c.answer("Пройдено.")
    b=InlineKeyboardBuilder(); b.button(text="Начать", callback_data=f"rsc{n}"); await c.message.edit_text(txt.CIN[f'c{n}'], reply_markup=b.as_markup(), parse_mode="HTML")

@r.callback_query(F.data=="rsc1")
async def rc1(c:types.CallbackQuery, s:FSMContext):
    await s.update_data(d={'m1':set(), 'm2':[], 'm2i':0, 'm3':set()}); await rc(c, "c1m1", txt.M1T, set(), "М.1", "nc1m1")

@r.callback_query(F.data.startswith("c1m1_"))
async def pc1m1(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); sl=d['d']['m1']
    if c.data=="nc1m1": await s.update_data(d=d['d']); await rs(c, "c1m2", txt.M2Q, 0, "М.2")
    else:
        i=int(c.data.split("_")[-1]); sl.remove(i) if i in sl else sl.add(i); await s.update_data(d=d['d']); await rc(c, "c1m1", txt.M1T, sl, "М.1", "nc1m1")

@r.callback_query(F.data.startswith("c1m2_"))
async def pc1m2(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); dt=d['d']
    if "a" in c.data: dt['m2'].append(int(c.data.split("_")[-1])); dt['m2i']+=1; await s.update_data(d=dt); await rs(c, "c1m2", txt.M2Q, dt['m2i'], "М.2")
    elif "n" in c.data: await rc(c, "c1m3", txt.M3T, set(), "М.3", "nc1m3")

@r.callback_query(F.data.startswith("c1m3_"))
async def pc1m3(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); sl=d['d']['m3']
    if c.data=="nc1m3": await s.set_state(St.pc1); await s.update_data(m4i=0, m4a=[]); await c.message.answer(txt.MIN['tm4']); await sm4(c.message, 0)
    else: i=int(c.data.split("_")[-1]); sl.remove(i) if i in sl else sl.add(i); await s.update_data(d=d['d']); await rc(c, "c1m3", txt.M3T, sl, "М.3", "nc1m3")

async def sm4(m,i):
    if i>=len(txt.M4P): return
    await m.answer(f"V {i+1}: {txt.M4P[i]}")

@r.message(St.pc1)
async def pm4(m:types.Message, s:FSMContext):
    d=await s.get_data(); i=d['m4i']; d['m4a'].append((txt.M4P[i], m.text)); i+=1
    if i>=len(txt.M4P):
        await m.answer("AI..."); at,asc,al=await ai(d['m4a']); c1=d['d']; s1=sum(txt.M1I[k] for k in c1['m1']); s2=sum(c1['m2']); s3=sum(txt.M3I[k] for k in c1['m3']); t=s1+s2+s3+asc; l1,l2,l3=clc(s1,3,5),clc(s2,27,41),clc(s3,2,3); fl=1 if (l1+l2+l3+al)/4 < 1.6 else (2 if (l1+l2+l3+al)/4 < 2.5 else 3)
        rt=f"📊 C1\nM1: {s1}\nM2: {s2}\nM3: {s3}\nAI: {asc}\n\n{at}\n\nI: {txt.LVS[fl]}"; await bz.sr(m.chat.id, 'c1', rt, t, fl, {'m1':list(c1['m1']), 'm2':c1['m2'], 'm3':list(c1['m3']), 'm4':d['m4a']}); await m.answer(rt); await s.clear(); await mn(m)
    else: await s.update_data(m4i=i, m4a=d['m4a']); await sm4(m, i)

@r.callback_query(F.data=="rsc2")
async def rc2(c:types.CallbackQuery, s:FSMContext):
    await s.update_data(d={'m4i':0, 'm4s':0, 'm4t':set(), 'm4a':[], 'm5':set(), 'm6i':0, 'm6a':[]}); await rm4(c, 0, set())

async def rm4(c,i,ts):
    if i>=len(txt.M4Q): await rc(c, "c2m5", txt.M5T, set(), "М.5", "nc2m5"); return
    q=txt.M4Q[i]; b=InlineKeyboardBuilder()
    if q['t']=='s':
        for x,o in enumerate(q['o']): b.button(text=o[0], callback_data=f"c2m4_s_{o[1]}")
    else:
        for x,t in enumerate(q['o']): mk="✅" if x in ts else ""; b.button(text=f"{x+1} {mk}", callback_data=f"c2m4_m_{x}")
        b.button(text="OK", callback_data="c2m4_ok")
    b.adjust(3); await c.message.edit_text(f"М.4 ({i+1})\n{q['q']}", reply_markup=b.as_markup())

@r.callback_query(F.data.startswith("c2m4_"))
async def pc2m4(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); cd=d['d']; i=cd['m4i']
    if "s_" in c.data: sc=float(c.data.split("_")[-1]); cd['m4s']+=sc; cd['m4a'].append(sc); cd['m4i']+=1; await s.update_data(d=cd); await rm4(c, cd['m4i'], set())
    elif "m_" in c.data: o=int(c.data.split("_")[-1]); st=set(cd['m4t']); st.remove(o) if o in st else st.add(o); cd['m4t']=list(st); await s.update_data(d=cd); await rm4(c, i, st)
    elif "ok" in c.data: q=txt.M4Q[i]; cr=set(q['c']); sl=set(cd['m4t']); sc=len(sl.intersection(cr))*q['w']; cd['m4s']+=sc; cd['m4a'].append(sc); cd['m4t']=[]; cd['m4i']+=1; await s.update_data(d=cd); await rm4(c, cd['m4i'], set())

@r.callback_query(F.data.startswith("c2m5_"))
async def pc2m5(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); sl=set(d['d']['m5'])
    if c.data=="nc2m5": d['d']['m5']=list(sl); await s.update_data(d=d['d']); await rs(c, "c2m6", txt.M6Q, 0, "М.6")
    else: i=int(c.data.split("_")[-1]); sl.remove(i) if i in sl else sl.add(i); d['d']['m5']=list(sl); await s.update_data(d=d['d']); await rc(c, "c2m5", txt.M5T, sl, "М.5", "nc2m5")

@r.callback_query(F.data.startswith("c2m6_"))
async def pc2m6(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); cd=d['d']
    if "a" in c.data: cd['m6a'].append(int(c.data.split("_")[-1])); cd['m6i']+=1; await s.update_data(d=cd); await rs(c, "c2m6", txt.M6Q, cd['m6i'], "М.6")
    elif "n" in c.data: s4,s5=cd['m4s'],sum(txt.M5I[k] for k in cd['m5']); s6=sum(cd['m6a']); l=clc((s4+s5+s6)/3, 5, 10); t=f"📊 C2\nM4: {s4}\nM5: {s5}\nM6: {s6}\nI: {txt.LVS[l]}"; await bz.sr(c.message.chat.id, 'c2', t, s4+s5+s6, l, cd); await c.message.answer(t); await mn(c.message)

@r.callback_query(F.data=="rsc3")
async def rc3(c:types.CallbackQuery, s:FSMContext):
    await s.update_data(d={'m7':[], 'm7i':0, 'm8':[], 'm8i':0, 'm10':[], 'm10i':0}); await rs(c, "c3m7", txt.GT['m7'], 0, "М.7")

@r.callback_query(F.data.startswith("c3"))
async def pc3(c:types.CallbackQuery, s:FSMContext):
    d=await s.get_data(); cd=d['d']; pt=c.data.split("_"); ts=pt[0].replace("c3","")
    if "a" in c.data: cd[f'{ts}'].append(int(pt[-1])); cd[f'{ts}i']+=1; await s.update_data(d=cd); await rs(c, f"c3{ts}", txt.GT[ts], cd[f'{ts}i'], ts.upper())
    elif "n" in c.data:
        nxt="m8" if ts=="m7" else ("m10" if ts=="m8" else None)
        if nxt: await rs(c, f"c3{nxt}", txt.GT[nxt], 0, nxt.upper())
        else: s7,s8,s10=sum(cd['m7']),sum(cd['m8']),sum(cd['m10']); l=clc((s7+s8+s10)/3, 20, 40); t=f"📊 C3\nM7: {s7}\nM8: {s8}\nM10: {s10}\nI: {txt.LVS[l]}"; await bz.sr(c.message.chat.id, 'c3', t, s7+s8+s10, l, cd); await c.message.answer(t); await mn(c.message)

async def rc(c,pf,it,sl,tl,ncb):
    b=InlineKeyboardBuilder()
    for k,v in it.items(): m="✅" if k in sl else ""; b.button(text=f"{k} {m}", callback_data=f"{pf}_{k}")
    b.button(text=">", callback_data=ncb); b.adjust(5); await c.message.edit_text(f"<b>{tl}</b>\n:", reply_markup=b.as_markup(), parse_mode="HTML")

async def rs(c,pf,qs,i,tl):
    if i>=len(qs): b=InlineKeyboardBuilder(); b.button(text=">>", callback_data=f"{pf}_n"); await c.message.edit_text(f"{tl} end.", reply_markup=b.as_markup()); return
    q=qs[i]; b=InlineKeyboardBuilder()
    for x,o in enumerate(q[1]): b.button(text=f"{x+1}", callback_data=f"{pf}_a_{o[1]}")
    tx=f"<b>{tl} {i+1}/{len(qs)}</b>\n{q[0]}\n"+"\n".join([f"{x+1}. {z[0]}" for x,z in enumerate(q[1])]); await c.message.edit_text(tx, reply_markup=b.as_markup(), parse_mode="HTML")

async def su(d): await bz.ini(); await Sess.gs()
async def sd(d): await Sess.cl()
async def main(): await bt.delete_webhook(drop_pending_updates=True); dp.startup.register(su); dp.shutdown.register(sd); await dp.start_polling(bt)

if __name__=="__main__": asyncio.run(main())
