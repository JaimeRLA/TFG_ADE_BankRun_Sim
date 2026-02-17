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
# Parámetros cliente
k_ruido_cliente = 10 
x0_ruido_cliente = 0.4

# Parámetros no cliente
k_ruido_no_cliente = 12 
x0_no_cliente = 0.45 

# --- PESOS DE LA DECISIÓN (Suman 1.0) ---
PESO_NOTICIA = 0.4   # Impacto de los medios
PESO_SOCIAL = 0.5    # Lo que hacen sus vecinos (efecto rebaño)
PESO_LIQUIDEZ = 0.1  # Salud financiera real del banco