import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
import numpy as np
from simulation.model import BancoModel

st.set_page_config(page_title="CaixaBank Stress Test Lab v2", layout="wide")

# --- SIDEBAR: CONFIGURACIÓN ---
st.sidebar.header("🛡️ Parámetros de la Crisis")
score = st.sidebar.slider("Gravedad de la Noticia", 0.0, 1.0, 0.8)
validez = st.sidebar.slider("Credibilidad del Medio", 0.0, 1.0, 0.9)
difusion = st.sidebar.slider("% Difusión Inicial (Alcance)", 0.0, 1.0, 0.4)

st.sidebar.header("👥 Estructura de la Población")
n_agentes = st.sidebar.slider("Nº Total de Nodos (Red)", 50, 400, 200)
p_externos = st.sidebar.slider("% de No-Clientes (Propagadores)", 0.0, 0.5, 0.2)
liq_input = st.sidebar.number_input("Liquidez Bancaria Inicial (€)", value=2000000)

# --- EJECUCIÓN ---
if st.button("🚀 Lanzar Simulación Small-World"):
    # Inicializamos el modelo con los nuevos parámetros
    model = BancoModel(n_agentes, liq_input, score, validez, difusion, p_no_clientes=p_externos)
    
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
    for t in range(50):
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
            node_x.append(x); node_y.append(y)
            
            # Lógica de colores:
            if a.tipo == "No-Cliente":
                colors.append("#FFD700" if a.estado == "ALERTA" else "#4F4F4F") # Dorado (Alerta) o Gris
                sizes.append(9)
            else:
                colors.append("#FF0000" if a.estado == "RETIRADO" else "#00FF7F") # Rojo o Verde
                sizes.append(13)
            
            text.append(f"ID: {a.unique_id} | {a.tipo}<br>Estado: {a.estado}<br>Saldo: {a.saldo:,.0f}€")

        node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', text=text,
                                marker=dict(color=colors, size=sizes, line_width=1.5, line=dict(color='white')))

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
        df_plot = pd.DataFrame({"Paso": stats_data["paso"], "Liquidez": stats_data["liquidez"]})
        fig_liq = go.Figure()
        fig_liq.add_trace(go.Scatter(x=df_plot["Paso"], y=df_plot["Liquidez"], name="Liquidez", line=dict(color="#FF0000")))
        fig_liq.update_layout(title="Fuga de Depósitos", template="plotly_dark", height=300)
        placeholder_metricas.plotly_chart(fig_liq, use_container_width=True)

        if liq_actual <= 0:
            st.error("🚨 QUIEBRA TÉCNICA: Reservas Agotadas.")
            break

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