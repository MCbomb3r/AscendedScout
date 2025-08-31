import discord
import asyncio
import os
import time
import hashlib
import re
import unicodedata
import difflib
import shutil
from collections import defaultdict

# =========================
# DISCORD CLIENT / INTENTS
# =========================
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # ⚠️ must also be enabled in Developer Portal
client = discord.Client(intents=intents)

# =========================
# PATHS
# =========================
base_dir = os.path.dirname(__file__)
base_log_path = os.path.join(base_dir, "..", "logs")

tribemembers_log_path = os.path.join(base_log_path, "tribemembers_log.txt")
players_log_path      = os.path.join(base_log_path, "players_log.txt")
center_log_path       = os.path.join(base_log_path, "center_log.txt")

audio_file_path = os.path.join(base_dir, "..", "assets", "ALERT NUKE.mp3")

FFMPEG_EXEC = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg")
print(f"[VOICE] ffmpeg = {FFMPEG_EXEC or 'NOT FOUND'}")

try:
    import nacl
    print("[VOICE] PyNaCl OK")
except Exception as e:
    print(f"[VOICE] PyNaCl MANQUANT: {e}  ->  pip install PyNaCl")

# =========================
# DISCORD IDS
# =========================
tribemembers_channel_id = your_tribemembers_channel_id_here  # Replace with your channel ID
players_channel_id      = your_players_channel_id_here      # Replace with your channel ID
center_channel_id       = your_center_channel_id_here       # Replace with your channel ID
voice_channel_id        = your_voice_channel_id_here        # Replace with your voice channel ID

# =========================
# FILE TAIL & DEDUPE
# =========================
SKIP_HISTORY_ON_START = True
POLL_INTERVAL_SEC     = 0.5

file_positions: dict[str, int] = {}
LINE_DEDUPE_TTL_SEC = 45
_last_lines_cache: dict[str, float] = {}

def _now() -> float: return time.time()
def _hash(s: str) -> str: return hashlib.sha1(s.encode("utf-8")).hexdigest()

