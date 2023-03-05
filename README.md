# BBaVAC
 Bitcoin Balance and Vanity Address Checker

![BBaVAC](https://i.imgur.com/o3Heufc.png "BBaVAC")

#### Summary
This project includes 4 Python files that work together to scan Bitcoin private keys for balances and vanity addresses:

1. scan.py - This file contains the main logic for scanning Bitcoin addresses for balances. It uses an optional custom private key list and private key generator to generate addresses and checks their balances using the blockchain API.

2. private_key.py - This file contains a PrivateKey class that is used to generate and manipulate private keys.

3. file_management.py - This file contains a FileManagement class that is used to read and write files, including the wordlist and private key list.

4. main.py - This file is the main entry point for the program. It initializes the FileManagement and Scan objects, launches a Flask web server to display real-time statistics, and runs the scan using command-line arguments.


# Installation

### Clone the repository
```bash
git clone https://github.com/airobinnet/BBaVAC.git
cd <repository>
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Usage
Optional: Prepare a list of Bitcoin private keys that you want to scan. Save the private keys in a text file, with each key on a separate line. The file should be named **custom_private_keys.txt**, or you can specify a different input file using the -i or --input command-line argument.

Optional: Prepare a list of words you would like to see in your vanity addresses. Save the words in a text file, with each word on a separate line. The file should be named **pieces.txt**

## Run the application
```bash
python main.py
```

This will launch the Flask web interface and start the scan.

Optionally, you can specify the output file using the -o or --output command-line argument. By default, the scanner writes the results to output.txt.
You can also enable compressed addresses using the -c or --compressed command-line argument. This will generate compressed addresses instead of uncompressed ones.

While the scanner is running, you can view real-time statistics by visiting http://localhost:5000 in your web browser.

Note this is not an ideal vanity address generator since it's much slower than others because it also checks the balances. The vanity addresses are just a little extra while you scan for balances.

Note that the scanner can take a long time to complete, especially if you're scanning a large number of private keys. Be patient, and let the scanner run until it finishes. If you need to stop the scan, press CTRL+C in the terminal window. The scanner will write the results to the output file before exiting.

Note that there is only an extreme, massive, gigantic small percentage chance of finding any actual balances.