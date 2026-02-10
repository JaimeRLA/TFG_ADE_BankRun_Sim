from mesa import Agent
import numpy as np
import parametros as p

class ClienteCaixa(Agent):
    def __init__(self, unique_id, model, saldo, tipo):
        super().__init__(unique_id, model)
        self.unique_id = unique_id
        
        # --- LÓGICA DE CLÚSTER ---
        self.saldo_inicial = saldo  # El 100% del dinero del grupo
        self.saldo = saldo          # Lo que queda actualmente en el banco
        self.porcentaje_retirado = 0.0 # De 0.0 a 1.0
        self.tipo = tipo
        edad_random = self.random.gauss(50, 15) 
        self.edad = int(np.clip(edad_random, 18, 90))
        
        # Parámetros de comportamiento
        self.digitalizacion = 1.0 - (self.edad / p.EDAD_MAXIMA)
        factor_generacional = (self.edad / p.EDAD_MAXIMA) * 0.5
        self.aversion = np.clip(self.random.uniform(0.2, 0.8) + factor_generacional, 0, 1)
        self.estado = "NEUTRAL"
        self.alcance_noticia = False

    def step(self):
        # 1. DIFUSIÓN (Común)
        if not self.alcance_noticia:
            if self.random.random() < (self.model.noticia_difusion * self.digitalizacion):
                self.alcance_noticia = True

        # 2. CONTAGIO SOCIAL (Los vecinos miran cuánto pánico hay alrededor)
        vecinos_ids = list(self.model.G.neighbors(self.pos))
        vecinos_agentes = [self.model.grid.get_cell_list_contents([v])[0] for v in vecinos_ids]
        
        # IMPORTANTE: Los vecinos se asustan por el 'porcentaje_retirado' de otros 
        if vecinos_agentes:
            fuga_vecinos = sum(v.porcentaje_retirado for v in vecinos_agentes) / len(vecinos_agentes)
        else:
            fuga_vecinos = 0

        # 3. LÓGICA PARA NO-CLIENTES (Vector de propagación puro)
        if self.tipo == "No-Cliente":
            impacto_noticia = self.model.noticia_score * self.model.noticia_validez if self.alcance_noticia else 0
            
            # El No-Cliente NO mira la liquidez del banco (no tiene cuenta)
            score_opinion = (impacto_noticia * p.PESO_NOTICIA + fuga_vecinos * p.PESO_SOCIAL)
            score_opinion = np.clip(score_opinion, 0, 1)

            # Su 'porcentaje_retirado' NO es dinero, es su 'Nivel de Escándalo'
            k_ruido = 10 
            x0_ruido = 0.4
            self.porcentaje_retirado = 1 / (1 + np.exp(-k_ruido * (score_opinion - x0_ruido)))

            # ESTO ES LO QUE ACTIVA EL CONTADOR:
            if self.porcentaje_retirado > 0.1: # Si el rumor supera el 10% de intensidad
                self.estado = "ALERTA"
            else:
                self.estado = "NEUTRAL"
            return

        # 4. LÓGICA PARA CLIENTES (Sigue igual, ellos sí retiran)
        impacto_noticia = self.model.noticia_score * self.model.noticia_validez if self.alcance_noticia else 0
        miedo_banco = 1.0 - (self.model.liquidez_banco / self.model.liquidez_inicial)
        
        score_final = (
            impacto_noticia * p.PESO_NOTICIA + 
            fuga_vecinos * p.PESO_SOCIAL + 
            miedo_banco * p.PESO_LIQUIDEZ
        ) * (1 + self.aversion)
        
        score_final = np.clip(score_final, 0, 1)

        k = 12 
        x0 = 0.45 
        meta_fuga = 1 / (1 + np.exp(-k * (score_final - x0)))
        
        if meta_fuga > self.porcentaje_retirado:
            self.ejecutar_retirada_progresiva(meta_fuga)

    def ejecutar_retirada_progresiva(self, meta_fuga):
        # Calculamos cuánto dinero extra representa ese incremento de pánico
        diferencia_fuga = meta_fuga - self.porcentaje_retirado
        monto_a_retirar = diferencia_fuga * self.saldo_inicial
        
        if self.model.liquidez_banco > 0:
            # El banco paga lo que puede
            monto_real = min(monto_a_retirar, self.model.liquidez_banco)
            self.model.liquidez_banco -= monto_real
            self.model.depositos_totales -= monto_real
            
            # Actualizamos el estado interno del agente
            self.saldo -= monto_real
            self.porcentaje_retirado += (monto_real / self.saldo_inicial)
            
            # 5. ACTUALIZACIÓN VISUAL DEL ESTADO (Para el color en app.py)
            if self.porcentaje_retirado > 0.8:
                self.estado = "RETIRADO" # Bola Roja (Casi vacío)
            elif self.porcentaje_retirado > 0.1:
                self.estado = "ALERTA"   # Bola Naranja (Fuga en curso)