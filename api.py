
# ============================================================
# BOT AI - DISCORD INTELLIGENT ASSISTANT
# API REST PROFESIONAL
# ============================================================

# ============================================================
# 1. IMPORTACIONES
# ============================================================

import os
import importlib
import io
import json
import time
import uuid
import math
import sqlite3
import asyncio
import logging
import traceback
import platform
import statistics

from dotenv import load_dotenv

load_dotenv()
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict, List, Union, Literal
from contextlib import asynccontextmanager

# ============================================================
# 2. FASTAPI
# ============================================================

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Header,
    Depends,
    Request,
    status,
)

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# 3. PYDANTIC
# ============================================================

from pydantic import BaseModel, Field, ConfigDict

# ============================================================
# 4. DISCORD
# ============================================================

import discord
from discord.ext import commands

# ============================================================
# 5. HTTP
# ============================================================

import aiohttp

# ============================================================
# 6. IA
# ============================================================

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from keras.models import load_model
except ImportError:
    try:
        load_model = importlib.import_module("tensorflow.keras.models").load_model
    except ImportError:
        load_model = None

# ============================================================
# 7. CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


class APIConfig:
    """
    Configuración central de la API.
    """

    HOST = os.getenv("API_HOST", "127.0.0.1")

    PORT = int(os.getenv("API_PORT", "8000"))

    API_TITLE = os.getenv(
        "API_TITLE",
        "Bot AI Discord API"
    )

    API_VERSION = os.getenv(
        "API_VERSION",
        "1.0.0"
    )

    API_PREFIX = "/api/v1"

    API_KEY = os.getenv("API_KEY", "")

    DISCORD_TOKEN = os.getenv(
        "DISCORD_TOKEN",
        ""
    )

    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "data" / "bot_ai.db")
    )

    MODEL_PATH = os.getenv(
        "MODEL_PATH",
        str(BASE_DIR / "keras_model.h5")
    )

    LABELS_PATH = os.getenv(
        "LABELS_PATH",
        str(BASE_DIR / "labels.txt")
    )

    MAX_IMAGE_SIZE = 8 * 1024 * 1024

    IMAGE_SIZE = 224

    REQUEST_TIMEOUT = 15

    DEBUG = os.getenv(
        "API_DEBUG",
        "false"
    ).lower() == "true"


# ============================================================
# 8. DIRECTORIOS
# ============================================================

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
LOG_DIR = DATA_DIR / "logs"
MODEL_DIR = DATA_DIR / "model"

for directory in [
    DATA_DIR,
    UPLOAD_DIR,
    LOG_DIR,
    MODEL_DIR
]:
    directory.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# 9. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_DIR / "api.log",
            encoding="utf-8"
        ),
    ],
)

logger = logging.getLogger("BOT_AI_API")


# ============================================================
# 10. UTILIDADES
# ============================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().isoformat()


def unix_time() -> int:
    return int(time.time())


def format_uptime(seconds: float) -> str:

    seconds = int(seconds)

    days = seconds // 86400
    seconds %= 86400

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)


def clean_text(
    text: str,
    max_length: int = 1000
) -> str:

    if not text:
        return ""

    text = str(text).strip()

    if len(text) > max_length:
        text = text[:max_length - 3] + "..."

    return text


def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


# ============================================================
# 11. MODELOS PYDANTIC
# ============================================================

class APIStatusResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    status: str
    api_version: str
    bot_ready: bool
    uptime: str
    timestamp: str


class MessageRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    channel_id: int

    content: str = Field(
        ...,
        min_length=1,
        max_length=2000
    )


class AnnouncementRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    channel_id: int

    content: str = Field(
        ...,
        min_length=1,
        max_length=2000
    )


class KickRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    user_id: int

    reason: str = Field(
        default="Acción ejecutada mediante API",
        max_length=500
    )


class BanRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    user_id: int

    reason: str = Field(
        default="Acción ejecutada mediante API",
        max_length=500
    )


class TimeoutRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    user_id: int

    minutes: int = Field(
        ...,
        ge=1,
        le=40320
    )

    reason: str = Field(
        default="Timeout ejecutado mediante API",
        max_length=500
    )


class UserXPResponse(BaseModel):

    user_id: int
    guild_id: int
    xp: int
    level: int
    messages: int


class EconomyResponse(BaseModel):

    user_id: int
    guild_id: int
    balance: int


class PredictionResponse(BaseModel):

    success: bool
    filename: str
    prediction: str
    confidence: float
    predictions: List[Dict[str, Any]]


# ============================================================
# 12. BASE DE DATOS
# ============================================================

