import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
import numpy as np
import time
from simulation.model import BancoModel

st.set_page_config(page_title="Stress Test Lab v2", layout="wide")


# --- SIDEBAR: CONFIGURACIÓN ---
st.sidebar.header("🛡️ Parámetros de la Crisis")
score = st.sidebar.slider("Gravedad de la Noticia", 0.0, 1.0, 0.8)
validez = st.sidebar.slider("Credibilidad del Medio", 0.0, 1.0, 0.9)
difusion = st.sidebar.slider("% Difusión Inicial (Alcance)", 0.0, 1.0, 0.4)
# Añade esto en la sección de configuración de la sidebar
st.sidebar.header("⏱️ Control de Simulación")
velocidad = st.sidebar.slider("Segundos por turno", 0.0, 2.0, 0.5)
max_turnos = st.sidebar.slider("Turnos máximos", 5, 500, 150)

st.sidebar.header("👥 Estructura de la Población")
n_agentes = st.sidebar.slider("Nº Total de Nodos (Red)", 50, 1000, 200)
p_externos = st.sidebar.slider("% de No-Clientes (Propagadores)", 0.0, 0.5, 0.2)

# --- SIDEBAR ---
st.sidebar.header("💰 Estructura Bancaria")
dep_input = st.sidebar.number_input("Depósitos Totales de Clientes (€)", value=10000000)
# Podrías añadir un slider para que el usuario elija el encaje legal (liquidez)
encaje = st.sidebar.slider("% Liquidez Inmediata)", 0.01, 0.20, 0.10)
liq_input=dep_input*encaje


