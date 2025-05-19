import sys
import json
import struct


# Read a message from stdin and decode it.
def get_messsage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        sys.exit(0)
    messageLength = struct.unpack('@I', rawLength)[0]
    message = sys.stdin.buffer.read(messageLength).decode('utf-8')
    return json.loads(message)

# Encode a message for transmission, given its content.
def encode_message(messageContent):
    encodedContent = json.dumps(messageContent, separators=(',', ':')).encode('utf-8')
    encodedLength = struct.pack('@I', len(encodedContent))
    return {'length': encodedLength, 'content': encodedContent}

# Send an encoded message to stdout
def send_message(encodedMessage):
    sys.stdout.buffer.write(encodedMessage['length'])
    sys.stdout.buffer.write(encodedMessage['content'])
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
