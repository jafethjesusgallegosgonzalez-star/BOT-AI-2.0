# ================================================================
# BOT AI DISCORD - PROFESSIONAL HIGH PERFORMANCE EDITION
# ================================================================
# Versión: 4.0.0
# Python: 3.11+
# Discord.py: 2.x
#
# Características principales:
# - Arquitectura modular dentro de un solo archivo.
# - SQLite asíncrono mediante asyncio.to_thread.
# - Sistema de configuración por servidor.
# - Moderación avanzada.
# - Anti-spam.
# - Sistema de niveles y XP.
# - Economía.
# - Sistema de advertencias.
# - Sistema de tickets.
# - Encuestas.
# - Sugerencias.
# - Recordatorios.
# - AFK.
# - Bienvenidas y despedidas.
# - Auto roles.
# - Logs.
# - Sistema de IA para clasificación de imágenes.
# - Compatible con modelos de Google Teachable Machine/Keras.
# - Comandos de utilidad.
# - Comandos de entretenimiento.
# - Sistema de estadísticas.
# - Manejo avanzado de errores.
# - Cooldowns.
# - Caché.
# - Health check.
# - Métricas.
# - Seguridad básica.
# - Paneles interactivos.
# - Botones y modales.
# - Persistencia de datos.
# - Preparado para crecer.
#
# IMPORTANTE:
# Guarda el token en la variable de entorno DISCORD_TOKEN.
# Nunca publiques tu token.
# ================================================================


# ================================================================
# 001. IMPORTACIONES
# ================================================================

import os
import re
import io
import ast
import math
import json
import time
import uuid
import random
import asyncio
import logging
import sqlite3
import platform
import traceback
import operator
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from collections import defaultdict
from collections import deque
from typing import Optional
from typing import Any
from typing import Union
from typing import Callable


# ================================================================
# 002. IMPORTACIONES DE DISCORD
# ================================================================

import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands


# ================================================================
# 003. IMPORTACIONES HTTP
# ================================================================

import aiohttp


# ================================================================
# 004. IMPORTACIONES OPCIONALES DE IMÁGENES
# ================================================================

try:
    from PIL import Image
    from PIL import ImageOps
except ImportError:
    Image = None
    ImageOps = None


# ================================================================
# 005. IMPORTACIONES OPCIONALES DE NUMPY
# ================================================================

try:
    import numpy as np
except ImportError:
    np = None


# ================================================================
# 006. IMPORTACIONES OPCIONALES DE KERAS
# ================================================================

try:
    from keras.models import load_model
except ImportError:
    load_model = None


# ================================================================
# 007. CONFIGURACIÓN PRINCIPAL
# ================================================================

class Config:
    BOT_NAME = "BOT AI"
    VERSION = "4.0.0"
    PREFIX = "$"

    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    MODEL_DIR = BASE_DIR / "model"
    IMAGE_DIR = BASE_DIR / "images"
    LOG_DIR = BASE_DIR / "logs"

    DATABASE_PATH = DATA_DIR / "bot.db"

    MODEL_PATH = MODEL_DIR / "keras_model.h5"
    LABELS_PATH = MODEL_DIR / "labels.txt"

    MAX_IMAGE_SIZE = 8 * 1024 * 1024
    IMAGE_SIZE = (224, 224)

    HTTP_TIMEOUT = 12
    CACHE_TTL = 300

    XP_MIN = 5
    XP_MAX = 15

    XP_COOLDOWN = 60

    SPAM_LIMIT = 6
    SPAM_WINDOW = 8

    MAX_COMMANDS_PER_PAGE = 8

    DEFAULT_COLOR = 0x5865F2
    SUCCESS_COLOR = 0x57F287
    ERROR_COLOR = 0xED4245
    WARNING_COLOR = 0xFEE75C
    INFO_COLOR = 0x5865F2

    TOKEN = os.getenv("DISCORD_TOKEN")

    @classmethod
    def initialize(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        cls.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)


# ================================================================
# 008. INICIALIZACIÓN
# ================================================================

Config.initialize()


# ================================================================
# 009. LOGGING
# ================================================================

LOG_FILE = Config.LOG_DIR / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("BOT_AI")


# ================================================================
# 010. UTILIDADES GENERALES
# ================================================================

def utc_now():
    return datetime.now(timezone.utc)


def unix_now():
    return int(time.time())


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def truncate(text, length=1000):
    if text is None:
        return ""
    text = str(text)
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


def format_seconds(seconds):
    seconds = int(max(0, seconds))

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def format_number(number):
    return f"{number:,}"


def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def get_display_name(member):
    return getattr(member, "display_name", str(member))


def get_avatar_url(user):
    avatar = getattr(user, "display_avatar", None)
    if avatar:
        return str(avatar.url)
    return None


def is_image_attachment(attachment):
    content_type = attachment.content_type or ""

    if content_type.startswith("image/"):
        return True

    extension = Path(attachment.filename).suffix.lower()

    return extension in {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif"
    }


def parse_duration(value):
    if not value:
        return None

    value = value.lower().strip()

    pattern = r"^(\d+)\s*(s|sec|secs|seg|m|min|mins|h|hr|hrs|d|day|days|w|week|weeks)$"

    match = re.match(pattern, value)

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "sec": 1,
        "secs": 1,
        "seg": 1,
        "m": 60,
        "min": 60,
        "mins": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800
    }

    return amount * multipliers[unit]


def parse_duration_text(text):
    pattern = r"(\d+)\s*(s|sec|secs|seg|min|mins|m|h|hr|hrs|d|day|days|w|week|weeks)"

    matches = re.findall(pattern, text.lower())

    if not matches:
        return None

    total = 0

    multipliers = {
        "s": 1,
        "sec": 1,
        "secs": 1,
        "seg": 1,
        "m": 60,
        "min": 60,
        "mins": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800
    }

    for amount, unit in matches:
        total += int(amount) * multipliers[unit]

    return total


# ================================================================
# 011. EMBEDS
# ================================================================

def make_embed(
    title,
    description="",
    color=Config.DEFAULT_COLOR,
    footer=True
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=utc_now()
    )

    if footer:
        embed.set_footer(
            text=f"{Config.BOT_NAME} v{Config.VERSION}"
        )

    return embed


def success_embed(title, description):
    return make_embed(
        title,
        description,
        Config.SUCCESS_COLOR
    )


def error_embed(title, description):
    return make_embed(
        title,
        description,
        Config.ERROR_COLOR
    )


def warning_embed(title, description):
    return make_embed(
        title,
        description,
        Config.WARNING_COLOR
    )


def info_embed(title, description):
    return make_embed(
        title,
        description,
        Config.INFO_COLOR
    )


# ================================================================
# 012. PAGINACIÓN
# ================================================================

class PaginationView(discord.ui.View):

    def __init__(self, pages, timeout=120):
        super().__init__(timeout=timeout)

        self.pages = pages
        self.index = 0

    async def update(self, interaction):
        await interaction.response.edit_message(
            embed=self.pages[self.index],
            view=self
        )

    @discord.ui.button(
        label="◀",
        style=discord.ButtonStyle.secondary
    )
    async def previous(self, interaction, button):
        if self.index > 0:
            self.index -= 1

        await self.update(interaction)

    @discord.ui.button(
        label="▶",
        style=discord.ButtonStyle.secondary
    )
    async def next(self, interaction, button):
        if self.index < len(self.pages) - 1:
            self.index += 1

        await self.update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ================================================================
# 013. CONFIRMACIÓN
# ================================================================

class ConfirmView(discord.ui.View):

    def __init__(self, author_id, timeout=30):
        super().__init__(timeout=timeout)

        self.author_id = author_id
        self.result = None

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "No puedes utilizar estos botones.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Confirmar",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction, button):
        self.result = True

        await interaction.response.edit_message(
            content="Acción confirmada.",
            view=None
        )

        self.stop()

    @discord.ui.button(
        label="Cancelar",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(self, interaction, button):
        self.result = False

        await interaction.response.edit_message(
            content="Acción cancelada.",
            view=None
        )

        self.stop()


# ================================================================
# 014. BASE DE DATOS
# ================================================================

class Database:

    def __init__(self, path):
        self.path = str(path)

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _execute(self, query, params=()):
        connection = self._connect()

        try:
            cursor = connection.execute(query, params)
            connection.commit()
            return cursor.lastrowid
        finally:
            connection.close()

    def _fetchone(self, query, params=()):
        connection = self._connect()

        try:
            cursor = connection.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def _fetchall(self, query, params=()):
        connection = self._connect()

        try:
            cursor = connection.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    async def execute(self, query, params=()):
        return await asyncio.to_thread(
            self._execute,
            query,
            params
        )

    async def fetchone(self, query, params=()):
        return await asyncio.to_thread(
            self._fetchone,
            query,
            params
        )

    async def fetchall(self, query, params=()):
        return await asyncio.to_thread(
            self._fetchall,
            query,
            params
        )

    async def initialize(self):
        await self.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '$',
                log_channel INTEGER,
                welcome_channel INTEGER,
                leave_channel INTEGER,
                welcome_message TEXT,
                leave_message TEXT,
                autorole INTEGER,
                level_channel INTEGER,
                modlog_channel INTEGER,
                anti_spam INTEGER DEFAULT 1,
                anti_links INTEGER DEFAULT 0,
                auto_mod INTEGER DEFAULT 1
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                created_at INTEGER NOT NULL
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                balance INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0,
                last_work INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS xp (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER,
                message TEXT NOT NULL,
                execute_at INTEGER NOT NULL
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS afk (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(guild_id, user_id)
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                closed INTEGER DEFAULT 0
            )
        """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at INTEGER NOT NULL
            """)

        await self.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                commands INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                images INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            )
        """)

    async def ensure_guild(self, guild_id):
        await self.execute("""
            INSERT OR IGNORE INTO guild_settings(guild_id)
            VALUES(?)
        """, (guild_id,))

    async def get_guild(self, guild_id):
        await self.ensure_guild(guild_id)

        return await self.fetchone("""
            SELECT *
            FROM guild_settings
            WHERE guild_id = ?
        """, (guild_id,))

    async def set_guild_value(self, guild_id, key, value):
        allowed = {
            "prefix",
            "log_channel",
            "welcome_channel",
            "leave_channel",
            "welcome_message",
            "leave_message",
            "autorole",
            "level_channel",
            "modlog_channel",
            "anti_spam",
            "anti_links",
            "auto_mod"
        }

        if key not in allowed:
            raise ValueError("Configuración no permitida.")

        await self.ensure_guild(guild_id)

        query = f"""
            UPDATE guild_settings
            SET {key} = ?
            WHERE guild_id = ?
        """

        await self.execute(query, (value, guild_id))

    async def add_warning(
        self,
        guild_id,
        user_id,
        moderator_id,
        reason
    ):
        return await self.execute("""
            INSERT INTO warnings(
                guild_id,
                user_id,
                moderator_id,
                reason,
                created_at
            )
            VALUES(?, ?, ?, ?, ?)
        """, (
            guild_id,
            user_id,
            moderator_id,
            reason,
            unix_now()
        ))

    async def get_warnings(self, guild_id, user_id):
        return await self.fetchall("""
            SELECT *
            FROM warnings
            WHERE guild_id = ?
            AND user_id = ?
            ORDER BY id DESC
        """, (guild_id, user_id))

    async def clear_warnings(self, guild_id, user_id):
        await self.execute("""
            DELETE FROM warnings
            WHERE guild_id = ?
            AND user_id = ?
        """, (guild_id, user_id))

    async def ensure_economy(self, guild_id, user_id):
        await self.execute("""
            INSERT OR IGNORE INTO economy(
                guild_id,
                user_id
            )
            VALUES(?, ?)
        """, (guild_id, user_id))

    async def get_balance(self, guild_id, user_id):
        await self.ensure_economy(guild_id, user_id)

        row = await self.fetchone("""
            SELECT *
            FROM economy
            WHERE guild_id = ?
            AND user_id = ?
        """, (guild_id, user_id))

        return row

    async def change_balance(self, guild_id, user_id, amount):
        await self.ensure_economy(guild_id, user_id)

        await self.execute("""
            UPDATE economy
            SET balance = balance + ?
            WHERE guild_id = ?
            AND user_id = ?
        """, (amount, guild_id, user_id))

    async def set_balance(self, guild_id, user_id, amount):
        await self.ensure_economy(guild_id, user_id)

        await self.execute("""
            UPDATE economy
            SET balance = ?
            WHERE guild_id = ?
            AND user_id = ?
        """, (amount, guild_id, user_id))

    async def set_daily(self, guild_id, user_id, timestamp):
        await self.ensure_economy(guild_id, user_id)

        await self.execute("""
            UPDATE economy
            SET last_daily = ?
            WHERE guild_id = ?
            AND user_id = ?
        """, (timestamp, guild_id, user_id))

    async def set_work(self, guild_id, user_id, timestamp):
        await self.ensure_economy(guild_id, user_id)

        await self.execute("""
            UPDATE economy
            SET last_work = ?
            WHERE guild_id = ?
            AND user_id = ?
        """, (timestamp, guild_id, user_id))

    async def economy_leaderboard(self, guild_id, limit=10):
        return await self.fetchall("""
            SELECT user_id, balance
            FROM economy
            WHERE guild_id = ?
            ORDER BY balance DESC
            LIMIT ?
        """, (guild_id, limit))

    async def ensure_xp(self, guild_id, user_id):
        await self.execute("""
            INSERT OR IGNORE INTO xp(
                guild_id,
                user_id
            )
            VALUES(?, ?)
        """, (guild_id, user_id))

    async def get_xp(self, guild_id, user_id):
        await self.ensure_xp(guild_id, user_id)

        return await self.fetchone("""
            SELECT *
            FROM xp
            WHERE guild_id = ?
            AND user_id = ?
        """, (guild_id, user_id))

    async def add_xp(self, guild_id, user_id, amount):
        await self.ensure_xp(guild_id, user_id)

        row = await self.get_xp(guild_id, user_id)

        old_level = row["level"]

        new_xp = row["xp"] + amount
        new_level = int(math.sqrt(new_xp / 100))

        await self.execute("""
            UPDATE xp
            SET xp = ?,
                level = ?,
                messages = messages + 1
            WHERE guild_id = ?
            AND user_id = ?
        """, (
            new_xp,
            new_level,
            guild_id,
            user_id
        ))

        return old_level, new_level

    async def xp_leaderboard(self, guild_id, limit=10):
        return await self.fetchall("""
            SELECT user_id, xp, level, messages
            FROM xp
            WHERE guild_id = ?
            ORDER BY xp DESC
            LIMIT ?
        """, (guild_id, limit))

    async def add_reminder(
        self,
        user_id,
        channel_id,
        guild_id,
        message,
        execute_at
    ):
        return await self.execute("""
            INSERT INTO reminders(
                user_id,
                channel_id,
                guild_id,
                message,
                execute_at
            )
            VALUES(?, ?, ?, ?, ?)
        """, (
            user_id,
            channel_id,
            guild_id,
            message,
            execute_at
        ))

    async def get_due_reminders(self):
        return await self.fetchall("""
            SELECT *
            FROM reminders
            WHERE execute_at <= ?
            ORDER BY execute_at ASC
        """, (unix_now(),))

    async def delete_reminder(self, reminder_id):
        await self.execute("""
            DELETE FROM reminders
            WHERE id = ?
        """, (reminder_id,))

    async def set_afk(self, guild_id, user_id, reason):
        await self.execute("""
            INSERT INTO afk(
                guild_id,
                user_id,
                reason,
                created_at
            )
            VALUES(?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                reason = excluded.reason,
                created_at = excluded.created_at
        """, (
            guild_id,
            user_id,
            reason,
            unix_now()
        ))

    async def get_afk(self, guild_id, user_id):
        return await self.fetchone("""
            SELECT *
            FROM afk
            WHERE guild_id = ?
            AND user_id = ?
        """, (guild_id, user_id))

    async def remove_afk(self, guild_id, user_id):
        await self.execute("""
            DELETE FROM afk
            WHERE guild_id = ?
            AND user_id = ?
        """, (guild_id, user_id))

    async def add_ticket(
        self,
        guild_id,
        channel_id,
        owner_id
    ):
        return await self.execute("""
            INSERT INTO tickets(
                guild_id,
                channel_id,
                owner_id,
                created_at
            )
            VALUES(?, ?, ?, ?)
        """, (
            guild_id,
            channel_id,
            owner_id,
            unix_now()
        ))

    async def get_ticket_by_owner(self, guild_id, owner_id):
        return await self.fetchone("""
            SELECT *
            FROM tickets
            WHERE guild_id = ?
            AND owner_id = ?
            AND closed = 0
            ORDER BY id DESC
            LIMIT 1
        """, (guild_id, owner_id))

    async def close_ticket(self, channel_id):
        await self.execute("""
            UPDATE tickets
            SET closed = 1
            WHERE channel_id = ?
        """, (channel_id,))

    async def add_suggestion(
        self,
        guild_id,
        user_id,
        content
    ):
        return await self.execute("""
            INSERT INTO suggestions(
                guild_id,
                user_id,
                content,
                created_at
            )
            VALUES(?, ?, ?, ?)
        """, (
            guild_id,
            user_id,
            content,
            unix_now()
        ))

    async def increment_stat(
        self,
        guild_id,
        user_id,
        field
    ):
        allowed = {
            "commands",
            "messages",
            "images"
        }

        if field not in allowed:
            return

        await self.execute("""
            INSERT OR IGNORE INTO stats(
                guild_id,
                user_id
            )
            VALUES(?, ?)
        """, (guild_id, user_id))

        await self.execute(
            f"""
            UPDATE stats
            SET {field} = {field} + 1
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (guild_id, user_id)
        )


