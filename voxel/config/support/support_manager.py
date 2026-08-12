"""Ferramentas de diagnóstico e correção do VOXEL.

As rotinas deste módulo não instalam pacotes nem alteram o sistema operativo.
Elas verificam capacidades disponíveis, executam testes controlados e guardam
as preferências/resultados em database_general.json.
"""
from __future__ import annotations

import json
import math
import platform
import shutil
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class SupportManager:
    def __init__(self, project_root=None, config_path=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.config_path = Path(config_path) if config_path else self.project_root / "config" / "database" / "database_general.json"

    def load_config(self) -> dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def save_config(self, config: dict[str, Any]) -> None:
        temporary = self.config_path.with_suffix(".support.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=4)
        temporary.replace(self.config_path)

    def _record(self, section: str, result: dict[str, Any], updates=None) -> dict[str, Any]:
        config = self.load_config()
        support = config.setdefault("support_diagnostics", {})
        support["last_run_at"] = datetime.now().isoformat(timespec="seconds")
        support.setdefault("tests", {})[section] = result
        if updates:
            for target_section, values in updates.items():
                config.setdefault(target_section, {}).update(values)
        self.save_config(config)
        return result

    @staticmethod
    def _status(ok: bool, message: str, **extra) -> dict[str, Any]:
        return {"status": "OK" if ok else "WARNING", "message": message, **extra}

    def check_audio_input(self, device_probe: Callable | None = None) -> dict[str, Any]:
        config = self.load_config().get("microphone_config", {})
        devices = []
        error = ""
        try:
            if device_probe:
                devices = device_probe() or []
            else:
                import sounddevice
                for index, device in enumerate(sounddevice.query_devices()):
                    if device.get("max_input_channels", 0) > 0:
                        devices.append({"id": index, "name": device.get("name", f"Dispositivo {index}"), "sample_rate": device.get("default_samplerate")})
        except (ImportError, OSError, Exception) as exc:
            error = str(exc)
        selected = config.get("input_device")
        valid = bool(devices) and (selected is None or any(str(item.get("id")) == str(selected) for item in devices))
        result = self._status(valid, "Microfone disponível e configuração válida." if valid else (error or "Nenhum microfone disponível no ambiente atual."), devices=devices, selected_device=selected, settings={"samplerate": config.get("samplerate"), "channels": config.get("channels"), "blocksize": config.get("blocksize"), "threshold_volume": config.get("threshold_volume", config.get("volume_threshold")), "silence_time": config.get("silence_time"), "max_speech_time": config.get("max_speech_time")})
        return self._record("audio_input", result)

    def calibrate_audio_input(self, volume_samples=None) -> dict[str, Any]:
        config = self.load_config().get("microphone_config", {})
        values = []
        if volume_samples is not None:
            values = [abs(float(value)) for sample in volume_samples for value in (sample if hasattr(sample, "__iter__") else [sample])]
        average = sum(values) / len(values) if values else None
        if average is None:
            result = self._status(False, "Não foi possível calibrar: forneça amostras ou execute a captura com um microfone disponível.", samples=0)
            return self._record("audio_calibration", result)
        threshold = max(average * 1.5, 0.001)
        energy = max(average * 1000, 1.0)
        result = self._status(True, "Sensibilidade calibrada a partir das amostras fornecidas.", samples=len(values), average_volume=average, threshold_volume=threshold, energy_threshold=energy)
        return self._record("audio_calibration", result, {"microphone_config": {"threshold_volume": threshold, "energy_threshold": energy, "calibration_profile": "support_calibrated"}})

    def capture_audio_input(self) -> dict[str, Any]:
        try:
            from config.config_audio_input import AudioInputConfig
            audio = AudioInputConfig(project_root=self.project_root)
            text = audio.get_text_from_mic()
            ok = bool(text and text != "AUDIO_NOT_UNDERSTOOD")
            result = self._status(ok, "Voz reconhecida." if ok else "A captura terminou sem texto reconhecido.", transcript=text if ok else "", engine=audio.recognition_engine)
        except Exception as exc:
            result = self._status(False, f"Falha na captura de Voz em Texto: {exc}", transcript="")
        return self._record("audio_input_capture", result)

    def check_audio_output(self, output_probe: Callable | None = None) -> dict[str, Any]:
        config = self.load_config().get("voice_config", {})
        engines = {"pyttsx3": False, "google_tts": False, "edge_tts": False}
        errors = {}
        if output_probe:
            try: engines.update(output_probe() or {})
            except Exception as exc: errors["probe"] = str(exc)
        else:
            try:
                import pyttsx3
                engine = pyttsx3.init(); engines["pyttsx3"] = bool(engine); engine.stop() if hasattr(engine, "stop") else None
            except Exception as exc: errors["pyttsx3"] = str(exc)
            try:
                import gtts
                engines["google_tts"] = bool(gtts)
            except Exception as exc: errors["google_tts"] = str(exc)
            try:
                import edge_tts
                engines["edge_tts"] = bool(edge_tts)
            except Exception as exc: errors["edge_tts"] = str(exc)
        primary = str(config.get("primary_engine", "pyttsx3"))
        ok = bool(engines.get(primary)) or bool(config.get("use_fallback", True) and any(engines.values()))
        result = self._status(ok, "Motor de Texto em Voz disponível." if ok else "Nenhum motor de Texto em Voz disponível.", engines=engines, primary_engine=primary, fallback_engine=config.get("fallback_engine"), errors=errors)
        return self._record("audio_output", result)

    def test_audio_output(self, engine=None, text=None) -> dict[str, Any]:
        audio_path = None
        try:
            from config.config_audio_output import AudioOutputConfig
            audio = AudioOutputConfig(project_root=self.project_root)
            if engine:
                audio.primary_engine = engine
                audio.use_fallback = False
            result_tts = audio.speak_text(text or self.load_config().get("support_diagnostics", {}).get("audio_output", {}).get("test_text", "Este é um teste de voz do VOXEL."))
            audio_path = result_tts.get("audio") if isinstance(result_tts, dict) else None
            result = self._status(result_tts.get("status") == "SUCCESS", result_tts.get("message", "Texto em Voz executado."), engine=result_tts.get("engine", engine), text=result_tts.get("text", text or ""), audio_file_created=bool(audio_path))
        except Exception as exc:
            result = self._status(False, f"Falha no teste de Texto em Voz: {exc}", engine=engine)
        finally:
            if audio_path:
                try: Path(audio_path).unlink(missing_ok=True)
                except OSError: pass
        return self._record("audio_output_test", result)

    def check_local_ai(self, local_probe: Callable | None = None) -> dict[str, Any]:
        config = self.load_config().get("local_ai_config", {})
        model = str(config.get("default_model", "simple"))
        available = False; response = ""; error = ""
        try:
            if local_probe:
                probe = local_probe(model) or {}
                available = bool(probe.get("available")); response = str(probe.get("response", "")); error = str(probe.get("error", ""))
            elif model in {"simple", "echo"}:
                available = True; response = "Resposta local de diagnóstico."
            elif model == "ollama":
                with socket.create_connection(("127.0.0.1", 11434), timeout=2): available = True
            else:
                available = bool(config.get("model_name") or config.get("model_path") or config.get("installed_model_info"))
        except Exception as exc:
            error = str(exc)
        result = self._status(available, "IA Local pronta para teste." if available else (error or f"Modelo local indisponível: {model}."), model=model, response=response, error=error)
        return self._record("local_ai", result)

    def test_local_ai(self, prompt=None) -> dict[str, Any]:
        try:
            from config.config_local_ai import LocalAIConfig
            settings = self.load_config().get("support_diagnostics", {}).get("local_ai", {})
            ai = LocalAIConfig(project_root=self.project_root)
            response = ai.generate_response(prompt or settings.get("test_prompt", "Responda apenas: teste local concluído."))
            ok = response not in {"LOCAL_AI_NOT_AVAILABLE", ""}
            result = self._status(ok, "Resposta da IA Local recebida." if ok else "IA Local não devolveu uma resposta.", model=ai.default_model, response=response)
        except Exception as exc:
            result = self._status(False, f"Falha no teste de IA Local: {exc}", response="")
        return self._record("local_ai_test", result)

    def check_online_ai(self, online_probe: Callable | None = None) -> dict[str, Any]:
        config = self.load_config().get("online_ai_config", {})
        provider = str(config.get("default_provider", config.get("provider", "none"))).lower()
        key = config.get("api_key") or config.get("api_keys", {}).get(provider, "")
        online = False; error = ""
        try:
            if online_probe:
                probe = online_probe(provider, config) or {}
                online = bool(probe.get("available")); error = str(probe.get("error", ""))
            else:
                with socket.create_connection(("8.8.8.8", 53), timeout=2): online = True
        except Exception as exc:
            error = str(exc)
        ready = online and provider not in {"", "none"} and bool(key)
        message = "IA Online pronta para teste." if ready else ("Internet disponível, mas provedor/chave API não configurados." if online else "Sem ligação à Internet no ambiente atual.")
        result = self._status(ready, message, provider=provider, internet=online, api_key_configured=bool(key), error=error)
        return self._record("online_ai", result)

    def test_online_ai(self, prompt=None) -> dict[str, Any]:
        try:
            from config.config_online_ai import OnlineAIConfig
            settings = self.load_config().get("support_diagnostics", {}).get("online_ai", {})
            ai = OnlineAIConfig(project_root=self.project_root)
            response = ai.generate_response(prompt or settings.get("test_prompt", "Responda apenas: teste online concluído."))
            ok = response not in {"ONLINE_AI_TIMEOUT", "ONLINE_AI_ERROR", "NO_INTERNET_CONNECTION", "MISSING_API_KEY", ""}
            result = self._status(ok, "Resposta da IA Online recebida." if ok else "IA Online não devolveu uma resposta.", provider=ai.active_provider, response=response)
        except Exception as exc:
            result = self._status(False, f"Falha no teste de IA Online: {exc}", response="")
        return self._record("online_ai_test", result)

    def run_all(self) -> dict[str, Any]:
        return {"audio_input": self.check_audio_input(), "audio_output": self.check_audio_output(), "local_ai": self.check_local_ai(), "online_ai": self.check_online_ai()}
