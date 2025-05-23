import http.server
import socketserver
from queue import Queue
import json
from http import HTTPStatus

from pubsub import PubSub


class JSONHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, message_queue: Queue, **kwargs):
        self.message_queue = message_queue
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path_parts = self.path.split('/')
        if len(path_parts) == 3 and path_parts[1] == 'mid':
            message_id = path_parts[2]
            self.message_queue.put({'type': 'mid', 'payload': message_id})
            return  # important to return after sending the response
        
        super().do_GET()

def run_server(port, message_queue):
    """Runs a simple web server with JSON endpoint."""
    handler = lambda *args, **kwargs: JSONHandler(*args, message_queue=message_queue, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        # print(f"Serving at port {port}")
        httpd.serve_forever()


class WebServer(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, pub_sub: PubSub, **kwargs):
        self.pub_sub = pub_sub
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path_parts = self.path.split('/')
        if len(path_parts) == 3 and path_parts[1] == 'mid':
            message_id = path_parts[2]
            self.pub_sub.publish('TB_REQUEST', {'type': 'mid', 'payload': message_id})
            return 
        
        super().do_GET()


def start_server(port, pub_sub: PubSub):
    """Runs a simple web server with JSON endpoint."""
    handler = lambda *args, **kwargs: WebServer(*args, pub_sub=pub_sub, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        # print(f"Serving at port {port}")
        httpd.serve_forever()
