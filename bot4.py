# ============================================================
# BOT AI - DISCORD INTELLIGENT ASSISTANT
# Version: 2.0.0
# ============================================================

import os
import asyncio
import logging
import random

from pathlib import Path
from uuid import uuid4
from urllib.parse import quote

import discord
import aiohttp
import numpy as np

from discord.ext import commands
from PIL import Image, ImageOps
from keras.models import load_model


# ============================================================
# 1. CONFIGURATION
# ============================================================

class Config:

    PREFIX = "$"

    BASE_DIR = Path(__file__).resolve().parent

    MODEL_PATH = BASE_DIR / "keras_model.h5"
    LABELS_PATH = BASE_DIR / "labels.txt"

    IMAGES_DIR = BASE_DIR / "images"
    UPLOADS_DIR = BASE_DIR / "uploads"

    IMAGE_SIZE = (224, 224)
    MAX_IMAGE_SIZE = 8 * 1024 * 1024

    HTTP_TIMEOUT = 12

    TOKEN = os.getenv("DISCORD_TOKEN")

    @classmethod
    def initialize(cls):

        cls.IMAGES_DIR.mkdir(exist_ok=True)
        cls.UPLOADS_DIR.mkdir(exist_ok=True)


Config.initialize()


# ============================================================
# 2. LOGGING SYSTEM
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("BotAI")


# ============================================================
# 3. DISCORD CONFIGURATION
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=Config.PREFIX,
    intents=intents,
    help_command=commands.DefaultHelpCommand()
)


# ============================================================
# 4. AI MODEL MANAGER
# ============================================================

class ImageClassifier:

    def __init__(self):

        self.model = None
        self.labels = []

    def load(self):

        """Carga el modelo y las etiquetas una sola vez."""

        if not Config.MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"No existe el modelo: {Config.MODEL_PATH}"
            )

        if not Config.LABELS_PATH.is_file():
            raise FileNotFoundError(
                f"No existe el archivo: {Config.LABELS_PATH}"
            )

        self.model = load_model(
            Config.MODEL_PATH
        )

        self.labels = [
            line.strip()
            for line in Config.LABELS_PATH.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        logger.info("Modelo de inteligencia artificial cargado.")

    def predict(self, image_path):

        """Clasifica una imagen y devuelve su resultado."""

        if self.model is None:
            raise RuntimeError("El modelo no está disponible.")

        with Image.open(image_path) as original:

            image = original.convert("RGB")

            image = ImageOps.fit(
                image,
                Config.IMAGE_SIZE,
                method=Image.Resampling.LANCZOS
            )

            image_array = np.asarray(
                image,
                dtype=np.float32
            ) / 255.0

        image_array = np.expand_dims(
            image_array,
            axis=0
        )

        predictions = self.model.predict(
            image_array,
            verbose=0
        )[0]

        index = int(np.argmax(predictions))

        confidence = float(
            predictions[index] * 100
        )

        class_name = (
            self.labels[index]
            if index < len(self.labels)
            else f"Clase {index}"
        )

        return class_name, confidence


classifier = ImageClassifier()


# ============================================================
# 5. BOT INITIALIZATION
# ============================================================

@bot.event
async def setup_hook():

    logger.info("Inicializando servicios del bot...")

    try:

        await asyncio.to_thread(
            classifier.load
        )

    except Exception:

        logger.exception(
            "No se pudo inicializar el clasificador."
        )

    logger.info("Inicialización finalizada.")


@bot.event
async def on_ready():

    logger.info(
        "Bot conectado: %s | ID: %s",
        bot.user,
        bot.user.id
    )

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="$help | Bot AI"
        )
    )


# ============================================================
# 6. IMAGE PROCESSING SERVICE
# ============================================================

async def process_image(message, attachment):

    if attachment.size > Config.MAX_IMAGE_SIZE:

        await message.channel.send(
            "La imagen supera el límite permitido de 8 MB."
        )

        return

    extension = Path(
        attachment.filename
    ).suffix.lower()

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp"
    }

    if extension not in allowed_extensions:

        await message.channel.send(
            "Formato de imagen no compatible."
        )

        return

    image_path = (
        Config.UPLOADS_DIR
        / f"{uuid4().hex}{extension}"
    )

    try:

        await attachment.save(image_path)

        if classifier.model is None:

            await message.channel.send(
                "El servicio de inteligencia artificial "
                "no está disponible."
            )

            return

        async with message.channel.typing():

            class_name, confidence = await asyncio.to_thread(
                classifier.predict,
                image_path
            )

        embed = discord.Embed(
            title="Análisis de imagen",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Archivo",
            value=attachment.filename,
            inline=False
        )

        embed.add_field(
            name="Clase detectada",
            value=class_name,
            inline=True
        )

        embed.add_field(
            name="Confianza",
            value=f"{confidence:.2f}%",
            inline=True
        )

        embed.set_footer(
            text="Bot AI | Image Classification System"
        )

        await message.channel.send(
            embed=embed
        )

        logger.info(
            "Imagen clasificada: %s | %.2f%%",
            class_name,
            confidence
        )

    except Exception:

        logger.exception(
            "Error procesando imagen."
        )

        await message.channel.send(
            "Ocurrió un error al analizar la imagen."
        )

    finally:

        if image_path.exists():

            image_path.unlink(missing_ok=True)


