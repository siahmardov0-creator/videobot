import asyncio, html as htmllib, json, os, re, sys, tempfile, urllib.request
from urllib.parse import urljoin
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

TOKEN = os.environ["BOT_TOKEN"]
HERE = os.path.dirname(os.path.abspath(__file__))
COOKIES = os.path.join(HERE, "cookies.txt")
DATA = os.environ.get("DATA_PATH", os.path.join(HERE, "data.json"))
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
FMT = ("bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/b[ext=mp4][height<=1080]"
       "/bv*[height<=1080]+ba/b")
LIMIT = 49 * 1024 * 1024

FALLBACK = {
    "ok": "✅", "load": "⏳", "fail": "❌", "video": "🎬", "link": "🔗",
    "lang": "🌐", "admin": "👑", "stat": "📊", "bc": "📢", "gem": "💎",
}

TX = {
    "ru": {
        "hello": "{video} Привет! Отправьте ссылку на любое видео с любого сайта, и я скачаю и пришлю его.\n\n{lang} Сменить язык: /lang",
        "choose_lang": "{lang} Выберите язык / Забонро интихоб кунед:",
        "lang_set": "{ok} Язык: Русский",
        "need_link": "{link} Отправьте ссылку (она должна начинаться с https://).",
        "loading": "{load} Скачиваю...",
        "searching": "{load} Ищу видео на странице...",
        "converting": "{load} Конвертирую...",
        "shrinking": "{load} Файл большой, уменьшаю (<h>p)...",
        "too_big": "{fail} Видео больше 50 МБ, отправить невозможно.",
        "fail": "{fail} Видео не найдено. Возможно, страница закрыта, требует вход или видео защищено (например, Netflix).",
        "done": "{ok} Готово!",
        "adm_title": "{admin} Админ-панель",
        "adm_claimed": "{admin} Вы теперь администратор бота.",
        "adm_denied": "{fail} Нет доступа.",
        "adm_stats": "{stat} Статистика\n\nПользователей: <u>\nСкачано видео: <d>",
        "adm_bc_ask": "{bc} Отправьте текст рассылки одним сообщением.\nОтмена: /cancel",
        "adm_bc_done": "{ok} Рассылка завершена: <s> из <n>",
        "adm_emoji": "{gem} Premium-эмодзи\n\n1) Отправьте мне сообщение с premium-эмодзи, и я покажу его ID.\n2) Привяжите: /setemoji имя ID\n\nИмена: ok, load, fail, video, link, lang, admin, stat, bc, gem\n\nПривязано: <list>",
        "emoji_ids": "{gem} ID эмодзи:\n<ids>",
        "emoji_saved": "{ok} Сохранено: <name>",
        "emoji_usage": "{fail} Формат: /setemoji имя ID",
        "cancel": "{ok} Отменено.",
        "b_stats": "📊 Статистика", "b_bc": "📢 Рассылка",
        "b_emoji": "💎 Premium-эмодзи", "b_lang": "🌐 Язык / Забон",
    },
    "tj": {
        "hello": "{video} Салом! Линки ҳар видеоро аз ҳар сайт фиристед, ман онро зеркашӣ карда мефиристам.\n\n{lang} Иваз кардани забон: /lang",
        "choose_lang": "{lang} Выберите язык / Забонро интихоб кунед:",
        "lang_set": "{ok} Забон: Тоҷикӣ",
        "need_link": "{link} Линк фиристед (бояд бо https:// оғоз шавад).",
        "loading": "{load} Зеркашӣ мешавад...",
        "searching": "{load} Дар саҳифа видео меҷӯям...",
        "converting": "{load} Табдил мешавад...",
        "shrinking": "{load} Файл калон аст, хурд мекунам (<h>p)...",
        "too_big": "{fail} Видео аз 50 МБ калон аст, фиристода намешавад.",
        "fail": "{fail} Видео нашуд. Эҳтимол саҳифа пӯшида аст, воридшавӣ талаб мекунад ё видео муҳофизатшудааст (масалан Netflix).",
        "done": "{ok} Тайёр!",
        "adm_title": "{admin} Панели админ",
        "adm_claimed": "{admin} Шумо акнун админи бот ҳастед.",
        "adm_denied": "{fail} Дастрасӣ нест.",
        "adm_stats": "{stat} Омор\n\nИстифодабарандагон: <u>\nВидеоҳои зеркашишуда: <d>",
        "adm_bc_ask": "{bc} Матни паёмро дар як хабар фиристед.\nБекор кардан: /cancel",
        "adm_bc_done": "{ok} Паём фиристода шуд: <s> аз <n>",
        "adm_emoji": "{gem} Premium-эмодзи\n\n1) Ба ман паём бо premium-эмодзи фиристед, ман ID-и онро нишон медиҳам.\n2) Пайваст кунед: /setemoji ном ID\n\nНомҳо: ok, load, fail, video, link, lang, admin, stat, bc, gem\n\nПайваст шудааст: <list>",
        "emoji_ids": "{gem} ID-и эмодзи:\n<ids>",
        "emoji_saved": "{ok} Нигоҳ дошта шуд: <name>",
        "emoji_usage": "{fail} Шакл: /setemoji ном ID",
        "cancel": "{ok} Бекор шуд.",
        "b_stats": "📊 Омор", "b_bc": "📢 Паём",
        "b_emoji": "💎 Premium-эмодзи", "b_lang": "🌐 Язык / Забон",
    },
}


