from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.sql import func
import json
from .database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False) # Ex: sala-001
    room_id = Column(String, nullable=False) # Ex: ROOM_LIVING
    hardware = Column(String, nullable=False) # Ex: esp32s3-deepseek-ball
    firmware_version = Column(String, nullable=False)
    # Salvando a lista de capabilities como JSON string no SQLite
    _capabilities = Column("capabilities", String, default="[]") 
    volume = Column(Integer, default=70)
    brightness = Column(Integer, default=50)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def capabilities(self):
        return json.loads(self._capabilities)

    @capabilities.setter
    def capabilities(self, value):
        self._capabilities = json.dumps(value)

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, nullable=False)
    room_id = Column(String, nullable=False)
    # input_text ficará vazio inicialmente até o Vosk processar
    input_text = Column(String, nullable=True) 
    output_text = Column(String, nullable=True) 
    latency_ms = Column(Integer, nullable=True, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class AIUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False) # Ex: Groq, Gemini
    tokens_used = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    room_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    temperature = Column(String, nullable=False) # Usar string formatada ajuda na precisão
    humidity = Column(String, nullable=False)
    weather_code = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    max_temp = Column(String, nullable=True)
    min_temp = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Timer(Base):
    __tablename__ = "timers"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    message = Column(String, nullable=True)
    timer_type = Column(String, default="timer")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ListItem(Base):
    __tablename__ = "list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_type = Column(String, nullable=False, index=True) # "compras" ou "tarefas"
    content = Column(String, nullable=False)
    room_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    room_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AppIntegration(Base):
    __tablename__ = "app_integrations"

    id = Column(Integer, primary_key=True, index=True)
    app_name = Column(String, unique=True, index=True, nullable=False) # ex: 'spotify'
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)
    is_connected = Column(Boolean, default=False)

class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False) # Ex: "Bom dia"
    trigger_type = Column(String, nullable=False) # "time" ou "event"
    trigger_value = Column(String, nullable=False) # "07:00" ou "user_arrived"
    action_type = Column(String, nullable=False) # "simulate_command"
    action_value = Column(String, nullable=False) # "como está o clima"
    room_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    days_of_week = Column(String, default="0,1,2,3,4,5,6") # 0=Sunday, 6=Saturday
    last_run = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=True)

class SavedLocation(Base):
    __tablename__ = "saved_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # "Casa", "Trabalho", "Estádio"
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    icon = Column(String, default="pin")            # "home", "work", "school", "stadium", "pin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DreamLog(Base):
    __tablename__ = "dream_logs"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(String, nullable=True)
    themes = Column(String, nullable=True) # Will store JSON string of tags
    interpretation = Column(String, nullable=False)
    room_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id = Column(Integer, primary_key=True, index=True)
    fact = Column(String, nullable=False)
    room_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SessionState(Base):
    __tablename__ = "session_states"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True, nullable=False)
    skill_name = Column(String, nullable=False)
    state_data = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TVConfig(Base):
    __tablename__ = "tv_configs"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True, nullable=False) # Ex: ROOM_LIVING
    ip_address = Column(String, nullable=True)
    mac_address = Column(String, nullable=True)
    smartthings_pat = Column(String, nullable=True)
    smartthings_device_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
