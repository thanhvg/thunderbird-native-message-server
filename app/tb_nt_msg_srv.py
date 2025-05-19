#!/usr/bin/env python3


import argparse
import http.server
import json
import json
import queue  # For thread-safe communication
import socketserver
import struct
import sys

from http import HTTPStatus
from queue import Queue
from threading import Thread

def get_messsage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        sys.exit(0)
    messageLength = struct.unpack('@I', rawLength)[0]
    message = sys.stdin.buffer.read(messageLength).decode('utf-8')
    return json.loads(message)

# Encode a message for transmission, given its content.
def encode_message(message_content):
    encoded_content = json.dumps(message_content, separators=(',', ':')).encode('utf-8')
    encoded_length = struct.pack('@I', len(encoded_content))
    return {'length': encoded_length, 'content': encoded_content}

# Send an encoded message to stdout
def send_message(encoded_message):
    sys.stdout.buffer.write(encoded_message['length'])
    sys.stdout.buffer.write(encoded_message['content'])
    sys.stdout.buffer.flush()


def process_stdin(message_queue):
    """Reads messages from stdin, interacts with web server, and sends processed messages to stdout."""
    while True:
        try:
            message = get_messsage()
            # Process the message
            # Example:  If it's a request for the web server, handle it.  Otherwise, treat it as regular stdin message
            if message.get("target") == "web_server":
                # Get the data and forward it to the web server
                message_queue.put(("stdin_request", message["data"])) # Tag the message source
                # Wait for response from the web server.  Important to handle timeout in real code.
                response = message_queue.get()
                if response[0] == "web_response":
                    response_data = response[1]
                    encoded_message = encode_message(response_data)
                    send_message(encoded_message)
                else:
                    error_data = {"error": "Unexpected response from web server"}
                    encoded_message = encode_message(error_data)
                    send_message(encoded_message)

            else:
                # Default stdin handling: Echo back the received message.
                response_data = {"status": "received", "message": message}
                encoded_message = encode_message(response_data)
                send_message(encoded_message)

        except Exception as e:
            # Handle potential errors during message processing or encoding
            print(f"Error processing stdin: {e}", file=sys.stderr)
            sys.stderr.flush()  # Crucial to flush stderr too
            break  # Exit the loop

def process_stdout(message_queue):
    while True:
        request = message_queue.get();
        encoded_message = encode_message(request)
        send_message(encoded_message)

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
            self.message_queue.put(message_id)
            return  # important to return after sending the response
        
        # Serve other files as usual
        super().do_GET()


def run_server(port, message_queue):
    """Runs a simple web server with JSON endpoint."""
    handler = lambda *args, **kwargs: JSONHandler(*args, message_queue=message_queue, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        # print(f"Serving at port {port}")
        httpd.serve_forever()



def main():
    parser = argparse.ArgumentParser(description="Web server and stdin processor.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the web server.")
    args = parser.parse_args()

    # Shared queue for communication between server and stdin
    message_queue = queue.Queue()

    # Start the web server in a separate thread
    server_thread = Thread(target=run_server, args=(args.port, message_queue))
    # server_thread.daemon = True
    server_thread.start()

    # Process stdin in another thread
    # stdin_thread = Thread(target=process_stdin, args=(message_queue,))
    # stdin_thread.daemon = True
    # stdin_thread.start()

    stdout_thread = Thread(target=process_stdout, args=(message_queue, ))
    stdout_thread.start()

    server_thread.join()
    stdout_thread.join()



# if __name__ == "__main__":
    # Ensure stderr is not buffered
    # sys.stderr.reconfigure(line_buffering=True)
    # main()

    print("why")

# print("why2")
main()