# ================================================================
# 015. CACHÉ
# ================================================================

class TTLCache:

    def __init__(self, ttl=300):
        self.ttl = ttl
        self.data = {}

    def get(self, key):
        item = self.data.get(key)

        if not item:
            return None

        value, expires = item

        if time.monotonic() >= expires:
            self.data.pop(key, None)
            return None

        return value

    def set(self, key, value, ttl=None):
        duration = ttl if ttl is not None else self.ttl

        self.data[key] = (
            value,
            time.monotonic() + duration
        )

    def delete(self, key):
        self.data.pop(key, None)

    def clear(self):
        self.data.clear()

    def __len__(self):
        return len(self.data)


# ================================================================
# 016. CLASIFICADOR DE IMÁGENES
# ================================================================

class ImageClassifier:

    def __init__(self):
        self.model = None
        self.labels = []
        self.loaded = False
        self.error = None
        self.last_loaded = None

    def normalize_label(self, label):
        label = label.strip()

        match = re.match(
            r"^\d+\s+(.+)$",
            label
        )

        if match:
            return match.group(1).strip()

        return label

    def load(self):
        self.loaded = False
        self.error = None

        if load_model is None:
            self.error = "Keras no está instalado."
            return False

        if np is None:
            self.error = "NumPy no está instalado."
            return False

        if Image is None:
            self.error = "Pillow no está instalado."
            return False

        if not Config.MODEL_PATH.exists():
            self.error = "No se encontró keras_model.h5."
            return False

        if not Config.LABELS_PATH.exists():
            self.error = "No se encontró labels.txt."
            return False

        try:
            self.model = load_model(
                Config.MODEL_PATH,
                compile=False
            )

            raw_labels = Config.LABELS_PATH.read_text(
                encoding="utf-8"
            ).splitlines()

            self.labels = [
                self.normalize_label(label)
                for label in raw_labels
                if label.strip()
            ]

            self.loaded = True
            self.last_loaded = utc_now()

            logger.info(
                "Modelo de IA cargado correctamente."
            )

            return True

        except Exception as exc:
            self.error = str(exc)

            logger.exception(
                "Error cargando el modelo."
            )

            return False

    def preprocess(self, image_bytes):
        image = Image.open(
            io.BytesIO(image_bytes)
        )

        image = image.convert("RGB")

        image = ImageOps.fit(
            image,
            Config.IMAGE_SIZE,
            Image.Resampling.LANCZOS
        )

        array = np.asarray(image).astype(
            np.float32
        )

        array = array / 255.0

        array = np.expand_dims(
            array,
            axis=0
        )

        return array

    def normalize_predictions(self, predictions):
        values = np.asarray(
            predictions,
            dtype=np.float32
        ).flatten()

        if values.size == 0:
            return values

        if (
            np.any(values < 0)
            or np.sum(values) <= 0
            or abs(np.sum(values) - 1) > 0.05
        ):
            shifted = values - np.max(values)
            exp_values = np.exp(shifted)
            values = exp_values / np.sum(exp_values)

        return values

    def predict(self, image_bytes, top_k=3):
        if not self.loaded:
            raise RuntimeError(
                self.error or "Modelo no disponible."
            )

        array = self.preprocess(image_bytes)

        predictions = self.model.predict(
            array,
            verbose=0
        )

        predictions = self.normalize_predictions(
            predictions
        )

        indexes = np.argsort(
            predictions
        )[::-1][:top_k]

        results = []

        for index in indexes:
            index = int(index)

            if index < len(self.labels):
                label = self.labels[index]
            else:
                label = f"Clase {index}"

            confidence = float(
                predictions[index]
            ) * 100

            results.append({
                "label": label,
                "confidence": confidence
            })

        return results

    def model_info(self):
        if not self.loaded:
            return {
                "loaded": False,
                "error": self.error
            }

        try:
            input_shape = self.model.input_shape
        except Exception:
            input_shape = "Desconocido"

        try:
            output_shape = self.model.output_shape
        except Exception:
            output_shape = "Desconocido"

        return {
            "loaded": True,
            "labels": len(self.labels),
            "input_shape": str(input_shape),
            "output_shape": str(output_shape),
            "loaded_at": (
                self.last_loaded.isoformat()
                if self.last_loaded
                else None
            )
        }


# ================================================================
# 017. CLIENTE HTTP
# ================================================================

class HTTPClient:

    def __init__(self):
        self.session = None

    async def start(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(
                total=Config.HTTP_TIMEOUT
            )

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent":
                    f"{Config.BOT_NAME}/{Config.VERSION}"
                }
            )

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def get_json(self, url):
        if not self.session:
            await self.start()

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None

                return await response.json()

        except Exception as exc:
            logger.warning(
                "HTTP error: %s",
                exc
            )

            return None

    async def get_bytes(self, url):
        if not self.session:
            await self.start()

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None

                return await response.read()

        except Exception:
            return None


# ================================================================
# 018. ASISTENTE LOCAL
# ================================================================

class SmartAssistant:

    def __init__(self):
        self.responses = {
            "hola": [
                "Hola. ¿En qué puedo ayudarte?",
                "Hola. Estoy listo para ayudarte.",
                "Buenas. ¿Qué necesitas?"
            ],
            "gracias": [
                "De nada.",
                "Con gusto.",
                "Para eso estoy."
            ],
            "adios": [
                "Hasta luego.",
                "Nos vemos.",
                "Que tengas un buen día."
            ],
            "ayuda": [
                "Usa `$help` para ver los comandos disponibles.",
                "Puedes escribir `$help` para consultar el sistema."
            ]
        }

    def respond(self, text):
        normalized = text.lower().strip()

        for keyword, responses in self.responses.items():
            if keyword in normalized:
                return random.choice(responses)

        return (
            "No tengo una respuesta específica para eso. "
            "Prueba `$help` para ver mis funciones."
        )


# ================================================================
# 019. MOTOR DE CÁLCULO SEGURO
# ================================================================

