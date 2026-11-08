# Pega el código de la función aquí, ¡y envía la tarea!
import discord
from discord.ext import commands
import random
import os
import requests
from pathlib import Path
from uuid import uuid4
from keras.models import load_model  # TensorFlow is required for Keras to work
from PIL import Image, ImageOps  # Install pillow instead of PIL
import numpy as np

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)
PROJECT_FOLDER = Path(__file__).resolve().parent


def get_class(model_path, labels_path, image_path):
    """Clasifica una imagen usando un modelo Keras y devuelve la clase y la confianza."""
    try:
        model = load_model(model_path)
    except Exception as error:
        print(f'No se pudo cargar el modelo: {error}')
        return 'desconocido', 0.0

    try:
        labels = [
            line.strip()
            for line in labels_path.read_text(encoding='utf-8').splitlines()
            if line.strip()
        ]
    except Exception as error:
        print(f'No se pudieron cargar las etiquetas: {error}')
        return 'desconocido', 0.0

    try:
        image = Image.open(image_path).convert('RGB')
        image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
        image_array = np.asarray(image, dtype=np.float32) / 255.0
        image_array = np.expand_dims(image_array, axis=0)

        probabilities = model.predict(image_array, verbose=0)[0]
        index = int(np.argmax(probabilities))
        confidence = float(probabilities[index] * 100)
        class_name = labels[index] if index < len(labels) else str(index)
        return class_name, confidence
    except Exception as error:
        print(f'No se pudo clasificar la imagen: {error}')
        return 'desconocido', 0.0


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image/'):
            extension = Path(attachment.filename).suffix.lower() or '.img'
            image_path = PROJECT_FOLDER / '{uuid4().hex}{extension}'

            try:
                await attachment.save(image_path)
            except (discord.HTTPException, OSError) as error:
                print(f'No se pudo guardar la imagen: {error}')
                await message.channel.send(
                    f'No pude guardar la imagen **{attachment.filename}**.'
                )
            else:
                print(f'Imagen guardada en: {image_path}')
                await message.channel.send(
                    f'Imagen guardada correctamente como **{image_path.name}**.'
                )
            print(f'Imagen guardada en: {image_path}')
            class_name, confidence = get_classification(image_path)
            await message.channel.send(
                f'La imagen **{image_path.name}** es un **{class_name}** con un **{confidence:.2f}%** de certeza.'
            )

    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hola, soy un bot {bot.user}!')

@bot.command()
async def heh(ctx, count_heh = 5):
    await ctx.send("he" * count_heh)

@bot.command()
async def mem(ctx):
    img_name = random.choice(os.listdir('images'))
    with open(f'images/{img_name}', 'rb') as f:
        # ¡Vamos a almacenar el archivo de la biblioteca Discord convertido en esta variable!
        picture = discord.File(f)
    # A continuación, podemos enviar este archivo como parámetro.
    print(os.listdir('images'))
    await ctx.send(file=picture)

def get_duck_image_url():    
    url = 'https://random-d.uk/api/random'
    res = requests.get(url)
    data = res.json()
    return data['url']

def get_classification(image_path):
    model_path = "keras_model.h5"
    labels_path = "labels.txt"
    return get_class(model_path, labels_path, image_path)

@bot.command('duck')
async def duck(ctx):
    '''Una vez que llamamos al comando duck, 
    el programa llama a la función get_duck_image_url'''
    image_url = get_duck_image_url()
    await ctx.send(image_url)

bot.run("MTQ4NzIyODg2MzQ1MTg5Mzg0Mg.G15aYi.8IXV9uBRFB8pTpbGJGO-NXrFEbjwXXCTwvDMyQ")