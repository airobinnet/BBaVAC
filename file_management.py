import os

class FileManagement:
    def __init__(self, outputfile, inputfile=None, max_discoveries=10):
        # Initialize FileManagement object with outputfile, inputfile (if provided), and max_discoveries
        self.inputfile = inputfile
        self.outputfile = outputfile
        self.max_discoveries = max_discoveries

    def read_dictionary(self):
        # Read inputfile and return its contents as a list of lines
        f = open(self.inputfile, "r")
        lines = f.read().splitlines()
        f.close()
        return lines

    def write_discovery(self, address, password, wif, balance):
        # Write address, password (if provided), wif, and balance to discovery.txt file
        if address is None:
            address = ''
        if password is None:
            password = ''
        if wif is None:
            wif = ''
        if balance is None:
            balance = ''
        with open("discovery.txt", "a") as f:
            f.write(address + "|" + password + "|" + wif + "|" + str(balance) + "\n")

    def write_file(self, filename, content):
        # Safely write content to a file
        # Prevent path traversal by only allowing specific files
        allowed_files = ['custom_private_keys.txt', 'pieces.txt']
        if filename not in allowed_files:
            raise ValueError("File not allowed")
        
        with open(filename, 'w') as f:
            f.write(content)

    def read_pieces_file(self):
        # Read pieces.txt file and return its contents as a list of strings
        if not os.path.exists('pieces.txt'):
            return []
        with open('pieces.txt', 'r') as file:
            lines = file.readlines()
            strings = []
            for line in lines:
                line = line.strip()
                if not line: continue
                if ',' in line:
                    for s in line.split(','):
                        strings.append(s.strip())
                else:
                    strings.append(line)
            return strings
