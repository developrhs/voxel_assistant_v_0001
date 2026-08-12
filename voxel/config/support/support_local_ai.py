"""Suporte específico para IA Local."""
from .support_manager import SupportManager


class LocalAISupport:
    def __init__(self, project_root=None):
        self.manager = SupportManager(project_root)

    def check(self, local_probe=None):
        return self.manager.check_local_ai(local_probe=local_probe)

    def run_test(self, prompt=None):
        return self.manager.test_local_ai(prompt=prompt)
