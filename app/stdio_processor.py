import sys
import json
import struct


# Read a message from stdin and decode it.
def get_messsage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        sys.exit(0)
    message_length = struct.unpack('@I', rawLength)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
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
            message_queue.put(message)

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


    
