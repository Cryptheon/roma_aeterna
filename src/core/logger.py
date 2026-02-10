import logging
import os
from datetime import datetime

class SimLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimLogger, cls).__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Simulation Log
        self.sim_logger = logging.getLogger('rome_sim')
        self.sim_logger.setLevel(logging.INFO)
        fh = logging.FileHandler(f'logs/sim_{datetime.now().strftime("%Y%m%d")}.log')
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        self.sim_logger.addHandler(fh)

        # Chat Log
        self.chat_logger = logging.getLogger('rome_chat')
        self.chat_logger.setLevel(logging.INFO)
        ch = logging.FileHandler('logs/chat.log')
        ch.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
        self.chat_logger.addHandler(ch)

    def log_event(self, category: str, message: str):
        print(f"[{category}] {message}")
        self.sim_logger.info(f"[{category}] {message}")

    def log_chat(self, speaker, content):
        self.chat_logger.info(f"{speaker}: {content}")
