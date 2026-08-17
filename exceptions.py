import os
import sys
import traceback
from datetime import datetime

class ElonaError(Exception):
    def __init__(self, message='', context=None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()
    def log_to_file(self, log_dir='logs'):
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fn = os.path.join(log_dir, f'error_log_{ts}.txt')
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(f'=== Error: {self.__class__.__name__} ===\n{self.message}\n')
            traceback.print_exc(file=f)
        return fn

class GameLogicError(ElonaError): pass
class SaveSystemError(ElonaError): pass
class SaveDataCorruptedError(SaveSystemError): pass
class ConfigError(ElonaError): pass
class NetworkError(ElonaError): pass
