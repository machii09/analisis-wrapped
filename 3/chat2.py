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

# -------- PATRÓN PARA LÍNEAS DE MENSAJE --------
# Formato ejemplo: 26/05/25 12:28 p. m. - Gerald Malagua: Mensaje
msg_pattern = r"^(\d{1,2}/\d{1,2}/\d{2}) (\d{1,2}:\d{2})\s*([ap])\.?\s*\.?\s*m\.? - (.*?): (.*)"

# -------- RECONSTRUIR MENSAJES MULTILÍNEA --------
raw_messages = []
buffer = ""

for line in lines:
    # Limpia espacios invisibles
    line_clean = line.replace('\u202f', ' ').replace('\u200e', '').strip()
    if re.match(msg_pattern, line_clean, re.IGNORECASE):
        if buffer:
            raw_messages.append(buffer)
        buffer = line_clean
    else:
        # Continúa el mensaje multilinea
        buffer += " " + line_clean

if buffer:
    raw_messages.append(buffer)

# -------- PARSEAR MENSAJES --------
messages = []
for raw_msg in raw_messages:
    match = re.match(msg_pattern, raw_msg, re.IGNORECASE)
    if match:
        date_str, time_str, ampm, sender, text = match.groups()
        ampm = ampm.lower()
        datetime_str = f"{date_str} {time_str} {ampm}m"
        try:
            dt = datetime.strptime(datetime_str, "%d/%m/%y %I:%M %p")
        except ValueError:
            continue
        messages.append({
            "datetime": dt,
            "sender": sender.strip(),
            "message": text.strip()
        })

if not messages:
    print("❌ No se detectaron mensajes.")
    exit()

# -------- CONVERTIR A DATAFRAME Y FILTRAR --------
df = pd.DataFrame(messages)
df = df[~df['message'].str.contains('<Multimedia omitido>', regex=False)]
df = df[df['message'].str.strip() != '']
df['month'] = df['datetime'].dt.to_period('M')
df['hour'] = df['datetime'].dt.hour

# -------- CLASIFICAR POR RANGO HORARIO --------
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

# -------- ANÁLISIS --------
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

# -------- GRAFICAS (matplotlib) --------
fig, axs = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle("📊 Análisis del Chat de WhatsApp", fontsize=18)

# Mensajes por mes
axs[0, 0].bar(mensajes_por_mes.index.astype(str), mensajes_por_mes.values, color='skyblue')
axs[0, 0].set_title("🗓️ Mensajes por mes")
axs[0, 0].tick_params(axis='x', rotation=45)
for i, v in enumerate(mensajes_por_mes.values):
    axs[0, 0].text(i, v + 1, str(v), ha='center')

# Mensajes por persona
axs[0, 1].bar(mensajes_por_usuario.index, mensajes_por_usuario.values, color='salmon')
axs[0, 1].set_title("👤 Mensajes por persona")
axs[0, 1].tick_params(axis='x', rotation=45)
for i, v in enumerate(mensajes_por_usuario.values):
    axs[0, 1].text(i, v + 1, str(v), ha='center')

# Nube de palabras
axs[1, 0].imshow(wordcloud, interpolation='bilinear')
axs[1, 0].axis("off")
axs[1, 0].set_title("☁️ Palabras más usadas")

# Emojis más usados
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

# -------- TABLA DE RANGOS HORARIOS --------
print("\n🕓 Cantidad de mensajes por rango horario:")
print(mensajes_por_rango)

# -------- NUBE INTERACTIVA (plotly) --------
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