# --- EJECUCIÓN ---
if st.button("🚀 Lanzar Simulación Small-World"):
    # Inicializamos el modelo con los nuevos parámetros
    model = BancoModel(n_agentes, dep_input,encaje, score, validez, difusion, p_no_clientes=p_externos)
    
    # Layout fijo para evitar que el grafo salte
    pos = nx.spring_layout(model.G, seed=42) 
    
    # Contenedores para visualización dinámica
    col_graph, col_stats = st.columns([2, 1])
    placeholder_grafo = col_graph.empty()
    placeholder_metricas = col_stats.empty()

    # Históricos para estadísticas finales
    stats_data = {
        "paso": [],
        "liquidez": [],
        "clientes_huidos": [],
        "no_clientes_alerta": [],
        "alcance_noticia": []
    }

    # --- BUCLE DE SIMULACIÓN ---
    stats_data["prestamos"] = [] # Añadir a tu diccionario de stats
    for t in range(max_turnos):
        # ... dentro del for t in range(150):
        prestamos = model.prestamos_activos
        stats_data["prestamos"].append(prestamos)
        model.step()
        
        agentes = model.schedule.agents
        liq_actual = model.liquidez_banco
        huidos = sum(1 for a in agentes if a.estado == "RETIRADO")
        alerta = sum(1 for a in agentes if a.tipo == "No-Cliente" and a.estado == "ALERTA")
        conocen_noticia = sum(1 for a in agentes if a.alcance_noticia)

        # Guardar datos
        stats_data["paso"].append(t)
        stats_data["liquidez"].append(liq_actual)
        stats_data["clientes_huidos"].append(huidos)
        stats_data["no_clientes_alerta"].append(alerta)
        stats_data["alcance_noticia"].append(conocen_noticia)

        # 1. Dibujar Conexiones (Edges)
        edge_x, edge_y = [], []
        for edge in model.G.edges():
            x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.4, color='#555'), mode='lines', hoverinfo='none')

        # 2. Dibujar Nodos (Agentes)
        node_x, node_y, colors, text, sizes = [], [], [], [], []

        for a in agentes:
            x, y = pos[a.unique_id]
            node_x.append(x)
            node_y.append(y)
            
            # --- NUEVA JERARQUÍA DE COLORES ---
            if a.estado == "RETIRADO":
                color = "#FF0000"  # ROJO: Ya han huido
            elif a.alcance_noticia:
                color = "#FF8C00"  # NARANJA: Sabe la noticia pero sigue en el banco
            else:
                color = "#00FF7F"  # VERDE: No sabe nada / Está en calma
            
            # Distinción visual para No-Clientes (más pequeños o con borde diferente)
            if a.tipo == "No-Cliente":
                sizes.append(9)
                # Si es No-cliente y está en ALERTA, lo marcamos naranja fuerte
                if a.estado == "ALERTA": color = "#FFA500" 
            else:
                sizes.append(13)
                
            colors.append(color)
            # Calculamos el grado (número de conexiones) del nodo actual
            num_conexiones = len(list(model.G.neighbors(a.unique_id)))

            text.append(
                f"ID: {a.unique_id} | {a.tipo}<br>"
                f"Conexiones: {num_conexiones}<br>"  # <--- NUEVO
                f"Edad: {a.edad} | Estado: {a.estado}<br>"
                f"Saldo: {round(a.saldo,2)} <br>"
                f"Sabe noticia: {'Sí' if a.alcance_noticia else 'No'}"
            )
        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers', hoverinfo='text', text=text,
            marker=dict(
                color=colors, 
                size=sizes, 
                line_width=1.5, 
                line=dict(color='white')
            )
        )

        
        # 3. Renderizar Grafo
        fig = go.Figure(data=[edge_trace, node_trace],
                         layout=go.Layout(
                            title=f"Estructura Small-World | Turno: {t} | Liquidez: {liq_actual:,.0f}€",
                            template="plotly_dark", showlegend=False,
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            margin=dict(b=0, l=0, r=0, t=40), height=600
                         ))
        
        placeholder_grafo.plotly_chart(fig, use_container_width=True)

        
        
        # 4. Gráfica de Liquidez lateral
        # --- 4. ACTUALIZACIÓN DE MÉTRICAS LATERALES ---
        with placeholder_metricas.container():
            # A. Gráfico de Barras del Balance (Solvencia vs Liquidez)
            # Mostramos cuánto queda en caja frente a lo que está prestado
            fig_balance = go.Figure(data=[
                go.Bar(name='Caja (Liquidez)', x=['Estado'], y=[liq_actual], marker_color='#00FF7F'),
                go.Bar(name='Préstamos (Activos)', x=['Estado'], y=[prestamos], marker_color='#555555')
            ])
            fig_balance.update_layout(
                barmode='stack', 
                title="Balance de Activos (€)", 
                template="plotly_dark", 
                height=300,
                showlegend=True,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_balance, use_container_width=True)

            # B. Gráfico de Evolución de Liquidez (Histórico)
            df_plot = pd.DataFrame({
                "Paso": stats_data["paso"], 
                "Liquidez": stats_data["liquidez"]
            })
            
            fig_liq = go.Figure()
            fig_liq.add_trace(go.Scatter(
                x=df_plot["Paso"], 
                y=df_plot["Liquidez"], 
                name="Efectivo disponible", 
                fill='tozeroy', # Rellena el área debajo de la línea
                line=dict(color="#FF0000", width=2)
            ))
            fig_liq.update_layout(
                title="Fuga de Depósitos (Caja)", 
                template="plotly_dark", 
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Turno",
                yaxis_title="€"
            )
            st.plotly_chart(fig_liq, use_container_width=True)

        # Control de velocidad y parada
        time.sleep(velocidad)

        if liq_actual <= 0:
            st.error("🚨 QUIEBRA TÉCNICA: Reservas Agotadas.")
            # Opcional: podrías poner liq_actual = 0 para que el gráfico no muestre negativos
            break


    # Leyenda rápida debajo del grafo
    st.markdown("""
    <div style="display: flex; justify-content: space-around; font-weight: bold; padding: 10px; background-color: #1e1e1e; border-radius: 10px;">
        <span style="color: #00FF7F;">● Sin Información (Verde)</span>
        <span style="color: #FF8C00;">● Informado / Alerta (Naranja)</span>
        <span style="color: #FF0000;">● Dinero Retirado (Rojo)</span>
    </div>
    """, unsafe_allow_html=True)


    # --- SECCIÓN DE ESTADÍSTICAS FINALES ---
    st.markdown("---")
    st.header("📊 Informe de Impacto y Propagación")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_clientes = sum(1 for a in model.schedule.agents if a.tipo != "No-Cliente")
    efectividad_panico = (huidos / total_clientes) * 100
    viralidad_final = (conocen_noticia / n_agentes) * 100
    
    col1.metric("Tasa de Retirada", f"{efectividad_panico:.1f}%")
    col2.metric("Alcance de la Noticia", f"{viralidad_final:.1f}%")
    col3.metric("Liquidez Remanente", f"{(liq_actual/liq_input)*100:.1f}%")
    col4.metric("Propagadores Activos (No-Cl)", alerta)

    st.subheader("Análisis de Velocidad de Contagio")
    # Gráfica comparativa: Gente que conoce la noticia vs Gente que huye
    df_final = pd.DataFrame({
        "Turno": stats_data["paso"],
        "Conocen la Noticia": stats_data["alcance_noticia"],
        "Han Retirado Dinero": stats_data["clientes_huidos"],
        "No-Clientes en Alerta": stats_data["no_clientes_alerta"]
    })

    
    
    fig_final = go.Figure()
    fig_final.add_trace(go.Scatter(x=df_final["Turno"], y=df_final["Conocen la Noticia"], name="Alcance Noticia", line=dict(dash='dash')))
    fig_final.add_trace(go.Scatter(x=df_final["Turno"], y=df_final["Han Retirado Dinero"], name="Retiradas Reales", line=dict(width=4)))
    fig_final.add_trace(go.Scatter(x=df_final["Turno"], y=df_final["No-Clientes en Alerta"], name="Influencia Externa", line=dict(color='orange')))
    
    fig_final.update_layout(title="Dinámica de la Crisis: Información vs Acción", template="plotly_dark")
    st.plotly_chart(fig_final, use_container_width=True)

    st.info("💡 **Interpretación del TFG:** La brecha entre la línea de 'Alcance Noticia' y 'Retiradas Reales' representa la inercia del cliente. El papel de los 'No-Clientes' es actuar como catalizadores que cierran esa brecha mediante la presión social en la red Small-World.")

    # En el bloque de "ESTADÍSTICAS FINALES" de tu app principal
    st.subheader("📊 Perfil Demográfico de la Red")
    edades = [a.edad for a in model.schedule.agents]
    fig_hist = go.Figure(data=[go.Histogram(x=edades, nbinsx=20, marker_color='#00FF7F')])
    fig_hist.update_layout(
        title="Distribución de Edades de los Agentes",
        xaxis_title="Edad",
        yaxis_title="Cantidad de Personas",
        template="plotly_dark"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    