class Database:

    def __init__(self, path: str):

        self.path = str(path)
        self.lock = asyncio.Lock()

    def connect(self):

        database_path = Path(self.path)

        database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        connection = sqlite3.connect(
            self.path,
            timeout=30
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys=ON"
        )

        return connection

    async def execute(
        self,
        query: str,
        params: tuple = ()
    ):

        async with self.lock:

            def operation():

                connection = self.connect()

                try:

                    cursor = connection.execute(
                        query,
                        params
                    )

                    connection.commit()

                    return cursor.lastrowid

                except sqlite3.Error:

                    connection.rollback()

                    logger.exception(
                        "Error ejecutando consulta SQLite."
                    )

                    raise

                finally:
                    connection.close()

            return await asyncio.to_thread(operation)

    async def fetchone(
        self,
        query: str,
        params: tuple = ()
    ):

        async with self.lock:

            def operation():

                connection = self.connect()

                try:

                    cursor = connection.execute(
                        query,
                        params
                    )

                    return cursor.fetchone()

                except sqlite3.Error:

                    logger.exception(
                        "Error consultando SQLite."
                    )

                    raise

                finally:
                    connection.close()

            return await asyncio.to_thread(operation)

    async def fetchall(
        self,
        query: str,
        params: tuple = ()
    ):

        async with self.lock:

            def operation():

                connection = self.connect()

                try:

                    cursor = connection.execute(
                        query,
                        params
                    )

                    return cursor.fetchall()

                except sqlite3.Error:

                    logger.exception(
                        "Error consultando SQLite."
                    )

                    raise

                finally:
                    connection.close()

            return await asyncio.to_thread(operation)

    async def initialize(self):

        queries = [

            """
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS api_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                response_time REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS user_xp (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS economy (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                balance INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS api_rate_limits (
                api_key TEXT PRIMARY KEY,
                requests INTEGER DEFAULT 0,
                window_start INTEGER DEFAULT 0
            )
            """,

        ]

        for query in queries:
            await self.execute(query)

        logger.info(
            "Base de datos inicializada correctamente."
        )


# ============================================================
# 13. CLASIFICADOR DE IMÁGENES
# ============================================================

