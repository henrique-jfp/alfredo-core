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
        Se houver tags <lang="XX">texto</lang>, o texto será dividido e renderizado com vozes nativas,
        e posteriormente concatenado.
        """
        import re
        import uuid
        import shutil
        
        # Limpa emojis e símbolos especiais antes de enviar para a voz
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        
        logger.info(f"Sintetizando áudio na nuvem para o texto: '{clean_text}'")
        
        VOICE_MAP = {
            "en-US": "en-US-AriaNeural",
            "es-ES": "es-ES-ElviraNeural",
            "de-DE": "de-DE-AmalaNeural",
            "fr-FR": "fr-FR-DeniseNeural",
            "it-IT": "it-IT-IsabellaNeural",
            "ja-JP": "ja-JP-NanamiNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural"
        }

        # Divide o texto em blocos buscando tags <lang="XX">texto</lang>
        pattern = r'<lang="([^"]+)">(.*?)</lang>'
        parts = re.split(pattern, clean_text)
        
        parsed_segments = []
        i = 0
        while i < len(parts):
            # Texto fora da tag
            if parts[i].strip():
                parsed_segments.append((self.current_voice_name, parts[i].strip()))
            i += 1
            # Se ainda houver partes, as próximas duas são locale e o texto interno
            if i < len(parts):
                locale = parts[i]
                inside_text = parts[i+1]
                if inside_text.strip():
                    voice = VOICE_MAP.get(locale, self.current_voice_name)
                    parsed_segments.append((voice, inside_text.strip()))
                i += 2

        if not parsed_segments:
            parsed_segments = [(self.current_voice_name, clean_text)]
            
        temp_dir = os.path.dirname(output_filepath)
        session_id = str(uuid.uuid4())[:8]
        wav_files = []
        
        try:
            for idx, (voice, segment_text) in enumerate(parsed_segments):
                tmp_mp3 = os.path.join(temp_dir, f"tmp_{session_id}_{idx}.mp3")
                tmp_wav = os.path.join(temp_dir, f"tmp_{session_id}_{idx}.wav")
                
                communicate = edge_tts.Communicate(segment_text, voice)
                await communicate.save(tmp_mp3)
                
                cmd = [
                    "ffmpeg", "-y", "-i", tmp_mp3,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                    tmp_wav
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Erro ao converter áudio temporário com ffmpeg: {stderr.decode()}")
                    raise Exception("Falha na conversão de áudio para WAV")
                    
                wav_files.append(tmp_wav)
                
                if os.path.exists(tmp_mp3):
                    os.remove(tmp_mp3)
                    
            # Concatena os pedaços
            if len(wav_files) == 1:
                shutil.move(wav_files[0], output_filepath)
            else:
                concat_cmd = ["ffmpeg", "-y"]
                for w in wav_files:
                    concat_cmd.extend(["-i", w])
                    
                filter_str = "".join([f"[{j}:0]" for j in range(len(wav_files))])
                filter_str += f"concat=n={len(wav_files)}:v=0:a=1[out]"
                
                concat_cmd.extend(["-filter_complex", filter_str, "-map", "[out]", output_filepath])
                
                process = await asyncio.create_subprocess_exec(
                    *concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Erro ao concatenar áudios com ffmpeg: {stderr.decode()}")
                    raise Exception("Falha na concatenação dos áudios")
                    
            logger.info(f"Áudio TTS salvo e convertido em: {output_filepath}")
            
        except Exception as e:
            logger.error(f"Erro na síntese TTS Multi-Idioma: {e}")
            raise e
        finally:
            # Limpeza final dos arquivos temporários de WAV
            for w in wav_files:
                if os.path.exists(w):
                    try:
                        os.remove(w)
                    except:
                        pass
    async def stream_audio_generator(self, text: str):
        """
        Faz stream do áudio diretamente da nuvem em tempo real (em formato MP3).
        Suporta tags <lang="XX">texto</lang> enviando sequencialmente.
        """
        import re
        
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        logger.info(f"Iniciando stream TTS para: '{clean_text}'")
        
        VOICE_MAP = {
            "en-US": "en-US-AriaNeural",
            "es-ES": "es-ES-ElviraNeural",
            "de-DE": "de-DE-AmalaNeural",
            "fr-FR": "fr-FR-DeniseNeural",
            "it-IT": "it-IT-IsabellaNeural",
            "ja-JP": "ja-JP-NanamiNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural"
        }

        pattern = r'<lang="([^"]+)">(.*?)</lang>'
        parts = re.split(pattern, clean_text)
        
        parsed_segments = []
        i = 0
        while i < len(parts):
            if parts[i].strip():
                parsed_segments.append((self.current_voice_name, parts[i].strip()))
            i += 1
            if i < len(parts):
                locale = parts[i]
                inside_text = parts[i+1]
                if inside_text.strip():
                    voice = VOICE_MAP.get(locale, self.current_voice_name)
                    parsed_segments.append((voice, inside_text.strip()))
                i += 2
                
        if not parsed_segments:
            parsed_segments = [(self.current_voice_name, clean_text)]
            
        for voice, segment_text in parsed_segments:
            communicate = edge_tts.Communicate(segment_text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

# Singleton
_tts_instance = None

def get_tts_engine() -> TTSEngine:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSEngine()
    return _tts_instance
