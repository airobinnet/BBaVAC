import argparse
import sys
import time
import threading
import logging
import psutil
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from file_management import FileManagement
from scan import Scan
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bbavac_secret!'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

import re

# Custom Logging Handler for Socket.IO
class SocketIOHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        # Strip ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_log = ansi_escape.sub('', log_entry)
        socketio.emit('log', {'msg': clean_log, 'type': record.levelname.lower()})

# Setup Logging
logger = logging.getLogger('BBaVAC')
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(sh)
# logger.addHandler(SocketIOHandler()) # Removed to prevent double logging

# Disable Flask/Werkzeug logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send initial stats if needed
    if hasattr(app, 'scan_obj'):
        emit('stats', {
            'checked': app.scan_obj.checked,
            'balancetotal': app.scan_obj.balancetotal,
            'noemptyaddr': app.scan_obj.noemptyaddr,
            'fancies': len(app.scan_obj.fancies),
            'discoveries': app.scan_obj.discoveries
        })
        emit_engine_state()

def emit_engine_state():
    if hasattr(app, 'scan_obj'):
        socketio.emit('engine_state', {
            'is_running': not app.scan_obj.is_stopped,
            'is_paused': app.scan_obj.is_paused,
            'threads': app.scan_obj.max_threads,
            'throttle': app.scan_obj.sleep_throttle,
            'verbose': app.scan_obj.verbose
        })

@socketio.on('control')
def handle_control(data):
    action = data.get('action')
    if hasattr(app, 'scan_obj'):
        if action == 'start':
            app.scan_obj.is_stopped = False
            app.scan_obj.is_paused = False
            app.scan_obj._log("Engine started by user.", 'success')
        elif action == 'pause':
            app.scan_obj.pause()
        elif action == 'resume':
            app.scan_obj.resume()
        elif action == 'stop':
            app.scan_obj.stop()
        emit_engine_state()

@socketio.on('settings')
def handle_settings(data):
    if hasattr(app, 'scan_obj'):
        threads = int(data.get('threads', 10))
        throttle = float(data.get('throttle', 0.0))
        verbose = bool(data.get('verbose', False))
        app.scan_obj.update_settings(threads, throttle, verbose)
        emit_engine_state()

@socketio.on('get_config_files')
def handle_get_config_files():
    try:
        custom_keys = ""
        if os.path.exists('custom_private_keys.txt'):
            with open('custom_private_keys.txt', 'r') as f: custom_keys = f.read()
        
        pieces = ""
        if os.path.exists('pieces.txt'):
            with open('pieces.txt', 'r') as f: pieces = f.read()
            
        emit('config_files', {'custom_keys': custom_keys, 'pieces': pieces})
    except Exception as e:
        logger.error(f"Error reading config files: {e}")

@socketio.on('save_config_file')
def handle_save_config_file(data):
    try:
        filename = data.get('filename')
        content = data.get('content')
        if hasattr(app, 'scan_obj'):
            app.scan_obj.file.write_file(filename, content)
            app.scan_obj.reload_lists()
            emit('save_status', {'status': 'success', 'filename': filename})
    except Exception as e:
        logger.error(f"Error saving config file: {e}")
        emit('save_status', {'status': 'error', 'message': str(e)})

def run_scan(scan_obj, compressed):
    try:
        scan_obj.launch(compressed=compressed)
    except Exception as e:
        logger.error(f"Scan engine crashed: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Custom private keys file', type=str, required=False)
    parser.add_argument('-o', '--output', help='Output file', type=str, required=False)
    parser.add_argument('-c', '--compressed', help="Use compressed addresses", action='store_true', required=False)
    parser.add_argument('-p', '--port', help="Flask port", type=int, default=5000)
    
    args = parser.parse_args()
    
    inputfile = args.input or 'custom_private_keys.txt'
    outputfile = args.output or 'output.txt'
    
    # Ensure files exist
    if not os.path.exists(inputfile):
        with open(inputfile, 'w') as f: pass
        
    file_manager = FileManagement(outputfile, inputfile)
    scan_obj = Scan(file_manager, socketio=socketio)
    app.scan_obj = scan_obj
    
    # Start scan in background thread
    scan_thread = threading.Thread(target=run_scan, args=(scan_obj, args.compressed))
    scan_thread.daemon = True
    scan_thread.start()
    
    def system_monitor():
        while True:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            socketio.emit('sys_stats', {'cpu': cpu, 'ram': mem})

    monitor_thread = threading.Thread(target=system_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    logger.info(f"Starting BBaVAC Web UI on port {args.port}")
    socketio.run(app, host='0.0.0.0', port=args.port, allow_unsafe_werkzeug=True)
