import http.server
import socketserver
import queue
import json
from http import HTTPStatus

from pubsub import PubSub

import threading


class JSONHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, message_queue: queue.Queue, **kwargs):
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

    def do_POST(self):
        if self.path == '/query-read-status':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                string_list = data.get('messages', [])  # Expecting a list of strings under the 'messages' key

                # Expecting a list of strings under the  'messages' key
                response_queue = queue.Queue()
                callback = lambda message: response_queue.put(message)
                self.pub_sub.subscribe('TB_RESPONSE', callback=callback)
                self.pub_sub.publish('TB_REQUEST', {'type': 'query_read_status', 'payload': string_list})
                response = response_queue.get(timeout=5) 
                self.pub_sub.unsubscribe('TB_RESPONSE', callback)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'type': 'query_read_status', 'payload': response}).encode('utf-8'))

            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Invalid JSON'}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

def start_server(port, pub_sub: PubSub):
    """Runs a simple web server with JSON endpoint."""
    handler = lambda *args, **kwargs: WebServer(*args, pub_sub=pub_sub, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        # print(f"Serving at port {port}")
        httpd.serve_forever()
