from mesa import Agent
import numpy as np
# Importamos todas las constantes de nuestro nuevo archivo
import parametros as p

class ClienteCaixa(Agent):
    def __init__(self, unique_id, model, saldo, aversion_base, tipo, edad):
        super().__init__(unique_id, model)
        self.unique_id = unique_id
        self.saldo = saldo
        self.tipo = tipo
        self.edad = edad
        
        # Usamos los parámetros para calcular la digitalización y aversión
        self.digitalizacion = 1.0 - (self.edad / p.EDAD_MAXIMA)
        
        # Aversión ajustada por edad (factor generacional)
        factor_generacional = (self.edad / p.EDAD_MAXIMA) * 0.5
        self.aversion = np.clip(aversion_base + factor_generacional, 0, 1)
        
        self.estado = "CALMADO" if tipo != "No-Cliente" else "NEUTRAL"
        self.alcance_noticia = False

    def step(self):
        if self.estado == "RETIRADO":
            return

        # 1. DIFUSIÓN: Recibir la noticia
        if not self.alcance_noticia:
            if self.random.random() < (self.model.noticia_difusion * self.digitalizacion):
                self.alcance_noticia = True

        # 2. CONTAGIO SOCIAL
        vecinos_ids = list(self.model.G.neighbors(self.pos))
        vecinos_agentes = [self.model.grid.get_cell_list_contents([v])[0] for v in vecinos_ids]
        
        huidos = sum(1 for v in vecinos_agentes if v.estado in ["RETIRADO", "ALERTA"])
        ratio_social = huidos / len(vecinos_agentes) if vecinos_agentes else 0

        # 3. LÓGICA DE DECISIÓN (Usando los PESOS de parametros.py)
        impacto_noticia = self.model.noticia_score * self.model.noticia_validez if self.alcance_noticia else 0
        miedo_banco = 1.0 - (self.model.liquidez_banco / self.model.liquidez_inicial)
        
        score_final = (
            impacto_noticia * p.PESO_NOTICIA + 
            ratio_social * p.PESO_SOCIAL + 
            miedo_banco * p.PESO_LIQUIDEZ
        ) * (1 + self.aversion)

        # 4. APLICACIÓN DE UMBRALES
        if self.tipo == "No-Cliente":
            if score_final > p.UMBRAL_ALERTA_NOCLIENTE:
                self.estado = "ALERTA"
            return

        if score_final > p.UMBRAL_RETIRADA_CLIENTE:
            self.ejecutar_retirada()

    def ejecutar_retirada(self):
        # El cliente intenta sacar su saldo, pero solo puede sacar lo que haya en caja
        if self.model.liquidez_banco > 0:
            monto_a_retirar = self.saldo
            
            if self.model.liquidez_banco >= monto_a_retirar:
                self.model.liquidez_banco -= monto_a_retirar
                self.model.depositos_totales -= monto_a_retirar
            else:
                # El banco se queda sin efectivo antes de completar la retirada total
                self.model.depositos_totales -= self.model.liquidez_banco
                self.model.liquidez_banco = 0
                
            self.estado = "RETIRADO"