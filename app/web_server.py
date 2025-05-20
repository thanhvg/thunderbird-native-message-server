import http.server
from queue import Queue
import socketserver
import json
from http import HTTPStatus


class JSONHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, message_queue: Queue, **kwargs):
        self.message_queue = message_queue
        super().__init__(*args, **kwargs)

    # def do_POST(self):
    #     """Handles POST requests to the /api endpoint."""
    #     if self.path == '/api':
    #         content_length = int(self.headers['Content-Length'])
    #         body = self.rfile.read(content_length)
    #         try:
    #             data = json.loads(body.decode('utf-8'))

    #             # Send the data to the stdin processor via the queue
    #             self.message_queue.put(("web_request", data))  # Tag the message source

    #             # Wait for a response from the stdin processor
    #             response = self.message_queue.get()  # Block until a response is available
    #             if response[0] == "stdin_response":  # Check the response source
    #                 response_data = response[1]  # Extract the data

    #                 response_body = json.dumps(response_data).encode('utf-8')
    #                 self.send_response(HTTPStatus.OK)
    #                 self.send_header('Content-type', 'application/json')
    #                 self.end_headers()
    #                 self.wfile.write(response_body)
    #             else:
    #                 self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
    #                 self.send_header('Content-type', 'application/json')
    #                 self.send_header('Content-type', 'application/json')
    #                 self.end_headers()
    #                 error_message = json.dumps({"error": "Unexpected response from stdin"}).encode('utf-8')
    #                 self.wfile.write(error_message)


    #         except json.JSONDecodeError:
    #             self.send_response(HTTPStatus.BAD_REQUEST)
    #             self.send_header('Content-type', 'application/json')
    #             self.end_headers()
    #             error_message = json.dumps({"error": "Invalid JSON"}).encode('utf-8')
    #             self.wfile.write(error_message)
    #         except Exception as e:
    #             self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
    #             self.send_header('Content-type', 'application/json')
    #             self.end_headers()
    #             error_message = json.dumps({"error": f"Internal server error: {e}"}).encode('utf-8')
    #             self.wfile.write(error_message)

    #     else:
    #         path_parts = self.path.split('/')
    #         if path_parts[1] == 'mid' and len(path_parts) == 3:
    #             message_id = path_parts[2]
    #             # Send the id to the stdin processor via the queue
    #             self.message_queue.put(("web_request", {"id": message_id}))  # Tag the message source

    #             # Wait for a response from the stdin processor
    #             response = self.message_queue.get()  # Block until a response is available
    #             if response[0] == "stdin_response":  # Check the response source
    #                 response_data = response[1]  # Extract the data

    #                 response_body = json.dumps(response_data).encode('utf-8')
    #                 self.send_response(HTTPStatus.OK)
    #                 self.send_header('Content-type', 'application/json')
    #                 self.end_headers()
    #                 self.wfile.write(response_body)
    #             else:
    #                 self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
    #                 self.send_header('Content-type', 'application/json')
    #                 self.end_headers()
    #                 error_message = json.dumps({"error": "Unexpected response from stdin"}).encode('utf-8')
    #                 self.wfile.write(error_message)
    #             return # important to return after sending the response

    def do_GET(self):
        path_parts = self.path.split('/')
        if len(path_parts) == 3 and path_parts[1] == 'mid':
            message_id = path_parts[2]
            # Send the id to the stdin processor via the queue
            # self.message_queue.put(("web_request", {"id": message_id}))  # Tag the message source

            # # Wait for a response from the stdin processor
            # response = self.message_queue.get()  # Block until a response is available
            # if response[0] == "stdin_response":  # Check the response source
            #     response_data = response[1]  # Extract the data

            #     response_body = json.dumps(response_data).encode('utf-8')
            #     self.send_response(HTTPStatus.OK)
            #     self.send_header('Content-type', 'application/json')
            #     self.end_headers()
            #     self.wfile.write(response_body)
            # else:
            #     self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            #     self.send_header('Content-type', 'application/json')
            #     self.end_headers()
            #     error_message = json.dumps({"error": "Unexpected response from stdin"}).encode('utf-8')
            #     self.wfile.write(error_message)
            self.message_queue.put({'type': 'mid', 'payload': message_id})
            return  # important to return after sending the response
        
        # Serve other files as usual
        super().do_GET()


def run_server(port, message_queue):
    """Runs a simple web server with JSON endpoint."""
    handler = lambda *args, **kwargs: JSONHandler(*args, message_queue=message_queue, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        # print(f"Serving at port {port}")
        httpd.serve_forever()