class ImageClassifier:

    def __init__(
        self,
        model_path: str,
        labels_path: str
    ):

        self.model_path = Path(model_path)
        self.labels_path = Path(labels_path)

        self.model = None
        self.labels = []
        self.loaded = False

        self.lock = asyncio.Lock()

    async def load(self):

        if load_model is None:
            logger.warning(
                "Keras/TensorFlow no está instalado."
            )
            return False

        if np is None:
            logger.warning("NumPy no está instalado.")
            return False

        if Image is None:
            logger.warning("Pillow no está instalado.")
            return False

        if not self.model_path.exists():
            logger.warning(
                "Modelo no encontrado: %s",
                self.model_path
            )
            return False

        if not self.labels_path.exists():
            logger.warning(
                "Etiquetas no encontradas: %s",
                self.labels_path
            )
            return False

        try:

            def load_sync():

                model = load_model(
                    self.model_path,
                    compile=False
                )

                labels = []

                with open(
                    self.labels_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    for line in file:

                        label = line.strip()

                        if label:

                            if (
                                label[0].isdigit()
                                and " " in label
                            ):

                                label = label.split(
                                    " ",
                                    1
                                )[1]

                            labels.append(label)

                return model, labels

            self.model, self.labels = (
                await asyncio.to_thread(load_sync)
            )

            self.loaded = True

            logger.info(
                "Modelo de IA cargado correctamente."
            )

            return True

        except Exception:

            logger.exception(
                "No se pudo cargar el modelo."
            )

            return False

    async def predict(
        self,
        image_bytes: bytes,
        filename: str
    ):

        if not self.loaded:
            raise RuntimeError(
                "El modelo de IA no está disponible."
            )

        if len(image_bytes) > APIConfig.MAX_IMAGE_SIZE:
            raise ValueError(
                "La imagen supera el tamaño máximo permitido."
            )

        async with self.lock:

            def predict_sync():

                with Image.open(
                    io.BytesIO(image_bytes)
                ) as source_image:

                    image = source_image.convert("RGB")

                    image = image.resize(
                        (
                            APIConfig.IMAGE_SIZE,
                            APIConfig.IMAGE_SIZE
                        )
                    )

                    array = np.asarray(
                        image,
                        dtype=np.float32
                    )

                array = array / 255.0

                array = np.expand_dims(
                    array,
                    axis=0
                )

                result = self.model.predict(
                    array,
                    verbose=0
                )

                probabilities = np.asarray(result)[0]

                total = float(probabilities.sum())

                if total > 0:
                    probabilities = probabilities / total

                ranked = sorted(
                    enumerate(probabilities),
                    key=lambda item: item[1],
                    reverse=True
                )

                predictions = []

                for index, probability in ranked[:5]:

                    label = (
                        self.labels[index]
                        if index < len(self.labels)
                        else f"Clase {index}"
                    )

                    predictions.append({
                        "label": label,
                        "confidence": round(
                            float(probability),
                            6
                        )
                    })

                best = (
                    predictions[0]
                    if predictions
                    else {
                        "label": "Desconocido",
                        "confidence": 0
                    }
                )

                return best, predictions

            best, predictions = await asyncio.to_thread(
                predict_sync
            )

            return {
                "success": True,
                "filename": filename,
                "prediction": best["label"],
                "confidence": best["confidence"],
                "predictions": predictions
            }

    def info(self):

        return {
            "loaded": self.loaded,
            "model_path": str(self.model_path),
            "labels": self.labels if self.loaded else [],
            "classes": len(self.labels) if self.loaded else 0
        }


# ============================================================
# 14. BOT MANAGER
# ============================================================

class BotManager:

    def __init__(self):

        self.bot = None
        self.started_at = time.monotonic()

    def attach(self, bot):
        self.bot = bot

    @property
    def ready(self):

        return (
            self.bot is not None
            and self.bot.is_ready()
        )

    def uptime(self):

        return format_uptime(
            time.monotonic() - self.started_at
        )

    def guild_count(self):

        return len(self.bot.guilds) if self.bot else 0

    def user_count(self):

        if not self.bot:
            return 0

        users = set()

        for guild in self.bot.guilds:
            for member in guild.members:
                users.add(member.id)

        return len(users)


# ============================================================
# 15. ESTADÍSTICAS
# ============================================================

class APIStatistics:

    def __init__(self):

        self.requests = 0
        self.success = 0
        self.errors = 0
        self.total_response_time = 0.0
        self.endpoint_hits = {}

        self.lock = asyncio.Lock()

    async def record(
        self,
        endpoint: str,
        response_time: float,
        success: bool
    ):

        async with self.lock:

            self.requests += 1

            if success:
                self.success += 1
            else:
                self.errors += 1

            self.total_response_time += response_time

            self.endpoint_hits[endpoint] = (
                self.endpoint_hits.get(endpoint, 0) + 1
            )

    async def snapshot(self):

        async with self.lock:

            average = (
                self.total_response_time / self.requests
                if self.requests
                else 0
            )

            return {
                "requests": self.requests,
                "success": self.success,
                "errors": self.errors,
                "success_rate": (
                    round(
                        self.success / self.requests * 100,
                        2
                    )
                    if self.requests
                    else 0
                ),
                "average_response_time_ms": round(
                    average * 1000,
                    3
                ),
                "endpoint_hits": dict(self.endpoint_hits)
            }


# ============================================================
# 16. RATE LIMITER
# ============================================================

class RateLimiter:

    def __init__(
        self,
        max_requests: int = 60,
        window: int = 60
    ):

        self.max_requests = max_requests
        self.window = window
        self.clients = {}

        self.lock = asyncio.Lock()

    async def check(self, identifier: str):

        current = time.monotonic()

        async with self.lock:

            data = self.clients.get(identifier)

            if data is None:

                self.clients[identifier] = {
                    "count": 1,
                    "start": current
                }

                return True

            elapsed = current - data["start"]

            if elapsed >= self.window:

                data["count"] = 1
                data["start"] = current

                return True

            if data["count"] >= self.max_requests:
                return False

            data["count"] += 1

            return True


# ============================================================
# 17. INSTANCIAS
# ============================================================

database = Database(APIConfig.DATABASE_PATH)

classifier = ImageClassifier(
    APIConfig.MODEL_PATH,
    APIConfig.LABELS_PATH
)

bot_manager = BotManager()

api_statistics = APIStatistics()

rate_limiter = RateLimiter(
    max_requests=60,
    window=60
)


# ============================================================
# 18. INTENTS DE DISCORD
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


# ============================================================
# 19. BOT DISCORD
# ============================================================

class DiscordBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="$",
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):

        bot_manager.attach(self)

        try:

            await self.tree.sync()

            logger.info(
                "Slash commands sincronizados."
            )

        except discord.HTTPException:

            logger.exception(
                "Error sincronizando comandos."
            )

        except Exception:

            logger.exception(
                "Error inesperado durante setup_hook."
            )

    async def on_ready(self):

        logger.info("====================================")
        logger.info("BOT AI ONLINE")
        logger.info("Usuario: %s", self.user)
        logger.info("ID: %s", self.user.id)
        logger.info("Servidores: %s", len(self.guilds))
        logger.info("====================================")

    async def close(self):

        logger.info("Cerrando bot...")

        await super().close()


# ============================================================
# 20. CREAR BOT
# ============================================================

bot = DiscordBot()


# ============================================================
# 21. AUTENTICACIÓN API
# ============================================================

async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None)
):

    configured_key = APIConfig.API_KEY

    if not configured_key:
        return True

    if not x_api_key:

        raise HTTPException(
            status_code=401,
            detail="API key requerida."
        )

    if x_api_key != configured_key:

        raise HTTPException(
            status_code=403,
            detail="API key inválida."
        )

    return True


# ============================================================
# 22. RATE LIMIT API
# ============================================================

async def api_rate_limit(request: Request):

    identifier = (
        request.client.host
        if request.client
        else "unknown"
    )

    allowed = await rate_limiter.check(identifier)

    if not allowed:

        raise HTTPException(
            status_code=429,
            detail="Límite de solicitudes superado."
        )


