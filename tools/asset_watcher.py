import os
import time
import threading
from pathlib import Path
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class AssetWatcher:
    """Watches the assets directory for changes and triggers a reload callback."""
    
    def __init__(self, watch_dir: str | Path, on_change_callback: Callable[[], None], poll_interval: float = 1.0):
        self.watch_dir = Path(watch_dir)
        self.on_change_callback = on_change_callback
        self.poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._last_mtime = self._get_latest_mtime()
        
    def _get_latest_mtime(self) -> float:
        latest = 0.0
        if not self.watch_dir.exists():
            return latest
        for root, _, files in os.walk(self.watch_dir):
            for file in files:
                if file.endswith(('.png', '.json')):
                    try:
                        mtime = os.path.getmtime(os.path.join(root, file))
                        if mtime > latest:
                            latest = mtime
                    except OSError:
                        pass
        return latest
        
    def _poll_loop(self):
        while self._running:
            time.sleep(self.poll_interval)
            current_mtime = self._get_latest_mtime()
            if current_mtime > self._last_mtime:
                logger.info("AssetWatcher: Detected changes in assets, triggering reload.")
                self._last_mtime = current_mtime
                try:
                    self.on_change_callback()
                except Exception as e:
                    logger.error(f"AssetWatcher: Error during reload: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"AssetWatcher: Started watching {self.watch_dir}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    def dummy_callback():
        print("Reload callback triggered!")
    watcher = AssetWatcher(Path(__file__).parent.parent / "assets", dummy_callback)
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
