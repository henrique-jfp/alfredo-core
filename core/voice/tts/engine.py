import os
import logging
import asyncio
import subprocess
import edge_tts

logger = logging.getLogger("alfredo.tts")

class TTSEngine:
    def __init__(self, voice_name: str = "pt-BR-FranciscaNeural"):
        self.current_voice_name = voice_name
        logger.info(f"Modelo Edge-TTS inicializado com a voz: {voice_name}")
        
    def reload_voice(self, voice_name: str):
        """Troca a voz ativa em tempo real."""
        if self.current_voice_name != voice_name:
            self.current_voice_name = voice_name
            logger.info(f"Voz Edge-TTS alterada para: {voice_name}")

    async def synthesize_wav(self, text: str, output_filepath: str):
        """
        Gera o áudio a partir do texto usando edge-tts e salva no formato WAV especificado.
        Como o edge-tts gera MP3 nativamente, usaremos o ffmpeg para converter para WAV 16kHz mono.
        """
        import re
        # Limpa emojis e símbolos especiais antes de enviar para a voz
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        
        logger.info(f"Sintetizando áudio na nuvem para o texto: '{clean_text}'")
        
        # Gerar arquivo temporário MP3
        tmp_mp3_path = output_filepath.replace(".wav", ".mp3")
        
        try:
            # Chama a API da Microsoft via edge-tts
            communicate = edge_tts.Communicate(clean_text, self.current_voice_name)
            await communicate.save(tmp_mp3_path)
            
            # Converte o MP3 para WAV (16kHz, mono, PCM s16le) usando FFmpeg
            # Isso é vital para compatibilidade com o ESP32 I2S
            cmd = [
                "ffmpeg", "-y", "-i", tmp_mp3_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                output_filepath
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Erro ao converter áudio com ffmpeg: {stderr.decode()}")
                raise Exception("Falha na conversão de áudio para WAV")
                
            logger.info(f"Áudio TTS salvo e convertido em: {output_filepath}")
            
        except Exception as e:
            logger.error(f"Erro na síntese TTS: {e}")
            raise e
        finally:
            # Limpeza do arquivo temporário
            if os.path.exists(tmp_mp3_path):
                try:
                    os.remove(tmp_mp3_path)
                except:
                    pass

# Singleton
_tts_instance = None

def get_tts_engine() -> TTSEngine:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSEngine()
    return _tts_instance
