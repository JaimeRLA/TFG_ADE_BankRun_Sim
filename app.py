import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
import numpy as np
import time
from simulation.model import BancoModel

st.set_page_config(page_title="Stress Test Lab v2 - Human Impact", layout="wide")
st.markdown("""
    <style>
        .block-container {
            padding-top: 3rem !important; /* Damos un poco de aire arriba */
        }

        /* TÍTULO (Columna 1) */
        [data-testid="stHorizontalBlock"]:first-of-type > div:nth-child(1) {
            margin-top: -90px !important; 
        }

        /* BOTÓN (Columna 2) */
        /* Lo bajamos a una posición visualmente equilibrada */
        [data-testid="stHorizontalBlock"]:first-of-type > div:nth-child(2) {
            margin-top: 30px !important;  /* Valor positivo para BAJARLO */
        }

        [data-testid="stSidebarContent"] {
            padding-top: 0rem !important;
        }

        .stButton button {
            float: right;
        }

        header { visibility: hidden; height: 0px; }
        [data-testid="stDecoration"] { display: none; }
    </style>
""", unsafe_allow_html=True)
# --- FUNCIONES AUXILIARES ---
def get_color_fuga(agente):
    if not agente.alcance_noticia:
        return 'rgb(34, 139, 34)'
    fuga = agente.porcentaje_retirado
    if fuga < 0.05:
        return 'rgb(255, 165, 0)'
    sensibilidad = min((fuga - 0.05) / 0.20, 1.0)
    return f'rgb(255, {int(165 * (1 - sensibilidad))}, 0)'

def get_color_no_cliente(agente):
    if not agente.alcance_noticia:
        return 'rgb(100, 100, 100)'
    intensidad = np.nan_to_num(agente.porcentaje_retirado)
    return f'rgb({int(100 * (1 - intensidad))}, {int(150 + (105 * intensidad))}, 255)'

# --- SIDEBAR: CONFIGURACIÓN ---
st.markdown("""<style>.sidebar-title { margin-top: -55px; }</style>""", unsafe_allow_html=True)