# ============================================================
# 23. LIFESPAN FASTAPI
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Inicializando API...")

    discord_task = None

    try:

        await database.initialize()

        logger.info("Base de datos lista.")

        await classifier.load()

        if APIConfig.DISCORD_TOKEN:

            discord_task = asyncio.create_task(
                start_discord_bot(),
                name="discord-bot-task"
            )

            logger.info("Tarea de Discord iniciada.")

        else:

            logger.warning(
                "DISCORD_TOKEN no configurado. "
                "La API funcionará sin Discord."
            )

        yield

    except Exception:

        logger.exception(
            "Error durante el inicio de la API."
        )

        raise

    finally:

        logger.info("Apagando API...")

        if discord_task is not None:

            if not bot.is_closed():
                await bot.close()

            await asyncio.gather(
                discord_task,
                return_exceptions=True
            )

        logger.info("API apagada correctamente.")


# ============================================================
# 24. FASTAPI
# ============================================================

app = FastAPI(
    title=APIConfig.API_TITLE,
    version=APIConfig.API_VERSION,
    description="API REST para Bot AI de Discord.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ============================================================
# 25. CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
    allow_headers=["*"],
)


# ============================================================
# 26. MIDDLEWARE DE ESTADÍSTICAS
# ============================================================

@app.middleware("http")
async def statistics_middleware(
    request: Request,
    call_next
):

    start = time.perf_counter()
    status_code = 500

    try:

        response = await call_next(request)

        status_code = response.status_code

        return response

    finally:

        elapsed = time.perf_counter() - start

        await api_statistics.record(
            request.url.path,
            elapsed,
            status_code < 400
        )


# ============================================================
# 27. ENDPOINT RAÍZ
# ============================================================

@app.get("/")
async def root():

    return {
        "name": APIConfig.API_TITLE,
        "version": APIConfig.API_VERSION,
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "api": APIConfig.API_PREFIX
    }


# ============================================================
# 28. HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "api": "online",
        "bot": "online" if bot_manager.ready else "offline",
        "ai": "online" if classifier.loaded else "offline",
        "timestamp": utc_iso()
    }


# ============================================================
# 29. STATUS
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/status",
    response_model=APIStatusResponse
)
async def api_status():

    return {
        "status": "online",
        "api_version": APIConfig.API_VERSION,
        "bot_ready": bot_manager.ready,
        "uptime": bot_manager.uptime(),
        "timestamp": utc_iso()
    }


# ============================================================
# 30. ESTADÍSTICAS
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/stats",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def stats():

    api_stats = await api_statistics.snapshot()

    return {
        "api": api_stats,
        "bot": {
            "ready": bot_manager.ready,
            "guilds": bot_manager.guild_count(),
            "users": bot_manager.user_count(),
            "uptime": bot_manager.uptime()
        },
        "system": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine()
        }
    }


# ============================================================
# 31. INFORMACIÓN DE LA IA
# ============================================================

@app.get(APIConfig.API_PREFIX + "/ai/model")
async def ai_model():

    return classifier.info()


# ============================================================
# 32. ETIQUETAS DEL MODELO
# ============================================================

@app.get(APIConfig.API_PREFIX + "/ai/labels")
async def ai_labels():

    if not classifier.loaded:

        raise HTTPException(
            status_code=503,
            detail="El modelo de IA no está disponible."
        )

    return {
        "classes": len(classifier.labels),
        "labels": classifier.labels
    }


# ============================================================
# 33. CLASIFICACIÓN DE IMAGEN
# ============================================================

@app.post(
    APIConfig.API_PREFIX + "/ai/classify",
    response_model=PredictionResponse,
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def classify_image(
    image: UploadFile = File(...)
):

    try:

        if not classifier.loaded:

            raise HTTPException(
                status_code=503,
                detail="El modelo de IA no está disponible."
            )

        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/bmp"
        }

        if image.content_type not in allowed_types:

            raise HTTPException(
                status_code=415,
                detail="Formato de imagen no permitido."
            )

        content = await image.read(
            APIConfig.MAX_IMAGE_SIZE + 1
        )

        if len(content) > APIConfig.MAX_IMAGE_SIZE:

            raise HTTPException(
                status_code=413,
                detail="La imagen supera los 8 MB."
            )

        if not content:

            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío."
            )

        result = await classifier.predict(
            content,
            image.filename or "image"
        )

        return result

    except HTTPException:
        raise

    except (ValueError, OSError):

        raise HTTPException(
            status_code=400,
            detail="El archivo no contiene una imagen válida."
        )

    except Exception:

        logger.exception(
            "Error clasificando imagen."
        )

        raise HTTPException(
            status_code=500,
            detail="Error procesando la imagen."
        )

    finally:

        await image.close()


# ============================================================
# 34. LISTAR SERVIDORES
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/guilds",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def list_guilds():

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    guilds = []

    for guild in bot.guilds:

        guilds.append({
            "id": guild.id,
            "name": guild.name,
            "member_count": guild.member_count,
            "owner_id": guild.owner_id,
            "created_at": guild.created_at.isoformat()
        })

    return {
        "count": len(guilds),
        "guilds": guilds
    }


