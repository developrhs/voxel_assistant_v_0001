"""Suporte específico para Texto em Voz."""
from .support_manager import SupportManager


class AudioOutputSupport:
    def __init__(self, project_root=None):
        self.manager = SupportManager(project_root)

    def test_engines(self, output_probe=None):
        return self.manager.check_audio_output(output_probe=output_probe)

    def speak_test(self, engine=None, text=None):
        return self.manager.test_audio_output(engine=engine, text=text)
