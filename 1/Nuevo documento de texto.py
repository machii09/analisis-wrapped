import re
from collections import defaultdict, Counter

# ===== CONFIGURACIÓN =====
archivo_chat = 'Chat.txt'

# Pedir al usuario las palabras, separadas por comas
entrada = input("Escribe las palabras que quieres buscar (separadas por comas): ")
palabras_a_buscar = [p.strip().lower() for p in entrada.split(',') if p.strip()]

if not palabras_a_buscar:
    print("No ingresaste palabras para buscar. Saliendo...")
    exit()

# ===== PROCESO =====
conteo = defaultdict(Counter)

# Expresión regular para formato con "a. m." o "p. m."
patron_linea = re.compile(r'^\d{1,2}/\d{1,2}/\d{4}, \d{1,2}:\d{2} [ap]\. m\. - (.*?): (.*)$')

with open(archivo_chat, 'r', encoding='utf-8') as f:
    for linea in f:
        linea = linea.strip()
        match = patron_linea.match(linea)
        if match:
            persona = match.group(1)
            mensaje = match.group(2).lower()

            for palabra in palabras_a_buscar:
                ocurrencias = len(re.findall(r'\b' + re.escape(palabra) + r'\b', mensaje))
                if ocurrencias > 0:
                    conteo[persona][palabra] += ocurrencias

# ===== RESULTADOS =====
if conteo:
    for persona, counter in conteo.items():
        print(f'\nPalabras contadas para {persona}:')
        for palabra, cantidad in counter.items():
            print(f'  "{palabra}": {cantidad}')
else:
    print("No se encontraron coincidencias en el chat.")
