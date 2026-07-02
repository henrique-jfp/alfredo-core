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
            item_name = re.sub(r'(na minha lista.*|na sua lista.*|na lista.*|em minha lista.*|à lista.*|para a lista.*|da lista.*)$', '', item_name).strip()
        else:
            return f"Não consegui entender o que você quer adicionar na lista de {list_type}."
            
        if not item_name or item_name == "de":
            return "Não entendi o nome do item para adicionar."

        # Separa os itens se houver " e ", " e também " ou ","
        import re as regex
        items_to_add = regex.split(r'\s+e\s+também\s+|\s+e\s+tambem\s+|\s+e\s+|,\s*', item_name)
        items_to_add = [i.strip() for i in items_to_add if i.strip()]
        
        if not items_to_add:
            return "Não entendi o nome do item para adicionar."

        for item in items_to_add:
            new_item = models.ListItem(
                list_type=list_type,
                content=item,
                room_id=room_id
            )
            db.add(new_item)
            
        db.commit()
        
        # Formata a resposta com a lista correta
        if len(items_to_add) > 1:
            itens_str = ", ".join(items_to_add[:-1]) + " e " + items_to_add[-1]
        else:
            itens_str = items_to_add[0]
            
        logger.info(f"Itens '{itens_str}' adicionados à lista de {list_type} na sala {room_id}")
        return f"Adicionei {itens_str} na sua lista de {list_type}."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        room_id = context.get("room_id")
        action = kwargs.get("action")
        list_type = kwargs.get("list_type", "tarefas")
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
            return {"status": "success", "message": f"Lista de {list_type} esvaziada."}
            
        elif action == "read":
            items_db = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type
            ).all()
            if not items_db:
                return {"list_content": [], "message": f"Lista de {list_type} vazia"}
            return {"list_content": [i.content for i in items_db]}
            
        elif action == "add":
            if not items:
                return {"error": "Nenhum item fornecido para adicionar"}
            
            # Fetch existing items to prevent exact duplicates
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
            return {
                "status": "success",
                "added_items": added,
                "already_existing_items": already_exists
            }
            
        elif action == "email":
            items_db = db.query(models.ListItem).filter(
                models.ListItem.room_id == room_id,
                models.ListItem.list_type == list_type
            ).all()
            
            if not items_db:
                return {"error": f"A lista de {list_type} está vazia, não há nada para enviar."}
                
            html_items = "".join([f"<li style='margin-bottom: 8px; font-size: 16px;'>{i.content}</li>" for i in items_db])
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                        <h2 style="color: #4CAF50;">Sua Lista de {list_type.capitalize()} 🛒</h2>
                        <p>Aqui estão os itens da sua lista solicitada através do Alfredo:</p>
                        <ul style="list-style-type: square;">
                            {html_items}
                        </ul>
                        <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
                        <p style="font-size: 12px; color: #999;">Enviado por Alfredo Home OS</p>
                    </div>
                </body>
            </html>
            """
            
            from core.services.mail_service import send_email
            success = send_email(f"Sua lista de {list_type.capitalize()}", html_body)
            
            if success:
                return {"status": "success", "message": "Email enviado com sucesso."}
            else:
                return {"error": "Falha ao enviar email. Verifique as credenciais no .env."}
                
        return {"error": "Ação desconhecida"}
