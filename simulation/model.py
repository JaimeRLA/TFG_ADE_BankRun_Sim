import networkx as nx
from mesa import Model
from mesa.time import RandomActivation
from mesa.space import NetworkGrid
from .agent import ClienteCaixa
import numpy as np

class BancoModel(Model):
    def __init__(self, n, total_depositos, encaje, news_score, news_validez, news_difusion, p_no_clientes=0.2):
        super().__init__()
        
        # --- LÓGICA FINANCIERA: SOLVENCIA VS LIQUIDEZ ---
        self.depositos_totales = total_depositos # Patrimonio total del banco
        self.coeficiente_reserva = encaje
        
        # El banco comienza con una liquidez basada en el encaje
        self.liquidez_banco = total_depositos * self.coeficiente_reserva
        self.liquidez_inicial = self.liquidez_banco
        # El dinero prestado (inmovilizado)
        self.prestamos_activos = total_depositos - self.liquidez_banco
        
        # --- PARÁMETROS DE LA CRISIS ---
        self.noticia_score = news_score
        self.noticia_validez = news_validez
        self.noticia_difusion = news_difusion

        # --- RED SOCIAL (SMALL WORLD) ---
        self.G = nx.powerlaw_cluster_graph(n, 3, 0.5)
        self.grid = NetworkGrid(self.G)
        self.schedule = RandomActivation(self)

        self.poblacion_objetivo = 3000000
        self.representacion_por_nodo = self.poblacion_objetivo / n

        # --- CREACIÓN DE AGENTES (CLÚSTERES) ---
        n_clientes_estimados = n * (1 - p_no_clientes)
        
        for i, node in enumerate(self.G.nodes()):
            es_cliente = self.random.random() > p_no_clientes
            
            if es_cliente:
                tipo = self.random.choices(["Retail", "VIP", "Empresa"], [75, 20, 5])[0]
                
                # Cada nodo representa un fragmento del total de depósitos
                saldo_promedio_nodo = self.depositos_totales / n_clientes_estimados
                
                if tipo == 'Empresa':
                    # Las empresas gestionan clústeres de capital mucho más grandes
                    saldo = self.random.uniform(saldo_promedio_nodo * 4, saldo_promedio_nodo * 8)
                elif tipo == 'VIP':
                    saldo = self.random.uniform(saldo_promedio_nodo * 1.5, saldo_promedio_nodo * 3)
                else:
                    saldo = self.random.uniform(saldo_promedio_nodo * 0.5, saldo_promedio_nodo * 1.2)
            else:
                tipo = "No-Cliente"
                saldo = 0
        
            # El agente ahora recibe el "saldo" como el patrimonio inicial del clúster
            a = ClienteCaixa(i, self, saldo, tipo)
            self.schedule.add(a)
            self.grid.place_agent(a, node)

    def step(self):
        self.schedule.step()
        
        # Seguridad financiera: la liquidez no puede ser negativa
        if self.liquidez_banco < 0:
            self.liquidez_banco = 0
            
        # Actualizamos depósitos totales basado en lo que realmente queda en el banco
        self.depositos_totales = sum(a.saldo for a in self.schedule.agents if a.tipo != "No-Cliente")