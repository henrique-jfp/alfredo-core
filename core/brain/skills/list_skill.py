import re
import logging
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.list")

class ListSkill(Skill):
    @property
    def name(self) -> str:
        return "ListSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "LIST"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        room_id = context.get("room_id")
        
        if not db or not room_id:
            logger.error("Contexto sem DB ou room_id na ListSkill")
            return "Desculpe, não consegui acessar o banco de dados das listas."

        text_lower = text.lower()
        
        # Determina o tipo de lista (tarefas é o padrão caso não fale compras)
        list_type = "compras" if "compra" in text_lower else "tarefas"

        # Verifica se é remoção de item específico
        remove_match = re.search(r'(?:apague|apagar|remova|remover|exclua|excluir|tire|tirar|risque|riscar)\s+(?:o\s+|a\s+|os\s+|as\s+)?(.*?)\s+(?:da|de|na)\s+lista', text_lower)
        if remove_match:
            item_name = remove_match.group(1).strip()
            if item_name and item_name not in ["tudo", "tudo da", "toda a", "tudo de"]:
                return self._remove_item(db, room_id, list_type, item_name)

        # Identifica a ação geral
        if "limpe" in text_lower or "apague a lista" in text_lower or "esvazie" in text_lower or "limpar" in text_lower or "apagar tudo" in text_lower:
            return self._clear_list(db, room_id, list_type)
        elif "adicione" in text_lower or "coloque" in text_lower or "anote" in text_lower or "ponha" in text_lower or "inclua" in text_lower or "comprar" in text_lower:
            return self._add_item(db, room_id, list_type, text_lower)
        else:
            return self._read_list(db, room_id, list_type)

    def _clear_list(self, db, room_id, list_type) -> str:
        items = db.query(models.ListItem).filter(
            models.ListItem.room_id == room_id,
            models.ListItem.list_type == list_type
        ).all()
        
        for item in items:
            db.delete(item)
            
        db.commit()
        logger.info(f"Lista de {list_type} esvaziada para a sala {room_id}")
        return f"A sua lista de {list_type} foi esvaziada."

    def _remove_item(self, db, room_id, list_type, item_name) -> str:
        # Busca o item usando ilike para ignorar case e aceitar correspondência parcial
        item = db.query(models.ListItem).filter(
            models.ListItem.room_id == room_id,
            models.ListItem.list_type == list_type,
            models.ListItem.content.ilike(f"%{item_name}%")
        ).first()
        
        if item:
            content_name = item.content
            db.delete(item)
            db.commit()
            logger.info(f"Item '{content_name}' removido da lista de {list_type} na sala {room_id}")
            return f"Pronto, apaguei {content_name} da sua lista de {list_type}."
        else:
            return f"Não encontrei {item_name} na sua lista de {list_type}."


    def _read_list(self, db, room_id, list_type) -> str:
        items = db.query(models.ListItem).filter(
            models.ListItem.room_id == room_id,
            models.ListItem.list_type == list_type
        ).all()
        
        if not items:
            return f"A sua lista de {list_type} está vazia."
            
        # Formata com vírgulas e "e" no final. Ex: maçã, banana e leite
        item_names = [item.content for item in items]
        if len(item_names) > 1:
            itens_text = ", ".join(item_names[:-1]) + " e " + item_names[-1]
        else:
            itens_text = item_names[0]
            
        return f"Na sua lista de {list_type} tem: {itens_text}."

    def _add_item(self, db, room_id, list_type, text: str) -> str:
        # Regex para isolar o que foi pedido para adicionar
        match = re.search(r'(?:adicione|coloque|anote|ponha|inclua|comprar)\s+(.*)', text)
        
        if match:
            item_name = match.group(1).strip()
            # Remove as palavras do final da frase para isolar só o nome do item
            item_name = re.sub(r'(na lista.*|em minha lista.*|à lista.*|para a lista.*|da lista.*)$', '', item_name).strip()
        else:
            return f"Não consegui entender o que você quer adicionar na lista de {list_type}."
            
        if not item_name or item_name == "de":
            return "Não entendi o nome do item para adicionar."

        new_item = models.ListItem(
            list_type=list_type,
            content=item_name,
            room_id=room_id
        )
        db.add(new_item)
        db.commit()
        
        logger.info(f"Item '{item_name}' adicionado à lista de {list_type} na sala {room_id}")
        return f"Adicionei {item_name} na sua lista de {list_type}."
