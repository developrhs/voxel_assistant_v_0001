import asyncio
import json
import re
import tempfile
from pathlib import Path


class AudioOutputConfig:
    def __init__(self, project_root=None, engines=None, player=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.config_path = self.project_root / "config" / "database" / "database_general.json"
        self.engines = engines or {}
        self.player = player
        self.current_audio = None
        self.settings = {}
        self.update_voice_settings()
        self.setup_tts_engines()

    def update_voice_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
        self.settings = configuration.get("voice_config", {})
        self.primary_engine = self.settings.get("primary_engine", "google_tts")
        self.fallback_engine = self.settings.get("fallback_engine", "pyttsx3")
        self.use_fallback = bool(self.settings.get("use_fallback", True))
        self.voice_language = self.settings.get("voice_language", "en")
        self.accent = self.settings.get("accent", "com")
        self.voice_gender = self.settings.get("voice_gender", "female")
        self.pyttsx3_rate = float(self.settings.get("pyttsx3_rate", 150.0))
        self.voice_volume = float(self.settings.get("voice_volume", self.settings.get("output_volume", 1.0)))
        self.playback_library = self.settings.get("playback_library", "sounddevice")
        self.output_device = self.settings.get("output_device")
        self.wait_for_audio_end = bool(self.settings.get("wait_for_audio_end", True))
        return self.settings

    def _save_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
        configuration["voice_config"].update(self.settings)
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(configuration, file, ensure_ascii=False, indent=4)

    def setup_tts_engines(self):
        self.engine_handlers = dict(self.engines)
        if "pyttsx3" not in self.engine_handlers:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", self.pyttsx3_rate)
                engine.setProperty("volume", self.voice_volume)
                voices = engine.getProperty("voices") or []
                for voice in voices:
                    identity = f"{voice.id} {voice.name}".lower()
                    if self.voice_gender.lower() in identity:
                        engine.setProperty("voice", voice.id)
                        break
                self.engine_handlers["pyttsx3"] = engine
            except Exception:
                pass
        return list(self.engine_handlers)

    @staticmethod
    def clean_text(text_to_speak):
        text = str(text_to_speak)
        text = re.sub(r"(\*\*|__|~~|`|#+)", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def _synthesize_google(self, text):
        from gtts import gTTS
        output = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output.close()
        gTTS(text=text, lang=self.voice_language, tld=self.accent).save(output.name)
        return output.name

    def _synthesize_edge(self, text):
        handler = self.engine_handlers.get("edge_tts")
        if handler is None:
            raise RuntimeError("Motor edge_tts indisponível.")
        result = handler(text, self.voice_language, self.voice_gender)
        if asyncio.iscoroutine(result):
            return asyncio.run(result)
        return result

    def _synthesize(self, engine_name, text):
        handler = self.engine_handlers.get(engine_name)
        if engine_name == "google_tts" and handler is None:
            return self._synthesize_google(text)
        if engine_name == "edge_tts" and handler is None:
            return self._synthesize_edge(text)
        if handler is None:
            raise RuntimeError(f"Motor TTS indisponível: {engine_name}")
        if engine_name == "pyttsx3" and hasattr(handler, "save_to_file"):
            output = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            output.close()
            handler.setProperty("rate", self.pyttsx3_rate)
            handler.setProperty("volume", self.voice_volume)
            handler.save_to_file(text, output.name)
            handler.runAndWait()
            return output.name
        return handler(text, self.settings)

    def _play(self, audio):
        self.current_audio = audio
        if self.player is not None:
            return self.player(audio, self.voice_volume, self.output_device, self.wait_for_audio_end)
        if self.playback_library == "pygame":
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(audio)
            pygame.mixer.music.set_volume(self.voice_volume)
            pygame.mixer.music.play()
            if self.wait_for_audio_end:
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            return audio
        return audio

    def speak_text(self, text):
        clean = self.clean_text(text)
        if not clean:
            return {"status": "EMPTY_TEXT", "text": ""}
        engines = [self.primary_engine]
        if self.use_fallback and self.fallback_engine not in engines:
            engines.append(self.fallback_engine)
        last_error = None
        for engine_name in engines:
            try:
                audio = self._synthesize(engine_name, clean)
                self._play(audio)
                return {"status": "SUCCESS", "engine": engine_name, "text": clean, "audio": audio}
            except Exception as error:
                last_error = str(error)
        return {"status": "TTS_ERROR", "message": last_error or "Nenhum motor TTS disponível.", "text": clean}

    def speak(self, text_to_speak):
        return self.speak_text(text_to_speak)

    def stop_speaking(self):
        if self.player is not None and hasattr(self.player, "stop"):
            self.player.stop()
        if self.playback_library == "pygame":
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.current_audio = None
        return {"status": "STOPPED"}

    def set_volume(self, level):
        self.voice_volume = max(0.0, min(1.0, float(level)))
        self.settings["voice_volume"] = self.voice_volume
        self.settings["output_volume"] = self.voice_volume
        for engine in self.engine_handlers.values():
            if hasattr(engine, "setProperty"):
                try:
                    engine.setProperty("volume", self.voice_volume)
                except Exception:
                    pass
        self._save_settings()
        return self.voice_volume
