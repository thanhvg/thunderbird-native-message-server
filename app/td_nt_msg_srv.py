import argparse
from threading import Thread
import queue  # For thread-safe communication
import sys

from web_server import run_server
from stdio_processor import process_stdin

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
    stdin_thread = Thread(target=process_stdin, args=(message_queue,))
    # stdin_thread.daemon = True
    stdin_thread.start()


if __name__ == "__main__":
    # Ensure stderr is not buffered
    # sys.stderr.reconfigure(line_buffering=True)
    main()
