import threading
import queue

class PubSub:
    def __init__(self):
        self.topics = {}
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()

    def subscribe(self, topic, callback):
        with self.lock:
            if topic not in self.topics:
                self.topics[topic] = []
            self.topics[topic].append(callback)
        return (topic, callback) # Return subscription tuple for unsub

    def publish(self, topic, message):
        self.queue.put((topic, message))

    def unsubscribe(self, topic, callback):
        with self.lock:
            if topic in self.topics:
                try:
                    self.topics[topic].remove(callback)
                    if not self.topics[topic]:
                        del self.topics[topic]
                except ValueError:
                    pass  # Callback not found

    def _listen(self):
        while True:
            topic, message = self.queue.get()
            with self.lock:
                if topic in self.topics:
                    for callback in self.topics[topic]:
                        callback(message)
            self.queue.task_done()