st.sidebar.markdown("""
    <div class="sidebar-title">
        <h1 style='font-size: 40px; color: white; margin-bottom: 0px;'>Stress Test Lab</h1>
        <p style='font-size: 16px; color: #808495; margin-top: 0px;'>
            Simulación de Impacto Crítico<br>(Población: 3M)
        </p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.header("🛡️ Parámetros de la Crisis")
score = st.sidebar.slider("Gravedad de la Noticia", 0.0, 1.0, 0.8)
validez = st.sidebar.slider("Credibilidad del Medio", 0.0, 1.0, 0.9)
difusion = st.sidebar.slider("% Difusión Inicial (Alcance)", 0.0, 1.0, 0.4)

st.sidebar.header("⏱️ Control de Simulación")
velocidad = st.sidebar.slider("Segundos por turno", 0.0, 2.0, 0.1)
max_turnos = st.sidebar.slider("Turnos máximos", 5, 500, 150)
n_simulaciones_objetivo = st.sidebar.slider("Nº de Simulaciones a promediar", 1, 50, 5)

st.sidebar.header("👥 Estructura de la Población")
n_agentes = st.sidebar.slider("Nº Total de Nodos (Red)", 50, 1000, 200)
p_externos = st.sidebar.slider("% de No-Clientes", 0.0, 0.5, 0.2)

st.sidebar.header("💰 Estructura Bancaria")
dep_input = st.sidebar.number_input("Depósitos Totales (€)", value=10000000)
encaje = st.sidebar.slider("% Liquidez Inmediata (Caja)", 0.01, 0.30, 0.10)



# --- ÁREA PRINCIPAL ---
#--- CABECERA (Título y Botón) ---
# Usamos una proporción que deje espacio al título y pegue el botón a la derecha
col_tit, col_btn = st.columns([2.5, 1])
p_titulo = col_tit.empty()
p_boton = col_btn.empty()

# --- CUERPO (Grafo y Estadísticas) ---


col_graph, col_stats = st.columns([2, 1])
placeholder_grafo = col_graph.empty()
placeholder_metricas = col_stats.empty()
placeholder_informe_final = st.empty()

# --- LÓGICA ---
if p_boton.button("Lanzar Simulación Progresiva", use_container_width=True):
    historico_series = []
    todos_los_datos_agentes = []
    
    for sim_iter in range(n_simulaciones_objetivo):
        
        model = BancoModel(n_agentes, dep_input, encaje, score, validez, difusion, p_no_clientes=p_externos)
        pos = nx.spring_layout(model.G, seed=42) 
        
        # Pre-generar las líneas de la red (Estructura fija durante el run)
        edge_x, edge_y = [], []
        for edge in model.G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.4, color='#555'), mode='lines', hoverinfo='none',showlegend=False)

        stats_data = {"paso": [], "liquidez": [], "huidas": [], "informadas": []}

        for t in range(max_turnos):
            model.step()
            agentes = model.schedule.agents
            liq_actual = model.liquidez_banco
            
            fuga_total = sum(a.porcentaje_retirado for a in agentes if a.tipo != "No-Cliente")
            personas_huidas = fuga_total * model.representacion_por_nodo
            nodos_inf = sum(1 for a in agentes if a.alcance_noticia)
            personas_inf = nodos_inf * model.representacion_por_nodo
            intensidad_rumor = (sum(a.porcentaje_retirado for a in agentes if a.tipo == "No-Cliente") / 
                                sum(1 for a in agentes if a.tipo == "No-Cliente")) if p_externos > 0 else 0

            stats_data["paso"].append(t)
            stats_data["liquidez"].append(liq_actual)
            stats_data["huidas"].append(personas_huidas)
            stats_data["informadas"].append(personas_inf)

            p_titulo.markdown(
            f"""
            <div style='margin-top: -15px; margin-bottom: 5px;'>
                <p style='margin: 0px; font-size: 36px; font-weight: 600; color: white;'>
                    Lanzando Simulación {sim_iter + 1}/{n_simulaciones_objetivo} ...
                </p>
            </div>
            """, 
            unsafe_allow_html=True
            )

            # 1. Dibujar Grafo 
            node_x, node_y, colors, text, sizes, symbols = [], [], [], [], [], []
            for a in agentes:
                x, y = pos[a.unique_id]
                node_x.append(x); node_y.append(y)
                if a.tipo == "No-Cliente":
                    colors.append(get_color_no_cliente(a)); sizes.append(11); symbols.append("diamond")
                    text.append(
                    f"<b>📢 OPINIÓN PÚBLICA (No-Cliente)</b><br>"
                    f"Estado: {'Difundiendo' if a.alcance_noticia else 'Inactivo'}<br>"
                    f"Intensidad Rumor: {a.porcentaje_retirado*100:.1f}%"
                )
                else:
                    colors.append(get_color_fuga(a)); sizes.append(15 if a.porcentaje_retirado > 0.1 else 13); symbols.append("circle")
                    text.append(
                    f"<b>🏦 CLIENTE ({a.tipo})</b><br>"
                    f"Población: {int(model.representacion_por_nodo):,}<br>"
                    f"Fuga: {a.porcentaje_retirado*100:.1f}%<br>"
                    f"Saldo: {a.saldo:,.0f}€"
                )

            node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', text=text,
                                   marker=dict(color=colors, size=sizes, symbol=symbols, line=dict(color='white', width=0.5)),showlegend=False)

            legend_traces = [
                go.Scatter(x=[None], y=[None], mode='markers',
                        marker=dict(size=8, color='rgb(34, 139, 34)', symbol='circle'), # Tamaño 8 para que sea más pequeño
                        name='Cliente: Tranquilo', showlegend=True),
                go.Scatter(x=[None], y=[None], mode='markers',
                        marker=dict(size=8, color='rgb(255, 165, 0)', symbol='circle'),
                        name='Cliente: Alerta (Fuga < 5%)', showlegend=True),
                go.Scatter(x=[None], y=[None], mode='markers',
                        marker=dict(size=8, color='rgb(255, 0, 0)', symbol='circle'),
                        name='Cliente: Fuga Crítica', showlegend=True),
                go.Scatter(x=[None], y=[None], mode='markers',
                        marker=dict(size=8, color='rgb(100, 100, 100)', symbol='diamond'),
                        name='Opinión: Inactiva', showlegend=True),
                go.Scatter(x=[None], y=[None], mode='markers',
                        marker=dict(size=8, color='rgb(100, 150, 255)', symbol='diamond'),
                        name='Opinión: Difundiendo', showlegend=True),
            ]
            
            fig_grafo = go.Figure(data=[edge_trace, node_trace] + legend_traces)

            # --- FIGURA DEL GRAFO ---
            fig_grafo = go.Figure(data=[edge_trace, node_trace] + legend_traces)

            fig_grafo.update_layout(
                title=f"Red de Influencia Social | Turno: {t}",
                template="plotly_dark",
                height=600,
                margin=dict(b=0, l=0, r=0, t=40),
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.0,              # Pegado al borde izquierdo
                    bgcolor="rgba(0,0,0,0.4)", 
                    font=dict(size=9),  # Texto pequeño
                    itemsizing='constant',
                    itemwidth=30,       # Símbolos más compactos
                    tracegroupgap=0     # Espacio mínimo entre grupos
                ),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )

            placeholder_grafo.plotly_chart(fig_grafo, use_container_width=True)

            # 2. Métricas y Gráfico Rojo
            with placeholder_metricas.container():
                st.metric("Clientes que han huido", f"{int(personas_huidas):,}")
                st.metric("Alcance Poblacional", f"{(personas_inf / model.poblacion_objetivo)*100:.1f}%")
                st.metric("Intensidad Rumor", f"{intensidad_rumor*100:.1f}%")
                
                fig_liq = go.Figure(go.Scatter(x=stats_data["paso"], y=stats_data["liquidez"], fill='tozeroy', line=dict(color="#FF0000")))
                fig_liq.update_layout(title="Fuga de Depósitos (Caja)", template="plotly_dark", height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_liq, use_container_width=True)

            time.sleep(velocidad)
            if liq_actual <= 0: break
    
        # Capturamos el estado de los agentes al final de ESTA simulación específica
        for a in model.schedule.agents:
            if a.tipo != "No-Cliente":
                if a.edad < 35: cat_edad = "1. Jóvenes (<35)"
                elif a.edad < 60: cat_edad = "2. Adultos (35-60)"
                else: cat_edad = "3. Séniors (>60)"
                
                todos_los_datos_agentes.append({
                    "Simulacion": sim_iter,
                    "Rango Edad": cat_edad,
                    "Tipo": a.tipo,
                    "Fuga %": a.porcentaje_retirado * 100,
                    "Sexo": a.sexo,
                    "Protegido FGD": "Sí" if a.protegido_fgd else "No"
                })
        # ---------------------------------------
        
        historico_series.append(stats_data)

    # --- INFORME FINAL PROMEDIADO ---
    with placeholder_informe_final.container():
        st.markdown("---")
        st.header(f"Informe Agregado de Riesgo ({n_simulaciones_objetivo} simulaciones)")
        
        # 1. Procesamiento de datos estadísticos temporales
        max_t = max(len(s["paso"]) for s in historico_series)
        turnos_quiebra = [len(s["paso"]) for s in historico_series if s['liquidez'][-1] <= 0]
        prob_quiebra = (len(turnos_quiebra) / n_simulaciones_objetivo) * 100
        turno_medio_colapso = np.mean(turnos_quiebra) if turnos_quiebra else 0
        
        def get_avg(key, pad_val=0):
            matrix = []
            for s in historico_series:
                vals = s[key]
                # Padding para normalizar la duración de las simulaciones
                padding = [vals[-1] if pad_val is None else pad_val] * (max_t - len(vals))
                matrix.append(vals + padding)
            return np.mean(matrix, axis=0)

        avg_huidas = get_avg("huidas", None)
        avg_inf = get_avg("informadas", None)
        avg_liq = get_avg("liquidez", 0)

        # 2. Procesamiento de datos de agentes (PROMEDIO REAL DE TODAS LAS SIMULACIONES)
        # Se asume que has guardado 'todos_los_datos_agentes' en el bucle principal
        df_global = pd.DataFrame(todos_los_datos_agentes)
        
        resumen_edad = df_global.groupby("Rango Edad")["Fuga %"].mean().reset_index()
        resumen_tipo = df_global.groupby("Tipo")["Fuga %"].mean().reset_index()
        resumen_sexo = df_global.groupby("Sexo")["Fuga %"].mean()
        
        st.markdown("<div style='padding: 15px;'></div>", unsafe_allow_html=True)
        
        st.markdown("### 1. Estadísticas Básicas")

        # 3. Métricas de Cabecera
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Media Fugados Total", f"{int(avg_huidas[-1]):,}")
        col2.metric("Alcance Poblacional Medio", f"{(avg_inf[-1] / model.poblacion_objetivo)*100:.1f}%")
        col3.metric("Prob. de Quiebra", f"{prob_quiebra:.0f}%", 
                  delta="Riesgo Crítico" if prob_quiebra > 50 else None, delta_color="inverse")
        col4.metric("Turno Medio Colapso", f"{turno_medio_colapso:.1f}" if turno_medio_colapso > 0 else "N/A")
        col5.metric("Supervivencia Media", f"{(np.mean([len(s['paso']) for s in historico_series]) / max_turnos)*100:.1f}%")
        
        st.markdown("<div style='padding: 15px;'></div>", unsafe_allow_html=True)

        # --- SECCIÓN: ANÁLISIS POR SEGMENTOS PROMEDIADOS ---
        st.markdown("### 2. Comportamiento por Segmento y Perfil (Media Global)")
        c_seg1, c_seg2, c_seg3 = st.columns([1.5, 1.5, 1])
        
        with c_seg1:
            fig_edad = go.Figure(data=[
                go.Bar(
                    x=resumen_edad["Rango Edad"], 
                    y=resumen_edad["Fuga %"], 
                    marker_color=['#636EFA', '#EF553B', '#00CC96']
                )
            ])
            fig_edad.update_layout(
                title="Intensidad de Fuga Media por Generación", 
                template="plotly_dark", height=300, margin=dict(t=30, b=0, l=0, r=0),
                yaxis_title="% Retirado"
            )
            st.plotly_chart(fig_edad, use_container_width=True)
            
        with c_seg2:
            fig_seg = go.Figure(data=[
                go.Bar(
                    x=resumen_tipo["Tipo"], 
                    y=resumen_tipo["Fuga %"], 
                    marker_color=['#00CC96', '#FFA15A', '#EF553B']
                )
            ])
            fig_seg.update_layout(title="Intensidad de Fuga por Perfil", template="plotly_dark", height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_seg, use_container_width=True)
            
        with c_seg3:
            st.write("**Impacto Medio por Género**")
            for genero, valor in resumen_sexo.items():
                st.write(f"{'Hombre' if genero == 'H' else 'Mujer'}: **{valor:.1f}%**")
            
            avg_fgd = df_global[df_global['Protegido FGD'] == 'Sí']['Fuga %'].mean()
            st.caption(f"Fuga media en protegidos FGD: {avg_fgd:.1f}%")

        st.markdown("<div style='padding: 15px;'></div>", unsafe_allow_html=True)

        st.markdown("### 3. Análisis de Distribución y Tendencia")
        
        graf_izq, graf_der = st.columns(2)

        with graf_izq:
            fig_final = go.Figure()
            fig_final.add_trace(go.Scatter(y=avg_inf, name="Media Informados", line=dict(dash='dash', color='orange')))
            fig_final.add_trace(go.Scatter(y=avg_huidas, name="Media Retirados", line=dict(width=4, color='red')))
            fig_final.update_layout(title="Dinámica Social: Información vs Acción (Media)", template="plotly_dark", height=400, xaxis_title="Turnos")
            st.plotly_chart(fig_final, use_container_width=True)

        with graf_der:
            if turnos_quiebra:
                fig_hist = go.Figure(data=[go.Histogram(x=turnos_quiebra, nbinsx=15, marker_color='#FF4B4B', opacity=0.7)])
                fig_hist.update_layout(
                    title="Distribución Temporal de las Quiebras",
                    template="plotly_dark", height=400, xaxis_title="Turno de quiebra",
                    yaxis_title="Nº de Simulaciones", bargap=0.1
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No hubo quiebras suficientes para generar el histograma.")

        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(y=avg_liq, fill='tozeroy', name="Liquidez Media", line=dict(color="#00FFCC")))
        fig_area.update_layout(title="Salud Financiera Media (Reserva de Liquidez)", template="plotly_dark", height=350, xaxis_title="Turnos", yaxis_title="Euros (€)")
        st.plotly_chart(fig_area, use_container_width=True)

        st.info(f"💡 **Interpretación**: El turno medio de colapso ({turno_medio_colapso:.1f}) indica la velocidad de la corrida. " 
                f"El segmento que más capital retira en promedio es **{resumen_tipo.loc[resumen_tipo['Fuga %'].idxmax(), 'Tipo']}**.")












