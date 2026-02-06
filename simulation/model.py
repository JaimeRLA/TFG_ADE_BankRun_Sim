import networkx as nx
from mesa import Model
from mesa.time import RandomActivation
from mesa.space import NetworkGrid
from .agent import ClienteCaixa
import numpy as np

class BancoModel(Model):
    def __init__(self, n, total_depositos,encaje, news_score, news_validez, news_difusion, p_no_clientes=0.2):
        super().__init__()
        
        # --- LÓGICA FINANCIERA: SOLVENCIA VS LIQUIDEZ ---
        # El total de depósitos es la suma de todo el dinero de los clientes
        self.depositos_totales = total_depositos
        
        # Coeficiente de reserva (Encaje legal): el banco solo guarda el 10% en efectivo
        self.coeficiente_reserva = encaje
        
        # El dinero que realmente hay en caja para afrontar retiradas
        self.liquidez_banco = total_depositos * self.coeficiente_reserva
        self.liquidez_inicial = self.liquidez_banco
        
        # El resto del dinero está prestado (activos ilíquidos a largo plazo)
        self.prestamos_activos = total_depositos - self.liquidez_banco
        
        # --- PARÁMETROS DE LA CRISIS ---
        self.noticia_score = news_score
        self.noticia_validez = news_validez
        self.noticia_difusion = news_difusion

        # --- RED SOCIAL (SMALL WORLD) ---
        # Usamos powerlaw_cluster_graph para simular redes humanas con comunidades
        self.G = nx.powerlaw_cluster_graph(n, 3, 0.5)
        self.grid = NetworkGrid(self.G)
        self.schedule = RandomActivation(self)

        # --- CREACIÓN DE AGENTES ---
        for i, node in enumerate(self.G.nodes()):
            # Decidir si el nodo es cliente o un propagador externo
            es_cliente = self.random.random() > p_no_clientes
            
            if es_cliente:
                # Segmentación de clientes (Retail 75%, VIP 20%, Empresa 5%)
                tipo = self.random.choices(["Retail", "VIP", "Empresa"], [75, 20, 5])[0]
                
                # Asignación de saldos proporcionales al total de depósitos del banco
                # (Ajuste simple para que la suma de saldos sea coherente con el input)
                saldo_base = self.depositos_totales / (n * (1 - p_no_clientes))
                if tipo == 'Empresa':
                    saldo = self.random.uniform(saldo_base * 5, saldo_base * 10)
                elif tipo == 'VIP':
                    saldo = self.random.uniform(saldo_base * 2, saldo_base * 4)
                else:
                    saldo = self.random.uniform(saldo_base * 0.1, saldo_base * 1.5)
            else:
                tipo = "No-Cliente"
                saldo = 0
            
            # Perfil demográfico
            edad_random = self.random.gauss(50, 18) 
            edad = int(np.clip(edad_random, 18, 95))
            
            # Edad específica para gestores de empresas
            if tipo == "Empresa":
                edad = self.random.randint(25, 60)
            
            # Aversión al riesgo base (aleatoria)
            aversion = self.random.uniform(0.1, 0.9)
            
            # Crear y situar agente
            a = ClienteCaixa(i, self, saldo, aversion, tipo, edad)
            self.schedule.add(a)
            self.grid.place_agent(a, node)

    def step(self):
        """Avanzar un paso de la simulación"""
        self.schedule.step()
        
        # Si la liquidez cae por debajo de 0, el banco ya no puede pagar
        if self.liquidez_banco < 0:
            self.liquidez_banco = 0