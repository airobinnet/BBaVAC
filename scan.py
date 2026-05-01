import os
import requests
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from bit import Key, wif_to_key
from privatekey import PrivateKey
import time

# ANSI color codes
RED = "\033[1;31m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
MAGENTA = "\033[1;35m"
CYAN = "\033[1;36m"
RESET = "\033[0m"

class Scan:
    def __init__(self, file_manager, socketio=None):
        self.logger = logging.getLogger('BBaVAC')
        self.file = file_manager
        self.socketio = socketio
        self.balancetotal = 0
        self.noemptyaddr = 0
        self.max_threads = 10
        self.discoveries = []
        self.fancies = []
        self.checked = 0
        self.wordlist = []
        
        self.is_paused = False
        self.is_stopped = True  # Start stopped
        self.verbose = False
        self.sleep_throttle = 0.0
        self.max_threads_changed = False
        
        self.reload_lists()
        
        self.output_directory = 'output'
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
        
        self.current_file_index = 0
        self.current_file = self._create_new_file()
        self.key_list = []

    def reload_lists(self):
        # Reload pieces/wordlist
        self.wordlist = self.file.read_pieces_file()
        # Reload custom keys
        self.customwif = self.file.read_dictionary()
        self.maxCustom = 0
        self.checkedcustom = False
        self._log(f"Reloaded lists: {len(self.wordlist)} words, {len(self.customwif)} custom keys.", 'info')

    def _create_new_file(self):
        file_path = os.path.join(self.output_directory, f"output_{self.current_file_index}.txt")
        self.current_file_index += 1
        return file_path

    def _log(self, message, type='info'):
        if self.socketio:
            self.socketio.emit('log', {'msg': message, 'type': type})
        if type == 'success':
            self.logger.info(f"{GREEN}{message}{RESET}")
        elif type == 'warning':
            self.logger.warning(f"{YELLOW}{message}{RESET}")
        elif type == 'error':
            self.logger.error(f"{RED}{message}{RESET}")
        else:
            self.logger.info(message)

    def _check_key(self, wif):
        if self.is_stopped:
            return
        try:
            key = wif_to_key(wif)
            # Check balance for the Legacy address (standard check)
            addr = key.address
            balance_str = "0.00000000"
            balance = 0.0
            
            try:
                balance = float(key.get_balance('btc'))
                balance_str = f"{balance:.8f}"
            except:
                pass

            log_msg = f"WIF: {wif:52} | ADDR: {addr:34} | BAL: {balance_str} BTC"
            
            found_something = False
            
            if balance > 0:
                self._log(f"FOUND BALANCE! {log_msg}", 'success')
                self.file.write_discovery(addr, None, wif, balance)
                self.balancetotal += balance
                self.noemptyaddr += 1
                if addr not in self.discoveries:
                    self.discoveries.append(f"{addr} ({balance_str} BTC)")
                found_something = True
            else:
                # Check for vanity/fancy
                for word in self.wordlist:
                    if word.lower() in addr.lower():
                        if addr not in self.fancies:
                            self._log(f"FANCY HIT! {log_msg} (Match: {word})", 'warning')
                            with open('fancy_addresses.txt', 'a') as f:
                                f.write(f"{word} | {addr} | {wif} | Legacy\n")
                            self.fancies.append(addr)
                            found_something = True
                        break
            
            if self.verbose and not found_something:
                self._log(log_msg, 'info')
                
            self.checked += 1
            if self.checked % 10 == 0:
                self._emit_stats()
                
        except Exception as e:
            import traceback
            self._log(f"Error checking key {wif}: {str(e)}\n{traceback.format_exc()}", 'error')

    def _emit_stats(self):
        if self.socketio:
            self.socketio.emit('stats', {
                'checked': self.checked,
                'balancetotal': self.balancetotal,
                'noemptyaddr': self.noemptyaddr,
                'fancies': len(self.fancies),
                'discoveries': self.discoveries
            })

    def launch(self, compressed=False):
        self._log("Engine initialized. Standing by...", 'info')
        
        while True:
            if self.is_stopped:
                time.sleep(0.1)
                continue

            # Limit queue size to max_threads * 2 to keep engine responsive
            semaphore = threading.Semaphore(self.max_threads * 2)

            def task_wrapper(wif):
                try:
                    self._check_key(wif)
                finally:
                    semaphore.release()

            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                self.max_threads_changed = False
                while not self.is_stopped and not self.max_threads_changed:
                    if self.is_paused:
                        time.sleep(0.1)
                        continue

                    # Wait for a slot in the queue
                    if not semaphore.acquire(timeout=0.1):
                        continue

                    # Get next WIF
                    wif = None
                    if not self.checkedcustom:
                        if self.customwif and self.maxCustom < len(self.customwif):
                            wif = self.customwif[self.maxCustom]
                            self.maxCustom += 1
                        else:
                            self.checkedcustom = True
                    
                    if self.checkedcustom:
                        pkey = PrivateKey()
                        wif = pkey.privatekey_to_wif(compressed=compressed)
                    
                    executor.submit(task_wrapper, wif)
                    
                    if self.sleep_throttle > 0:
                        time.sleep(self.sleep_throttle)
        
        self._log("Engine stopped.", 'warning')

    def pause(self):
        self.is_paused = True
        self._log("Engine paused.", 'warning')

    def resume(self):
        self.is_paused = False
        self.is_stopped = False
        self._log("Engine resumed.", 'success')

    def stop(self):
        self.is_stopped = True
        self._log("Engine stopping...", 'warning')

    def update_settings(self, max_threads, sleep_throttle, verbose):
        if self.max_threads != max_threads:
            self.max_threads = max_threads
            self.max_threads_changed = True
            self._log(f"Max threads updated to {max_threads}. Restarting thread pool...", 'info')
        
        self.sleep_throttle = sleep_throttle
        self.verbose = verbose
        self._log(f"Settings updated: Throttle={sleep_throttle}s, Verbose={verbose}", 'info')
