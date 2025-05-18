import argparse
import http.server
import socketserver
import sys
import json
import struct
from threading import Thread
from http import HTTPStatus
import queue  # For thread-safe communication

# Shared queue for communication between server and stdin
message_queue = queue.Queue()


class JSONHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handles POST requests to the /api endpoint."""
        if self.path == '/api':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))

                # Send the data to the stdin processor via the queue
                message_queue.put(("web_request", data))  # Tag the message source

                # Wait for a response from the stdin processor
                response = message_queue.get()  # Block until a response is available
                if response[0] == "stdin_response":  # Check the response source
                    response_data = response[1]  # Extract the data

                    response_body = json.dumps(response_data).encode('utf-8')
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(response_body)
                else:
                    self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error_message = json.dumps({"error": "Unexpected response from stdin"}).encode('utf-8')
                    self.wfile.write(error_message)


            except json.JSONDecodeError:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_message = json.dumps({"error": "Invalid JSON"}).encode('utf-8')
                self.wfile.write(error_message)
            except Exception as e:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_message = json.dumps({"error": f"Internal server error: {e}"}).encode('utf-8')
                self.wfile.write(error_message)

        else:
            # Serve other files as usual
            super().do_GET()  # or super().do_POST() if you want to handle other POSTs


def run_server(port):
    """Runs a simple web server with JSON endpoint."""
    with socketserver.TCPServer(("", port), JSONHandler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()


# Read a message from stdin and decode it.
def getMessage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        sys.exit(0)
    messageLength = struct.unpack('@I', rawLength)[0]
    message = sys.stdin.buffer.read(messageLength).decode('utf-8')
    return json.loads(message)

# Encode a message for transmission, given its content.
def encodeMessage(messageContent):
    encodedContent = json.dumps(messageContent, separators=(',', ':')).encode('utf-8')
    encodedLength = struct.pack('@I', len(encodedContent))
    return {'length': encodedLength, 'content': encodedContent}

# Send an encoded message to stdout
def sendMessage(encodedMessage):
    sys.stdout.buffer.write(encodedMessage['length'])
    sys.stdout.buffer.write(encodedMessage['content'])
    sys.stdout.buffer.flush()


def process_stdin():
    """Reads messages from stdin, interacts with web server, and sends processed messages to stdout."""
    while True:
        try:
            message = getMessage()
            # Process the message
            # Example:  If it's a request for the web server, handle it.  Otherwise, treat it as regular stdin message
            if message.get("target") == "web_server":
                # Get the data and forward it to the web server
                message_queue.put(("stdin_request", message["data"])) # Tag the message source
                # Wait for response from the web server.  Important to handle timeout in real code.
                response = message_queue.get()
                if response[0] == "web_response":
                    response_data = response[1]
                    encoded_message = encodeMessage(response_data)
                    sendMessage(encoded_message)
                else:
                    error_data = {"error": "Unexpected response from web server"}
                    encoded_message = encodeMessage(error_data)
                    sendMessage(encoded_message)


            else:
                # Default stdin handling: Echo back the received message.
                response_data = {"status": "received", "message": message}
                encoded_message = encodeMessage(response_data)
                sendMessage(encoded_message)




        except Exception as e:
            # Handle potential errors during message processing or encoding
            print(f"Error processing stdin: {e}", file=sys.stderr)
            sys.stderr.flush()  # Crucial to flush stderr too
            break  # Exit the loop


def main():
    parser = argparse.ArgumentParser(description="Web server and stdin processor.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the web server.")
    args = parser.parse_args()

    # Start the web server in a separate thread
    server_thread = Thread(target=run_server, args=(args.port,))
    server_thread.daemon = True
    server_thread.start()

    # Process stdin in the main thread
    process_stdin()


if __name__ == "__main__":
    main()
