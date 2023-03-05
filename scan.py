from concurrent.futures import ThreadPoolExecutor, as_completed
from privatekey import PrivateKey  # Import PrivateKey class from privatekey module
from bit import Key, wif_to_key  # Import Key and wif_to_key functions from bit module
import requests
import os

# ANSI color codes for colorizing console output
RED = "\033[1;31m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
MAGENTA = "\033[1;35m"
CYAN = "\033[1;36m"
RESET = "\033[0m"  # reset to default color

class Scan:
    def __init__(self, file, max_threads=20):
        self.file = file  # File instance for reading and writing results
        self.balancetotal = 0  # Total balance across all discovered addresses
        self.noemptyaddr = 0  # Number of non-empty addresses discovered
        self.max_threads = max_threads  # Maximum number of threads to use
        self.discoveries = []  # List of discovered addresses
        self.fancies = []  # List of "fancy" addresses (containing words from wordlist)
        self.checked = 0  # Number of keys checked so far
        self.wordlist = []  # List of words to search for in addresses
        with open("pieces.txt", "r") as f:
            self.wordlist = f.read().splitlines()  # Read wordlist from pieces.txt
        self.maxCustom = 0  # Index of the last custom private key checked
        self.checkedcustom = False  # Flag indicating whether custom private keys have been exhausted
        self.customwif = self.file.read_dictionary()
        self.current_file_index = 0  # index of the current output file
        self.current_file_size = 0  # size of the current output file
        self.output_directory = 'output'  # directory to store output files
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
        self.current_file = self._create_new_file()
        self.key_list = []  # list of keys to write to file

    def _write_to_file(self, key_list):
            file_size = os.stat(self.file.file_path).st_size
            if file_size > 5 * 1024 * 1024:
                self.file.create_new_file()
            with open(self.file.file_path, "a") as f:
                for key in key_list:
                    f.write(f"{key['address']}, {key['wif']}, {key['balance']}\n")

    def _create_new_file(self):
        file_path = f"{self.output_directory}/output_{self.current_file_index}.txt"
        self.current_file_index += 1
        self.current_file_size = 0
        return file_path

    def _check_balance(self):
        try:
            wif = None

            # If customwif is empty or has been checked already
            if self.checkedcustom == False:
                if self.customwif is None:
                    self.checkedcustom = True
            
            # If there are still unchecked customwifs
            if self.checkedcustom == False:
                if self.maxCustom < len(self.customwif):
                    # Take next customwif to check
                    wif = self.customwif[self.maxCustom]
                    self.maxCustom += 1
                else:
                    # All customwifs have been checked
                    self.checkedcustom = True

            # If all customwifs have been checked, generate a new private key
            if self.checkedcustom == True:
                pkey = PrivateKey()
                wif = pkey.privatekey_to_wif()

            # Convert WIF to a Key object
            key = wif_to_key(wif)

            # Get balance for the associated Bitcoin address
            balance = key.get_balance('btc')
            wrote = False
                
            # If the balance is not empty
            if balance != "0" :
                if key.address not in self.discoveries:
                    # Print the balance, address, and WIF to console
                    print(f'{RED}Balance: {balance} for : {key.address} - {wif}{RESET}')
                    # Write the address, WIF, and balance to the discovery file
                    self.file.write_discovery(key.address, None, wif, balance)
                    self.balancetotal += float(balance)
                    self.noemptyaddr += 1
                    self.discoveries.append(key.address)
                    wrote = True
            else:
                # Check if the address contains any fancy word
                for piece in self.wordlist:
                    piece = piece.strip()  # Remove any leading/trailing whitespaces
                    if piece.lower() in key.address.lower() and key.address not in self.fancies:
                        # Add the address, private key, and balance to fancy_addresses.txt
                        with open('fancy_addresses.txt', 'a') as fancy_file:
                            tempkey = key.address
                            fancy_file.write(f'{piece} {key.address} {wif} {balance}\n')
                            # Print the balance, fancy address, and WIF to console
                            print(f'Balance: {balance} for : {tempkey.replace(piece, GREEN + piece + RESET)}{RESET} - {wif}')
                            self.fancies.append(key.address)
                            wrote = True

            # If there are no balances to print, just print the balance and address
            if not wrote:
                print(f'Balance: {balance} for : {key.address} - {wif}')
                self.key_list.append({"address": key.address, "wif": wif}) # Use a dictionary to append address and wif separately
                #every 100 keys, write to file
                if len(self.key_list) >= 100:
                    file_size = os.path.getsize(self.current_file) if os.path.exists(self.current_file) else 0
                    #5000000 bytes = 5MB
                    if file_size >= 5000000:
                        self.current_file = self._create_new_file()
                    with open(self.current_file, 'a') as f:
                        keysstring = ''
                        for key in self.key_list:
                            keysstring += key["address"] + ', ' + key["wif"] + '\n'
                        f.write(f'{keysstring}') # Use keysstring instead of str(self.key_list)
                    self.key_list = []

            self.checked += 1
        except requests.exceptions.RequestException as e:
            print(f"Error checking balance for WIF {wif}: {e}")


    def launch(self):
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = []
            # Loop indefinitely until we have found enough discoveries
            while True:
                # Submit a new future for each balance check
                futures.append(executor.submit(self._check_balance))
                # Check the results of futures that have completed
                for future in as_completed(futures):
                    future.result()
                    futures.remove(future)
                    # If we've found enough addresses, return the discoveries
                    if self.noemptyaddr >= self.file.max_discoveries:
                        return self.discoveries

