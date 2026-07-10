import re
from typing import List, Dict, Any, Optional
from core.brain.semantic_router import Route, _and, _not

def parse_timers(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Função customizada de extração de múltiplos timers da frase.
    Busca por padrões como "5 minutos", "1 hora e meia", etc.
    """
    # Se a frase não tiver indicativos de timer, falha rápido.
    if not re.search(r'\b(avisa|avisar|desperta|despertar|timer|alarme|cronometro|daqui a|em)\b', text):
        return None

    # Busca por números + unidades de tempo (ex: "5 minutos", "1 hora e 30 minutos")
    # Expressão simplificada para capturar pares de (número) (unidade)
    # Suporta numerais por extenso básicos se quisermos, mas aqui usamos dígitos
    pattern = re.compile(r'\b(\d+)\s*(minuto|minutos|hora|horas|segundo|segundos)\b')
    matches = pattern.finditer(text)
    
    actions = []
    
    for match in matches:
        value = int(match.group(1))
        unit = match.group(2)
        
        # Converte tudo para segundos para a action padrão
        seconds = 0
        if unit.startswith('hora'):
            seconds = value * 3600
        elif unit.startswith('minuto'):
            seconds = value * 60
        else:
            seconds = value
            
        # Opcional: tentar inferir o rótulo do timer ("para tirar o bolo")
        # pegando as palavras que vêm logo depois da unidade de tempo
        label_match = re.search(rf'{match.group(0)}\s+(?:para|pra)\s+([a-z0-9\s]+?)(?:\s+(?:e|daqui|em)\s+\d+|$)', text)
        label = label_match.group(1).strip() if label_match else f"Timer de {value} {unit}"
        
        actions.append({
            "action": "create",
            "duration": seconds,
            "label": label
        })

    if actions:
        return actions
    return None

ROUTES = [
    # Rota especial que usa um parser customizado (não batchable da maneira normal, 
    # pois o custom_parser já pode retornar múltiplas actions em um array).
    # Vamos marcar batchable=True para que o semantic_router saiba que pode agregar
    # se o custom_parser retornar uma lista de actions.
    Route(re.compile(r'.*'), "manage_timer", {}, None, True, custom_parser=parse_timers)
]
