"""Suporte específico para Voz em Texto e captura do microfone."""
from .support_manager import SupportManager


class AudioInputSupport:
    def __init__(self, project_root=None):
        self.manager = SupportManager(project_root)

    def test_devices(self, device_probe=None):
        return self.manager.check_audio_input(device_probe=device_probe)

    def calibrate(self, volume_samples=None):
        return self.manager.calibrate_audio_input(volume_samples)

    def capture(self):
        return self.manager.capture_audio_input()
