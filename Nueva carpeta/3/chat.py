import re
from collections import Counter
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import emoji
import plotly.graph_objects as go
import numpy as np
import tkinter as tk
from tkinter import filedialog

# -------- SELECCIÓN DEL ARCHIVO --------
root = tk.Tk()
root.withdraw()
ruta_archivo = filedialog.askopenfilename(
    title="Selecciona el archivo de chat de WhatsApp",
    filetypes=[("Archivos de texto", "*.txt")]
)

if not ruta_archivo:
    print("❌ No se seleccionó ningún archivo.")
    exit()

with open(ruta_archivo, "r", encoding="utf-8") as f:
    lines = f.readlines()

# -------- PARSEO DE MENSAJES --------
msg_pattern = r"^(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2})[^\-]* - (.*?): (.*)"
messages = []

for line in lines:
    line = line.replace('\u202f', ' ').replace('\u200e', '')  # limpia espacios invisibles
    match = re.match(msg_pattern, line.strip())
    if match:
        date_str, time_str, sender, text = match.groups()

        # Detectar AM/PM
        am_pm_match = re.search(r'(\d{1,2}:\d{2})\s*([ap]\.?m\.?)', line, re.IGNORECASE)
        if am_pm_match:
            time_raw = am_pm_match.group(1)
            ampm = am_pm_match.group(2).replace('.', '').lower()
            time_input = f"{time_raw} {ampm}"
            try:
                time_obj = datetime.strptime(time_input, "%I:%M %p")
            except:
                continue
        else:
            try:
                time_obj = datetime.strptime(time_str, "%H:%M")
            except:
                continue

        datetime_obj = datetime.strptime(date_str, "%d/%m/%Y").replace(
            hour=time_obj.hour, minute=time_obj.minute
        )

        messages.append({
            "datetime": datetime_obj,
            "sender": sender.strip(),
            "message": text.strip()
        })

# -------- CONVERSIÓN A DATAFRAME --------
if not messages:
    print("❌ No se detectaron mensajes.")
    exit()

df = pd.DataFrame(messages)
df = df[~df['message'].str.contains('<Multimedia omitido>', regex=False)]
df = df[df['message'].str.strip() != '']
df['month'] = df['datetime'].dt.to_period('M')
df['hour'] = df['datetime'].dt.hour

# -------- RANGO HORARIO --------
def clasificar_rango_hora(hora):
    if 0 <= hora < 6:
        return '00:00–05:59 (Madrugada)'
    elif 6 <= hora < 12:
        return '06:00–11:59 (Mañana)'
    elif 12 <= hora < 18:
        return '12:00–17:59 (Tarde)'
    else:
        return '18:00–23:59 (Noche)'

df['rango_hora'] = df['hour'].apply(clasificar_rango_hora)

# -------- ANÁLISIS DE DATOS --------
mensajes_por_mes = df.groupby('month').size()
mensajes_por_usuario = df['sender'].value_counts()
mensajes_por_rango = df['rango_hora'].value_counts().reindex([
    '00:00–05:59 (Madrugada)',
    '06:00–11:59 (Mañana)',
    '12:00–17:59 (Tarde)',
    '18:00–23:59 (Noche)'
])

# -------- NUBE DE PALABRAS --------
todo_el_texto = " ".join(df['message'])
stopwords = set([
    'el', 'la', 'lo', 'que', 'de', 'y', 'en', 'a', 'es', 'me', 'no', 'si', 'se', 'por',
    'ya', 'te', 'un', 'una', 'pero', 'como', 'con', 'al', 'mi', 'le', 'su', 'del', 'o',
    'ha', 'hay', 'bien', 'más', 'eso', 'fue', 'está', 'porque', 'para'
])
wordcloud = WordCloud(width=800, height=400, background_color='white',
                      stopwords=stopwords, colormap='viridis').generate(todo_el_texto)

# -------- EMOJIS --------
def extract_emojis(s):
    return [c for c in s if c in emoji.EMOJI_DATA]

all_emojis = df['message'].apply(extract_emojis).sum()
emoji_counts = Counter(all_emojis).most_common(10)
emoji_df = pd.DataFrame(emoji_counts, columns=["Emoji", "Cantidad"])

# -------- VISUALIZACIÓN (matplotlib) --------
fig, axs = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle("📊 Análisis del Chat de WhatsApp", fontsize=18)

# A. Mensajes por mes
axs[0, 0].bar(mensajes_por_mes.index.astype(str), mensajes_por_mes.values, color='skyblue')
axs[0, 0].set_title("🗓️ Mensajes por mes")
axs[0, 0].tick_params(axis='x', rotation=45)
for i, v in enumerate(mensajes_por_mes.values):
    axs[0, 0].text(i, v + 1, str(v), ha='center')

# B. Mensajes por persona
axs[0, 1].bar(mensajes_por_usuario.index, mensajes_por_usuario.values, color='salmon')
axs[0, 1].set_title("👤 Mensajes por persona")
axs[0, 1].tick_params(axis='x', rotation=45)
for i, v in enumerate(mensajes_por_usuario.values):
    axs[0, 1].text(i, v + 1, str(v), ha='center')

# C. Nube de palabras (imagen)
axs[1, 0].imshow(wordcloud, interpolation='bilinear')
axs[1, 0].axis("off")
axs[1, 0].set_title("☁️ Palabras más usadas")

# D. Emojis más usados
axs[1, 1].axis('off')
tabla = axs[1, 1].table(cellText=emoji_df.values,
                        colLabels=emoji_df.columns,
                        loc='center',
                        cellLoc='center')
tabla.auto_set_font_size(False)
tabla.set_fontsize(12)
tabla.scale(1.2, 1.5)
axs[1, 1].set_title("😄 Emojis más usados")

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("analisis_chat.png")
plt.show()

# -------- TABLA DE RANGO HORARIO --------
print("\n🕓 Cantidad de mensajes por rango horario:")
print(mensajes_por_rango)

# -------- NUBE INTERACTIVA CON TOOLTIP --------
palabras = [p.lower() for p in re.findall(r'\b\w+\b', todo_el_texto) if p.lower() not in stopwords]
conteo = Counter(palabras).most_common(100)
palabras_df = pd.DataFrame(conteo, columns=['Palabra', 'Frecuencia'])

np.random.seed(42)
palabras_df['x'] = np.random.rand(len(palabras_df)) * 100
palabras_df['y'] = np.random.rand(len(palabras_df)) * 100
palabras_df['size'] = palabras_df['Frecuencia'] * 3

fig_nube = go.Figure()
fig_nube.add_trace(go.Scatter(
    x=palabras_df['x'],
    y=palabras_df['y'],
    text=palabras_df['Palabra'],
    mode='text',
    textfont=dict(size=palabras_df['size'], color='black'),
    hovertext=["{}: {} veces".format(p, f) for p, f in zip(palabras_df['Palabra'], palabras_df['Frecuencia'])],
    hoverinfo='text'
))
fig_nube.update_layout(
    title="☁️ Nube de palabras interactiva (pasa el mouse)",
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    plot_bgcolor='white',
)
fig_nube.write_html("nube_interactiva.html")
fig_nube.show()
