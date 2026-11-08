import discord
from discord.ext import commands

import random
import os
import requests

from pathlib import Path
from uuid import uuid4

from keras.models import load_model
from PIL import Image, ImageOps
import numpy as np


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

PREFIX = "$"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents
)

# Carpeta principal del proyecto
PROJECT_FOLDER = Path(__file__).resolve().parent

# Archivos del modelo
MODEL_PATH = PROJECT_FOLDER / "keras_model.h5"
LABELS_PATH = PROJECT_FOLDER / "labels.txt"

# Carpeta de imágenes
IMAGES_FOLDER = PROJECT_FOLDER / "images"
IMAGES_FOLDER.mkdir(exist_ok=True)


# ==========================================================
# EVENTO: BOT INICIADO
# ==========================================================

@bot.event
async def on_ready():

    print("=" * 50)
    print("BOT INICIADO CORRECTAMENTE")
    print(f"Usuario: {bot.user}")
    print(f"ID: {bot.user.id}")
    print("=" * 50)


# ==========================================================
# CLASIFICACIÓN DE IMÁGENES
# ==========================================================

def get_class(model_path, labels_path, image_path):

    # ------------------------------------------
    # Cargar modelo
    # ------------------------------------------

    try:

        model = load_model(model_path)

    except Exception as error:

        print(
            f"[ERROR] No se pudo cargar el modelo: {error}"
        )

        return "desconocido", 0.0

    # ------------------------------------------
    # Cargar etiquetas
    # ------------------------------------------

    try:

        labels = [
            line.strip()
            for line in labels_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

    except Exception as error:

        print(
            f"[ERROR] No se pudieron cargar las etiquetas: {error}"
        )

        return "desconocido", 0.0

    # ------------------------------------------
    # Procesar imagen
    # ------------------------------------------

    try:

        image = Image.open(
            image_path
        ).convert("RGB")

        image = ImageOps.fit(
            image,
            (224, 224),
            Image.Resampling.LANCZOS
        )

        image_array = np.asarray(
            image,
            dtype=np.float32
        ) / 255.0

        image_array = np.expand_dims(
            image_array,
            axis=0
        )

        # Predicción
        probabilities = model.predict(
            image_array,
            verbose=0
        )[0]

        # Clase con mayor probabilidad
        index = int(
            np.argmax(probabilities)
        )

        # Porcentaje
        confidence = float(
            probabilities[index] * 100
        )

        # Nombre de la clase
        if index < len(labels):

            class_name = labels[index]

        else:

            class_name = f"clase_{index}"

        return class_name, confidence

    except Exception as error:

        print(
            f"[ERROR] No se pudo clasificar la imagen: {error}"
        )

        return "desconocido", 0.0


# ==========================================================
# FUNCIÓN DE CLASIFICACIÓN
# ==========================================================

def get_classification(image_path):

    return get_class(
        MODEL_PATH,
        LABELS_PATH,
        image_path
    )


# ==========================================================
# EVENTO: MENSAJES
# ==========================================================

@bot.event
async def on_message(message):

    # No responder al propio bot
    if message.author == bot.user:
        return

    # ------------------------------------------
    # Revisar archivos adjuntos
    # ------------------------------------------

    for attachment in message.attachments:

        if (
            attachment.content_type
            and attachment.content_type.startswith("image/")
        ):

            extension = (
                Path(
                    attachment.filename
                ).suffix.lower()
                or ".img"
            )

            # Nombre único para evitar conflictos
            image_path = (
                PROJECT_FOLDER
                / f"{uuid4().hex}{extension}"
            )

            # ----------------------------------
            # Guardar imagen
            # ----------------------------------

            try:

                await attachment.save(
                    image_path
                )

            except (
                discord.HTTPException,
                OSError
            ) as error:

                print(
                    f"[ERROR] No se pudo guardar la imagen: {error}"
                )

                await message.channel.send(
                    "No pude guardar la imagen."
                )

                continue

            print(
                f"[INFO] Imagen guardada: {image_path.name}"
            )

            # ----------------------------------
            # Clasificar
            # ----------------------------------

            class_name, confidence = (
                get_classification(
                    image_path
                )
            )

            await message.channel.send(
                f"**Análisis de imagen**\n"
                f"Archivo: `{image_path.name}`\n"
                f"Clase detectada: **{class_name}**\n"
                f"Confianza: **{confidence:.2f}%**"
            )

    # Procesar comandos
    await bot.process_commands(message)


# ==========================================================
# COMANDO $hello
# ==========================================================

@bot.command()
async def hello(ctx):

    await ctx.send(
        f"Hola, **{ctx.author.display_name}**. "
        f"Soy **{bot.user.name}**."
    )


# ==========================================================
# COMANDO $heh
# ==========================================================

@bot.command()
async def heh(
    ctx,
    count_heh: int = 5
):

    # Evitar cantidades excesivas
    count_heh = max(
        1,
        min(count_heh, 20)
    )

    await ctx.send(
        "he" * count_heh
    )


# ==========================================================
# COMANDO $mem
# ==========================================================

@bot.command()
async def mem(ctx):

    images = [
        file
        for file in IMAGES_FOLDER.iterdir()
        if file.is_file()
    ]

    if not images:

        await ctx.send(
            "No hay imágenes en la carpeta `images`."
        )

        return

    image_path = random.choice(
        images
    )

    with open(
        image_path,
        "rb"
    ) as file:

        picture = discord.File(
            file,
            filename=image_path.name
        )

        await ctx.send(
            file=picture
        )


# ==========================================================
# FUNCIÓN WTTR.IN
# ==========================================================

def get_weather(location):

    """
    Consulta wttr.in utilizando su formato de una línea.

    Ejemplo:
        https://wttr.in/Oaxaca?format=2&lang=es&m
    """

    url = (
        f"https://wttr.in/"
        f"{location}"
        f"?format=2&lang=es&m"
    )

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "DiscordWeatherBot/1.0"
            }
        )

        response.raise_for_status()

        return response.text.strip()

    except requests.RequestException as error:

        print(
            f"[ERROR] Error consultando wttr.in: {error}"
        )

        return None


# ==========================================================
# COMANDO $weather
# ==========================================================

@bot.command()
async def weather(ctx, *, location=None):

    # Si no especificaron ubicación
    if not location:

        await ctx.send(
            "Uso correcto:\n"
            "`$weather Oaxaca`\n"
            "`$weather Mexico City`"
        )

        return

    # Obtener clima
    weather_data = get_weather(
        location
    )

    # Error
    if weather_data is None:

        await ctx.send(
            "No pude obtener el clima "
            "para esa ubicación."
        )

        return

    # Respuesta
    await ctx.send(
        f"**Clima en {location}**\n"
        f"> {weather_data}"
    )


# ==========================================================
# COMANDO $duck
# ==========================================================

def get_duck_image_url():

    url = (
        "https://random-d.uk/api/random"
    )

    try:

        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return data.get("url")

    except requests.RequestException as error:

        print(
            f"[ERROR] No se pudo obtener el pato: {error}"
        )

        return None


@bot.command()
async def duck(ctx):

    image_url = get_duck_image_url()

    if not image_url:

        await ctx.send(
            "No pude obtener una imagen de pato."
        )

        return

    await ctx.send(
        image_url
    )


# ==========================================================
# INICIAR BOT
# ==========================================================

bot.run("MTQ4NzIyODg2MzQ1MTg5Mzg0Mg.G15aYi.8IXV9uBRFB8pTpbGJGO-NXrFEbjwXXCTwvDMyQ")