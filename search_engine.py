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

    def _parse_query(self, raw_query):
        """
        Parses the raw query string into a criteria dictionary.
        Supports:
        - term (standard text match)
        - ext:py,txt (extensions)
        - size:>1mb, size:<1kb
        """
        criteria = {
            'terms': [],
            'extensions': [],
            'min_size': None,
            'max_size': None
        }
        
        parts = raw_query.split()
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                key = key.lower()
                
                if key == 'ext':
                    criteria['extensions'] = [f".{x.lower()}" for x in value.split(',')]
                elif key == 'size':
                    self._parse_size_criteria(value, criteria)
            else:
                criteria['terms'].append(part.lower())
                
        return criteria

    def _parse_size_criteria(self, value, criteria):
        """Helper to parse size constraints like >1mb or <500kb"""
        try:
            multiplier = 1
            if value.lower().endswith('kb'):
                multiplier = 1024
                val_str = value[:-2]
            elif value.lower().endswith('mb'):
                multiplier = 1024 * 1024
                val_str = value[:-2]
            elif value.lower().endswith('gb'):
                multiplier = 1024 * 1024 * 1024
                val_str = value[:-2]
            else:
                val_str = value

            if val_str.startswith('>'):
                criteria['min_size'] = float(val_str[1:]) * multiplier
            elif val_str.startswith('<'):
                criteria['max_size'] = float(val_str[1:]) * multiplier
        except ValueError:
            pass # Ignore malformed size

    def _matches_criteria(self, name, path, criteria):
        """Checks if a file matches all parsed criteria."""
        
        # 1. Extension Check
        if criteria['extensions']:
            if not any(name.lower().endswith(ext) for ext in criteria['extensions']):
                return False

        # 2. Term Check (All terms must be present in name)
        name_lower = name.lower()
        if not all(term in name_lower for term in criteria['terms']):
            return False

        # 3. Size Check (Requires OS call, done last for performance)
        if criteria['min_size'] is not None or criteria['max_size'] is not None:
            try:
                size = os.path.getsize(path)
                if criteria['min_size'] is not None and size <= criteria['min_size']:
                    return False
                if criteria['max_size'] is not None and size >= criteria['max_size']:
                    return False
            except OSError:
                return False

        return True

    def _search_worker(self, raw_query, root_dirs):
        """
        Worker function that traverses directories with filtering.
        """
        criteria = self._parse_query(raw_query)
        
        for root_dir in root_dirs:
            if self.stop_event.is_set():
                break
            
            try:
                # Use scandir for better performance
                pass
                for root, dirs, files in os.walk(root_dir):
                    if self.stop_event.is_set():
                        return

                    # Check files
                    for file in files:
                        path = os.path.join(root, file)
                        if self._matches_criteria(file, path, criteria):
                            self.results_queue.put(('file', file, path))
                    
                    # Check directories (only if no extension/size filters are set, strict name match)
                    # If users type "ext:py", they likely don't want folder names.
                    if not criteria['extensions'] and not criteria['min_size'] and not criteria['max_size']:
                        for dir_name in dirs:
                            if all(term in dir_name.lower() for term in criteria['terms']):
                                self.results_queue.put(('folder', dir_name, os.path.join(root, dir_name)))
                            
            except (PermissionError, OSError):
                continue
        
        self.results_queue.put(('done', None, None))
