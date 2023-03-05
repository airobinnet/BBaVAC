import argparse
import sys
import time
import concurrent.futures
import threading
import logging
from flask import Flask, render_template, jsonify

from file_management import FileManagement
from scan import Scan

app = Flask(__name__)

# Disable Flask logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
log.propagate = False

class Stats:
    def __init__(self):
        self.balancetotal = 0
        self.noemptyaddr = 0
        self.fancies = 0
        self.checked = 0
        self.totaltime = 0
        self.average = 0
        self.wordlist = None
        self.balancelist = None


app.stats = Stats()

def update_stats():
    while True:
        time.sleep(1)  # Update stats every 1 second
        with app.app_context():
            # Update the stats in the Flask application context
            app.stats.balancetotal = scan.balancetotal
            app.stats.noemptyaddr = scan.noemptyaddr
            app.stats.fancies = scan.fancies
            app.stats.checked = scan.checked
            app.stats.totaltime = round(time.time() - start_time, 0)
            app.stats.average = round(app.stats.checked / app.stats.totaltime, 2) if app.stats.checked > 0 else 0
            app.stats.wordlist = scan.wordlist
            app.stats.balancelist = scan.discoveries

@app.route('/stats.json')
def stats_json():
    return jsonify({
        'balancetotal': app.stats.balancetotal,
        'noemptyaddr': app.stats.noemptyaddr,
        'fancies': app.stats.fancies,
        'checked': app.stats.checked,
        'totaltime': app.stats.totaltime,
        'average': app.stats.average,
        'wordlist': app.stats.wordlist,
        'balancelist': app.stats.balancelist
    })

@app.route('/')
def stats():
    return render_template('index.html', stats=app.stats)

if __name__ == '__main__':
    start_time = time.time()
    inputfile = 'custom_private_keys.txt'
    outputfile = 'output.txt'

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Words dictionary file (e.g. dictionary.txt)',
                        type=str, required=False)
    parser.add_argument('-o', '--output', help='output file (e.g. output.txt)',
                        type=str, required=False)
    parser.add_argument('-c', '--compressed', help="Use compressed addresses", action='store_true', required=False)
    parser.add_argument('--version', action='version', version='Version : 0.01')

    args = parser.parse_args()

    if args.input:
        inputfile = args.input
    if args.output:
        outputfile = args.output

    # We initialize file management
    file = FileManagement(outputfile, inputfile)

    # The scan object is initialized
    scan = Scan(file, max_threads=20)
    # Start the stats update thread
    stats_thread = threading.Thread(target=update_stats)
    stats_thread.daemon = True
    stats_thread.start()
    # Launch the Flask application in a separate thread
    flask_thread = threading.Thread(target=app.run)
    flask_thread.daemon = True
    flask_thread.start()
    # Start the scan and get the result.
    try:
        if args.compressed:
            print('Compressed Addresses : ON')
            discoveries = scan.launch(compressed=True)
        else:
            discoveries = scan.launch()

        print(f'Total scans: {scan.checked}')
        total_time = time.time() - start_time
        print(f'Total execution time: {total_time:.2f} seconds')
        print(f'Average per second: {scan.checked / total_time:.2f} scans/second')

        if not scan.fancies:
            print('We didn\'t find any fancy addresses!')
        else:
            print(f'Total number of fancy addresses found: {len(scan.fancies)}')

        # We write the result in a output file
        if not discoveries:
            print('We didn\'t find any addresses with balance :(')
        else:
            print(f'Total number of discoveries: {len(discoveries)}')

    except KeyboardInterrupt:
        print('Exit...')
        print(f'Total scans: {scan.checked}')
        total_time = time.time() - start_time
        print(f'Total execution time: {total_time:.2f} seconds')
        print(f'Average per second: {scan.checked / total_time:.2f} scans/second')
        # We write the result in a output file
        if not scan.fancies:
            print('We didn\'t find any fancy addresses!')
        else:
            print(f'Total number of fancy addresses found: {len(scan.fancies)}')
        if not scan.discoveries:
            print('We didn\'t find any addresses with balance :(')
        else:
            print(f'Total number of discoveries: {len(scan.discoveries)}')
        quit()
        sys.exit()

    print(f'Total execution time: {time.time() - start_time:.2f} seconds')
