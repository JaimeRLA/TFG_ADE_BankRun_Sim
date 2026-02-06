# parametros.py

# --- CONFIGURACIÓN DEMOGRÁFICA ---
EDAD_MEDIA = 50
EDAD_DESVIACION = 18
EDAD_MINIMA = 18
EDAD_MAXIMA = 95

# --- LÓGICA DE SALDOS (€) ---
SALDO_RETAIL_RANGO = (1000, 15000)
SALDO_EMPRESA_RANGO = (50000, 200000)
DISTRIBUCION_TIPOS = ["Retail", "VIP", "Empresa"]
PROBABILIDADES_TIPOS = [0.75, 0.20, 0.05]

# --- UMBRALES DE COMPORTAMIENTO ---
# Cuanto más bajo el umbral, más fácil es que entren en pánico
UMBRAL_RETIRADA_CLIENTE = 0.5
UMBRAL_ALERTA_NOCLIENTE = 0.4

# --- PESOS DE LA DECISIÓN (Suman 1.0) ---
# Define qué influye más en el cliente
PESO_NOTICIA = 0.4   # Impacto de los medios
PESO_SOCIAL = 0.5    # Lo que hacen sus vecinos (efecto rebaño)
PESO_LIQUIDEZ = 0.1  # Salud financiera real del banco