# ============================================================
# 35. INFORMACIÓN DE SERVIDOR
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/guilds/{guild_id}",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def guild_info(guild_id: int):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    guild = bot.get_guild(guild_id)

    if guild is None:

        raise HTTPException(
            status_code=404,
            detail="Servidor no encontrado."
        )

    text_channels = [
        channel for channel in guild.channels
        if isinstance(channel, discord.TextChannel)
    ]

    voice_channels = [
        channel for channel in guild.channels
        if isinstance(channel, discord.VoiceChannel)
    ]

    roles = [
        role for role in guild.roles
        if role != guild.default_role
    ]

    return {
        "id": guild.id,
        "name": guild.name,
        "description": guild.description,
        "owner_id": guild.owner_id,
        "member_count": guild.member_count,
        "channel_count": len(guild.channels),
        "text_channels": len(text_channels),
        "voice_channels": len(voice_channels),
        "roles": len(roles),
        "verification_level": str(guild.verification_level),
        "created_at": guild.created_at.isoformat(),
        "icon": str(guild.icon.url) if guild.icon else None
    }


# ============================================================
# 36. INFORMACIÓN DE USUARIO
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/users/{user_id}",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def user_info(user_id: int):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    try:

        user = await bot.fetch_user(user_id)

    except discord.NotFound:

        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado."
        )

    return {
        "id": user.id,
        "name": user.name,
        "display_name": user.display_name,
        "bot": user.bot,
        "created_at": user.created_at.isoformat(),
        "avatar": str(user.avatar.url) if user.avatar else None
    }


