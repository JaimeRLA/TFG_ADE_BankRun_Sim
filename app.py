import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
import numpy as np
import time
from simulation.model import BancoModel

st.set_page_config(page_title="Stress Test Lab v2 - Human Impact", layout="wide")

# --- FUNCIONES AUXILIARES ---
def get_color_fuga(agente):
    """
    Lógica de color para CLIENTES:
    Verde: No conoce la noticia.
    Naranja: Conoce la noticia pero fuga mínima.
    Rojo: Fuga crítica (escala sensible 5%-25%).
    """
    if not agente.alcance_noticia:
        return 'rgb(34, 139, 34)'  # Verde (Neutro)
    
    fuga = agente.porcentaje_retirado
    
    if fuga < 0.05:
        return 'rgb(255, 165, 0)' # Naranja (Informado)
    
    # Degradado sensible hacia el Rojo
    sensibilidad = min((fuga - 0.05) / 0.20, 1.0)
    r = 255
    g = int(165 * (1 - sensibilidad))
    b = 0
    return f'rgb({r},{g},{b})'

def get_color_no_cliente(agente):
    """
    Lógica de color para NO-CLIENTES:
    Gris: No conocen la noticia.
    Cian/Azul: Conocen la noticia (Brillo según intensidad de rumor).
    """
    if not agente.alcance_noticia:
        return 'rgb(100, 100, 100)' # Gris oscuro (Inactivo)
    
    # Degradado de Azul claro a Cian intenso según rumor
    intensidad = agente.porcentaje_retirado
    b = 255
    r = int(0 + (100 * (1 - intensidad)))
    g = int(150 + (105 * intensidad))
    return f'rgb({r},{g},{b})'

# --- SIDEBAR: CONFIGURACIÓN ---