def load():
    try:
        with open(DATA, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("users", {})
    d.setdefault("admin", None)
    d.setdefault("downloads", 0)
    d.setdefault("emoji", {})
    return d


D = load()


def save():
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False)


def lang_of(uid):
    return D["users"].get(str(uid), {}).get("lang", "ru")


def t(uid, key):
    return TX[lang_of(uid)][key]


def ensure(user):
    u = D["users"].setdefault(str(user.id), {"lang": "ru"})
    u["name"] = user.full_name
    save()


def u16(s):
    return len(s.encode("utf-16-le")) // 2


def fmt(text):
    out, ents, pos = "", [], 0
    for m in re.finditer(r"\{(\w+)\}", text):
        name = m.group(1)
        if name not in FALLBACK:
            continue
        out += text[pos:m.start()]
        ch = FALLBACK[name]
        eid = D["emoji"].get(name)
        if eid:
            ents.append(MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=u16(out),
                                      length=u16(ch), custom_emoji_id=str(eid)))
        out += ch
        pos = m.end()
    out += text[pos:]
    return out, ents


async def reply(msg, text, **kw):
    s, e = fmt(text)
    return await msg.reply_text(s, entities=e or None, **kw)


async def edit(msg, text, **kw):
    s, e = fmt(text)
    return await msg.edit_text(s, entities=e or None, **kw)


def lang_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang:tj"),
    ]])


def admin_kb(uid):
    x = TX[lang_of(uid)]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(x["b_stats"], callback_data="adm:stats"),
         InlineKeyboardButton(x["b_bc"], callback_data="adm:bc")],
        [InlineKeyboardButton(x["b_emoji"], callback_data="adm:emoji"),
         InlineKeyboardButton(x["b_lang"], callback_data="adm:lang")],
    ])


async def run(cmd, timeout=600):
    p = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    try:
        _, err = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        return 1, "timeout"
    return p.returncode, err.decode(errors="ignore")[-400:]


async def fetch(url, tmp, referer=None):
    for f in os.listdir(tmp):
        if f.startswith("v."):
            os.remove(os.path.join(tmp, f))
    cmd = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-warnings",
           "--socket-timeout", "20", "-f", FMT, "--merge-output-format", "mp4",
           "-o", os.path.join(tmp, "v.%(ext)s")]
    if referer:
        cmd += ["--referer", referer]
    if os.path.exists(COOKIES):
        cmd += ["--cookies", COOKIES]
    cmd.append(url)
    code, err = await run(cmd)
    files = [f for f in os.listdir(tmp) if f.startswith("v.")]
    if code == 0 and files:
        return os.path.join(tmp, files[0]), err
    return None, err


def find_media(page_url):
    req = urllib.request.Request(page_url, headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=20).read(3_000_000).decode("utf-8", "ignore")
    page = page.replace("\\/", "/")
    pats = [
        r'property=["\']og:video(?::url|:secure_url)?["\'][^>]*content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\'][^>]*property=["\']og:video',
        r'<(?:video|source)[^>]+src=["\']([^"\']+)',
        r'"(https?://[^"\s]+\.(?:mp4|m3u8)[^"\s]*)"',
    ]
    found = []
    for pat in pats:
        for u in re.findall(pat, page, re.I):
            u = urljoin(page_url, htmllib.unescape(u))
            if u not in found:
                found.append(u)
    return found[:6]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure(update.effective_user)
    uid = update.effective_user.id
    await reply(update.message, t(uid, "hello"), reply_markup=lang_kb())


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure(update.effective_user)
    await reply(update.message, t(update.effective_user.id, "choose_lang"),
                reply_markup=lang_kb())


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure(update.effective_user)
    uid = update.effective_user.id
    if D["admin"] is None:
        D["admin"] = uid
        save()
        await reply(update.message, t(uid, "adm_claimed"))
    if uid != D["admin"]:
        await reply(update.message, t(uid, "adm_denied"))
        return
    await reply(update.message, t(uid, "adm_title"), reply_markup=admin_kb(uid))


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("bc", None)
    await reply(update.message, t(update.effective_user.id, "cancel"))


