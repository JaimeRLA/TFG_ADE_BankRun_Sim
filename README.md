# **Agent.py**

## **1. __init__ (self, unique_id, model, saldo, aversion_base, tipo, edad)**

Aquí se definen las propiedades genéticas y financieras de cada grupo de personas.

**self.saldo_inicial** = saldo: Guarda el capital total que el clúster tenía al principio. Es la referencia para calcular porcentajes de fuga.

**self.porcentaje_retirado** = 0.0: Es el "termómetro" del pánico. En clientes es dinero fuera; en no-clientes es intensidad de indignación.

**self.digitalizacion** = 1.0 - (self.edad / p.EDAD_MAXIMA): Lógica de exposición. Cuanto más joven es el clúster, más alta es su digitalización y más rápido le llegará la noticia por canales digitales.

**self.aversion** = np.clip(...): Lógica de miedo. Se le suma un "factor generacional": a mayor edad, mayor aversión al riesgo (miedo a perder los ahorros).

**self.alcance_noticia** = False: El agente empieza ignorando la crisis hasta que la "detecta".

## **2. step (self)**

### **Fase 1**: Difusión de la noticia
- Un sorteo aleatorio decide si el clúster se entera de la noticia. La probabilidad depende de la difusión global de la crisis multiplicada por la digitalización propia del grupo.

### **Fase 2**: Contagio Social (Inter-Nodo)
- El agente mira a sus contactos en la red Small-World. Calcula la media de pánico (porcentaje_retirado) de sus vecinos. Si sus amigos están sacando dinero, él se pone nervioso.

### **Fase 3:** Lógica para No-Clientes (Opinión Pública)
- Los no-clientes no tienen dinero en el banco, así que su "fuga" es en realidad intensidad de rumor.Evalúa la fuerza de la noticia externa. Si el agente ha sido alcanzado por la noticia (self.alcance_noticia), multiplica la gravedad del hecho por la credibilidad del medio que lo publica.

- Su opinión se forma solo por la noticia y por lo que dicen sus vecinos. Se aplica la Función Sigmoide para que el rumor no crezca linealmente, sino que explote a partir de un umbral de escándalo.

### **Fase 4:** Lógica para Clientes (Decisión Financiera)
- El cliente suma tres miedos: la noticia, sus vecinos y el estado del banco (si ve que la liquidez del banco cae, su miedo aumenta drásticamente). Todo esto se multiplica por su aversion personal. Nuevamente, se usa la Sigmoide para calcular la meta_fuga (cuánto dinero quiere tener fuera del banco ahora mismo).

- Hasta que el pánico no supera un umbral, el agente se mantiene relativamente tranquilo. Al cruzar ese umbral, la intención de retirar dinero se dispara exponencialmente. Una pendiente alta simula una reacción rápida; el agente pasa de la calma a la acción en muy poco tiempo, replicando el comportamiento de las corridas bancarias digitales modernas.

## **3. ejecutar_retirada_progresiva (self, meta_fuga)**

- El agente no saca todo su dinero de golpe. Mira cuánto quiere tener fuera ahora (meta_fuga) y le resta lo que ya sacó antes (porcentaje_retirado). Esa diferencia (un porcentaje) se multiplica por el saldo_inicial del clúster para saber exactamente cuántos euros intenta retirar en este turno.

- El agente va a la "ventanilla" del banco. Si el banco tiene dinero (liquidez_banco > 0), se procede. El agente solo puede llevarse lo que el banco sea capaz de pagar. Si el agente quiere 1 millón pero el banco solo tiene 500.000€ en caja, el min() asegura que el agente solo se lleve esos 500.000€. Esto simula la falla de liquidez.






# **Model.py**

## **1. __init__ (self, n, total_depositos, encaje, news_score, news_validez, news_difusion, p_no_clientes=0.2)**

### **Fase 1:** Lógica Financiera (Balance del Banco)

En este bloque se establece la diferencia crítica entre Solvencia (cuánto dinero tiene el banco en total) y Liquidez (cuánto tiene disponible para devolver ya mismo).

- **self.depositos_totales**: Es el patrimonio total que los clientes han confiado al banco.

- **self.liquidez_banco**: Se calcula multiplicando los depósitos por el encaje (coeficiente de reserva). Es el dinero físico en caja.

- **self.prestamos_activos**: Es el dinero que el banco no tiene en mano porque lo ha prestado (hipotecas, créditos). Esto representa activos que son valiosos pero que no se pueden convertir en efectivo instantáneamente durante una corrida bancari

### **Fase 2:** Parámetros de la Crisis

Define la "fuerza" del rumor externo que va a estresar el sistema.

- **score:** La gravedad intrínseca de la noticia.
- **validez:** Cuánta credibilidad tiene el medio que la publica.
- **difusion:** La capacidad de la noticia para expandirse por la red.

### **Fase 3:** La Red Social (Small World)
Aquí se construye el mapa de relaciones entre los agentes. Se utiliza un grafo de Holme y Kim (Powerlaw Cluster Graph) que tiene dos propiedades fundamentales: 

- **Mundo Pequeño**: Hay "atajos" que permiten que una noticia salte de un grupo a otro muy rápido.

- **Clustering**: Crea comunidades densas, simulando grupos de amigos o círculos de confianza donde el pánico se refuerza.

### **Fase 4:** Creación de Agentes (Segmentación de Clientes)

**Probabilidad de Cliente:** Usa p_no_clientes para decidir si el nodo es un ahorrador o simplemente un nodo de opinión pública ("No-Cliente").

**Distribución de Riqueza:** Retail (75%): Pequeños ahorradores. Tienen entre el 50% y el 120% del saldo promedio, VIP (20%): Clientes con saldos altos (hasta 3 veces el promedio), Empresa (5%): Grandes depósitos (hasta 8 veces el promedio). Son los que más liquidez drenan si se asustan.

**Creación de los agentes**

## **2. step (self)**

- **Ordena a todos los agentes de la simulación que ejecuten su propia función step:** En este punto, cada clúster de clientes y no-clientes evalúa la noticia, mira a sus vecinos, calcula su pánico y, si es necesario, intenta retirar dinero de la ventanilla. Es el momento donde ocurre el "caos" de la corrida bancaria.

- **Verifica que el efectivo disponible en el banco no baje de cero:** Aunque en la vida real un banco no puede entregar dinero que no tiene, en las simulaciones matemáticas a veces pueden ocurrir pequeños errores de precisión si varios agentes retiran fondos simultáneamente. Si la liquidez intenta ser negativa, se fuerza a 0. Esto representa el estado de quiebra técnica total o "caja vacía". El banco ya no puede satisfacer más demandas de efectivo.

- **Realiza un "arqueo de caja" al final del turno:** Recorre a todos los agentes que existen en la simulación, filtra solo a los que son Clientes (if a.tipo != "No-Cliente") y suma sus saldos actuales (a.saldo). Como los agentes han estado retirando dinero durante el schedule.step(), el pasivo del banco (lo que debe a sus clientes) ha disminuido. Esta línea sincroniza el valor global del banco con la realidad de lo que queda en las cuentas de cada clúster.



