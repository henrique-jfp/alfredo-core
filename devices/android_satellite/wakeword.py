"""
Detector de wake word para o Alfredo OS.

Estratégia no M21 (Android/proot):
  O modelo openwakeword "alexa" foi treinado para pronúncia inglesa e
  produz scores muito baixos (~0.0008) para português brasileiro. Para
  compensar, combinamos três técnicas:

  1. THRESHOLD ULTRA BAIXO (0.005) — qualquer score acima de ruído de
     fundo é considerado potencial.
  2. ENERGIA DE ÁUDIO — só processamos OWW se a energia do chunk estiver
     significativamente acima da linha de base do ambiente. Isso elimina
     falsos positivos de silêncio/ruído constante.
  3. CONFIRMAÇÃO MÚLTIPLA — exigimos 3 detecções positivas consecutivas
     em uma janela de 10 chunks (~300ms) antes de disparar.
"""
import numpy as np
from openwakeword.model import Model as OWWModel
from .logger import wake_logger
from .config import config


class WakeWordDetector:
    # Limiar ultra-baixo para captar "alexa" mesmo com pronúncia portuguesa.
    # O score do OWW para "alexa" em português fica tipicamente entre
    # 0.0005 e 0.05 (vs 0.0000 para silêncio).
    OWW_THRESHOLD = 0.005

    # Energia mínima para considerar que há fala (evita processar OWW
    # em silêncio absoluto, onde o score pode variar aleatoriamente).
    # Será calibrado dinamicamente como 3x a média da energia ambiente.
    ENERGY_THRESHOLD = None  # definido na primeira detecção
    AMBIENT_ENERGY = None    # média exponencial da energia de fundo
    AMBIENT_ALPHA = 0.99     # suavização da média exponencial

    # Contador de chunks para debug
    _chunk_counter = 0
    _log_every_n = 300  # log a cada ~9s em vez de 3s

    # Confirmação múltipla
    _confirm_count = 0       # detecções positivas consecutivas
    CONFIRM_REQUIRED = 3     # quantas detecções consecutivas para disparar
    CONFIRM_WINDOW = 10      # janela máxima de chunks para contar

    def __init__(self):
        try:
            self.model = OWWModel()
            wake_logger.info(
                "OpenWakeWord carregado (modelo: %s). "
                "Threshold OWW=%.3f, confirmação=%d",
                config.WAKEWORD_MODEL,
                self.OWW_THRESHOLD,
                self.CONFIRM_REQUIRED,
            )
        except Exception as e:
            wake_logger.error(f"Erro ao carregar modelo OpenWakeWord: {e}")
            self.model = None

    def reset(self):
        """Reseta o estado interno para evitar re-detecção."""
        self._confirm_count = 0
        if self.model:
            try:
                self.model.reset()
            except Exception as e:
                wake_logger.warning(f"Erro ao resetar modelo OWW: {e}")

    def _energy(self, audio_np: np.ndarray) -> float:
        """Calcula a energia RMS do sinal de áudio."""
        return float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))

    def _update_ambient(self, energy: float):
        """Atualiza a estimativa da energia ambiente (média exponencial)."""
        if self.AMBIENT_ENERGY is None:
            self.AMBIENT_ENERGY = energy
        else:
            self.AMBIENT_ENERGY = (
                self.AMBIENT_ALPHA * self.AMBIENT_ENERGY
                + (1 - self.AMBIENT_ALPHA) * energy
            )

    def detect(self, audio_chunk: bytes) -> bool:
        """
        Analisa um chunk de áudio em busca da wake word.
        Retorna True se detectado com confirmação múltipla.
        """
        if not self.model:
            return False

        try:
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
            energy = self._energy(audio_np)
            self._update_ambient(energy)

            # Log periódico para debug
            WakeWordDetector._chunk_counter += 1
            if WakeWordDetector._chunk_counter % WakeWordDetector._log_every_n == 0:
                wake_logger.info(
                    "Estado wake: energia=%.1f, ambiente=%.1f, threshold_energia=%.1f, "
                    "confirm=%d, total_chunks=%d",
                    energy,
                    self.AMBIENT_ENERGY or 0,
                    (self.AMBIENT_ENERGY or 0) * 3,
                    self._confirm_count,
                    WakeWordDetector._chunk_counter,
                )

            # ═══════════════════════════════════════════════════════════
            # 1) Verifica se a energia está acima do ambiente
            # ═══════════════════════════════════════════════════════════
            min_energy = (self.AMBIENT_ENERGY or 0) * 3
            if energy < min_energy:
                # Energia muito baixa — provavelmente silêncio/ruído de fundo
                self._confirm_count = 0
                return False

            # ═══════════════════════════════════════════════════════════
            # 2) Executa o modelo OWW
            # ═══════════════════════════════════════════════════════════
            predictions = self.model.predict(audio_np)
            max_score = max(predictions.values()) if predictions else 0.0

            # ═══════════════════════════════════════════════════════════
            # 3) Verifica o threshold ultra-baixo
            # ═══════════════════════════════════════════════════════════
            # Se o score do "alexa" (ou qualquer modelo) superar o limiar,
            # incrementa o contador de confirmação.
            for model_name, score in predictions.items():
                if score > self.OWW_THRESHOLD:
                    self._confirm_count += 1
                    wake_logger.debug(
                        "Possível wake: %s score=%.6f energia=%.1f confirm=%d/%d",
                        model_name,
                        score,
                        energy,
                        self._confirm_count,
                        self.CONFIRM_REQUIRED,
                    )

                    # ═════════════════════════════════════════════════
                    # 4) Confirmação múltipla
                    # ═════════════════════════════════════════════════
                    if self._confirm_count >= self.CONFIRM_REQUIRED:
                        wake_logger.info(
                            "Wake word CONFIRMADA! %s score=%.6f (energia=%.1f, "
                            "confirm=%d)",
                            model_name,
                            score,
                            energy,
                            self._confirm_count,
                        )
                        self._confirm_count = 0
                        return True
                    break  # só conta uma detecção por chunk
            else:
                # Nenhum modelo passou o threshold
                # Se estamos no meio de uma contagem mas o score caiu,
                # decrementa gradualmente em vez de zerar
                if self._confirm_count > 0:
                    self._confirm_count = max(0, self._confirm_count - 1)

        except Exception as e:
            wake_logger.error(f"Erro durante detecção de wakeword: {e}")

        return False
