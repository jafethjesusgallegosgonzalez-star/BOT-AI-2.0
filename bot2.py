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


# ==========================================
# CONFIGURACIÓN
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

# Carpeta donde está este archivo Python
PROJECT_FOLDER = Path(__file__).resolve().parent

# Archivos del modelo
MODEL_PATH = PROJECT_FOLDER / "keras_model.h5"
LABELS_PATH = PROJECT_FOLDER / "labels.txt"

# Carpeta para imágenes
IMAGES_FOLDER = PROJECT_FOLDER / "images"
IMAGES_FOLDER.mkdir(exist_ok=True)


# ==========================================
# CLASIFICACIÓN DE IMÁGENES
# ==========================================

def get_class(model_path, labels_path, image_path):
    """
    Clasifica una imagen usando un modelo Keras.

    Devuelve:
        nombre de la clase
        porcentaje de confianza
    """

    # -------------------------------
    # Cargar modelo
    # -------------------------------

    try:
        model = load_model(model_path)
    except Exception as error:
        print(f"No se pudo cargar el modelo: {error}")
        return "desconocido", 0.0

    # -------------------------------
    # Cargar etiquetas
    # -------------------------------

    try:
        labels = [
            line.strip()
            for line in labels_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

    except Exception as error:
        print(f"No se pudieron cargar las etiquetas: {error}")
        return "desconocido", 0.0

    # -------------------------------
    # Procesar imagen
    # -------------------------------

    try:
        image = Image.open(image_path).convert("RGB")

        image = ImageOps.fit(
            image,
            (224, 224),
            Image.Resampling.LANCZOS
        )

        image_array = np.asarray(
            image,
            dtype=np.float32
        ) / 255.0

        # Agregar dimensión del batch
        image_array = np.expand_dims(
            image_array,
            axis=0
        )

        # Realizar predicción
        probabilities = model.predict(
            image_array,
            verbose=0
        )[0]

        # Obtener índice de la clase con mayor probabilidad
        index = int(np.argmax(probabilities))

        # Obtener confianza
        confidence = float(
            probabilities[index] * 100
        )

        # Obtener nombre de la clase
        if index < len(labels):
            class_name = labels[index]
        else:
            class_name = str(index)

        return class_name, confidence

    except Exception as error:
        print(f"No se pudo clasificar la imagen: {error}")
        return "desconocido", 0.0


# ==========================================
# FUNCIÓN PARA CLASIFICAR
# ==========================================

def get_classification(image_path):
    """
    Utiliza el modelo y las etiquetas del proyecto
    para clasificar una imagen.
    """

    return get_class(
        MODEL_PATH,
        LABELS_PATH,
        image_path
    )


# ==========================================
# EVENTO: BOT ENCENDIDO
# ==========================================

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


# ==========================================
# EVENTO: MENSAJES
# ==========================================

@bot.event
async def on_message(message):

    # Evitar que el bot responda a sí mismo
    if message.author == bot.user:
        return

    # Revisar archivos adjuntos
    for attachment in message.attachments:

        # Comprobar si el archivo es una imagen
        if (
            attachment.content_type
            and attachment.content_type.startswith("image/")
        ):

            # Obtener extensión
            extension = (
                Path(attachment.filename).suffix.lower()
                or ".img"
            )

            # Crear nombre único
            image_path = (
                PROJECT_FOLDER
                / f"{uuid4().hex}{extension}"
            )

            # -------------------------------
            # Guardar imagen
            # -------------------------------

            try:
                await attachment.save(image_path)

            except (discord.HTTPException, OSError) as error:

                print(
                    f"No se pudo guardar la imagen: {error}"
                )

                await message.channel.send(
                    f"No pude guardar la imagen "
                    f"**{attachment.filename}**."
                )

                # No intentar clasificar si no se guardó
                continue

            # -------------------------------
            # Imagen guardada
            # -------------------------------

            print(
                f"Imagen guardada en: {image_path}"
            )

            await message.channel.send(
                f"Imagen guardada correctamente como "
                f"**{image_path.name}**."
            )

            # -------------------------------
            # Clasificar imagen
            # -------------------------------

            class_name, confidence = get_classification(
                image_path
            )

            await message.channel.send(
                f"La imagen **{image_path.name}** "
                f"es un **{class_name}** "
                f"con un **{confidence:.2f}%** de certeza."
            )

    # Permitir que funcionen los comandos
    await bot.process_commands(message)


# ==========================================
# COMANDO $hello
# ==========================================

@bot.command()
async def hello(ctx):
    await ctx.send(
        f"Hola, soy un bot {bot.user}!"
    )


# ==========================================
# COMANDO $heh
# ==========================================

@bot.command()
async def heh(ctx, count_heh: int = 5):

    # Limitar cantidad
    count_heh = max(
        1,
        min(count_heh, 20)
    )

    await ctx.send(
        "he" * count_heh
    )


# ==========================================
# COMANDO $mem
# ==========================================

@bot.command()
async def mem(ctx):

    # Obtener imágenes disponibles
    images = [
        file
        for file in IMAGES_FOLDER.iterdir()
        if file.is_file()
    ]

    # Comprobar si existen imágenes
    if not images:
        await ctx.send(
            "No hay imágenes disponibles "
            "en la carpeta images."
        )
        return

    # Elegir imagen aleatoria
    img_path = random.choice(images)

    # Abrir imagen
    with open(img_path, "rb") as f:

        picture = discord.File(
            f,
            filename=img_path.name
        )

        await ctx.send(
            file=picture
        )


# ==========================================
# FUNCIÓN: OBTENER IMAGEN DE PATO
# ==========================================

def get_duck_image_url():

    url = "https://random-d.uk/api/random"

    try:

        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return data["url"]

    except requests.RequestException as error:

        print(
            f"Error al obtener imagen de pato: {error}"
        )

        return None


# ==========================================
# COMANDO $duck
# ==========================================

@bot.command()
async def duck(ctx):

    image_url = get_duck_image_url()

    if image_url is None:

        await ctx.send(
            "No pude obtener una imagen de pato."
        )

        return

    await ctx.send(image_url)


# ==========================================
# INICIAR BOT
# ==========================================

bot.run("MTQ4NzIyODg2MzQ1MTg5Mzg0Mg.G15aYi.8IXV9uBRFB8pTpbGJGO-NXrFEbjwXXCTwvDMyQ")