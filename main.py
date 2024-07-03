import json
import socket
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib


STORAGE_PATH = 'storage/data.json'


import logging
logging.basicConfig(level=logging.INFO)
class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', status=404)

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            params = urllib.parse.parse_qs(body.decode())
            message_data = {
                'username': params['username'][0],
                'message': params['message'][0]
            }
            self.send_to_socket_server(message_data)
            self.send_html_file('index.html')
        else:
            self.send_html_file('error.html', status=404)

    def send_html_file(self, filename, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open(filename, 'rb') as fd:
                self.wfile.write(fd.read())
            logging.info(f"Served {filename} with status {status}")
        except IOError:
            self.send_error(404, "File Not Found")

    def send_static(self):
        try:
            self.send_response(200)
            mt = mimetypes.guess_type(self.path)
            if mt and mt[0]:
                self.send_header("Content-type", mt[0])
            else:
                self.send_header("Content-type", 'application/octet-stream')
            self.end_headers()
            with open(f'.{self.path}', 'rb') as file:
                self.wfile.write(file.read())
            logging.info(f"Served static file: {self.path}")
        except IOError:
            self.send_error(404, "File Not Found")

    def send_to_socket_server(self, message_data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            server_address = ('localhost', 5000)
            sock.sendto(json.dumps(message_data).encode(), server_address)

def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', 3000)
    http = server_class(server_address, handler_class)
    try:
        logging.info("Starting HTTP server on port 3000")
        http.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down HTTP server")
        http.server_close()

def run_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', 5000))
    logging.info("Starting UDP Socket server on port 5000")

    while True:
        data, address = sock.recvfrom(1024)
        message_data = json.loads(data.decode())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        record = {timestamp: message_data}
        save_to_storage(record)

def save_to_storage(record):
    pathlib.Path('storage').mkdir(exist_ok=True)
    if pathlib.Path(STORAGE_PATH).exists():
        with open(STORAGE_PATH, 'r', encoding='utf-8') as f:
            storage_data = json.load(f)
    else:
        storage_data = {}

    storage_data.update(record)

    with open(STORAGE_PATH, 'w', encoding='utf-8') as f:
        json.dump(storage_data, f, indent=4)

if __name__ == '__main__':
    threading.Thread(target=run_http_server).start()
    threading.Thread(target=run_socket_server).start()
