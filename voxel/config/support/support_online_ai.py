"""Suporte específico para IA Online."""
from .support_manager import SupportManager


class OnlineAISupport:
    def __init__(self, project_root=None):
        self.manager = SupportManager(project_root)

    def check(self, online_probe=None):
        return self.manager.check_online_ai(online_probe=online_probe)

    def run_test(self, prompt=None):
        return self.manager.test_online_ai(prompt=prompt)
