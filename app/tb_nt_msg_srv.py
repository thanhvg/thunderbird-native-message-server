#!/usr/bin/env python3

from pubsub import PubSub
from stdio_processor import ThunderBirdRequestSender, ThunderBirdRespondBroadcaster
from web_server import start_server

import argparse
import signal
import sys
from threading import Thread

class ExitHandler:
    def __init__(self, *args):
        self.threads = [arg for arg in args if isinstance(arg, Thread)]

    def signal_handler(self, sig, frame):
        """Handles SIGTERM signal."""
        for thread in self.threads:
            thread.join(timeout=1)

        sys.exit(0)

def main():

    parser = argparse.ArgumentParser(description="Web server and stdin processor.")
    parser.add_argument("--port", type=int, default=1337, help="Port for the web server.")
    args = parser.parse_args()

    pub_sub = PubSub()
    tb_req_sender = ThunderBirdRequestSender(pub_sub=pub_sub)
    tb_res_broadcaster = ThunderBirdRespondBroadcaster(pub_sub=pub_sub)

    server_thread = Thread(target=start_server, args=(args.port, pub_sub))

    exit_handler = ExitHandler(tb_res_broadcaster.process_stdin_thread, server_thread)
    signal.signal(signal.SIGTERM, exit_handler.signal_handler)

    server_thread.start()

if __name__ == "__main__":
    # Ensure stderr is not buffered
    # sys.stderr.reconfigure(line_buffering=True)
    main()