class SafeCalculator:

    ALLOWED_BINOPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow
    }

    ALLOWED_UNARYOPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg
    }

    ALLOWED_FUNCTIONS = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log10,
        "ln": math.log,
        "abs": abs,
        "round": round
    }

    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e
    }

    @classmethod
    def evaluate(cls, expression):
        expression = expression.replace("^", "**")

        tree = ast.parse(
            expression,
            mode="eval"
        )

        return cls._evaluate_node(
            tree.body
        )

    @classmethod
    def _evaluate_node(cls, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError(
                "Valor no permitido."
            )

        if isinstance(node, ast.BinOp):
            operation = cls.ALLOWED_BINOPS.get(
                type(node.op)
            )

            if operation is None:
                raise ValueError(
                    "Operador no permitido."
                )

            left = cls._evaluate_node(
                node.left
            )

            right = cls._evaluate_node(
                node.right
            )

            if abs(right) > 10**6:
                raise ValueError(
                    "Número demasiado grande."
                )

            result = operation(
                left,
                right
            )

            if abs(result) > 10**100:
                raise ValueError(
                    "Resultado demasiado grande."
                )

            return result

        if isinstance(node, ast.UnaryOp):
            operation = cls.ALLOWED_UNARYOPS.get(
                type(node.op)
            )

            if operation is None:
                raise ValueError(
                    "Operador no permitido."
                )

            return operation(
                cls._evaluate_node(node.operand)
            )

        if isinstance(node, ast.Call):
            if not isinstance(
                node.func,
                ast.Name
            ):
                raise ValueError(
                    "Función no permitida."
                )

            function = cls.ALLOWED_FUNCTIONS.get(
                node.func.id
            )

            if function is None:
                raise ValueError(
                    "Función no permitida."
                )

            arguments = [
                cls._evaluate_node(argument)
                for argument in node.args
            ]

            return function(*arguments)

        if isinstance(node, ast.Name):
            if node.id in cls.ALLOWED_CONSTANTS:
                return cls.ALLOWED_CONSTANTS[node.id]

        raise ValueError(
            "Expresión no permitida."
        )


# ================================================================
# 020. CONTROL DE SPAM
# ================================================================

class SpamManager:

    def __init__(self):
        self.messages = defaultdict(deque)

    def register(self, guild_id, user_id):
        key = (guild_id, user_id)

        now = time.monotonic()

        queue = self.messages[key]

        queue.append(now)

        while queue and now - queue[0] > Config.SPAM_WINDOW:
            queue.popleft()

        return len(queue)

    def clear(self, guild_id, user_id):
        self.messages.pop(
            (guild_id, user_id),
            None
        )

    def cleanup(self):
        now = time.monotonic()

        expired = []

        for key, queue in self.messages.items():
            while queue and now - queue[0] > Config.SPAM_WINDOW:
                queue.popleft()

            if not queue:
                expired.append(key)

        for key in expired:
            self.messages.pop(key, None)


# ================================================================
# 021. XP MANAGER
# ================================================================

class XPManager:

    def __init__(self):
        self.cooldowns = {}

    def can_gain(self, guild_id, user_id):
        key = (guild_id, user_id)

        now = time.monotonic()

        last = self.cooldowns.get(
            key,
            0
        )

        if now - last < Config.XP_COOLDOWN:
            return False

        self.cooldowns[key] = now

        return True

    def random_xp(self):
        return random.randint(
            Config.XP_MIN,
            Config.XP_MAX
        )

    def cleanup(self):
        now = time.monotonic()

        expired = [
            key
            for key, value in self.cooldowns.items()
            if now - value > Config.XP_COOLDOWN * 5
        ]

        for key in expired:
            self.cooldowns.pop(key, None)


# ================================================================
# 022. BOT PRINCIPAL
# ================================================================

class ProfessionalBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()

        intents.message_content = True
        intents.members = True
        intents.presences = True
        intents.guilds = True
        intents.messages = True
        intents.reactions = True

        super().__init__(
            command_prefix=self.dynamic_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True
        )

        self.db = Database(
            Config.DATABASE_PATH
        )

        self.http = HTTPClient()

        self.classifier = ImageClassifier()

        self.assistant = SmartAssistant()

        self.spam = SpamManager()

        self.xp_manager = XPManager()

        self.cache = TTLCache(
            Config.CACHE_TTL
        )

        self.start_time = utc_now()

        self.ready_once = False

        self.command_counter = 0

        self.message_counter = 0

        self.image_counter = 0

        self.reminder_task = None

        self.maintenance_task = None

    async def dynamic_prefix(
        self,
        bot,
        message
    ):
        if not message.guild:
            return Config.PREFIX

        try:
            settings = await self.db.get_guild(
                message.guild.id
            )

            return settings["prefix"] or Config.PREFIX

        except Exception:
            return Config.PREFIX

    async def setup_hook(self):
        logger.info(
            "Inicializando base de datos..."
        )

        await self.db.initialize()

        logger.info(
            "Inicializando cliente HTTP..."
        )

        await self.http.start()

        logger.info(
            "Cargando modelo de IA..."
        )

        self.classifier.load()

        self.add_view(
            TicketPanelView(self)
        )

        self.reminder_task = self.reminder_loop.start()

        self.maintenance_task = self.maintenance_loop.start()

        try:
            await self.tree.sync()

            logger.info(
                "Comandos slash sincronizados."
            )

        except Exception:
            logger.exception(
                "No se pudieron sincronizar los comandos slash."
            )

    async def close(self):
        logger.info(
            "Cerrando BOT AI..."
        )

        if self.reminder_task:
            self.reminder_loop.cancel()

        if self.maintenance_task:
            self.maintenance_loop.cancel()

        await self.http.close()

        await super().close()

    async def send_log(
        self,
        guild,
        title,
        description,
        color=Config.INFO_COLOR
    ):
        if not guild:
            return

        try:
            settings = await self.db.get_guild(
                guild.id
            )

            channel_id = (
                settings["log_channel"]
                or settings["modlog_channel"]
            )

            if not channel_id:
                return

            channel = guild.get_channel(
                channel_id
            )

            if not channel:
                return

            embed = make_embed(
                title,
                description,
                color
            )

            await channel.send(
                embed=embed
            )

        except Exception as exc:
            logger.warning(
                "No se pudo enviar log: %s",
                exc
            )

    async def send_modlog(
        self,
        guild,
        title,
        description,
        color=Config.WARNING_COLOR
    ):
        await self.send_log(
            guild,
            title,
            description,
            color
        )

    async def on_ready(self):
        logger.info(
            "========================================"
        )

        logger.info(
            "BOT CONECTADO"
        )

        logger.info(
            "Usuario: %s",
            self.user
        )

        logger.info(
            "ID: %s",
            self.user.id
        )

        logger.info(
            "Servidores: %s",
            len(self.guilds)
        )

        logger.info(
            "Usuarios aproximados: %s",
            sum(
                guild.member_count or 0
                for guild in self.guilds
            )
        )

        logger.info(
            "Modelo IA: %s",
            self.classifier.loaded
        )

        logger.info(
            "========================================"
        )

        await self.change_presence(
            activity=discord.Game(
                name=f"{Config.PREFIX}help | AI"
            ),
            status=discord.Status.online
        )

    async def on_guild_join(self, guild):
        await self.db.ensure_guild(
            guild.id
        )

        logger.info(
            "Nuevo servidor: %s (%s)",
            guild.name,
            guild.id
        )

        owner = guild.owner

        if owner:
            try:
                embed = success_embed(
                    "BOT AI instalado",
                    (
                        f"Gracias por agregar **{self.user.name}** "
                        f"a **{guild.name}**.\n\n"
                        f"Usa `{Config.PREFIX}help` para comenzar."
                    )
                )

                await owner.send(
                    embed=embed
                )

            except Exception:
                pass

    async def on_guild_remove(self, guild):
        logger.info(
            "Bot eliminado de: %s (%s)",
            guild.name,
            guild.id
        )

    async def on_member_join(self, member):
        settings = await self.db.get_guild(
            member.guild.id
        )

        autorole_id = settings["autorole"]

        if autorole_id:
            role = member.guild.get_role(
                autorole_id
            )

            if role:
                try:
                    await member.add_roles(
                        role,
                        reason="Auto role"
                    )
                except Exception:
                    pass

        welcome_channel_id = (
            settings["welcome_channel"]
        )

        if welcome_channel_id:
            channel = member.guild.get_channel(
                welcome_channel_id
            )

            if channel:
                message = (
                    settings["welcome_message"]
                    or "Bienvenido {user} a {server}."
                )

                message = message.replace(
                    "{user}",
                    member.mention
                )

                message = message.replace(
                    "{server}",
                    member.guild.name
                )

                embed = success_embed(
                    "Nuevo miembro",
                    message
                )

                avatar = get_avatar_url(member)

                if avatar:
                    embed.set_thumbnail(
                        url=avatar
                    )

                try:
                    await channel.send(
                        embed=embed
                    )
                except Exception:
                    pass

    async def on_member_remove(self, member):
        settings = await self.db.get_guild(
            member.guild.id
        )

        channel_id = settings["leave_channel"]

        if not channel_id:
            return

        channel = member.guild.get_channel(
            channel_id
        )

        if not channel:
            return

        message = (
            settings["leave_message"]
            or "{user} ha salido del servidor."
        )

        message = message.replace(
            "{user}",
            member.name
        )

        message = message.replace(
            "{server}",
            member.guild.name
        )

        embed = warning_embed(
            "Miembro salió",
            message
        )

        try:
            await channel.send(
                embed=embed
            )
        except Exception:
            pass

    async def handle_afk_mentions(self, message):
        if not message.guild:
            return

        for member in message.mentions:
            afk = await self.db.get_afk(
                message.guild.id,
                member.id
            )

            if afk:
                elapsed = unix_now() - afk["created_at"]

                await message.channel.send(
                    f"**{member.display_name}** está AFK "
                    f"desde hace {format_seconds(elapsed)}.\n"
                    f"Motivo: {afk['reason'] or 'No especificado'}"
                )

        own_afk = await self.db.get_afk(
            message.guild.id,
            message.author.id
        )

        if own_afk:
            await self.db.remove_afk(
                message.guild.id,
                message.author.id
            )

            await message.channel.send(
                f"Bienvenido de vuelta, "
                f"{message.author.mention}."
            )

    async def process_image(self, message):
        if not message.attachments:
            return

        if not self.classifier.loaded:
            return

        image = None

        for attachment in message.attachments:
            if is_image_attachment(attachment):
                image = attachment
                break

        if not image:
            return

        if image.size > Config.MAX_IMAGE_SIZE:
            await message.reply(
                "La imagen supera el límite de 8 MB.",
                mention_author=False
            )

            return

        try:
            data = await image.read()

            results = await asyncio.to_thread(
                self.classifier.predict,
                data,
                3
            )

            if not results:
                return

            self.image_counter += 1

            await self.db.increment_stat(
                message.guild.id,
                message.author.id,
                "images"
            )

            embed = make_embed(
                "Análisis de imagen",
                f"Archivo: `{image.filename}`",
                Config.INFO_COLOR
            )

            for index, result in enumerate(
                results,
                start=1
            ):
                embed.add_field(
                    name=f"{index}. {result['label']}",
                    value=(
                        f"Confianza: "
                        f"**{result['confidence']:.2f}%**"
                    ),
                    inline=False
                )

            embed.set_footer(
                text=(
                    f"{Config.BOT_NAME} | "
                    f"Modelo Teachable Machine/Keras"
                )
            )

            await message.reply(
                embed=embed,
                mention_author=False
            )

        except Exception as exc:
            logger.exception(
                "Error procesando imagen: %s",
                exc
            )

    async def process_automod(self, message):
        if not message.guild:
            return False

        if message.author.guild_permissions.manage_messages:
            return False

        settings = await self.db.get_guild(
            message.guild.id
        )

        if not settings["auto_mod"]:
            return False

        if settings["anti_spam"]:
            count = self.spam.register(
                message.guild.id,
                message.author.id
            )

            if count >= Config.SPAM_LIMIT:
                try:
                    await message.delete()
                except Exception:
                    pass

                self.spam.clear(
                    message.guild.id,
                    message.author.id
                )

                try:
                    await message.channel.send(
                        f"{message.author.mention}, "
                        "reduce la velocidad de tus mensajes.",
                        delete_after=5
                    )
                except Exception:
                    pass

                await self.send_modlog(
                    message.guild,
                    "Anti-spam",
                    (
                        f"Usuario: {message.author.mention}\n"
                        f"ID: `{message.author.id}`"
                    )
                )

                return True

        if settings["anti_links"]:
            urls = re.findall(
                r"https?://\S+",
                message.content
            )

            if urls:
                try:
                    await message.delete()
                except Exception:
                    pass

                try:
                    await message.channel.send(
                        f"{message.author.mention}, "
                        "los enlaces no están permitidos aquí.",
                        delete_after=5
                    )
                except Exception:
                    pass

                return True

        return False

    async def on_message(self, message):
        if message.author.bot:
            return

        self.message_counter += 1

        if message.guild:
            await self.db.increment_stat(
                message.guild.id,
                message.author.id,
                "messages"
            )

            await self.handle_afk_mentions(
                message
            )

            blocked = await self.process_automod(
                message
            )

            if blocked:
                return

            if self.xp_manager.can_gain(
                message.guild.id,
                message.author.id
            ):
                amount = self.xp_manager.random_xp()

                old_level, new_level = await self.db.add_xp(
                    message.guild.id,
                    message.author.id,
                    amount
                )

                if new_level > old_level:
                    settings = await self.db.get_guild(
                        message.guild.id
                    )

                    channel_id = (
                        settings["level_channel"]
                    )

                    channel = (
                        message.guild.get_channel(channel_id)
                        if channel_id
                        else message.channel
                    )

                    if channel:
                        embed = success_embed(
                            "Nuevo nivel",
                            (
                                f"{message.author.mention} "
                                f"ha alcanzado el nivel **{new_level}**."
                            )
                        )

                        try:
                            await channel.send(
                                embed=embed
                            )
                        except Exception:
                            pass

        await self.process_image(
            message
        )

        await self.process_commands(
            message
        )

    async def on_command(self, ctx):
        self.command_counter += 1

        if ctx.guild:
            await self.db.increment_stat(
                ctx.guild.id,
                ctx.author.id,
                "commands"
            )

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        if isinstance(
            error,
            commands.CommandOnCooldown
        ):
            await ctx.reply(
                f"Debes esperar "
                f"**{error.retry_after:.1f}s**.",
                mention_author=False
            )

            return

        if isinstance(
            error,
            commands.MissingPermissions
        ):
            await ctx.reply(
                "No tienes los permisos necesarios.",
                mention_author=False
            )

            return

        if isinstance(
            error,
            commands.BotMissingPermissions
        ):
            await ctx.reply(
                "No tengo los permisos necesarios.",
                mention_author=False
            )

            return

        if isinstance(
            error,
            commands.MissingRequiredArgument
        ):
            await ctx.reply(
                f"Falta el argumento: `{error.param.name}`.",
                mention_author=False
            )

            return

        if isinstance(
            error,
            commands.BadArgument
        ):
            await ctx.reply(
                "Uno de los argumentos no es válido.",
                mention_author=False
            )

            return

        if isinstance(
            error,
            commands.NoPrivateMessage
        ):
            await ctx.reply(
                "Este comando solo funciona dentro de un servidor.",
                mention_author=False
            )

            return

        logger.error(
            "Error en %s: %s",
            ctx.command,
            traceback.format_exc()
        )

        await ctx.reply(
            "Ocurrió un error interno al ejecutar el comando.",
            mention_author=False
        )

    @tasks.loop(seconds=15)
    async def reminder_loop(self):
        reminders = await self.db.get_due_reminders()

        for reminder in reminders:
            channel = self.get_channel(
                reminder["channel_id"]
            )

            if channel:
                try:
                    await channel.send(
                        f"<@{reminder['user_id']}> "
                        f"Recordatorio: **{reminder['message']}**"
                    )
                except Exception:
                    pass

            await self.db.delete_reminder(
                reminder["id"]
            )

    @tasks.loop(minutes=10)
    async def maintenance_loop(self):
        self.cache.clear()

        self.spam.cleanup()

        self.xp_manager.cleanup()

    @reminder_loop.before_loop
    async def before_reminders(self):
        await self.wait_until_ready()

    @maintenance_loop.before_loop
    async def before_maintenance(self):
        await self.wait_until_ready()


# ================================================================
# 023. INSTANCIA
# ================================================================

bot = ProfessionalBot()


# ================================================================
# 024. CHECKS
# ================================================================

def guild_only():
    return commands.guild_only()


def admin_only():
    return commands.has_permissions(
        administrator=True
    )


def manage_messages():
    return commands.has_permissions(
        manage_messages=True
    )


def manage_guild():
    return commands.has_permissions(
        manage_guild=True
    )


# ================================================================
# 025. COMANDO HELP
# ================================================================

@bot.command(
    name="help",
    aliases=["ayuda", "commands", "comandos"]
)
async def help_command(ctx):
    pages = []

    categories = {
        "General": [
            "`$hello` - Saludo",
            "`$ping` - Latencia",
            "`$botinfo` - Información del bot",
            "`$serverinfo` - Información del servidor",
            "`$userinfo` - Información de usuario",
            "`$avatar` - Avatar",
            "`$uptime` - Tiempo activo",
            "`$stats` - Estadísticas"
        ],
        "Utilidad": [
            "`$calc <operación>` - Calculadora",
            "`$remind <tiempo> <mensaje>` - Recordatorio",
            "`$afk [motivo]` - Estado AFK",
            "`$poll <pregunta>` - Encuesta",
            "`$suggest <texto>` - Sugerencia",
            "`$weather <ciudad>` - Clima"
        ],
        "Moderación": [
            "`$clear <cantidad>` - Eliminar mensajes",
            "`$kick @usuario [razón]` - Expulsar",
            "`$ban @usuario [razón]` - Banear",
            "`$unban <ID>` - Desbanear",
            "`$timeout @usuario <tiempo>` - Silenciar",
            "`$warn @usuario [razón]` - Advertir",
            "`$warnings @usuario` - Advertencias"
        ],
        "Economía": [
            "`$balance` - Dinero",
            "`$daily` - Recompensa diaria",
            "`$work` - Trabajar",
            "`$pay @usuario <cantidad>` - Transferir",
            "`$rich` - Ranking económico"
        ],
        "Niveles": [
            "`$rank` - Nivel personal",
            "`$levels` - Ranking",
            "`$levelinfo` - Información del sistema"
        ],
        "IA": [
            "`$ai <mensaje>` - Asistente",
            "`$model` - Estado del modelo",
            "`$labels` - Clases del modelo",
            "`$reloadmodel` - Recargar modelo",
            "`$classify` + imagen - Clasificar imagen"
        ],
        "Configuración": [
            "`$config prefix <prefijo>`",
            "`$config log #canal`",
            "`$config welcome #canal`",
            "`$config leave #canal`",
            "`$config autorole @rol`",
            "`$config antispam on/off`",
            "`$config antilinks on/off`"
        ],
        "Tickets": [
            "`$ticket` - Crear ticket",
            "`$ticketpanel` - Panel de tickets",
            "`$close` - Cerrar ticket"
        ]
    }

    for category, commands_list in categories.items():
        embed = info_embed(
            f"BOT AI | {category}",
            "\n".join(commands_list)
        )

        pages.append(embed)

    view = PaginationView(
        pages
    )

    await ctx.send(
        embed=pages[0],
        view=view
    )


# ================================================================
# 026. HELLO
# ================================================================

@bot.command(
    name="hello",
    aliases=["hola", "saludo"]
)
@commands.cooldown(2, 10, commands.BucketType.user)
async def hello(ctx):
    await ctx.reply(
        f"Hola, {ctx.author.mention}. "
        "Soy BOT AI y estoy listo para ayudarte.",
        mention_author=False
    )


# ================================================================
# 027. PING
# ================================================================

@bot.command(
    name="ping"
)
async def ping(ctx):
    latency = bot.latency * 1000

    embed = info_embed(
        "Pong",
        f"Latencia: **{latency:.2f} ms**"
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 028. UPTIME
# ================================================================

@bot.command(
    name="uptime"
)
async def uptime(ctx):
    elapsed = utc_now() - bot.start_time

    embed = success_embed(
        "Tiempo activo",
        format_seconds(
            elapsed.total_seconds()
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 029. BOT INFO
# ================================================================

@bot.command(
    name="botinfo",
    aliases=["info", "about"]
)
async def botinfo(ctx):
    guilds = len(bot.guilds)

    users = sum(
        guild.member_count or 0
        for guild in bot.guilds
    )

    embed = info_embed(
        "BOT AI",
        "Asistente profesional para Discord."
    )

    embed.add_field(
        name="Versión",
        value=Config.VERSION,
        inline=True
    )

    embed.add_field(
        name="Python",
        value=platform.python_version(),
        inline=True
    )

    embed.add_field(
        name="Discord.py",
        value=discord.__version__,
        inline=True
    )

    embed.add_field(
        name="Servidores",
        value=format_number(guilds),
        inline=True
    )

    embed.add_field(
        name="Usuarios",
        value=format_number(users),
        inline=True
    )

    embed.add_field(
        name="Comandos ejecutados",
        value=format_number(
            bot.command_counter
        ),
        inline=True
    )

    embed.add_field(
        name="Modelo IA",
        value=(
            "Activo"
            if bot.classifier.loaded
            else "No disponible"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 030. SERVER INFO
# ================================================================

@bot.command(
    name="serverinfo",
    aliases=["server", "servidor"]
)
@guild_only()
async def serverinfo(ctx):
    guild = ctx.guild

    embed = info_embed(
        f"Servidor: {guild.name}",
        f"ID: `{guild.id}`"
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="Propietario",
        value=(
            guild.owner.mention
            if guild.owner
            else "Desconocido"
        ),
        inline=True
    )

    embed.add_field(
        name="Miembros",
        value=format_number(
            guild.member_count or 0
        ),
        inline=True
    )

    embed.add_field(
        name="Canales",
        value=format_number(
            len(guild.channels)
        ),
        inline=True
    )

    embed.add_field(
        name="Roles",
        value=format_number(
            len(guild.roles)
        ),
        inline=True
    )

    embed.add_field(
        name="Boosts",
        value=str(
            guild.premium_subscription_count
        ),
        inline=True
    )

    embed.add_field(
        name="Creado",
        value=discord.utils.format_dt(
            guild.created_at,
            "F"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 031. USER INFO
# ================================================================

@bot.command(
    name="userinfo",
    aliases=["user", "usuario"]
)
async def userinfo(ctx, member: Optional[discord.Member] = None):
    member = member or ctx.author

    embed = info_embed(
        f"Usuario: {member.display_name}",
        f"ID: `{member.id}`"
    )

    avatar = get_avatar_url(member)

    if avatar:
        embed.set_thumbnail(
            url=avatar
        )

    embed.add_field(
        name="Nombre",
        value=member.name,
        inline=True
    )

    embed.add_field(
        name="Apodo",
        value=member.display_name,
        inline=True
    )

    embed.add_field(
        name="Cuenta creada",
        value=discord.utils.format_dt(
            member.created_at,
            "F"
        ),
        inline=False
    )

    embed.add_field(
        name="Entró al servidor",
        value=(
            discord.utils.format_dt(
                member.joined_at,
                "F"
            )
            if member.joined_at
            else "Desconocido"
        ),
        inline=False
    )

    embed.add_field(
        name="Roles",
        value=str(
            len(member.roles) - 1
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 032. AVATAR
# ================================================================

@bot.command(
    name="avatar",
    aliases=["pfp"]
)
async def avatar(ctx, member: Optional[discord.Member] = None):
    member = member or ctx.author

    avatar_url = get_avatar_url(
        member
    )

    if not avatar_url:
        await ctx.send(
            "Este usuario no tiene avatar."
        )

        return

    embed = info_embed(
        f"Avatar de {member.display_name}",
        f"[Abrir imagen]({avatar_url})"
    )

    embed.set_image(
        url=avatar_url
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 033. STATS
# ================================================================

@bot.command(
    name="stats",
    aliases=["estadisticas"]
)
@guild_only()
async def stats(ctx):
    row = await bot.db.fetchone("""
        SELECT
            commands,
            messages,
            images
        FROM stats
        WHERE guild_id = ?
        AND user_id = ?
    """, (
        ctx.guild.id,
        ctx.author.id
    ))

    if not row:
        row = {
            "commands": 0,
            "messages": 0,
            "images": 0
        }

    embed = info_embed(
        f"Estadísticas de {ctx.author.display_name}",
        ""
    )

    embed.add_field(
        name="Mensajes",
        value=format_number(
            row["messages"]
        ),
        inline=True
    )

    embed.add_field(
        name="Comandos",
        value=format_number(
            row["commands"]
        ),
        inline=True
    )

    embed.add_field(
        name="Imágenes",
        value=format_number(
            row["images"]
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 034. CALCULADORA
# ================================================================

@bot.command(
    name="calc",
    aliases=["calculate", "calcular"]
)
async def calc(ctx, *, expression):
    try:
        result = SafeCalculator.evaluate(
            expression
        )

        await ctx.reply(
            f"Resultado: **{result}**",
            mention_author=False
        )

    except Exception as exc:
        await ctx.reply(
            f"No pude calcular la expresión: `{exc}`",
            mention_author=False
        )


# ================================================================
# 035. DADO
# ================================================================

@bot.command(
    name="dice",
    aliases=["dado", "roll"]
)
async def dice(ctx, sides: int = 6):
    if sides < 2 or sides > 1000:
        await ctx.reply(
            "El dado debe tener entre 2 y 1000 caras.",
            mention_author=False
        )

        return

    result = random.randint(
        1,
        sides
    )

    await ctx.send(
        f"🎲 {ctx.author.mention} lanzó un dado de "
        f"**{sides}** caras y obtuvo **{result}**."
    )


# ================================================================
# 036. COINFLIP
# ================================================================

@bot.command(
    name="coinflip",
    aliases=["coin", "moneda"]
)
async def coinflip(ctx):
    result = random.choice(
        ["Cara", "Cruz"]
    )

    await ctx.send(
        f"🪙 Resultado: **{result}**"
    )


# ================================================================
# 037. CHOOSE
# ================================================================

@bot.command(
    name="choose",
    aliases=["elegir"]
)
async def choose(ctx, *, options):
    parts = [
        clean_text(item)
        for item in re.split(
            r",|\|",
            options
        )
        if clean_text(item)
    ]

    if len(parts) < 2:
        await ctx.reply(
            "Escribe al menos dos opciones separadas por comas.",
            mention_author=False
        )

        return

    result = random.choice(
        parts
    )

    await ctx.send(
        f"Elección: **{result}**"
    )


# ================================================================
# 038. 8 BALL
# ================================================================

@bot.command(
    name="8ball",
    aliases=["bola8"]
)
async def eight_ball(ctx, *, question):
    answers = [
        "Sí.",
        "No.",
        "Probablemente.",
        "Es posible.",
        "No parece probable.",
        "Definitivamente.",
        "No puedo determinarlo.",
        "Pregunta de nuevo."
    ]

    await ctx.send(
        f"Pregunta: **{question}**\n"
        f"Respuesta: **{random.choice(answers)}**"
    )


# ================================================================
# 039. JOKE
# ================================================================

@bot.command(
    name="joke",
    aliases=["chiste"]
)
async def joke(ctx):
    jokes = [
        "¿Por qué el programador confundió Halloween con Navidad? Porque OCT 31 = DEC 25.",
        "Un programador entra a un bar y pide 1 cerveza. Pide 0 cervezas. Pide -1 cervezas.",
        "¿Qué hace un programador cuando tiene frío? Cierra Windows.",
        "Hay 10 tipos de personas: las que entienden binario y las que no."
    ]

    await ctx.send(
        random.choice(jokes)
    )


# ================================================================
# 040. MOTIVATE
# ================================================================

@bot.command(
    name="motivate",
    aliases=["motivar", "animo"]
)
async def motivate(ctx):
    messages = [
        "Cada proyecto mejora cuando sigues practicando.",
        "Los errores de código también forman parte del aprendizaje.",
        "La constancia supera a la improvisación.",
        "Un problema difícil se vuelve manejable cuando lo divides en partes."
    ]

    await ctx.send(
        f"{ctx.author.mention} {random.choice(messages)}"
    )


# ================================================================
# 041. AI
# ================================================================

@bot.command(
    name="ai",
    aliases=["ask", "ia"]
)
@commands.cooldown(5, 30, commands.BucketType.user)
async def ai(ctx, *, message):
    response = bot.assistant.respond(
        message
    )

    embed = info_embed(
        "BOT AI",
        response
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 042. MODEL
# ================================================================

@bot.command(
    name="model",
    aliases=["modelo", "aistatus"]
)
async def model(ctx):
    information = bot.classifier.model_info()

    if not information["loaded"]:
        embed = error_embed(
            "Modelo IA",
            information["error"] or "No disponible."
        )

        await ctx.send(
            embed=embed
        )

        return

    embed = success_embed(
        "Modelo IA activo",
        "El sistema de clasificación está disponible."
    )

    embed.add_field(
        name="Clases",
        value=str(
            information["labels"]
        ),
        inline=True
    )

    embed.add_field(
        name="Entrada",
        value=information["input_shape"],
        inline=True
    )

    embed.add_field(
        name="Salida",
        value=information["output_shape"],
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 043. LABELS
# ================================================================

@bot.command(
    name="labels",
    aliases=["clases"]
)
async def labels(ctx):
    if not bot.classifier.loaded:
        await ctx.reply(
            "El modelo de IA no está disponible.",
            mention_author=False
        )

        return

    if not bot.classifier.labels:
        await ctx.reply(
            "El modelo no tiene etiquetas.",
            mention_author=False
        )

        return

    description = "\n".join(
        f"`{index}` - {label}"
        for index, label
        in enumerate(
            bot.classifier.labels
        )
    )

    embed = info_embed(
        "Clases del modelo",
        description
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 044. RELOAD MODEL
# ================================================================

@bot.command(
    name="reloadmodel",
    aliases=["reloadai", "recargarmodelo"]
)
@admin_only()
async def reloadmodel(ctx):
    success = await asyncio.to_thread(
        bot.classifier.load
    )

    if success:
        await ctx.reply(
            "Modelo de IA recargado correctamente.",
            mention_author=False
        )

    else:
        await ctx.reply(
            "No se pudo cargar el modelo.",
            mention_author=False
        )


# ================================================================
# 045. CLASSIFY
# ================================================================

@bot.command(
    name="classify",
    aliases=["clasificar", "analizar"]
)
async def classify(ctx):
    if not bot.classifier.loaded:
        await ctx.reply(
            "El modelo de IA no está disponible.",
            mention_author=False
        )

        return

    attachment = None

    for item in ctx.message.attachments:
        if is_image_attachment(item):
            attachment = item
            break

    if attachment is None:
        await ctx.reply(
            "Adjunta una imagen al utilizar este comando.",
            mention_author=False
        )

        return

    if attachment.size > Config.MAX_IMAGE_SIZE:
        await ctx.reply(
            "La imagen supera el límite permitido.",
            mention_author=False
        )

        return

    try:
        data = await attachment.read()

        results = await asyncio.to_thread(
            bot.classifier.predict,
            data,
            5
        )

        embed = info_embed(
            "Resultado de clasificación",
            f"Imagen: `{attachment.filename}`"
        )

        for index, result in enumerate(
            results,
            start=1
        ):
            embed.add_field(
                name=f"{index}. {result['label']}",
                value=(
                    f"{result['confidence']:.2f}% "
                    f"de confianza"
                ),
                inline=False
            )

        await ctx.send(
            embed=embed
        )

    except Exception as exc:
        logger.exception(
            "Error de clasificación: %s",
            exc
        )

        await ctx.reply(
            "No pude analizar la imagen.",
            mention_author=False
        )


# ================================================================
# 046. REMIND
# ================================================================

@bot.command(
    name="remind",
    aliases=["recordar", "recordatorio"]
)
async def remind(ctx, duration, *, message):
    seconds = parse_duration(
        duration
    )

    if seconds is None:
        await ctx.reply(
            "Formato inválido. Ejemplos: `10m`, `2h`, `1d`.",
            mention_author=False
        )

        return

    if seconds > 30 * 86400:
        await ctx.reply(
            "El máximo es de 30 días.",
            mention_author=False
        )

        return

    execute_at = unix_now() + seconds

    reminder_id = await bot.db.add_reminder(
        ctx.author.id,
        ctx.channel.id,
        ctx.guild.id if ctx.guild else None,
        message,
        execute_at
    )

    embed = success_embed(
        "Recordatorio creado",
        (
            f"Te recordaré **{message}** "
            f"en **{format_seconds(seconds)}**."
        )
    )

    embed.add_field(
        name="ID",
        value=str(
            reminder_id
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 047. AFK
# ================================================================

@bot.command(
    name="afk"
)
@guild_only()
async def afk(ctx, *, reason="No especificado"):
    await bot.db.set_afk(
        ctx.guild.id,
        ctx.author.id,
        reason
    )

    await ctx.send(
        f"{ctx.author.mention} ahora está AFK.\n"
        f"Motivo: **{reason}**"
    )


# ================================================================
# 048. POLL
# ================================================================

@bot.command(
    name="poll",
    aliases=["encuesta"]
)
async def poll(ctx, *, question):
    embed = info_embed(
        "Encuesta",
        question
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=get_avatar_url(
            ctx.author
        ) or discord.Embed.Empty
    )

    message = await ctx.send(
        embed=embed
    )

    try:
        await message.add_reaction("👍")
        await message.add_reaction("👎")
    except Exception:
        pass


# ================================================================
# 049. SUGGEST
# ================================================================

@bot.command(
    name="suggest",
    aliases=["sugerir", "sugerencia"]
)
@guild_only()
async def suggest(ctx, *, content):
    suggestion_id = await bot.db.add_suggestion(
        ctx.guild.id,
        ctx.author.id,
        content
    )

    embed = info_embed(
        "Nueva sugerencia",
        content
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=get_avatar_url(
            ctx.author
        ) or discord.Embed.Empty
    )

    embed.set_footer(
        text=f"Sugerencia #{suggestion_id}"
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 050. WEATHER
# ================================================================

@bot.command(
    name="weather",
    aliases=["clima"]
)
async def weather(ctx, *, city):
    encoded = city.replace(
        " ",
        "+"
    )

    url = (
        f"https://wttr.in/{encoded}"
        f"?format=j1"
    )

    data = await bot.http.get_json(
        url
    )

    if not data:
        await ctx.reply(
            "No pude obtener información meteorológica.",
            mention_author=False
        )

        return

    try:
        current = data["current_condition"][0]

        temperature = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        description = current[
            "weatherDesc"
        ][0]["value"]

        embed = info_embed(
            f"Clima: {city}",
            description
        )

        embed.add_field(
            name="Temperatura",
            value=f"{temperature} °C",
            inline=True
        )

        embed.add_field(
            name="Sensación",
            value=f"{feels} °C",
            inline=True
        )

        embed.add_field(
            name="Humedad",
            value=f"{humidity}%",
            inline=True
        )

        await ctx.send(
            embed=embed
        )

    except Exception:
        await ctx.reply(
            "La respuesta del servicio meteorológico no fue válida.",
            mention_author=False
        )


# ================================================================
# 051. CLEAR
# ================================================================

@bot.command(
    name="clear",
    aliases=["purge", "limpiar"]
)
@manage_messages()
@commands.bot_has_permissions(
    manage_messages=True
)
async def clear(ctx, amount: int):
    if amount < 1 or amount > 100:
        await ctx.reply(
            "La cantidad debe estar entre 1 y 100.",
            mention_author=False
        )

        return

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    confirmation = await ctx.send(
        f"Se eliminaron **{len(deleted) - 1}** mensajes.",
        delete_after=5
    )

    await bot.send_modlog(
        ctx.guild,
        "Mensajes eliminados",
        (
            f"Moderador: {ctx.author.mention}\n"
            f"Cantidad: {len(deleted) - 1}"
        )
    )


# ================================================================
# 052. KICK
# ================================================================

@bot.command(
    name="kick",
    aliases=["expulsar"]
)
@commands.has_permissions(
    kick_members=True
)
@commands.bot_has_permissions(
    kick_members=True
)
async def kick(ctx, member: discord.Member, *, reason="Sin razón"):
    if member == ctx.author:
        await ctx.reply(
            "No puedes expulsarte a ti mismo.",
            mention_author=False
        )

        return

    if member.top_role >= ctx.author.top_role:
        await ctx.reply(
            "No puedes expulsar a un miembro con un rol igual o superior al tuyo.",
            mention_author=False
        )

        return

    await member.kick(
        reason=f"{reason} | Moderador: {ctx.author}"
    )

    await ctx.send(
        f"{member} fue expulsado.\n"
        f"Razón: **{reason}**"
    )

    await bot.send_modlog(
        ctx.guild,
        "Miembro expulsado",
        (
            f"Usuario: {member.mention}\n"
            f"Moderador: {ctx.author.mention}\n"
            f"Razón: {reason}"
        )
    )


# ================================================================
# 053. BAN
# ================================================================

@bot.command(
    name="ban",
    aliases=["banear"]
)
@commands.has_permissions(
    ban_members=True
)
@commands.bot_has_permissions(
    ban_members=True
)
async def ban(ctx, member: discord.Member, *, reason="Sin razón"):
    if member == ctx.author:
        await ctx.reply(
            "No puedes banearte a ti mismo.",
            mention_author=False
        )

        return

    if member.top_role >= ctx.author.top_role:
        await ctx.reply(
            "No puedes banear a un miembro con un rol igual o superior al tuyo.",
            mention_author=False
        )

        return

    await member.ban(
        reason=f"{reason} | Moderador: {ctx.author}"
    )

    await ctx.send(
        f"{member} fue baneado.\n"
        f"Razón: **{reason}**"
    )

    await bot.send_modlog(
        ctx.guild,
        "Miembro baneado",
        (
            f"Usuario: {member.mention}\n"
            f"Moderador: {ctx.author.mention}\n"
            f"Razón: {reason}"
        )
    )


# ================================================================
# 054. UNBAN
# ================================================================

@bot.command(
    name="unban",
    aliases=["desbanear"]
)
@commands.has_permissions(
    ban_members=True
)
@commands.bot_has_permissions(
    ban_members=True
)
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(
            user_id
        )

        await ctx.guild.unban(
            user
        )

        await ctx.send(
            f"{user} fue desbaneado."
        )

    except discord.NotFound:
        await ctx.reply(
            "El usuario no está baneado o no existe.",
            mention_author=False
        )

    except Exception:
        await ctx.reply(
            "No pude quitar el baneo.",
            mention_author=False
        )


# ================================================================
# 055. TIMEOUT
# ================================================================

@bot.command(
    name="timeout",
    aliases=["mute", "silenciar"]
)
@commands.has_permissions(
    moderate_members=True
)
@commands.bot_has_permissions(
    moderate_members=True
)
async def timeout(
    ctx,
    member: discord.Member,
    duration,
    *,
    reason="Sin razón"
):
    seconds = parse_duration(
        duration
    )

    if seconds is None:
        await ctx.reply(
            "Duración inválida.",
            mention_author=False
        )

        return

    if seconds > 28 * 86400:
        await ctx.reply(
            "Discord limita el timeout a 28 días.",
            mention_author=False
        )

        return

    if member.top_role >= ctx.author.top_role:
        await ctx.reply(
            "No puedes aplicar timeout a ese miembro.",
            mention_author=False
        )

        return

    until = utc_now() + timedelta(
        seconds=seconds
    )

    await member.timeout(
        until,
        reason=reason
    )

    await ctx.send(
        f"{member.mention} recibió timeout durante "
        f"**{format_seconds(seconds)}**."
    )

    await bot.send_modlog(
        ctx.guild,
        "Timeout aplicado",
        (
            f"Usuario: {member.mention}\n"
            f"Moderador: {ctx.author.mention}\n"
            f"Duración: {format_seconds(seconds)}\n"
            f"Razón: {reason}"
        )
    )


# ================================================================
# 056. WARN
# ================================================================

@bot.command(
    name="warn",
    aliases=["advertir"]
)
@commands.has_permissions(
    moderate_members=True
)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="Sin razón"
):
    warning_id = await bot.db.add_warning(
        ctx.guild.id,
        member.id,
        ctx.author.id,
        reason
    )

    warnings = await bot.db.get_warnings(
        ctx.guild.id,
        member.id
    )

    await ctx.send(
        f"{member.mention} recibió una advertencia.\n"
        f"Razón: **{reason}**\n"
        f"Advertencias totales: **{len(warnings)}**"
    )

    await bot.send_modlog(
        ctx.guild,
        "Advertencia",
        (
            f"Usuario: {member.mention}\n"
            f"Moderador: {ctx.author.mention}\n"
            f"ID: {warning_id}\n"
            f"Razón: {reason}"
        )
    )


# ================================================================
# 057. WARNINGS
# ================================================================

@bot.command(
    name="warnings",
    aliases=["warns", "advertencias"]
)
async def warnings(
    ctx,
    member: Optional[discord.Member] = None
):
    member = member or ctx.author

    records = await bot.db.get_warnings(
        ctx.guild.id,
        member.id
    )

    if not records:
        await ctx.send(
            f"{member.mention} no tiene advertencias."
        )

        return

    lines = []

    for record in records[:10]:
        date = datetime.fromtimestamp(
            record["created_at"],
            tz=timezone.utc
        )

        lines.append(
            f"**#{record['id']}** - "
            f"{record['reason']} - "
            f"{discord.utils.format_dt(date, 'R')}"
        )

    embed = warning_embed(
        f"Advertencias de {member.display_name}",
        "\n".join(lines)
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 058. CLEAR WARNINGS
# ================================================================

@bot.command(
    name="clearwarnings",
    aliases=["clearwarns"]
)
@commands.has_permissions(
    moderate_members=True
)
async def clearwarnings(
    ctx,
    member: discord.Member
):
    await bot.db.clear_warnings(
        ctx.guild.id,
        member.id
    )

    await ctx.send(
        f"Se eliminaron las advertencias de {member.mention}."
    )


# ================================================================
# 059. SLOWMODE
# ================================================================

@bot.command(
    name="slowmode",
    aliases=["slow"]
)
@commands.has_permissions(
    manage_channels=True
)
@commands.bot_has_permissions(
    manage_channels=True
)
async def slowmode(ctx, seconds: int):
    if seconds < 0 or seconds > 21600:
        await ctx.reply(
            "El valor debe estar entre 0 y 21600 segundos.",
            mention_author=False
        )

        return

    await ctx.channel.edit(
        slowmode_delay=seconds
    )

    await ctx.send(
        f"Slowmode configurado en **{seconds} segundos**."
    )


# ================================================================
# 060. LOCK
# ================================================================

@bot.command(
    name="lock",
    aliases=["bloquear"]
)
@commands.has_permissions(
    manage_channels=True
)
@commands.bot_has_permissions(
    manage_channels=True
)
async def lock(ctx):
    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = False

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔒 Canal bloqueado."
    )


# ================================================================
# 061. UNLOCK
# ================================================================

@bot.command(
    name="unlock",
    aliases=["desbloquear"]
)
@commands.has_permissions(
    manage_channels=True
)
@commands.bot_has_permissions(
    manage_channels=True
)
async def unlock(ctx):
    overwrite = ctx.channel.overwrites_for(
        ctx.guild.default_role
    )

    overwrite.send_messages = None

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send(
        "🔓 Canal desbloqueado."
    )


# ================================================================
# 062. BALANCE
# ================================================================

@bot.command(
    name="balance",
    aliases=["bal", "dinero"]
)
@guild_only()
async def balance(ctx, member: Optional[discord.Member] = None):
    member = member or ctx.author

    row = await bot.db.get_balance(
        ctx.guild.id,
        member.id
    )

    embed = info_embed(
        f"Balance de {member.display_name}",
        f"💰 **{format_number(row['balance'])} monedas**"
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 063. DAILY
# ================================================================

@bot.command(
    name="daily",
    aliases=["diario"]
)
@guild_only()
@commands.cooldown(1, 10, commands.BucketType.user)
async def daily(ctx):
    row = await bot.db.get_balance(
        ctx.guild.id,
        ctx.author.id
    )

    now = unix_now()

    if now - row["last_daily"] < 86400:
        remaining = 86400 - (
            now - row["last_daily"]
        )

        await ctx.reply(
            f"Ya reclamaste tu recompensa. "
            f"Espera **{format_seconds(remaining)}**.",
            mention_author=False
        )

        return

    reward = random.randint(
        100,
        500
    )

    await bot.db.change_balance(
        ctx.guild.id,
        ctx.author.id,
        reward
    )

    await bot.db.set_daily(
        ctx.guild.id,
        ctx.author.id,
        now
    )

    await ctx.send(
        f"🎁 Recibiste **{format_number(reward)}** monedas."
    )


# ================================================================
# 064. WORK
# ================================================================

@bot.command(
    name="work",
    aliases=["trabajar"]
)
@guild_only()
async def work(ctx):
    row = await bot.db.get_balance(
        ctx.guild.id,
        ctx.author.id
    )

    now = unix_now()

    if now - row["last_work"] < 3600:
        remaining = 3600 - (
            now - row["last_work"]
        )

        await ctx.reply(
            f"Debes esperar **{format_seconds(remaining)}**.",
            mention_author=False
        )

        return

    jobs = [
        "programador",
        "diseñador",
        "desarrollador web",
        "analista",
        "tester",
        "administrador"
    ]

    job = random.choice(
        jobs
    )

    reward = random.randint(
        50,
        250
    )

    await bot.db.change_balance(
        ctx.guild.id,
        ctx.author.id,
        reward
    )

    await bot.db.set_work(
        ctx.guild.id,
        ctx.author.id,
        now
    )

    await ctx.send(
        f"Trabajaste como **{job}** "
        f"y ganaste **{reward}** monedas."
    )


# ================================================================
# 065. PAY
# ================================================================

@bot.command(
    name="pay",
    aliases=["pagar", "transferir"]
)
@guild_only()
async def pay(
    ctx,
    member: discord.Member,
    amount: int
):
    if amount <= 0:
        await ctx.reply(
            "La cantidad debe ser positiva.",
            mention_author=False
        )

        return

    if member == ctx.author:
        await ctx.reply(
            "No puedes transferirte dinero a ti mismo.",
            mention_author=False
        )

        return

    sender = await bot.db.get_balance(
        ctx.guild.id,
        ctx.author.id
    )

    if sender["balance"] < amount:
        await ctx.reply(
            "No tienes suficiente dinero.",
            mention_author=False
        )

        return

    await bot.db.change_balance(
        ctx.guild.id,
        ctx.author.id,
        -amount
    )

    await bot.db.change_balance(
        ctx.guild.id,
        member.id,
        amount
    )

    await ctx.send(
        f"{ctx.author.mention} transfirió "
        f"**{format_number(amount)}** monedas a "
        f"{member.mention}."
    )


# ================================================================
# 066. RICH
# ================================================================

@bot.command(
    name="rich",
    aliases=["economy", "economia"]
)
@guild_only()
async def rich(ctx):
    records = await bot.db.economy_leaderboard(
        ctx.guild.id,
        10
    )

    if not records:
        await ctx.send(
            "No hay datos de economía."
        )

        return

    lines = []

    for index, record in enumerate(
        records,
        start=1
    ):
        member = ctx.guild.get_member(
            record["user_id"]
        )

        name = (
            member.display_name
            if member
            else f"Usuario {record['user_id']}"
        )

        lines.append(
            f"**{index}.** {name} — "
            f"{format_number(record['balance'])} monedas"
        )

    embed = success_embed(
        "Ranking económico",
        "\n".join(lines)
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 067. RANK
# ================================================================

@bot.command(
    name="rank",
    aliases=["nivel", "level"]
)
@guild_only()
async def rank(
    ctx,
    member: Optional[discord.Member] = None
):
    member = member or ctx.author

    row = await bot.db.get_xp(
        ctx.guild.id,
        member.id
    )

    next_level = (
        (row["level"] + 1) ** 2
    ) * 100

    current_xp = row["xp"]

    remaining = max(
        0,
        next_level - current_xp
    )

    embed = info_embed(
        f"Nivel de {member.display_name}",
        ""
    )

    embed.add_field(
        name="Nivel",
        value=str(
            row["level"]
        ),
        inline=True
    )

    embed.add_field(
        name="XP",
        value=format_number(
            current_xp
        ),
        inline=True
    )

    embed.add_field(
        name="Mensajes",
        value=format_number(
            row["messages"]
        ),
        inline=True
    )

    embed.add_field(
        name="XP restante",
        value=format_number(
            remaining
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 068. LEVELS
# ================================================================

@bot.command(
    name="levels",
    aliases=["leaderboard", "ranking"]
)
@guild_only()
async def levels(ctx):
    records = await bot.db.xp_leaderboard(
        ctx.guild.id,
        10
    )

    if not records:
        await ctx.send(
            "No hay datos de niveles."
        )

        return

    lines = []

    for index, record in enumerate(
        records,
        start=1
    ):
        member = ctx.guild.get_member(
            record["user_id"]
        )

        name = (
            member.display_name
            if member
            else f"Usuario {record['user_id']}"
        )

        lines.append(
            f"**{index}.** {name} — "
            f"Nivel {record['level']} "
            f"({format_number(record['xp'])} XP)"
        )

    embed = success_embed(
        "Ranking de niveles",
        "\n".join(lines)
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 069. LEVEL INFO
# ================================================================

@bot.command(
    name="levelinfo"
)
async def levelinfo(ctx):
    embed = info_embed(
        "Sistema de niveles",
        (
            "Ganas XP participando en el servidor.\n\n"
            f"XP por mensaje: {Config.XP_MIN}-{Config.XP_MAX}\n"
            f"Cooldown: {Config.XP_COOLDOWN}s\n"
            "La experiencia se guarda en SQLite."
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 070. CONFIG GROUP
# ================================================================

@bot.group(
    name="config",
    invoke_without_command=True
)
@manage_guild()
async def config(ctx):
    if ctx.invoked_subcommand is None:
        embed = info_embed(
            "Configuración",
            (
                "`$config prefix <prefijo>`\n"
                "`$config log #canal`\n"
                "`$config welcome #canal`\n"
                "`$config leave #canal`\n"
                "`$config autorole @rol`\n"
                "`$config level #canal`\n"
                "`$config antispam on/off`\n"
                "`$config antilinks on/off`\n"
                "`$config automod on/off`"
            )
        )

        await ctx.send(
            embed=embed
        )


# ================================================================
# 071. CONFIG PREFIX
# ================================================================

@config.command(
    name="prefix"
)
@manage_guild()
async def config_prefix(ctx, prefix):
    if len(prefix) > 5:
        await ctx.reply(
            "El prefijo no puede superar 5 caracteres.",
            mention_author=False
        )

        return

    await bot.db.set_guild_value(
        ctx.guild.id,
        "prefix",
        prefix
    )

    await ctx.send(
        f"Prefijo actualizado a `{prefix}`."
    )


# ================================================================
# 072. CONFIG LOG
# ================================================================

@config.command(
    name="log"
)
@manage_guild()
async def config_log(
    ctx,
    channel: discord.TextChannel
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "log_channel",
        channel.id
    )

    await ctx.send(
        f"Canal de logs configurado: {channel.mention}"
    )


# ================================================================
# 073. CONFIG WELCOME
# ================================================================

@config.command(
    name="welcome"
)
@manage_guild()
async def config_welcome(
    ctx,
    channel: discord.TextChannel
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "welcome_channel",
        channel.id
    )

    await ctx.send(
        f"Canal de bienvenida: {channel.mention}"
    )


# ================================================================
# 074. CONFIG LEAVE
# ================================================================

@config.command(
    name="leave"
)
@manage_guild()
async def config_leave(
    ctx,
    channel: discord.TextChannel
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "leave_channel",
        channel.id
    )

    await ctx.send(
        f"Canal de despedidas: {channel.mention}"
    )


# ================================================================
# 075. CONFIG AUTOROLE
# ================================================================

@config.command(
    name="autorole"
)
@manage_guild()
async def config_autorole(
    ctx,
    role: discord.Role
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "autorole",
        role.id
    )

    await ctx.send(
        f"Auto rol configurado: {role.mention}"
    )


# ================================================================
# 076. CONFIG LEVEL
# ================================================================

@config.command(
    name="level"
)
@manage_guild()
async def config_level(
    ctx,
    channel: discord.TextChannel
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "level_channel",
        channel.id
    )

    await ctx.send(
        f"Canal de niveles: {channel.mention}"
    )


# ================================================================
# 077. CONFIG ANTISPAM
# ================================================================

@config.command(
    name="antispam"
)
@manage_guild()
async def config_antispam(ctx, value):
    value = value.lower()

    if value not in {
        "on",
        "off",
        "enable",
        "disable"
    }:
        await ctx.reply(
            "Usa `on` u `off`.",
            mention_author=False
        )

        return

    enabled = value in {
        "on",
        "enable"
    }

    await bot.db.set_guild_value(
        ctx.guild.id,
        "anti_spam",
        int(enabled)
    )

    await ctx.send(
        f"Anti-spam: {'activado' if enabled else 'desactivado'}."
    )


# ================================================================
# 078. CONFIG ANTILINKS
# ================================================================

@config.command(
    name="antilinks"
)
@manage_guild()
async def config_antilinks(ctx, value):
    value = value.lower()

    if value not in {
        "on",
        "off",
        "enable",
        "disable"
    }:
        await ctx.reply(
            "Usa `on` u `off`.",
            mention_author=False
        )

        return

    enabled = value in {
        "on",
        "enable"
    }

    await bot.db.set_guild_value(
        ctx.guild.id,
        "anti_links",
        int(enabled)
    )

    await ctx.send(
        f"Anti-links: {'activado' if enabled else 'desactivado'}."
    )


# ================================================================
# 079. CONFIG AUTOMOD
# ================================================================

@config.command(
    name="automod"
)
@manage_guild()
async def config_automod(ctx, value):
    value = value.lower()

    if value not in {
        "on",
        "off"
    }:
        await ctx.reply(
            "Usa `on` u `off`.",
            mention_author=False
        )

        return

    enabled = value == "on"

    await bot.db.set_guild_value(
        ctx.guild.id,
        "auto_mod",
        int(enabled)
    )

    await ctx.send(
        f"AutoMod: {'activado' if enabled else 'desactivado'}."
    )


# ================================================================
# 080. CONFIG SHOW
# ================================================================

@config.command(
    name="show",
    aliases=["ver"]
)
@manage_guild()
async def config_show(ctx):
    settings = await bot.db.get_guild(
        ctx.guild.id
    )

    embed = info_embed(
        "Configuración del servidor",
        ""
    )

    embed.add_field(
        name="Prefijo",
        value=f"`{settings['prefix']}`",
        inline=True
    )

    embed.add_field(
        name="Anti-spam",
        value=(
            "Activo"
            if settings["anti_spam"]
            else "Inactivo"
        ),
        inline=True
    )

    embed.add_field(
        name="Anti-links",
        value=(
            "Activo"
            if settings["anti_links"]
            else "Inactivo"
        ),
        inline=True
    )

    embed.add_field(
        name="AutoMod",
        value=(
            "Activo"
            if settings["auto_mod"]
            else "Inactivo"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 081. TICKET VIEW
# ================================================================

class TicketPanelView(discord.ui.View):

    def __init__(self, bot_instance):
        super().__init__(
            timeout=None
        )

        self.bot = bot_instance

    @discord.ui.button(
        label="Crear ticket",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="bot_ai:create_ticket"
    )
    async def create_ticket(
        self,
        interaction,
        button
    ):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Este botón solo funciona en servidores.",
                ephemeral=True
            )

            return

        existing = await self.bot.db.get_ticket_by_owner(
            guild.id,
            interaction.user.id
        )

        if existing:
            channel = guild.get_channel(
                existing["channel_id"]
            )

            if channel:
                await interaction.response.send_message(
                    f"Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )

                return

        category = discord.utils.get(
            guild.categories,
            name="TICKETS"
        )

        if category is None:
            try:
                category = await guild.create_category(
                    "TICKETS"
                )
            except Exception:
                category = None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.name}".lower()[:90],
                category=category,
                overwrites=overwrites,
                reason="Creación de ticket"
            )

        except Exception as exc:
            await interaction.response.send_message(
                f"No pude crear el ticket: {exc}",
                ephemeral=True
            )

            return

        await self.bot.db.add_ticket(
            guild.id,
            channel.id,
            interaction.user.id
        )

        embed = success_embed(
            "Ticket creado",
            (
                f"Hola {interaction.user.mention}.\n\n"
                "Describe tu problema y un miembro del equipo "
                "podrá ayudarte.\n\n"
                "Usa `$close` cuando hayas terminado."
            )
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed
        )

        await interaction.response.send_message(
            f"Ticket creado: {channel.mention}",
            ephemeral=True
        )


# ================================================================
# 082. TICKET PANEL
# ================================================================

@bot.command(
    name="ticketpanel"
)
@commands.has_permissions(
    administrator=True
)
async def ticketpanel(ctx):
    embed = info_embed(
        "Centro de soporte",
        (
            "Pulsa el botón para crear un ticket privado.\n\n"
            "Los tickets son visibles para ti y el equipo "
            "con los permisos adecuados."
        )
    )

    await ctx.send(
        embed=embed,
        view=TicketPanelView(bot)
    )


# ================================================================
# 083. TICKET
# ================================================================

@bot.command(
    name="ticket"
)
async def ticket(ctx):
    view = TicketPanelView(bot)

    await ctx.send(
        "Pulsa el botón para crear tu ticket.",
        view=view
    )


# ================================================================
# 084. CLOSE TICKET
# ================================================================

@bot.command(
    name="close",
    aliases=["cerrar"]
)
@guild_only()
async def close_ticket(ctx):
    record = await bot.db.fetchone("""
        SELECT *
        FROM tickets
        WHERE channel_id = ?
        AND closed = 0
    """, (
        ctx.channel.id,
    ))

    if not record:
        await ctx.reply(
            "Este canal no es un ticket activo.",
            mention_author=False
        )

        return

    if (
        ctx.author.id != record["owner_id"]
        and not ctx.author.guild_permissions.manage_channels
    ):
        await ctx.reply(
            "No tienes permiso para cerrar este ticket.",
            mention_author=False
        )

        return

    await bot.db.close_ticket(
        ctx.channel.id
    )

    await ctx.send(
        "Ticket cerrado. El canal será eliminado."
    )

    await asyncio.sleep(
        5
    )

    try:
        await ctx.channel.delete(
            reason="Ticket cerrado"
        )
    except Exception:
        pass


# ================================================================
# 085. HEALTH
# ================================================================

@bot.command(
    name="health",
    aliases=["salud", "estado"]
)
async def health(ctx):
    latency = bot.latency * 1000

    embed = success_embed(
        "Sistema saludable",
        "Estado general del bot."
    )

    embed.add_field(
        name="Discord",
        value=f"{latency:.2f} ms",
        inline=True
    )

    embed.add_field(
        name="Database",
        value="SQLite / WAL",
        inline=True
    )

    embed.add_field(
        name="HTTP",
        value=(
            "Activo"
            if bot.http.session
            else "Inactivo"
        ),
        inline=True
    )

    embed.add_field(
        name="IA",
        value=(
            "Activo"
            if bot.classifier.loaded
            else "Inactivo"
        ),
        inline=True
    )

    embed.add_field(
        name="Cache",
        value=str(
            len(bot.cache)
        ),
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=format_seconds(
            (
                utc_now() - bot.start_time
            ).total_seconds()
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 086. SAY
# ================================================================

@bot.command(
    name="say"
)
@commands.has_permissions(
    manage_messages=True
)
async def say(ctx, *, message):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    await ctx.send(
        message
    )


# ================================================================
# 087. REVERSE
# ================================================================

@bot.command(
    name="reverse",
    aliases=["invertir"]
)
async def reverse(ctx, *, text):
    await ctx.send(
        text[::-1]
    )


# ================================================================
# 088. LENGTH
# ================================================================

@bot.command(
    name="length",
    aliases=["longitud"]
)
async def length(ctx, *, text):
    await ctx.send(
        f"Longitud: **{len(text)}** caracteres."
    )


# ================================================================
# 089. UPPER
# ================================================================

@bot.command(
    name="upper",
    aliases=["mayusculas"]
)
async def upper(ctx, *, text):
    await ctx.send(
        text.upper()
    )


# ================================================================
# 090. LOWER
# ================================================================

@bot.command(
    name="lower",
    aliases=["minusculas"]
)
async def lower(ctx, *, text):
    await ctx.send(
        text.lower()
    )


# ================================================================
# 091. DICE MULTI
# ================================================================

@bot.command(
    name="roll"
)
async def roll(ctx, notation="1d6"):
    match = re.match(
        r"^(\d+)d(\d+)$",
        notation.lower()
    )

    if not match:
        await ctx.reply(
            "Formato: `2d6`.",
            mention_author=False
        )

        return

    amount = int(
        match.group(1)
    )

    sides = int(
        match.group(2)
    )

    if amount < 1 or amount > 50:
        await ctx.reply(
            "Puedes lanzar entre 1 y 50 dados.",
            mention_author=False
        )

        return

    if sides < 2 or sides > 1000:
        await ctx.reply(
            "Cada dado debe tener entre 2 y 1000 caras.",
            mention_author=False
        )

        return

    results = [
        random.randint(
            1,
            sides
        )
        for _ in range(amount)
    ]

    total = sum(
        results
    )

    await ctx.send(
        f"🎲 Resultados: `{results}`\n"
        f"Total: **{total}**"
    )


# ================================================================
# 092. CHOICE LIST
# ================================================================

@bot.command(
    name="random"
)
async def random_number(ctx, minimum=1, maximum=100):
    minimum = safe_int(
        minimum,
        1
    )

    maximum = safe_int(
        maximum,
        100
    )

    if minimum > maximum:
        minimum, maximum = maximum, minimum

    if maximum - minimum > 1_000_000:
        await ctx.reply(
            "El rango es demasiado grande.",
            mention_author=False
        )

        return

    result = random.randint(
        minimum,
        maximum
    )

    await ctx.send(
        f"🎯 Número aleatorio: **{result}**"
    )


# ================================================================
# 093. ECHO
# ================================================================

@bot.command(
    name="echo"
)
async def echo(ctx, *, message):
    embed = info_embed(
        "Mensaje",
        message
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=get_avatar_url(
            ctx.author
        ) or discord.Embed.Empty
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 094. MEMBER COUNT
# ================================================================

@bot.command(
    name="members",
    aliases=["miembros"]
)
@guild_only()
async def members(ctx):
    online = 0

    for member in ctx.guild.members:
        if member.status != discord.Status.offline:
            online += 1

    embed = info_embed(
        "Miembros",
        ""
    )

    embed.add_field(
        name="Total",
        value=str(
            ctx.guild.member_count
        ),
        inline=True
    )

    embed.add_field(
        name="En línea",
        value=str(
            online
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 095. CHANNEL INFO
# ================================================================

@bot.command(
    name="channelinfo",
    aliases=["canal"]
)
async def channelinfo(ctx):
    channel = ctx.channel

    embed = info_embed(
        f"Canal: {channel.name}",
        f"ID: `{channel.id}`"
    )

    embed.add_field(
        name="Tipo",
        value=str(
            channel.type
        ),
        inline=True
    )

    embed.add_field(
        name="Creado",
        value=discord.utils.format_dt(
            channel.created_at,
            "F"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 096. ROLE INFO
# ================================================================

@bot.command(
    name="roleinfo"
)
async def roleinfo(
    ctx,
    role: discord.Role
):
    embed = info_embed(
        f"Rol: {role.name}",
        f"ID: `{role.id}`"
    )

    embed.add_field(
        name="Posición",
        value=str(
            role.position
        ),
        inline=True
    )

    embed.add_field(
        name="Miembros",
        value=str(
            len(role.members)
        ),
        inline=True
    )

    embed.add_field(
        name="Mencionable",
        value=(
            "Sí"
            if role.mentionable
            else "No"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 097. SERVER ICON
# ================================================================

@bot.command(
    name="servericon",
    aliases=["icon"]
)
@guild_only()
async def servericon(ctx):
    if not ctx.guild.icon:
        await ctx.send(
            "El servidor no tiene icono."
        )

        return

    embed = info_embed(
        "Icono del servidor",
        ""
    )

    embed.set_image(
        url=ctx.guild.icon.url
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 098. SERVER BANNER
# ================================================================

@bot.command(
    name="banner"
)
@guild_only()
async def banner(ctx):
    if not ctx.guild.banner:
        await ctx.send(
            "El servidor no tiene banner."
        )

        return

    embed = info_embed(
        "Banner del servidor",
        ""
    )

    embed.set_image(
        url=ctx.guild.banner.url
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 099. WHOIS
# ================================================================

@bot.command(
    name="whois"
)
async def whois(
    ctx,
    member: Optional[discord.Member] = None
):
    member = member or ctx.author

    embed = info_embed(
        f"Perfil de {member}",
        ""
    )

    embed.add_field(
        name="Bot",
        value="Sí" if member.bot else "No",
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(
            member.id
        ),
        inline=True
    )

    embed.add_field(
        name="Estado",
        value=str(
            member.status
        ),
        inline=True
    )

    embed.add_field(
        name="Cuenta",
        value=discord.utils.format_dt(
            member.created_at,
            "R"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 100. TIME
# ================================================================

@bot.command(
    name="time",
    aliases=["hora"]
)
async def time_command(ctx):
    now = utc_now()

    await ctx.send(
        f"Hora UTC: **{now.strftime('%H:%M:%S')}**\n"
        f"Fecha: **{now.strftime('%d/%m/%Y')}**"
    )


# ================================================================
# 101. DATE
# ================================================================

@bot.command(
    name="date",
    aliases=["fecha"]
)
async def date_command(ctx):
    now = utc_now()

    await ctx.send(
        f"Fecha actual UTC: **{now.strftime('%d/%m/%Y')}**"
    )


# ================================================================
# 102. CALCULATE PERCENT
# ================================================================

@bot.command(
    name="percent",
    aliases=["porcentaje"]
)
async def percent(ctx, value: float, percentage: float):
    result = value * percentage / 100

    await ctx.send(
        f"El **{percentage}%** de **{value}** es "
        f"**{result}**."
    )


# ================================================================
# 103. DISCOUNT
# ================================================================

@bot.command(
    name="discount",
    aliases=["descuento"]
)
async def discount(
    ctx,
    price: float,
    percentage: float
):
    discount_value = (
        price * percentage / 100
    )

    final_price = (
        price - discount_value
    )

    await ctx.send(
        f"Precio original: **{price:.2f}**\n"
        f"Descuento: **{discount_value:.2f}**\n"
        f"Precio final: **{final_price:.2f}**"
    )


# ================================================================
# 104. CONVERT
# ================================================================

@bot.command(
    name="convert"
)
async def convert(
    ctx,
    value: float,
    unit_from: str,
    unit_to: str
):
    conversions = {
        ("km", "m"): 1000,
        ("m", "km"): 0.001,
        ("m", "cm"): 100,
        ("cm", "m"): 0.01,
        ("kg", "g"): 1000,
        ("g", "kg"): 0.001,
        ("l", "ml"): 1000,
        ("ml", "l"): 0.001
    }

    key = (
        unit_from.lower(),
        unit_to.lower()
    )

    factor = conversions.get(
        key
    )

    if factor is None:
        await ctx.reply(
            "Conversión no disponible.",
            mention_author=False
        )

        return

    result = value * factor

    await ctx.send(
        f"{value} {unit_from} = "
        f"**{result} {unit_to}**"
    )


# ================================================================
# 105. INVITE INFO
# ================================================================

@bot.command(
    name="invite"
)
async def invite(ctx):
    permissions = discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_messages=True,
        kick_members=True,
        ban_members=True,
        moderate_members=True,
        manage_channels=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions
    )

    await ctx.send(
        f"Enlace de invitación:\n{url}"
    )


# ================================================================
# 106. SAY EMBED
# ================================================================

@bot.command(
    name="embed"
)
@commands.has_permissions(
    manage_messages=True
)
async def embed_command(ctx, *, text):
    embed = info_embed(
        "Mensaje",
        text
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 107. ROLE ADD
# ================================================================

@bot.command(
    name="giverole"
)
@commands.has_permissions(
    manage_roles=True
)
@commands.bot_has_permissions(
    manage_roles=True
)
async def giverole(
    ctx,
    member: discord.Member,
    role: discord.Role
):
    if role >= ctx.guild.me.top_role:
        await ctx.reply(
            "No puedo administrar ese rol.",
            mention_author=False
        )

        return

    await member.add_roles(
        role
    )

    await ctx.send(
        f"Se asignó {role.mention} a {member.mention}."
    )


# ================================================================
# 108. ROLE REMOVE
# ================================================================

@bot.command(
    name="removerole"
)
@commands.has_permissions(
    manage_roles=True
)
@commands.bot_has_permissions(
    manage_roles=True
)
async def removerole(
    ctx,
    member: discord.Member,
    role: discord.Role
):
    if role >= ctx.guild.me.top_role:
        await ctx.reply(
            "No puedo administrar ese rol.",
            mention_author=False
        )

        return

    await member.remove_roles(
        role
    )

    await ctx.send(
        f"Se quitó {role.mention} de {member.mention}."
    )


# ================================================================
# 109. NICKNAME
# ================================================================

@bot.command(
    name="nickname",
    aliases=["nick"]
)
@commands.has_permissions(
    manage_nicknames=True
)
@commands.bot_has_permissions(
    manage_nicknames=True
)
async def nickname(
    ctx,
    member: discord.Member,
    *,
    name
):
    await member.edit(
        nick=name
    )

    await ctx.send(
        f"Apodo actualizado para {member.mention}."
    )


# ================================================================
# 110. RESET NICKNAME
# ================================================================

@bot.command(
    name="resetnick"
)
@commands.has_permissions(
    manage_nicknames=True
)
@commands.bot_has_permissions(
    manage_nicknames=True
)
async def resetnick(
    ctx,
    member: discord.Member
):
    await member.edit(
        nick=None
    )

    await ctx.send(
        f"Apodo eliminado de {member.mention}."
    )


# ================================================================
# 111. USER PERMISSIONS
# ================================================================

@bot.command(
    name="permissions",
    aliases=["permisos"]
)
async def permissions(
    ctx,
    member: Optional[discord.Member] = None
):
    member = member or ctx.author

    permissions = member.guild_permissions

    enabled = []

    for name, value in permissions:
        if value:
            enabled.append(
                name.replace("_", " ").title()
            )

    description = "\n".join(
        f"• {permission}"
        for permission in enabled
    )

    embed = info_embed(
        f"Permisos de {member.display_name}",
        description or "Sin permisos especiales."
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 112. CLEANUP
# ================================================================

@bot.command(
    name="cleanup"
)
@commands.has_permissions(
    manage_messages=True
)
async def cleanup(ctx):
    await ctx.send(
        "Limpieza interna ejecutada."
    )

    bot.cache.clear()

    bot.spam.cleanup()

    bot.xp_manager.cleanup()


# ================================================================
# 113. DEBUG
# ================================================================

@bot.command(
    name="debug"
)
@admin_only()
async def debug(ctx):
    embed = info_embed(
        "Debug",
        ""
    )

    embed.add_field(
        name="Guilds",
        value=str(
            len(bot.guilds)
        )
    )

    embed.add_field(
        name="Latency",
        value=f"{bot.latency * 1000:.2f} ms"
    )

    embed.add_field(
        name="Cache",
        value=str(
            len(bot.cache)
        )
    )

    embed.add_field(
        name="Messages",
        value=str(
            bot.message_counter
        )
    )

    embed.add_field(
        name="Commands",
        value=str(
            bot.command_counter
        )
    )

    embed.add_field(
        name="Images",
        value=str(
            bot.image_counter
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 114. JSON EXPORT SETTINGS
# ================================================================

@bot.command(
    name="configjson"
)
@admin_only()
async def configjson(ctx):
    settings = await bot.db.get_guild(
        ctx.guild.id
    )

    data = json.dumps(
        settings,
        indent=4,
        ensure_ascii=False
    )

    if len(data) > 1900:
        data = data[:1900]

    await ctx.send(
        f"```json\n{data}\n```"
    )


# ================================================================
# 115. INFO
# ================================================================

@bot.command(
    name="info"
)
async def info(ctx):
    embed = info_embed(
        "BOT AI",
        (
            "Asistente multifunción para Discord.\n\n"
            "Incluye moderación, economía, niveles, "
            "tickets, IA, utilidades, estadísticas y más."
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 116. SUPPORT
# ================================================================

@bot.command(
    name="support",
    aliases=["soporte"]
)
async def support(ctx):
    await ctx.send(
        "Para recibir soporte utiliza `$ticket` "
        "si el servidor tiene habilitado el sistema de tickets."
    )


# ================================================================
# 117. FAQ
# ================================================================

@bot.command(
    name="faq"
)
async def faq(ctx):
    embed = info_embed(
        "Preguntas frecuentes",
        (
            "**¿Cómo veo los comandos?**\n"
            "Usa `$help`.\n\n"
            "**¿Cómo clasifico una imagen?**\n"
            "Usa `$classify` adjuntando una imagen.\n\n"
            "**¿Cómo creo un ticket?**\n"
            "Usa `$ticket`.\n\n"
            "**¿Cómo cambio la configuración?**\n"
            "Usa `$config`."
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 118. QUOTE
# ================================================================

@bot.command(
    name="quote",
    aliases=["frase"]
)
async def quote(ctx):
    quotes = [
        "La práctica convierte conceptos en habilidades.",
        "Un buen proyecto comienza con una idea clara.",
        "La programación se aprende construyendo.",
        "Los errores son información para mejorar.",
        "La constancia produce resultados."
    ]

    await ctx.send(
        f"“{random.choice(quotes)}”"
    )


# ================================================================
# 119. FACT
# ================================================================

@bot.command(
    name="fact",
    aliases=["dato"]
)
async def fact(ctx):
    facts = [
        "Python fue creado por Guido van Rossum.",
        "SQLite es una base de datos embebida.",
        "Discord usa una API para permitir bots.",
        "Keras facilita la construcción de modelos de aprendizaje automático.",
        "HTTP es uno de los protocolos fundamentales de la web."
    ]

    await ctx.send(
        random.choice(
            facts
        )
    )


# ================================================================
# 120. COMPATIBILITY
# ================================================================

@bot.command(
    name="compatibility"
)
async def compatibility(ctx, member: discord.Member):
    score = random.randint(
        0,
        100
    )

    await ctx.send(
        f"Compatibilidad entre "
        f"{ctx.author.mention} y {member.mention}: "
        f"**{score}%**"
    )


# ================================================================
# 121. MEMORY
# ================================================================

@bot.command(
    name="mem",
    aliases=["memory"]
)
async def mem(ctx):
    embed = info_embed(
        "Memoria del bot",
        (
            "El bot utiliza SQLite para persistencia y "
            "caché temporal para reducir operaciones repetidas."
        )
    )

    embed.add_field(
        name="Cache",
        value=str(
            len(bot.cache)
        )
    )

    embed.add_field(
        name="Base de datos",
        value="SQLite WAL"
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 122. HEH
# ================================================================

@bot.command(
    name="heh"
)
async def heh(ctx):
    responses = [
        "heh",
        "heh heh",
        "HEH",
        "heh.",
        "heh..."
    ]

    await ctx.send(
        random.choice(
            responses
        )
    )


# ================================================================
# 123. DUCK
# ================================================================

@bot.command(
    name="duck"
)
async def duck(ctx):
    data = await bot.http.get_json(
        "https://random-d.uk/api/random"
    )

    if not data:
        await ctx.reply(
            "No pude obtener un pato en este momento.",
            mention_author=False
        )

        return

    url = data.get(
        "url"
    )

    if not url:
        await ctx.reply(
            "La API no devolvió una imagen válida.",
            mention_author=False
        )

        return

    embed = info_embed(
        "Pato aleatorio",
        ""
    )

    embed.set_image(
        url=url
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 124. RANDOM COLOR
# ================================================================

@bot.command(
    name="color"
)
async def color(ctx):
    value = random.randint(
        0,
        0xFFFFFF
    )

    hex_value = f"#{value:06X}"

    embed = make_embed(
        "Color aleatorio",
        hex_value,
        value
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 125. HEX
# ================================================================

@bot.command(
    name="hex"
)
async def hex_command(ctx, value: str):
    value = value.lstrip("#")

    if not re.fullmatch(
        r"[0-9a-fA-F]{6}",
        value
    ):
        await ctx.reply(
            "Usa un color hexadecimal de 6 caracteres.",
            mention_author=False
        )

        return

    number = int(
        value,
        16
    )

    embed = make_embed(
        "Color",
        f"Hex: `#{value.upper()}`",
        number
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 126. REMIND HELP
# ================================================================

@bot.command(
    name="remindhelp"
)
async def remindhelp(ctx):
    embed = info_embed(
        "Recordatorios",
        (
            "`$remind 10m estudiar`\n"
            "`$remind 2h hacer tarea`\n"
            "`$remind 1d revisar proyecto`\n\n"
            "Unidades: s, m, h, d, w."
        )
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 127. POLL ADVANCED
# ================================================================

@bot.command(
    name="poll2"
)
async def poll2(ctx, *, content):
    parts = content.split("|")

    question = parts[0].strip()

    options = [
        item.strip()
        for item in parts[1:]
        if item.strip()
    ]

    if len(options) < 2:
        await ctx.reply(
            "Usa: `$poll2 pregunta | opción 1 | opción 2`.",
            mention_author=False
        )

        return

    if len(options) > 10:
        await ctx.reply(
            "Máximo 10 opciones.",
            mention_author=False
        )

        return

    emojis = [
        "1️⃣",
        "2️⃣",
        "3️⃣",
        "4️⃣",
        "5️⃣",
        "6️⃣",
        "7️⃣",
        "8️⃣",
        "9️⃣",
        "🔟"
    ]

    description = "\n".join(
        f"{emojis[index]} {option}"
        for index, option
        in enumerate(options)
    )

    embed = info_embed(
        question,
        description
    )

    message = await ctx.send(
        embed=embed
    )

    for index in range(
        len(options)
    ):
        await message.add_reaction(
            emojis[index]
        )


# ================================================================
# 128. SEARCH MEMBER
# ================================================================

@bot.command(
    name="findmember"
)
@guild_only()
async def findmember(ctx, *, query):
    query = query.lower()

    matches = []

    for member in ctx.guild.members:
        if (
            query in member.name.lower()
            or query in member.display_name.lower()
        ):
            matches.append(
                member
            )

    if not matches:
        await ctx.send(
            "No encontré miembros."
        )

        return

    matches = matches[:10]

    lines = []

    for member in matches:
        lines.append(
            f"{member.mention} — `{member.id}`"
        )

    await ctx.send(
        "\n".join(
            lines
        )
    )


# ================================================================
# 129. ROLE LIST
# ================================================================

@bot.command(
    name="roles"
)
@guild_only()
async def roles(ctx):
    roles = [
        role
        for role in reversed(
            ctx.guild.roles
        )
        if role.name != "@everyone"
    ]

    lines = [
        f"{role.mention} — posición {role.position}"
        for role in roles[:30]
    ]

    embed = info_embed(
        "Roles",
        "\n".join(lines)
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 130. CHANNELS
# ================================================================

@bot.command(
    name="channels"
)
@guild_only()
async def channels(ctx):
    categories = defaultdict(list)

    for channel in ctx.guild.channels:
        if isinstance(
            channel,
            discord.CategoryChannel
        ):
            continue

        category = (
            channel.category.name
            if channel.category
            else "Sin categoría"
        )

        categories[category].append(
            channel
        )

    lines = []

    for category, channels_list in categories.items():
        lines.append(
            f"**{category}**"
        )

        for channel in channels_list[:15]:
            lines.append(
                f"• {channel.mention}"
            )

    embed = info_embed(
        "Canales",
        "\n".join(lines)[:4000]
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 131. EMOJI LIST
# ================================================================

@bot.command(
    name="emojis"
)
@guild_only()
async def emojis(ctx):
    if not ctx.guild.emojis:
        await ctx.send(
            "El servidor no tiene emojis personalizados."
        )

        return

    description = " ".join(
        str(emoji)
        for emoji in ctx.guild.emojis
    )

    embed = info_embed(
        "Emojis",
        description[:4000]
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 132. BOOST
# ================================================================

@bot.command(
    name="boost"
)
@guild_only()
async def boost(ctx):
    embed = info_embed(
        "Boost del servidor",
        ""
    )

    embed.add_field(
        name="Nivel",
        value=str(
            ctx.guild.premium_tier
        ),
        inline=True
    )

    embed.add_field(
        name="Boosts",
        value=str(
            ctx.guild.premium_subscription_count
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 133. OWNER
# ================================================================

@bot.command(
    name="owner"
)
@guild_only()
async def owner(ctx):
    if ctx.guild.owner:
        await ctx.send(
            f"Propietario: {ctx.guild.owner.mention}"
        )


# ================================================================
# 134. CREATED
# ================================================================

@bot.command(
    name="created"
)
async def created(ctx):
    await ctx.send(
        f"Tu cuenta fue creada "
        f"{discord.utils.format_dt(ctx.author.created_at, 'R')}."
    )


# ================================================================
# 135. JOINED
# ================================================================

@bot.command(
    name="joined"
)
@guild_only()
async def joined(ctx):
    if not ctx.author.joined_at:
        await ctx.send(
            "No tengo información de tu fecha de entrada."
        )

        return

    await ctx.send(
        f"Entraste al servidor "
        f"{discord.utils.format_dt(ctx.author.joined_at, 'R')}."
    )


# ================================================================
# 136. MODEL TEST
# ================================================================

@bot.command(
    name="modeltest"
)
@admin_only()
async def modeltest(ctx):
    information = bot.classifier.model_info()

    embed = info_embed(
        "Prueba del modelo",
        json.dumps(
            information,
            indent=2,
            ensure_ascii=False
        )[:4000]
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 137. BOT STATUS
# ================================================================

@bot.command(
    name="status"
)
@admin_only()
async def status(ctx, *, text):
    await bot.change_presence(
        activity=discord.Game(
            name=text
        )
    )

    await ctx.send(
        f"Estado actualizado a: **{text}**"
    )


# ================================================================
# 138. STATUS RESET
# ================================================================

@bot.command(
    name="statusreset"
)
@admin_only()
async def statusreset(ctx):
    await bot.change_presence(
        activity=discord.Game(
            name=f"{Config.PREFIX}help | AI"
        )
    )

    await ctx.send(
        "Estado restaurado."
    )


# ================================================================
# 139. SET WELCOME MESSAGE
# ================================================================

@config.command(
    name="welcomemsg"
)
@manage_guild()
async def config_welcomemsg(
    ctx,
    *,
    message
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "welcome_message",
        message
    )

    await ctx.send(
        "Mensaje de bienvenida actualizado."
    )


# ================================================================
# 140. SET LEAVE MESSAGE
# ================================================================

@config.command(
    name="leavemsg"
)
@manage_guild()
async def config_leavemsg(
    ctx,
    *,
    message
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "leave_message",
        message
    )

    await ctx.send(
        "Mensaje de despedida actualizado."
    )


# ================================================================
# 141. MODLOG
# ================================================================

@config.command(
    name="modlog"
)
@manage_guild()
async def config_modlog(
    ctx,
    channel: discord.TextChannel
):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "modlog_channel",
        channel.id
    )

    await ctx.send(
        f"Canal de moderación configurado: {channel.mention}"
    )


# ================================================================
# 142. RESET CONFIG
# ================================================================

@config.command(
    name="reset"
)
@manage_guild()
async def config_reset(ctx):
    await bot.db.set_guild_value(
        ctx.guild.id,
        "prefix",
        Config.PREFIX
    )

    await bot.db.set_guild_value(
        ctx.guild.id,
        "log_channel",
        None
    )

    await bot.db.set_guild_value(
        ctx.guild.id,
        "welcome_channel",
        None
    )

    await bot.db.set_guild_value(
        ctx.guild.id,
        "leave_channel",
        None
    )

    await bot.db.set_guild_value(
        ctx.guild.id,
        "autorole",
        None
    )

    await bot.db.set_guild_value(
        ctx.guild.id,
        "level_channel",
        None
    )

    await bot.db.set_guild_value(
        ctx.guild.id,
        "modlog_channel",
        None
    )

    await ctx.send(
        "Configuración restaurada a los valores predeterminados."
    )


# ================================================================
# 143. BOT CHECK
# ================================================================

@bot.command(
    name="check"
)
async def check(ctx):
    checks = {
        "Discord": bot.is_ready(),
        "Database": Config.DATABASE_PATH.exists(),
        "HTTP": bot.http.session is not None,
        "IA": bot.classifier.loaded
    }

    lines = []

    for name, status in checks.items():
        symbol = "OK" if status else "ERROR"

        lines.append(
            f"**{name}:** {symbol}"
        )

    await ctx.send(
        "\n".join(lines)
    )


# ================================================================
# 144. VERSION
# ================================================================

@bot.command(
    name="version"
)
async def version(ctx):
    await ctx.send(
        f"**{Config.BOT_NAME}** "
        f"versión **{Config.VERSION}**"
    )


# ================================================================
# 145. PLATFORM
# ================================================================

@bot.command(
    name="platform"
)
async def platform_command(ctx):
    embed = info_embed(
        "Plataforma",
        ""
    )

    embed.add_field(
        name="Sistema",
        value=platform.system(),
        inline=True
    )

    embed.add_field(
        name="Versión",
        value=platform.version()[:100],
        inline=True
    )

    embed.add_field(
        name="Python",
        value=platform.python_version(),
        inline=True
    )

    embed.add_field(
        name="Arquitectura",
        value=platform.machine(),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# ================================================================
# 146. JSON STATUS
# ================================================================

@bot.command(
    name="jsonstatus"
)
@admin_only()
async def jsonstatus(ctx):
    data = {
        "version": Config.VERSION,
        "guilds": len(bot.guilds),
        "latency_ms": round(
            bot.latency * 1000,
            2
        ),
        "model_loaded": bot.classifier.loaded,
        "commands": bot.command_counter,
        "messages": bot.message_counter,
        "images": bot.image_counter,
        "cache": len(bot.cache)
    }

    await ctx.send(
        f"```json\n"
        f"{json.dumps(data, indent=2)}"
        f"\n```"
    )


# ================================================================
# 147. CLEAN TEXT
# ================================================================

@bot.command(
    name="cleantext"
)
async def cleantext(ctx, *, text):
    await ctx.send(
        clean_text(text)
    )


# ================================================================
# 148. COUNT WORDS
# ================================================================

@bot.command(
    name="wordcount"
)
async def wordcount(ctx, *, text):
    words = re.findall(
        r"\b[\wáéíóúüñÁÉÍÓÚÜÑ]+\b",
        text
    )

    await ctx.send(
        f"Palabras: **{len(words)}**\n"
        f"Caracteres: **{len(text)}**"
    )


# ================================================================
# 149. RANDOM RESPONSE
# ================================================================

@bot.command(
    name="randomresponse"
)
async def randomresponse(ctx):
    responses = [
        "Sistema operativo.",
        "Todo funcionando.",
        "Procesando datos.",
        "Listo.",
        "Esperando instrucciones."
    ]

    await ctx.send(
        random.choice(
            responses
        )
    )


# ================================================================
# 150. BOT SHUTDOWN
# ================================================================

@bot.command(
    name="shutdown"
)
@admin_only()
async def shutdown(ctx):
    view = ConfirmView(
        ctx.author.id
    )

    message = await ctx.send(
        "¿Confirmas que quieres apagar el bot?",
        view=view
    )

    await view.wait()

    if view.result is not True:
        return

    await ctx.send(
        "Apagando BOT AI..."
    )

    await bot.close()


# ================================================================
# 151. ERROR HANDLING GLOBAL
# ================================================================

@bot.tree.error
async def on_app_command_error(
    interaction,
    error
):
    logger.error(
        "Error en slash command: %s",
        traceback.format_exc()
    )

    if interaction.response.is_done():
        await interaction.followup.send(
            "Ocurrió un error interno.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Ocurrió un error interno.",
            ephemeral=True
        )


# ================================================================
# 152. SLASH COMMAND PING
# ================================================================

@bot.tree.command(
    name="ping",
    description="Comprueba la latencia del bot."
)
async def slash_ping(
    interaction: discord.Interaction
):
    latency = bot.latency * 1000

    await interaction.response.send_message(
        f"Pong: **{latency:.2f} ms**"
    )


# ================================================================
# 153. SLASH COMMAND INFO
# ================================================================

@bot.tree.command(
    name="botinfo",
    description="Muestra información del bot."
)
async def slash_botinfo(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        f"BOT AI v{Config.VERSION}\n"
        f"Servidores: {len(bot.guilds)}\n"
        f"Latencia: {bot.latency * 1000:.2f} ms"
    )


# ================================================================
# 154. TOKEN VALIDATION
# ================================================================

def validate_environment():
    if not Config.TOKEN:
        logger.error(
            "No se encontró DISCORD_TOKEN."
        )

        return False

    return True


# ================================================================
# 155. STARTUP
# ================================================================

async def main():
    if not validate_environment():
        return

    logger.info(
        "Iniciando %s v%s...",
        Config.BOT_NAME,
        Config.VERSION
    )

    try:
        await bot.start(
            Config.TOKEN
        )

    except discord.LoginFailure:
        logger.error(
            "Token de Discord inválido."
        )

    except KeyboardInterrupt:
        logger.info(
            "Bot detenido manualmente."
        )

    except Exception:
        logger.exception(
            "Error crítico durante la ejecución."
        )

    finally:
        if not bot.is_closed():
            await bot.close()


# ================================================================
# 156. EJECUCIÓN
# ================================================================

if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:
        logger.info(
            "Programa finalizado."
        )

bot.run("")
# ================================================================
# FIN DEL BOT AI
# ================================================================