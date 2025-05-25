import sys
import json
import struct
import threading

from pubsub import PubSub


# Read a message from stdin and decode it.
def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        sys.exit(0)
    message_length = struct.unpack('@I', raw_length)[0]
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
            message = get_message()
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


class ThunderBirdRequestSender:
    def __init__(self, pub_sub: PubSub) -> None:
        self.pub_sub = pub_sub
        self.pub_sub.subscribe('TB_REQUEST', self.listen)

    def listen(self, message):
        encoded_message = encode_message(message)
        send_message(encoded_message)


class ThunderBirdRespondBroadcaster:
    def __init__(self, pub_sub: PubSub) -> None:
        self.pub_sub = pub_sub
        self.process_stdin_thread = threading.Thread(target=self.process_stdin, daemon=True)
        self.process_stdin_thread.start()

    def process_stdin(self):
        while True:
            try:
                message = get_message()
                self.pub_sub.publish('TB_RESPONSE', message)

            except Exception as e:
                # Handle potential errors during message processing or encoding
                print(f"Error processing stdin: {e}", file=sys.stderr)
                sys.stderr.flush()  # Crucial to flush stderr too
                break  # Exit the loop