async def setemoji_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != D["admin"]:
        await reply(update.message, t(uid, "adm_denied"))
        return
    a = context.args
    if len(a) != 2 or a[0] not in FALLBACK or not a[1].isdigit():
        await reply(update.message, t(uid, "emoji_usage"))
        return
    D["emoji"][a[0]] = a[1]
    save()
    await reply(update.message, t(uid, "emoji_saved").replace("<name>", a[0]))


async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    ensure(q.from_user)
    await q.answer()
    data = q.data or ""
    if data.startswith("lang:"):
        D["users"][str(uid)]["lang"] = data[5:] if data[5:] in TX else "ru"
        save()
        await edit(q.message, t(uid, "hello"), reply_markup=lang_kb())
        return
    if not data.startswith("adm:") or uid != D["admin"]:
        return
    act = data[4:]
    if act == "stats":
        txt = (t(uid, "adm_stats").replace("<u>", str(len(D["users"])))
               .replace("<d>", str(D["downloads"])))
        await reply(q.message, txt)
    elif act == "bc":
        context.user_data["bc"] = True
        await reply(q.message, t(uid, "adm_bc_ask"))
    elif act == "emoji":
        lst = ", ".join(f"{k}={v}" for k, v in D["emoji"].items()) or "-"
        await reply(q.message, t(uid, "adm_emoji").replace("<list>", lst))
    elif act == "lang":
        new = "tj" if lang_of(uid) == "ru" else "ru"
        D["users"][str(uid)]["lang"] = new
        save()
        await edit(q.message, t(uid, "adm_title"), reply_markup=admin_kb(uid))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    ensure(update.effective_user)
    uid = update.effective_user.id
    text = msg.text or ""

    if uid == D["admin"]:
        ids = [e.custom_emoji_id for e in (msg.entities or [])
               if e.type == MessageEntity.CUSTOM_EMOJI]
        if ids:
            await reply(msg, t(uid, "emoji_ids").replace("<ids>", "\n".join(ids)))
            return
        if context.user_data.pop("bc", None):
            ok = 0
            users = list(D["users"].keys())
            for u in users:
                try:
                    await context.bot.send_message(int(u), text)
                    ok += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            await reply(msg, t(uid, "adm_bc_done").replace("<s>", str(ok))
                        .replace("<n>", str(len(users))))
            return

    m = re.search(r"https?://\S+", text)
    if not m:
        await reply(msg, t(uid, "need_link"))
        return
    url = m.group(0)
    status = await reply(msg, t(uid, "loading"))
    with tempfile.TemporaryDirectory() as tmp:
        path, err = await fetch(url, tmp)
        if not path:
            await edit(status, t(uid, "searching"))
            try:
                cands = await asyncio.to_thread(find_media, url)
            except Exception:
                cands = []
            for c in cands:
                path, e = await fetch(c, tmp, referer=url)
                if path:
                    break
        if not path:
            await edit(status, t(uid, "fail") + "\n\n" + err[-200:])
            return

        if not path.endswith(".mp4"):
            conv = os.path.join(tmp, "conv.mp4")
            await edit(status, t(uid, "converting"))
            await run(["ffmpeg", "-y", "-i", path, "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "26", "-c:a", "aac", "-movflags", "+faststart", conv])
            if os.path.exists(conv):
                path = conv

        for h, crf in [(720, 30), (480, 34)]:
            if os.path.getsize(path) <= LIMIT:
                break
            small = os.path.join(tmp, f"small{h}.mp4")
            await edit(status, t(uid, "shrinking").replace("<h>", str(h)))
            await run(["ffmpeg", "-y", "-i", path, "-vf", f"scale=-2:{h}",
                       "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
                       "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", small])
            if os.path.exists(small):
                path = small

        if os.path.getsize(path) > 50 * 1024 * 1024:
            await edit(status, t(uid, "too_big"))
            return
        s, e = fmt(t(uid, "done"))
        with open(path, "rb") as v:
            await msg.reply_video(v, caption=s, caption_entities=e or None,
                                  supports_streaming=True)
        D["downloads"] += 1
        save()
        await status.delete()


def main():
    app = (
        Application.builder().token(TOKEN)
        .read_timeout(60).write_timeout(120).connect_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("setemoji", setemoji_cmd))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Бот кор мекунад...")
    app.run_polling()


if __name__ == "__main__":
    main()
