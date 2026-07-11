import os
import re
import logging
from typing import Dict, Any
import requests
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.list")

class ListSkill(Skill):
    VALID_LIST_TYPES = {"compras", "tarefas"}

    @property
    def name(self) -> str:
        return "ListSkill"

    def _normalize_list_type(self, list_type: str) -> str:
        """Garante que só usamos os dois tipos de lista que o Dashboard conhece.

        BUG CORRIGIDO: o schema da tool manage_list não restringia list_type,
        então o Gemini podia inventar algo como 'churrasco'. Tecnicamente o
        item era salvo no banco, mas o Dashboard só sabe agrupar 'compras' e
        'tarefas' — na prática a lista "sumia" da tela. Agora normalizamos
        aqui como segunda camada de defesa (a primeira é o enum no schema,
        ver core/brain/router.py).
        """
        normalized = (list_type or "").strip().lower()
        if normalized in self.VALID_LIST_TYPES:
            return normalized
        if any(w in normalized for w in ("compra", "mercado", "feira", "supermercado")):
            return "compras"
        return "tarefas"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "LIST"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Para gerenciar listas, por favor use as funções de dashboard."

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
        match = re.search(r'(?:adicione|adicionar|coloque|anote|ponha|inclua|acrescente|acrescentar|comprar)\s+(.*)', text)
        
        if match:
            item_name = match.group(1).strip()
            # Remove as palavras do final da frase para isolar só o nome do item
            item_name = re.sub(r'(na minha lista.*|na sua lista.*|na lista.*|em minha lista.*|à lista.*|para a lista.*|da lista.*)$', '', item_name).strip()
        else:
            return f"Não consegui entender o que você quer adicionar na lista de {list_type}."
            
        if not item_name or item_name == "de":
            return "Não entendi o nome do item para adicionar."

        # Separa os itens se houver " e ", " e também " ou ","
        items_to_add = re.split(r'\s+e\s+também\s+|\s+e\s+tambem\s+|\s+e\s+|,\s*', item_name)
        items_to_add = [i.strip() for i in items_to_add if i.strip()]
        
        if not items_to_add:
            return "Não entendi o nome do item para adicionar."

        # Busca itens existentes para evitar duplicatas
        existing_items = db.query(models.ListItem).filter(
            models.ListItem.room_id == room_id,
            models.ListItem.list_type == list_type
        ).all()
        existing_names_lower = {i.content.lower().strip() for i in existing_items}

        added = []
        already_exists = []

        for item in items_to_add:
            item_lower = item.lower().strip()
            if item_lower in existing_names_lower:
                already_exists.append(item)
            else:
                new_item = models.ListItem(
                    list_type=list_type,
                    content=item,
                    room_id=room_id
                )
                db.add(new_item)
                added.append(item)
                existing_names_lower.add(item_lower)
            
        db.commit()
        
        resp_parts = []
        if added:
            if len(added) > 1:
                itens_str = ", ".join(added[:-1]) + " e " + added[-1]
            else:
                itens_str = added[0]
            resp_parts.append(f"Adicionei {itens_str} na sua lista de {list_type}.")
        if already_exists:
            if len(already_exists) > 1:
                exist_str = ", ".join(already_exists[:-1]) + " e " + already_exists[-1]
            else:
                exist_str = already_exists[0]
            resp_parts.append(f"{exist_str} já estava na lista.")
            
        if not resp_parts:
            return f"Todos os itens já estavam na sua lista de {list_type}."
            
        logger.info(f"Itens adicionados à lista de {list_type} na sala {room_id}: +{len(added)}, dup={len(already_exists)}")
        return " ".join(resp_parts)

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        room_id = context.get("room_id")
        action = kwargs.get("action")
        list_type = self._normalize_list_type(kwargs.get("list_type", "tarefas"))
        items = kwargs.get("items", [])
        
        if not db or not room_id:
            return {"error": "Sem contexto de banco ou sala"}
            
        if action == "clear":
            items_db = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type
            ).all()
            for item in items_db:
                db.delete(item)
            db.commit()
            return {
                "status": "success",
                "message": f"Lista de {list_type} esvaziada.",
                "direct_response": f"Pronto, sua lista de {list_type} foi esvaziada."
            }
            
        elif action == "read":
            items_db = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type
            ).all()
            if not items_db:
                return {
                    "list_content": [],
                    "message": f"Lista de {list_type} vazia",
                    "direct_response": f"Sua lista de {list_type} está vazia."
                }
            names = [i.content for i in items_db]
            if len(names) > 1:
                text = ", ".join(names[:-1]) + " e " + names[-1]
            else:
                text = names[0]
            return {
                "list_content": names,
                "direct_response": f"Na sua lista de {list_type} tem: {text}."
            }
            
        elif action == "remove":
            item_name = kwargs.get("item", "").strip()
            if not item_name:
                return {"error": "Nenhum item fornecido para remover"}
            item = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type,
                models.ListItem.content.ilike(f"%{item_name}%")
            ).first()
            if item:
                db.delete(item)
                db.commit()
                return {"direct_response": f"Pronto, apaguei {item.content} da sua lista de {list_type}.", "status": "success"}
            else:
                return {"direct_response": f"Não encontrei {item_name} na sua lista de {list_type}.", "status": "fail"}

        elif action == "add":
            if not items:
                return {"error": "Nenhum item fornecido para adicionar"}
            
            existing_items_db = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type
            ).all()
            existing_names_lower = [i.content.lower().strip() for i in existing_items_db]
            
            added = []
            already_exists = []
            
            for item in items:
                item_lower = item.lower().strip()
                if item_lower in existing_names_lower:
                    already_exists.append(item)
                else:
                    new_item = models.ListItem(
                        list_type=list_type,
                        content=item,
                        room_id=room_id
                    )
                    db.add(new_item)
                    added.append(item)
                    existing_names_lower.append(item_lower)
                    
            db.commit()
            
            direct = f"Adicionei {' e '.join(added)} na sua lista de {list_type}." if added else ""
            if already_exists:
                direct += f" {' e '.join(already_exists)} já estava na lista."
            return {
                "status": "success",
                "added_items": added,
                "already_existing_items": already_exists,
                "direct_response": direct
            }
            
        elif action in ("email", "telegram"):
            items_db = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type
            ).all()

            if not items_db:
                return {
                    "error": f"A lista de {list_type} está vazia, não há nada para enviar.",
                    "direct_response": f"Sua lista de {list_type} está vazia, não tenho nada para enviar."
                }

            def _get_env(*names: str) -> str:
                for name in names:
                    value = os.getenv(name, "").strip()
                    if value:
                        return value
                return ""

            telegram_token = _get_env("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_API_TOKEN", "TQDM_TELEGRAM_TOKEN")
            telegram_chat_id = _get_env("TELEGRAM_CHAT_ID", "TELEGRAM_TARGET_CHAT_ID", "TELEGRAM_BOT_CHAT_ID", "TQDM_TELEGRAM_CHAT_ID")

            if not telegram_token or not telegram_chat_id:
                return {
                    "error": "Telegram não configurado. Defina token e chat_id no .env.",
                    "direct_response": "Não consegui enviar por Telegram porque faltou configuração do token ou chat_id."
                }

            item_lines = "\n".join([f"• {i.content}" for i in items_db])
            message = f"Lista de {list_type.capitalize()}\n\n{item_lines}"

            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": telegram_chat_id,
                        "text": message,
                        "disable_web_page_preview": True,
                    },
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                logger.error(f"Falha ao enviar lista por Telegram: {exc}")
                return {
                    "error": "Falha ao enviar lista por Telegram.",
                    "direct_response": "Não consegui enviar sua lista por Telegram agora."
                }

            if not payload.get("ok"):
                logger.error(f"Telegram respondeu com erro: {payload}")
                return {
                    "error": "Falha ao enviar lista por Telegram.",
                    "direct_response": "Não consegui enviar sua lista por Telegram agora."
                }

            return {
                "status": "success",
                "message": "Lista enviada por Telegram com sucesso.",
                "direct_response": f"Pronto, enviei sua lista de {list_type} por Telegram."
            }
                
        return {"error": "Ação desconhecida"}
