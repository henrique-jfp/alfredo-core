from typing import List, Optional
from .constants import State
from .logger import state_logger

class StateMachine:
    def __init__(self):
        self.state = State.BOOTING
        
        # Mapa de transições válidas
        self.valid_transitions = {
            State.BOOTING: [State.CONNECTING, State.ERROR],
            State.CONNECTING: [State.CONNECTED, State.ERROR, State.RECONNECTING],
            State.CONNECTED: [State.LISTENING, State.ERROR, State.RECONNECTING],
            State.LISTENING: [State.WAKE_DETECTED, State.ERROR, State.RECONNECTING, State.STREAMING_ONLY],
            State.WAKE_DETECTED: [State.STREAMING_AUDIO, State.LISTENING, State.ERROR, State.RECONNECTING],
            State.STREAMING_AUDIO: [State.WAITING_RESPONSE, State.LISTENING, State.ERROR, State.RECONNECTING],
            State.WAITING_RESPONSE: [State.PLAYING_TTS, State.LISTENING, State.ERROR, State.RECONNECTING],
            State.PLAYING_TTS: [State.LISTENING, State.ERROR, State.RECONNECTING],
            State.ERROR: [State.RECONNECTING, State.BOOTING],
            State.RECONNECTING: [State.CONNECTING, State.ERROR],
            State.STREAMING_ONLY: [State.LISTENING, State.ERROR, State.RECONNECTING]
        }
        
    def transition(self, new_state: State) -> bool:
        if new_state in self.valid_transitions.get(self.state, []):
            state_logger.info(f"[{self.state.name}] -> [{new_state.name}]")
            self.state = new_state
            return True
        else:
            state_logger.error(f"Transição inválida! [{self.state.name}] -> [{new_state.name}]")
            return False

    def get_state(self) -> State:
        return self.state
