import os
import threading
import queue

class SearchEngine:
    def __init__(self):
        self.stop_event = threading.Event()
        self.results_queue = queue.Queue()
        self.search_thread = None

    def search(self, query, root_dirs=None):
        """
        Starts the search in a separate thread.
        """
        self.stop_search()  # Stop any existing search
        self.stop_event.clear()
        
        # Clear previous queue
        with self.results_queue.mutex:
            self.results_queue.queue.clear()

        if root_dirs is None:
            # Default to user home directory for performance and safety
            root_dirs = [os.path.expanduser("~")]

        self.search_thread = threading.Thread(target=self._search_worker, args=(query, root_dirs))
        self.search_thread.daemon = True
        self.search_thread.start()

    def stop_search(self):
        """
        Signals the search thread to stop.
        """
        if self.search_thread and self.search_thread.is_alive():
            self.stop_event.set()
            self.search_thread.join(timeout=1.0)

    def _search_worker(self, query, root_dirs):
        """
        Worker function that traverses directories.
        """
        query = query.lower()
        for root_dir in root_dirs:
            if self.stop_event.is_set():
                break
            
            try:
                for root, dirs, files in os.walk(root_dir):
                    if self.stop_event.is_set():
                        return

                    # Check files
                    for file in files:
                        if query in file.lower():
                            self.results_queue.put(('file', file, os.path.join(root, file)))
                    
                    # Check directories
                    for dir_name in dirs:
                        if query in dir_name.lower():
                            self.results_queue.put(('folder', dir_name, os.path.join(root, dir_name)))
                            
            except (PermissionError, OSError):
                continue
        
        self.results_queue.put(('done', None, None))
