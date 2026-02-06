from mesa import Agent

class ClienteCaixa(Agent):
    def __init__(self, unique_id, model, saldo, aversion, tipo, edad):
        super().__init__(unique_id, model)
        self.saldo = saldo
        self.aversion = aversion
        self.tipo = tipo
        self.edad = edad
        self.estado = "CALMADO" if tipo != "No-Cliente" else "NEUTRAL"
        self.digitalizacion = 1.0 - (edad / 100)
        self.alcance_noticia = False

    def step(self):
        # Los que ya retiraron o son no-clientes propagadores no 'huyen', pero siguen en el paso
        if self.estado == "RETIRADO":
            return

        # 1. DIFUSIÓN: Recibir la noticia (Digitalización)
        if not self.alcance_noticia:
            if self.random.random() < (self.model.noticia_difusion * self.digitalizacion):
                self.alcance_noticia = True

        # 2. CONTAGIO SOCIAL: Ver vecinos asustados
        vecinos_ids = list(self.model.G.neighbors(self.pos))
        vecinos_agentes = [self.model.grid.get_cell_list_contents([v])[0] for v in vecinos_ids]
        
        # Un No-Cliente se 'asusta' (cambia a modo alerta) y propaga más la noticia
        huidos = sum(1 for v in vecinos_agentes if v.estado in ["RETIRADO", "ALERTA"])
        ratio_social = huidos / len(vecinos_agentes) if vecinos_agentes else 0

        # 3. LÓGICA DE DECISIÓN
        impacto_noticia = self.model.noticia_score * self.model.noticia_validez if self.alcance_noticia else 0
        miedo_banco = 1.0 - (self.model.liquidez_banco / self.model.liquidez_inicial)
        
        score_final = (impacto_noticia * 0.4 + ratio_social * 0.5 + miedo_banco * 0.1) * (1 + self.aversion)

        # Si es No-Cliente, solo cambia a estado ALERTA (ayuda al contagio social)
        if self.tipo == "No-Cliente":
            if score_final > 0.4:
                self.estado = "ALERTA"
            return

        # Si es Cliente, ejecuta retirada
        if score_final > 0.5:
            self.ejecutar_retirada()

    def ejecutar_retirada(self):
        monto = min(self.saldo, self.model.liquidez_banco)
        self.model.liquidez_banco -= monto
        self.estado = "RETIRADO"