# ============================================================
# 7. MESSAGE EVENT
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    for attachment in message.attachments:

        content_type = attachment.content_type or ""

        if content_type.startswith("image/"):

            await process_image(
                message,
                attachment
            )

    await bot.process_commands(message)


# ============================================================
# 8. COMMAND: HELLO
# ============================================================

@bot.command(
    name="hello",
    help="Saluda al usuario."
)
async def hello(ctx):

    embed = discord.Embed(
        title="¡Hola!",
        description=(
            f"Bienvenido, **{ctx.author.display_name}**.\n"
            "Soy Bot AI, tu asistente de Discord."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text="Bot AI | Intelligent Assistant"
    )

    await ctx.send(embed=embed)


# ============================================================
# 9. COMMAND: HEH
# ============================================================

@bot.command(
    name="heh",
    help="Genera una pequeña broma."
)
async def heh(ctx, repetitions: int = 5):

    repetitions = max(
        1,
        min(repetitions, 20)
    )

    await ctx.send(
        " ".join(["he"] * repetitions)
    )


# ============================================================
# 10. COMMAND: MEM
# ============================================================

@bot.command(
    name="mem",
    help="Envía una imagen aleatoria."
)
async def mem(ctx):

    images = [
        file
        for file in Config.IMAGES_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".webp"
        }
    ]

    if not images:

        await ctx.send(
            "No hay imágenes disponibles."
        )

        return

    image_path = random.choice(images)

    await ctx.send(
        file=discord.File(
            image_path,
            filename=image_path.name
        )
    )


# ============================================================
# 11. WEATHER SERVICE - WTTR.IN
# ============================================================

async def get_weather(location):

    encoded_location = quote(
        location,
        safe=""
    )

    url = (
        f"https://wttr.in/{encoded_location}"
        "?format=2&lang=es&m"
    )

    timeout = aiohttp.ClientTimeout(
        total=Config.HTTP_TIMEOUT
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return None

                result = await response.text()

                result = result.strip()

                if not result or "Unknown location" in result:
                    return None

                return result

    except (aiohttp.ClientError, asyncio.TimeoutError):

        logger.exception(
            "Error consultando wttr.in."
        )

        return None


# ============================================================
# 12. COMMAND: WEATHER
# ============================================================

@bot.command(
    name="weather",
    aliases=["clima"],
    help="Consulta el clima de una ciudad."
)
async def weather(ctx, *, location=None):

    if not location:

        await ctx.send(
            "Uso: `$weather Oaxaca`\n"
            "También puedes usar: `$clima Ixtepec`."
        )

        return

    async with ctx.typing():

        weather_data = await get_weather(
            location
        )

    if weather_data is None:

        await ctx.send(
            "No fue posible obtener el clima. "
            "Comprueba el nombre de la ubicación."
        )

        return

    embed = discord.Embed(
        title=f"Información meteorológica: {location}",
        description=f"```{weather_data}```",
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="Fuente: wttr.in | Bot AI"
    )

    await ctx.send(embed=embed)


# ============================================================
# 13. DUCK IMAGE SERVICE
# ============================================================

async def get_duck_image_url():

    url = "https://random-d.uk/api/random"

    timeout = aiohttp.ClientTimeout(
        total=Config.HTTP_TIMEOUT
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return None

                data = await response.json()

                return data.get("url")

    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ValueError
    ):

        logger.exception(
            "Error consultando API de patos."
        )

        return None


# ============================================================
# 14. COMMAND: DUCK
# ============================================================

@bot.command(
    name="duck",
    help="Envía una imagen aleatoria de un pato."
)
async def duck(ctx):

    async with ctx.typing():

        image_url = await get_duck_image_url()

    if not image_url:

        await ctx.send(
            "No pude obtener una imagen de pato."
        )

        return

    embed = discord.Embed(
        title="Pato aleatorio",
        color=discord.Color.yellow()
    )

    embed.set_image(
        url=image_url
    )

    embed.set_footer(
        text="Bot AI | Random Duck Generator"
    )

    await ctx.send(embed=embed)


# ============================================================
# 15. ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "Falta un argumento para ejecutar este comando."
        )

        return

    if isinstance(
        error,
        commands.BadArgument
    ):

        await ctx.send(
            "El argumento introducido no es válido."
        )

        return

    logger.error(
        "Error en comando %s: %s",
        ctx.command,
        error,
        exc_info=(
            type(error),
            error,
            error.__traceback__
        )
    )

    await ctx.send(
        "Ocurrió un error interno al ejecutar el comando."
    )


# ============================================================
# 16. APPLICATION ENTRY POINT
# ============================================================

def main():

    if not Config.TOKEN:

        raise RuntimeError(
            "No se encontró DISCORD_TOKEN. "
            "Configura la variable de entorno."
        )

    logger.info("Iniciando Bot AI...")

    bot.run(
        Config.TOKEN,
        log_handler=None
    )


if __name__ == "__main__":

    main()

bot.run("")