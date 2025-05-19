#!/usr/bin/env python3


#!/usr/bin/env python3

from stdio_processor import encode_message, get_messsage, process_stdout, send_message
from web_server import run_server

import argparse
import queue
import signal
import sys
from threading import Thread
import time


# Global flag to indicate whether to exit gracefully
exit_flag = False


def signal_handler(sig, frame):
    """Handles SIGTERM signal."""
    global exit_flag
    exit_flag = True
    print("SIGTERM received. Exiting gracefully...")

class ExitHandler:
    def __init__(self, server_thread, stdout_thread):
        self._server_thread = server_thread
        self._stdout_thread = stdout_thread

    def signal_handler(self, sig, frame):
        """Handles SIGTERM signal."""
        self._server_thread.join(timeout=1)
        self._stdout_thread.join(timeout=1)
        print("Exited gracefully.")
        sys.exit(0)


def main():
    """Main function to start the web server and stdin processor."""

    parser = argparse.ArgumentParser(description="Web server and stdin processor.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the web server.")
    args = parser.parse_args()

    # Shared queue for communication between server and stdin
    message_queue = queue.Queue()

    # Start the web server in a separate thread
    server_thread = Thread(target=run_server, args=(args.port, message_queue))
    server_thread.daemon = True  # Allow the main thread to exit even if this thread is running
    server_thread.start()

    # Process stdin in another thread
    stdout_thread = Thread(target=process_stdout, args=(message_queue,))
    stdout_thread.daemon = True  # Allow the main thread to exit even if this thread is running
    stdout_thread.start()

    # Instantiate the ExitHandler
    exit_handler = ExitHandler(server_thread, stdout_thread)

    # Register the SIGTERM signal handler
    signal.signal(signal.SIGTERM, exit_handler.signal_handler)

    # receivedMessage = get_messsage()
    # send_message(encode_message(receivedMessage))

    try:
        server_thread.join()
        stdout_thread.join()
    except Exception:
        exit_handler.signal_handler(None, None)


if __name__ == "__main__":
    # Ensure stderr is not buffered
    # sys.stderr.reconfigure(line_buffering=True)
    main()