# ============================================================
# 37. XP DEL USUARIO
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/users/{user_id}/xp/{guild_id}",
    response_model=UserXPResponse
)
async def user_xp(
    user_id: int,
    guild_id: int
):

    row = await database.fetchone(
        """
        SELECT guild_id, user_id, xp, level, messages
        FROM user_xp
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (guild_id, user_id)
    )

    if row is None:

        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "xp": 0,
            "level": 0,
            "messages": 0
        }

    return dict(row)


# ============================================================
# 38. ECONOMÍA
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/users/{user_id}/economy/{guild_id}",
    response_model=EconomyResponse
)
async def user_economy(
    user_id: int,
    guild_id: int
):

    row = await database.fetchone(
        """
        SELECT guild_id, user_id, balance
        FROM economy
        WHERE guild_id = ?
        AND user_id = ?
        """,
        (guild_id, user_id)
    )

    if row is None:

        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "balance": 0
        }

    return dict(row)


# ============================================================
# 39. RANKING XP
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/leaderboard/xp",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def xp_leaderboard(
    guild_id: int,
    limit: int = 10
):

    limit = max(1, min(limit, 100))

    rows = await database.fetchall(
        """
        SELECT user_id, xp, level, messages
        FROM user_xp
        WHERE guild_id = ?
        ORDER BY xp DESC
        LIMIT ?
        """,
        (guild_id, limit)
    )

    return {
        "guild_id": guild_id,
        "limit": limit,
        "users": [dict(row) for row in rows]
    }


# ============================================================
# 40. RANKING ECONOMÍA
# ============================================================

@app.get(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/leaderboard/economy",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def economy_leaderboard(
    guild_id: int,
    limit: int = 10
):

    limit = max(1, min(limit, 100))

    rows = await database.fetchall(
        """
        SELECT user_id, balance
        FROM economy
        WHERE guild_id = ?
        ORDER BY balance DESC
        LIMIT ?
        """,
        (guild_id, limit)
    )

    return {
        "guild_id": guild_id,
        "limit": limit,
        "users": [dict(row) for row in rows]
    }


# ============================================================
# 41. ENVIAR MENSAJE
# ============================================================

@app.post(
    APIConfig.API_PREFIX + "/messages",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def send_message(data: MessageRequest):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    channel = bot.get_channel(data.channel_id)

    if channel is None:

        raise HTTPException(
            status_code=404,
            detail="Canal no encontrado."
        )

    if not isinstance(channel, discord.TextChannel):

        raise HTTPException(
            status_code=400,
            detail="El canal no permite mensajes de texto."
        )

    try:

        message = await channel.send(
            data.content,
            allowed_mentions=discord.AllowedMentions.none()
        )

        return {
            "success": True,
            "message_id": message.id,
            "channel_id": channel.id
        }

    except discord.Forbidden:

        raise HTTPException(
            status_code=403,
            detail="El bot no tiene permiso para enviar mensajes."
        )

    except Exception:

        logger.exception("Error enviando mensaje.")

        raise HTTPException(
            status_code=500,
            detail="Error interno."
        )


# ============================================================
# 42. ANUNCIO
# ============================================================

@app.post(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/announce",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def announce(
    guild_id: int,
    data: AnnouncementRequest
):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    guild = bot.get_guild(guild_id)

    if guild is None:

        raise HTTPException(
            status_code=404,
            detail="Servidor no encontrado."
        )

    channel = guild.get_channel(data.channel_id)

    if channel is None:

        raise HTTPException(
            status_code=404,
            detail="Canal no encontrado."
        )

    if not isinstance(channel, discord.TextChannel):

        raise HTTPException(
            status_code=400,
            detail="Canal inválido."
        )

    embed = discord.Embed(
        title="Anuncio",
        description=data.content,
        color=discord.Color.blurple(),
        timestamp=utc_now()
    )

    embed.set_footer(text="Bot AI")

    try:

        message = await channel.send(embed=embed)

        return {
            "success": True,
            "message_id": message.id
        }

    except discord.Forbidden:

        raise HTTPException(
            status_code=403,
            detail="El bot no puede enviar el anuncio."
        )


# ============================================================
# 43. KICK
# ============================================================

@app.post(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/kick",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def kick_member(
    guild_id: int,
    data: KickRequest
):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    guild = bot.get_guild(guild_id)

    if guild is None:

        raise HTTPException(
            status_code=404,
            detail="Servidor no encontrado."
        )

    member = guild.get_member(data.user_id)

    if member is None:

        raise HTTPException(
            status_code=404,
            detail="Miembro no encontrado."
        )

    if not member.kickable:

        raise HTTPException(
            status_code=403,
            detail="No puedo expulsar a este miembro."
        )

    try:

        await member.kick(reason=data.reason)

        return {
            "success": True,
            "action": "kick",
            "user_id": data.user_id,
            "guild_id": guild_id,
            "reason": data.reason
        }

    except discord.Forbidden:

        raise HTTPException(
            status_code=403,
            detail="Discord rechazó la operación."
        )


# ============================================================
# 44. BAN
# ============================================================

@app.post(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/ban",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def ban_member(
    guild_id: int,
    data: BanRequest
):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    guild = bot.get_guild(guild_id)

    if guild is None:

        raise HTTPException(
            status_code=404,
            detail="Servidor no encontrado."
        )

    member = guild.get_member(data.user_id)

    if member is None:

        raise HTTPException(
            status_code=404,
            detail="Miembro no encontrado."
        )

    if not member.bannable:

        raise HTTPException(
            status_code=403,
            detail="No puedo aplicar esta acción al miembro."
        )

    try:

        await member.ban(reason=data.reason)

        return {
            "success": True,
            "action": "ban",
            "user_id": data.user_id,
            "guild_id": guild_id,
            "reason": data.reason
        }

    except discord.Forbidden:

        raise HTTPException(
            status_code=403,
            detail="Discord rechazó la operación."
        )


# ============================================================
# 45. TIMEOUT
# ============================================================

@app.post(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/timeout",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def timeout_member(
    guild_id: int,
    data: TimeoutRequest
):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    guild = bot.get_guild(guild_id)

    if guild is None:

        raise HTTPException(
            status_code=404,
            detail="Servidor no encontrado."
        )

    member = guild.get_member(data.user_id)

    if member is None:

        raise HTTPException(
            status_code=404,
            detail="Miembro no encontrado."
        )

    if not member.moderatable:

        raise HTTPException(
            status_code=403,
            detail="No puedo aplicar timeout a este miembro."
        )

    duration = timedelta(minutes=data.minutes)

    try:

        await member.timeout(
            duration,
            reason=data.reason
        )

        return {
            "success": True,
            "action": "timeout",
            "user_id": data.user_id,
            "guild_id": guild_id,
            "minutes": data.minutes,
            "reason": data.reason
        }

    except discord.Forbidden:

        raise HTTPException(
            status_code=403,
            detail="Discord rechazó la operación."
        )


# ============================================================
# 46. ELIMINAR MENSAJES
# ============================================================

@app.delete(
    APIConfig.API_PREFIX + "/guilds/{guild_id}/messages",
    dependencies=[
        Depends(verify_api_key),
        Depends(api_rate_limit)
    ]
)
async def delete_messages(
    guild_id: int,
    channel_id: int,
    amount: int = 10
):

    if not bot_manager.ready:

        raise HTTPException(
            status_code=503,
            detail="Bot no disponible."
        )

    amount = max(1, min(amount, 100))

    guild = bot.get_guild(guild_id)

    if guild is None:

        raise HTTPException(
            status_code=404,
            detail="Servidor no encontrado."
        )

    channel = guild.get_channel(channel_id)

    if channel is None:

        raise HTTPException(
            status_code=404,
            detail="Canal no encontrado."
        )

    if not isinstance(channel, discord.TextChannel):

        raise HTTPException(
            status_code=400,
            detail="Canal inválido."
        )

    try:

        deleted = await channel.purge(limit=amount)

        return {
            "success": True,
            "deleted": len(deleted)
        }

    except discord.Forbidden:

        raise HTTPException(
            status_code=403,
            detail="No tengo permisos para eliminar mensajes."
        )


# ============================================================
# 47. LISTA DE COMANDOS
# ============================================================

@app.get(APIConfig.API_PREFIX + "/commands")
async def commands_list():

    commands_data = []

    for command in bot.commands:

        commands_data.append({
            "name": command.name,
            "description": (
                command.description
                or "Sin descripción"
            ),
            "aliases": list(command.aliases)
        })

    commands_data.sort(
        key=lambda item: item["name"]
    )

    return {
        "count": len(commands_data),
        "commands": commands_data
    }


# ============================================================
# 48. COMANDOS SLASH
# ============================================================

@app.get(APIConfig.API_PREFIX + "/slash-commands")
async def slash_commands():

    commands_data = []

    for command in bot.tree.get_commands():

        commands_data.append({
            "name": command.name,
            "description": command.description
        })

    return {
        "count": len(commands_data),
        "commands": commands_data
    }


# ============================================================
# 49. MÉTRICAS DEL SISTEMA
# ============================================================

@app.get(APIConfig.API_PREFIX + "/system")
async def system_info():

    return {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation()
        },
        "system": {
            "platform": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine()
        },
        "application": {
            "api_version": APIConfig.API_VERSION,
            "uptime": bot_manager.uptime()
        }
    }


# ============================================================
# 50. REVISIÓN DEL BOT
# ============================================================

@app.get(APIConfig.API_PREFIX + "/diagnostics")
async def diagnostics():

    diagnostics_data = {
        "api": True,
        "database": False,
        "discord": bot_manager.ready,
        "ai": classifier.loaded
    }

    try:

        await database.fetchone("SELECT 1")

        diagnostics_data["database"] = True

    except Exception:

        logger.exception(
            "Error comprobando la base de datos."
        )

    healthy = all(diagnostics_data.values())

    return {
        "healthy": healthy,
        "components": diagnostics_data,
        "timestamp": utc_iso()
    }


# ============================================================
# 51. MANEJO DE ERRORES HTTP
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "status_code": exc.status_code,
                "message": str(exc.detail)
            },
            "path": request.url.path,
            "timestamp": utc_iso()
        },
        headers=exc.headers
    )


# ============================================================
# 52. MANEJO DE ERRORES GENERALES
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    logger.error(
        "Error no controlado: %s",
        exc
    )

    logger.debug(
        traceback.format_exc()
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "status_code": 500,
                "message": "Error interno del servidor."
            },
            "path": request.url.path,
            "timestamp": utc_iso()
        }
    )


# ============================================================
# 53. COMANDO HELLO
# ============================================================

@bot.command(
    name="hello",
    aliases=["hola", "saludar"]
)
async def hello(ctx: commands.Context):

    embed = discord.Embed(
        title="Hola",
        description=(
            f"Hola {ctx.author.mention}. "
            "Soy Bot AI."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(text="Bot AI")

    await ctx.send(embed=embed)


# ============================================================
# 54. COMANDO PING
# ============================================================

@bot.command(name="ping")
async def ping(ctx: commands.Context):

    latency = bot.latency * 1000

    await ctx.send(
        f"Pong! `{latency:.2f} ms`"
    )


# ============================================================
# 55. COMANDO BOTINFO
# ============================================================

@bot.command(name="botinfo")
async def botinfo(ctx: commands.Context):

    embed = discord.Embed(
        title="Bot AI",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Servidores",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Latencia",
        value=f"{bot.latency * 1000:.2f} ms",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=bot_manager.uptime(),
        inline=True
    )

    embed.add_field(
        name="IA",
        value="Online" if classifier.loaded else "Offline",
        inline=True
    )

    embed.add_field(
        name="API",
        value="Online",
        inline=True
    )

    await ctx.send(embed=embed)


# ============================================================
# 56. COMANDO SERVERINFO
# ============================================================

@bot.command(
    name="serverinfo",
    aliases=["servidor"]
)
@commands.guild_only()
async def serverinfo(ctx: commands.Context):

    guild = ctx.guild

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ID",
        value=str(guild.id),
        inline=True
    )

    embed.add_field(
        name="Miembros",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="Canales",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="Roles",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="Creado",
        value=guild.created_at.strftime("%d/%m/%Y"),
        inline=True
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)


# ============================================================
# 57. COMANDO USERINFO
# ============================================================

@bot.command(
    name="userinfo",
    aliases=["usuario"]
)
async def userinfo(
    ctx: commands.Context,
    member: Optional[discord.Member] = None
):

    member = member or ctx.author

    embed = discord.Embed(
        title="Información de usuario",
        color=member.color
    )

    embed.add_field(
        name="Usuario",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Bot",
        value="Sí" if member.bot else "No",
        inline=True
    )

    embed.add_field(
        name="Cuenta creada",
        value=member.created_at.strftime("%d/%m/%Y"),
        inline=True
    )

    embed.add_field(
        name="Entró al servidor",
        value=(
            member.joined_at.strftime("%d/%m/%Y")
            if member.joined_at
            else "Desconocido"
        ),
        inline=True
    )

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    await ctx.send(embed=embed)


# ============================================================
# 58. COMANDO AVATAR
# ============================================================

@bot.command(name="avatar")
async def avatar(
    ctx: commands.Context,
    member: Optional[discord.Member] = None
):

    member = member or ctx.author

    if not member.avatar:

        await ctx.send(
            "Este usuario no tiene avatar personalizado."
        )

        return

    embed = discord.Embed(
        title=f"Avatar de {member}",
        color=discord.Color.blurple()
    )

    embed.set_image(url=member.avatar.url)

    await ctx.send(embed=embed)


# ============================================================
# 59. COMANDO IA
# ============================================================

@bot.command(
    name="ai",
    aliases=["ia", "ask"]
)
async def ai_command(
    ctx: commands.Context,
    *,
    question: str
):

    question = clean_text(question, 500)
    lowered = question.lower()

    if any(
        word in lowered
        for word in ["hola", "buenas", "hey", "hello"]
    ):

        response = "Hola. ¿En qué puedo ayudarte?"

    elif any(
        word in lowered
        for word in ["gracias", "thank"]
    ):

        response = "De nada. Estoy disponible."

    elif any(
        word in lowered
        for word in ["ayuda", "help"]
    ):

        response = (
            "Usa `$help` para ver "
            "los comandos disponibles."
        )

    elif any(
        word in lowered
        for word in ["hora", "tiempo"]
    ):

        response = (
            f"La hora UTC es "
            f"{utc_now().strftime('%H:%M:%S')}."
        )

    else:

        response = (
            "Puedo ayudarte con comandos de Discord, "
            "moderación, estadísticas, IA y herramientas."
        )

    await ctx.send(response)


# ============================================================
# 60. COMANDO HELP
# ============================================================

@bot.command(name="help")
async def help_command(ctx: commands.Context):

    embed = discord.Embed(
        title="Bot AI - Comandos",
        description="Lista de comandos disponibles.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="General",
        value=(
            "`$hello`\n"
            "`$ping`\n"
            "`$botinfo`\n"
            "`$serverinfo`\n"
            "`$userinfo`\n"
            "`$avatar`"
        ),
        inline=False
    )

    embed.add_field(
        name="IA",
        value="`$ai <pregunta>`\n`$modelinfo`",
        inline=False
    )

    embed.add_field(
        name="API",
        value=(
            "`/health`\n"
            "`/api/v1/status`\n"
            "`/api/v1/stats`\n"
            "`/docs`"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# ============================================================
# 61. COMANDO MODELINFO
# ============================================================

@bot.command(name="modelinfo")
async def modelinfo(ctx: commands.Context):

    info = classifier.info()

    embed = discord.Embed(
        title="Modelo de IA",
        color=(
            discord.Color.green()
            if info["loaded"]
            else discord.Color.red()
        )
    )

    embed.add_field(
        name="Estado",
        value="Cargado" if info["loaded"] else "No disponible",
        inline=True
    )

    embed.add_field(
        name="Clases",
        value=str(info["classes"]),
        inline=True
    )

    if info["labels"]:

        labels = ", ".join(info["labels"])

        if len(labels) > 1000:
            labels = labels[:997] + "..."

        embed.add_field(
            name="Etiquetas",
            value=labels,
            inline=False
        )

    await ctx.send(embed=embed)


# ============================================================
# 62. COMANDO API
# ============================================================

@bot.command(name="api")
async def api_command(ctx: commands.Context):

    await ctx.send(
        "API disponible en `/docs` "
        "si el servidor FastAPI está ejecutándose."
    )


# ============================================================
# 63. MANEJO DE ERRORES DE COMANDOS
# ============================================================

@bot.event
async def on_command_error(
    ctx: commands.Context,
    error
):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.send(
            "Falta un argumento requerido."
        )

        return

    if isinstance(error, commands.MissingPermissions):

        await ctx.send(
            "No tienes permisos para ejecutar este comando."
        )

        return

    if isinstance(error, commands.NoPrivateMessage):

        await ctx.send(
            "Este comando solo funciona en servidores."
        )

        return

    logger.error(
        "Error de comando %s: %s",
        getattr(
            ctx.command,
            "qualified_name",
            "unknown"
        ),
        error
    )


# ============================================================
# 64. EVENTO DE MENSAJES
# ============================================================

@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    await bot.process_commands(message)


# ============================================================
# 65. EVENTO MIEMBRO ENTRA
# ============================================================

@bot.event
async def on_member_join(member: discord.Member):

    logger.info(
        "Nuevo miembro: %s (%s)",
        member,
        member.id
    )


# ============================================================
# 66. EVENTO MIEMBRO SALE
# ============================================================

@bot.event
async def on_member_remove(member: discord.Member):

    logger.info(
        "Miembro salió: %s (%s)",
        member,
        member.id
    )


# ============================================================
# 67. START DISCORD
# ============================================================

async def start_discord_bot():

    if not APIConfig.DISCORD_TOKEN:

        logger.warning(
            "DISCORD_TOKEN no configurado."
        )

        return

    try:

        await bot.start(
            APIConfig.DISCORD_TOKEN
        )

    except discord.LoginFailure:

        logger.exception(
            "El token de Discord es inválido."
        )

    except discord.PrivilegedIntentsRequired:

        logger.exception(
            "Discord requiere habilitar intents privilegiados."
        )

    except asyncio.CancelledError:

        raise

    except Exception:

        logger.exception(
            "No se pudo iniciar Discord."
        )


# ============================================================
# 68. MAIN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "api:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=APIConfig.DEBUG
    )