def _normalize_quotes_spaces(s: str) -> str:
    s = s.replace("‘", "'").replace("’", "'").replace("´", "'").replace("`", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("\r", " ").replace("\n", " ")
    s = s.replace("..", ".").replace("::", ":").replace(" ,", ", ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def should_emit_line(line: str) -> bool:
    now = _now()
    for k, ts in list(_last_lines_cache.items()):
        if now - ts > LINE_DEDUPE_TTL_SEC:
            _last_lines_cache.pop(k, None)
    h = _hash(line)
    if h in _last_lines_cache:
        return False
    _last_lines_cache[h] = now
    return True

def prime_file_offsets(skip_history: bool):
    for p in (tribemembers_log_path, players_log_path, center_log_path):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if not os.path.exists(p):
                with open(p, 'w', encoding='utf-8'):
                    pass
            file_positions[p] = os.path.getsize(p) if skip_history else 0
            print(f"[BOT] Init offset for {p} -> {file_positions[p]}")
        except Exception as e:
            print(f"[BOT] prime_file_offsets error for {p}: {e}")
            file_positions[p] = 0

# =========================
# CENTER LINE DEDUPE
# =========================
RE_CENTER_TS = re.compile(r"Day\s+(\d+),\s+(\d{2})[.:](\d{2})[.:](\d{2})", re.IGNORECASE)
RE_OBJ_ACT   = re.compile(r"Your\s+['\"]?(.+?)['\"]?\s+was\s+(destroyed|demolished|killed)\b", re.IGNORECASE)

_seen_by_ts: dict[str, list[tuple[str, str]]] = defaultdict(list)
SIM_OBJ = 0.90

def _center_ts_key(line: str) -> str | None:
    m = RE_CENTER_TS.search(line)
    if not m:
        return None
    day, hh, mm, ss = m.groups()
    return f"{int(day)}-{hh}:{mm}:{ss}"

def _canon_obj(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.replace("‘","'").replace("’","'").replace("`","'").replace("´","'")
    s = s.replace("“",'"').replace("”",'"')
    s = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s)
    return " ".join(s.split())

def _parse_obj_action(line: str) -> tuple[str | None, str | None]:
    m = RE_OBJ_ACT.search(line)
    if not m:
        return None, None
    obj, act = m.group(1), m.group(2).lower()
    return _canon_obj(obj), act

def should_post_center_line(line: str) -> bool:
    ts = _center_ts_key(line)
    if not ts:
        return True
    obj, act = _parse_obj_action(line)
    if obj is None or act is None:
        return True
    for prev_obj, prev_act in _seen_by_ts.get(ts, []):
        if prev_act == act and difflib.SequenceMatcher(a=obj, b=prev_obj).ratio() >= SIM_OBJ:
            return False
    _seen_by_ts[ts].append((obj, act))
    if len(_seen_by_ts[ts]) > 6:
        _seen_by_ts[ts] = _seen_by_ts[ts][-6:]
    return True

# =========================
# VOICE MANAGER
# =========================
_voice_lock = asyncio.Lock()
_voice_task: asyncio.Task | None = None
_stop_voice_task = asyncio.Event()

def _ffmpeg_src(path: str):
    if not FFMPEG_EXEC:
        raise RuntimeError("FFmpeg introuvable (définis FFMPEG_PATH ou ajoute ffmpeg au PATH).")
    try:
        return discord.FFmpegOpusAudio(path, executable=FFMPEG_EXEC)
    except Exception as e:
        print(f"[VOICE] FFmpegOpusAudio indisponible ({e}), fallback PCM…")
        return discord.FFmpegPCMAudio(path, executable=FFMPEG_EXEC)

async def _connect_once() -> discord.VoiceClient | None:
    """One-shot connect guarded by _voice_lock."""
    async with _voice_lock:
        if not client.guilds:
            print("[VOICE] Pas de guilds.")
            return None
        guild = client.guilds[0]
        target = guild.get_channel(voice_channel_id)
        if not target:
            print(f"[VOICE] Salon vocal introuvable: {voice_channel_id}")
            return None
        vc = guild.voice_client
        if vc and vc.is_connected():
            if vc.channel.id != voice_channel_id:
                print(f"[VOICE] Déplacement vocal {vc.channel.name} -> {target.name}")
                await vc.move_to(target)
            return guild.voice_client
        try:
            print(f"[VOICE] Connexion au salon: {target.name}")
            vc = await target.connect(timeout=15.0, reconnect=False)
            print(f"[VOICE] Connecté à: {target.name}")
            return vc
        except discord.ClientException as e:
            print(f"[VOICE] ClientException: {e}")
            return guild.voice_client
        except Exception as e:
            print(f"[VOICE] Connexion échouée: {type(e).__name__}: {e}")
            return None

async def _voice_keeper():
    """Keeps the voice connection alive, with backoff on failures."""
    backoff = 1.0
    while not _stop_voice_task.is_set():
        vc = await _connect_once()
        if vc and vc.is_connected():
            backoff = 1.0
            for _ in range(10):
                if _stop_voice_task.is_set():
                    break
                await asyncio.sleep(1.5)
        else:
            print(f"[VOICE] Reconnexion dans {backoff:.1f}s…")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, 15.0)

def start_voice_keeper():
    global _voice_task
    if _voice_task is None or _voice_task.done():
        _stop_voice_task.clear()
        _voice_task = asyncio.create_task(_voice_keeper())

def stop_voice_keeper():
    _stop_voice_task.set()
    if _voice_task:
        _voice_task.cancel()

_audio_lock = asyncio.Lock()
_last_audio = 0.0
AUDIO_COOLDOWN_SEC = 15

async def play_alert_audio():
    """Plays alert without initiating a new connect storm."""
    global _last_audio
    async with _audio_lock:
        now = asyncio.get_running_loop().time()
        if now - _last_audio < AUDIO_COOLDOWN_SEC:
            print("[VOICE] Cooldown audio -> skip")
            return
        _last_audio = now

        if not os.path.exists(audio_file_path):
            print(f"[VOICE] Fichier audio introuvable: {audio_file_path}")
            return

        if not client.guilds:
            print("[VOICE] Pas de guilds.")
            return
        guild = client.guilds[0]
        vc = guild.voice_client
        if not (vc and vc.is_connected()):
            print("[VOICE] Pas de voice client (pas connecté).")
            return

        try:
            if vc.is_playing():
                vc.stop()
            src = _ffmpeg_src(audio_file_path)
            vc.play(src, after=lambda e: print("[VOICE] Lecture OK" if e is None else f"[VOICE] Erreur lecture: {e}"))
            print("[VOICE] Lecture démarrée.")
        except Exception as e:
            print(f"[VOICE] Lecture échouée: {type(e).__name__}: {e}")

def schedule_audio():
    try:
        asyncio.get_running_loop().create_task(play_alert_audio())
    except RuntimeError:
        pass

# =========================
# COMMANDS TEST
# =========================
@client.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    cmd = msg.content.strip().lower()
    if cmd == "!beep":
        await msg.channel.send("🔊 Test audio…")
        schedule_audio()
    elif cmd == "!join":
        await msg.channel.send("🔁 Forcing voice keeper reconnect…")
        stop_voice_keeper()
        await asyncio.sleep(0.1)
        start_voice_keeper()
    elif cmd == "!leave":
        g = msg.guild
        if g and g.voice_client:
            await g.voice_client.disconnect(force=True)
            await msg.channel.send("👋 Disconnected.")
        else:
            await msg.channel.send("ℹ️ Not connected.")

# =========================
# FILE MONITOR LOOP
# =========================
async def monitor_logs():
    print("[BOT] Watching:",
          os.path.abspath(tribemembers_log_path),
          os.path.abspath(players_log_path),
          os.path.abspath(center_log_path))
    while True:
        await check_for_new_log_entries()
        await asyncio.sleep(POLL_INTERVAL_SEC)

async def check_for_new_log_entries():
    await tail_and_send(tribemembers_log_path, tribemembers_channel_id, is_center=False)
    await tail_and_send(players_log_path,      players_channel_id,      is_center=False)
    await tail_and_send(center_log_path,       center_channel_id,       is_center=True)

async def tail_and_send(log_path: str, channel_id: int, is_center: bool):
    try:
        if not os.path.exists(log_path):
            return
        current_size = os.path.getsize(log_path)
        last_pos = file_positions.get(log_path, 0)
        if current_size < last_pos:
            last_pos = 0
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_pos)
            data = f.read()
            file_positions[log_path] = f.tell()
        if not data:
            return
        for raw in (ln for ln in data.splitlines() if ln.strip()):
            line = _normalize_quotes_spaces(raw)
            if is_center:
                if not should_post_center_line(line):
                    continue
                await handle_log_line(line, channel_id, is_center=True)
            else:
                if not should_emit_line(line):
                    continue
                await handle_log_line(line, channel_id, is_center=False)
    except Exception as e:
        print(f"[BOT] ERROR reading {log_path}: {type(e).__name__}: {e}")

async def handle_log_line(line: str, channel_id: int, is_center: bool):
    channel = client.get_channel(channel_id)
    if channel is None:
        print(f"[BOT] Canal {channel_id} introuvable.")
        return
    try:
        await channel.send(line)
        print(f"[SEND] -> {channel_id} : {line}")
        if is_center and "destroyed" in line.lower():
            await channel.send("@everyone **We are under attack! DEFEND!**")
            schedule_audio()
    except Exception as e:
        print(f"[BOT] Envoi échoué {channel_id}: {type(e).__name__}: {e}")

# =========================
# EVENTS
# =========================
@client.event
async def on_ready():
    print(f"Connecté en tant que {client.user} (guilds={len(client.guilds)})")
    prime_file_offsets(SKIP_HISTORY_ON_START)
    start_voice_keeper()
    asyncio.create_task(monitor_logs())

# =========================
# ENTRYPOINT
# =========================
def main():
    TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your bot token or use environment variable
    print("[BOT] Starting client.run()")
    client.run(TOKEN)