# Inyección de CSS para corregir el solapamiento y posicionamiento
st.markdown(
    """
    <style>
        .sidebar-title {
            margin-top: -55px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Título de la Sidebar
st.sidebar.markdown(
    """
    <div class="sidebar-title">
        <h1 style='font-size: 36px; color: white; margin-bottom: 0px;'>Stress Test Lab</h1>
        <p style='font-size: 16px; color: #808495; margin-top: 0px;'>
            Simulación de Impacto Crítico<br>(Población: 3M)
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

st.sidebar.divider()
st.sidebar.header("🛡️ Parámetros de la Crisis")
score = st.sidebar.slider("Gravedad de la Noticia", 0.0, 1.0, 0.8)
validez = st.sidebar.slider("Credibilidad del Medio", 0.0, 1.0, 0.9)
difusion = st.sidebar.slider("% Difusión Inicial (Alcance)", 0.0, 1.0, 0.4)

st.sidebar.header("⏱️ Control de Simulación")
velocidad = st.sidebar.slider("Segundos por turno", 0.0, 2.0, 0.5)
max_turnos = st.sidebar.slider("Turnos máximos", 5, 500, 150)

st.sidebar.header("👥 Estructura de la Población")
n_agentes = st.sidebar.slider("Nº Total de Nodos (Red)", 50, 1000, 200)
p_externos = st.sidebar.slider("% de No-Clientes (Propagadores)", 0.0, 0.5, 0.2)

st.sidebar.header("💰 Estructura Bancaria")
dep_input = st.sidebar.number_input("Depósitos Totales de Clientes (€)", value=10000000)
encaje = st.sidebar.slider("% Liquidez Inmediata (Caja)", 0.01, 0.30, 0.10)
liq_inicial_ref = dep_input * encaje

# --- ESCALA HUMANA PARA EL TFG ---
poblacion_objetivo = 3000000
representacion_por_nodo = poblacion_objetivo / n_agentes

# --- EJECUCIÓN ---

if st.button("Lanzar Simulación Progresiva"):
    model = BancoModel(n_agentes, dep_input, encaje, score, validez, difusion, p_no_clientes=p_externos)
    pos = nx.spring_layout(model.G, seed=42) 
    
    col_graph, col_stats = st.columns([2, 1])
    placeholder_grafo = col_graph.empty()
    placeholder_metricas = col_stats.empty()

    stats_data = {
        "paso": [],
        "liquidez": [],
        "personas_huidas": [],
        "personas_informadas": [],
        "prestamos": [],
    }

    # --- BUCLE DE SIMULACIÓN ---
    for t in range(max_turnos):
        model.step()
        agentes = model.schedule.agents
        liq_actual = model.liquidez_banco
        
        # Métrica clave: Suma de la fuga SOLO de clientes
        fuga_total_equiv = sum(a.porcentaje_retirado for a in agentes if a.tipo != "No-Cliente")
        personas_huidas = fuga_total_equiv * representacion_por_nodo
        
        # Alcance de noticia escalado a población real
        nodos_informados = sum(1 for a in agentes if a.alcance_noticia)
        personas_informadas = nodos_informados * representacion_por_nodo

        # No-Clientes en Alarma (Propagadores)
        # En lugar de buscar el estado "ALERTA" exacto, contamos por intensidad real
        alerta_nocl = sum(1 for a in agentes if a.tipo == "No-Cliente" and a.porcentaje_retirado > 0.05)
        intensidad_rumor = (sum(a.porcentaje_retirado for a in agentes if a.tipo == "No-Cliente") / 
                            sum(1 for a in agentes if a.tipo == "No-Cliente")) if p_externos > 0 else 0


        # Guardar datos
        stats_data["paso"].append(t)
        stats_data["liquidez"].append(liq_actual)
        stats_data["personas_huidas"].append(personas_huidas)
        stats_data["personas_informadas"].append(personas_informadas)
        stats_data["prestamos"].append(model.prestamos_activos)

        # 1. Dibujar Grafo
        # --- DENTRO DEL BUCLE DE SIMULACIÓN EN app.py ---
        node_x, node_y, colors, text, sizes, symbols = [], [], [], [], [], []
        for a in agentes:
            x, y = pos[a.unique_id]
            node_x.append(x)
            node_y.append(y)
            
            if a.tipo == "No-Cliente":
                color_actual = get_color_no_cliente(a)
                sizes.append(11)
                symbols.append("diamond") # Símbolo distinto para No-Clientes
                text.append(
                    f"<b>📢 OPINIÓN PÚBLICA (No-Cliente)</b><br>"
                    f"Estado: {'Difundiendo' if a.alcance_noticia else 'Inactivo'}<br>"
                    f"Intensidad Rumor: {a.porcentaje_retirado*100:.1f}%"
                )
            else:
                color_actual = get_color_fuga(a)
                sizes.append(15 if a.porcentaje_retirado > 0.1 else 13)
                symbols.append("circle")
                text.append(
                    f"<b>🏦 CLIENTE ({a.tipo})</b><br>"
                    f"Población: {int(representacion_por_nodo):,}<br>"
                    f"Fuga: {a.porcentaje_retirado*100:.1f}%<br>"
                    f"Saldo: {a.saldo:,.0f}€"
                )
            colors.append(color_actual)

        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers', hoverinfo='text', text=text,
            marker=dict(
                color=colors, 
                size=sizes, 
                symbol=symbols, # Aplicamos los símbolos
                line=dict(color='white', width=1)
            )
        )

        node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', text=text,
                                marker=dict(color=colors, size=sizes, line=dict(color='white', width=1)))
        
        edge_x, edge_y = [], [],
        for edge in model.G.edges():
            x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.4, color='#555'), mode='lines', hoverinfo='none')

        fig_grafo = go.Figure(data=[edge_trace, node_trace],
                             layout=go.Layout(title=f"Turno: {t} | Liquidez: {liq_actual:,.0f}€",
                             template="plotly_dark", showlegend=False, height=600, margin=dict(b=0, l=0, r=0, t=40),
                             xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                             yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
        placeholder_grafo.plotly_chart(fig_grafo, use_container_width=True)

        # 2. Métricas Laterales (Recuperando el gráfico de Evolución de Caja)
        with placeholder_metricas.container():
            st.metric("Clientes que han huido", f"{int(personas_huidas):,}")
            st.metric("Alcance Poblacional", f"{personas_informadas / poblacion_objetivo}")
            st.metric("Intensidad Rumor Externo", f"{intensidad_rumor*100:.1f}%")
        

            
            # --- RECUPERACIÓN DEL GRÁFICO ANTERIOR: EVOLUCIÓN DE CAJA ---
            df_hist = pd.DataFrame({
                "Turno": stats_data["paso"], 
                "Liquidez": stats_data["liquidez"]
            })
            
            fig_liq = go.Figure()
            fig_liq.add_trace(go.Scatter(
                x=df_hist["Turno"], 
                y=df_hist["Liquidez"], 
                name="Efectivo disponible", 
                fill='tozeroy', # Rellena el área debajo de la línea
                line=dict(color="#FF0000", width=2)
            ))
            
            fig_liq.update_layout(
                title="Fuga de Depósitos (Caja)", 
                template="plotly_dark", 
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Turno",
                yaxis_title="Euros (€)"
            )
            st.plotly_chart(fig_liq, use_container_width=True)
            
            # Nota para el TFG sobre solvencia (opcional, para mantener el rigor)
            st.caption(f"Activos Ilíquidos (Préstamos): {model.prestamos_activos:,.0f} €")

        time.sleep(velocidad)
        if liq_actual <= 0:
            st.error("🚨 QUIEBRA TÉCNICA: El banco se ha quedado sin efectivo.")
            break

    # --- ESTADÍSTICAS FINALES ---
    st.markdown("---")
    st.header(f"📊 Informe de Impacto Humano (Población: {str(poblacion_objetivo)[0]}M)")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Clientes Fugados", f"{int(personas_huidas):,}")
    col2.metric("Personas Informadas", f"{int(personas_informadas):,}")
    col3.metric("Alcance Poblacional", f"{(personas_informadas / poblacion_objetivo)*100:.1f}%")
    col4.metric("Propagadores Activos", alerta_nocl)

    # Gráfica Final: Evolución Humana
    df_final = pd.DataFrame(stats_data)
    fig_final = go.Figure()
    fig_final.add_trace(go.Scatter(x=df_final["paso"], y=df_final["personas_informadas"], name="Informados (Saben la noticia)", line=dict(dash='dash', color='orange')))
    fig_final.add_trace(go.Scatter(x=df_final["paso"], y=df_final["personas_huidas"], name="Retirados (Han sacado dinero)", line=dict(width=4, color='red')))
    
    fig_final.update_layout(title="Dinámica Social: Información vs Acción", yaxis_title="Número de Personas", template="plotly_dark")
    st.plotly_chart(fig_final, use_container_width=True)

    st.info(f"💡 **Interpretación TFG:** El modelo escalado muestra que el banco colapsa cuando aproximadamente {int(personas_huidas)} clientes retiran sus fondos, movidos por una red de desconfianza donde la opinión pública (No-Clientes) alcanzó una intensidad del {intensidad_rumor*100:.1f}%.")