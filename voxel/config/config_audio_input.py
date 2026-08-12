import io
import json
import time
import wave
from pathlib import Path


class AudioInputConfig:
    def __init__(self, project_root=None, audio_backend=None, recognizers=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.config_path = self.project_root / "config" / "database" / "database_general.json"
        self.audio_backend = audio_backend
        self.recognizers = recognizers or {}
        self.settings = {}
        self.update_settings()

    def update_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            settings = json.load(file)
        self.settings = settings.get("microphone_config", {})
        self.input_device = self.settings.get("input_device")
        self.samplerate = int(self.settings.get("samplerate", 44100))
        self.channels = int(self.settings.get("channels", 1))
        self.blocksize = int(self.settings.get("blocksize", 512))
        self.volume_threshold = float(self.settings.get("threshold_volume", self.settings.get("volume_threshold", 0.05)))
        self.silence_time = float(self.settings.get("silence_time", 3.0))
        self.max_speech_time = float(self.settings.get("max_speech_time", 20.0))
        self.recognition_engine = str(self.settings.get("recognition_engine", "google")).lower()
        self.recognition_language = str(self.settings.get("recognition_language", "en-US"))
        self.normalize_audio = bool(self.settings.get("normalize_audio", True))
        self.remove_noise = bool(self.settings.get("remove_noise", False))
        self.microphone_gain = float(self.settings.get("microphone_gain", 1.0))
        self.calibration_profile = self.settings.get("calibration_profile", "normal")
        self.energy_threshold = float(self.settings.get("energy_threshold", 100.0))
        return settings

    def _save_settings(self):
        with self.config_path.open("r", encoding="utf-8") as file:
            configuration = json.load(file)
        configuration["microphone_config"].update(self.settings)
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(configuration, file, ensure_ascii=False, indent=4)

    def get_available_microphones(self):
        if self.audio_backend is not None and hasattr(self.audio_backend, "query_devices"):
            devices = self.audio_backend.query_devices()
            microphones = [
                {"id": index, "name": device["name"]}
                for index, device in enumerate(devices)
                if device.get("max_input_channels", 0) > 0
            ]
        else:
            try:
                import sounddevice
                devices = sounddevice.query_devices()
                microphones = [
                    {"id": index, "name": device["name"]}
                    for index, device in enumerate(devices)
                    if device.get("max_input_channels", 0) > 0
                ]
            except (ImportError, OSError):
                microphones = []
        self.settings["input_device_options"] = microphones
        self._save_settings()
        return microphones

    def calibrate_noise_level(self, volume_samples=None):
        if volume_samples is None:
            volume_samples = []
            if self.audio_backend is not None and hasattr(self.audio_backend, "record"):
                volume_samples = self.audio_backend.record(
                    int(self.samplerate * 1.5), samplerate=self.samplerate,
                    channels=self.channels, device=self.input_device
                )
        values = [abs(float(value)) for sample in volume_samples for value in (sample if hasattr(sample, "__iter__") else [sample])]
        average = sum(values) / len(values) if values else 0.0
        self.energy_threshold = max(average * 1000, 1.0)
        self.volume_threshold = max(average * 1.5, 0.001)
        self.settings["energy_threshold"] = self.energy_threshold
        self.settings["threshold_volume"] = self.volume_threshold
        self._save_settings()
        return {"energy_threshold": self.energy_threshold, "volume_threshold": self.volume_threshold}

    def _normalize(self, samples):
        peak = max((abs(float(sample)) for sample in samples), default=0.0)
        if peak == 0:
            return samples
        return [float(sample) / peak for sample in samples]

    def _reduce_noise(self, samples):
        if not samples:
            return samples
        average = sum(float(sample) for sample in samples) / len(samples)
        return [float(sample) - average for sample in samples]

    def start_listening(self, blocks=None):
        if blocks is None:
            if self.audio_backend is None:
                try:
                    import sounddevice
                    self.audio_backend = sounddevice
                except ImportError as error:
                    raise RuntimeError("Nenhum backend de áudio disponível.") from error
            blocks = self.audio_backend.rec(
                int(self.samplerate * self.max_speech_time), samplerate=self.samplerate,
                channels=self.channels, dtype="float32", device=self.input_device
            )

        captured = []
        started = False
        silent_since = None
        started_at = time.monotonic()
        for block in blocks:
            values = [float(value) * self.microphone_gain for value in (block if hasattr(block, "__iter__") else [block])]
            if self.remove_noise:
                values = self._reduce_noise(values)
            volume = sum(abs(value) for value in values) / len(values) if values else 0.0
            now = time.monotonic()
            if not started and volume >= self.volume_threshold:
                started = True
                started_at = now
            if started:
                captured.extend(values)
                if volume < self.volume_threshold:
                    silent_since = silent_since or now
                    if now - silent_since >= self.silence_time:
                        break
                else:
                    silent_since = None
                if now - started_at >= self.max_speech_time:
                    break
        if self.normalize_audio:
            captured = self._normalize(captured)
        audio_bytes = self._to_wav_bytes(captured)
        return self.recognize_audio(audio_bytes)

    def _to_wav_bytes(self, samples):
        pcm = bytearray()
        for sample in samples:
            value = max(-1.0, min(1.0, float(sample)))
            pcm.extend(int(value * 32767).to_bytes(2, "little", signed=True))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as audio:
            audio.setnchannels(self.channels)
            audio.setsampwidth(2)
            audio.setframerate(self.samplerate)
            audio.writeframes(bytes(pcm))
        return buffer.getvalue()

    def recognize_audio(self, audio_bytes):
        engines = [self.recognition_engine] + [
            engine for engine in self.settings.get("engine_options", []) if engine != self.recognition_engine
        ]
        for engine in engines:
            recognizer = self.recognizers.get(engine)
            if recognizer is None:
                continue
            try:
                text = recognizer(audio_bytes, self.recognition_language)
                if text:
                    return str(text)
            except Exception:
                continue
        return ""

    def get_text_from_mic(self):
        text = self.start_listening()
        return text if text else "AUDIO_NOT_UNDERSTOOD"

    def set_microphone_device(self, device_id):
        self.input_device = device_id
        self.settings["input_device"] = device_id
        self._save_settings()
        return device_id
