import networkx as nx
from mesa import Model
from mesa.time import RandomActivation
from mesa.space import NetworkGrid
from .agent import ClienteCaixa

class BancoModel(Model):
    def __init__(self, n, liq, news_score, news_validez, news_difusion, p_no_clientes=0.2):
        super().__init__()
        self.liquidez_inicial = liq
        self.liquidez_banco = liq
        self.noticia_score = news_score
        self.noticia_validez = news_validez
        self.noticia_difusion = news_difusion

        # --- SMALL WORLD NETWORK (Realismo Humano) ---
        # n: nodos, 3: conexiones iniciales, 0.5: probabilidad de triángulos (clustering)
        self.G = nx.powerlaw_cluster_graph(n, 3, 0.5)
        self.grid = NetworkGrid(self.G)
        self.schedule = RandomActivation(self)

        for i, node in enumerate(self.G.nodes()):
            # Determinamos si es cliente o un propagador externo
            es_cliente = self.random.random() > p_no_clientes
            
            if es_cliente:
                tipo = self.random.choices(["Retail", "VIP", "Empresa"], [75, 20, 5])[0]
                saldo = self.random.uniform(50000, 200000) if tipo == 'Empresa' else self.random.uniform(1000, 15000)
            else:
                tipo = "No-Cliente" # Solo propaga la noticia
                saldo = 0
            
            edad = self.random.randint(18, 85)
            aversion = self.random.uniform(0.1, 0.9)
            
            a = ClienteCaixa(i, self, saldo, aversion, tipo, edad)
            self.schedule.add(a)
            self.grid.place_agent(a, node)

    def step(self):
        self.schedule.step()