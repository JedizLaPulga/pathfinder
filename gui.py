import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import platform
import pyperclip
from search_engine import SearchEngine
import queue

class PathfinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pathfinder")
        self.root.geometry("900x600")
        self.root.configure(bg="#1e1e1e")

        # Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()

        self.search_engine = SearchEngine()
        self.search_query = tk.StringVar()

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def configure_styles(self):
        # Theme Colors
        self.colors = {
            "bg": "#1e1e1e",
            "fg": "#ffffff",
            "accent": "#007acc",
            "button_bg": "#333333",
            "entry_bg": "#252526",
            "active_accent": "#005f9e",
            "tree_fg": "#cccccc",
            "tree_heading_bg": "#333333",
            "status_bg": "#2d2d2d",
            "status_fg": "#aaaaaa",
            "action_btn_bg": "#3e3e42"
        }

        self.style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"])
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 10))
        self.style.configure("TButton", background=self.colors["button_bg"], foreground=self.colors["fg"], font=("Segoe UI", 9), borderwidth=0)
        self.style.map("TButton", background=[("active", self.colors["accent"])])
        
        self.style.configure("TEntry", fieldbackground=self.colors["entry_bg"], foreground=self.colors["fg"], borderwidth=0)
        
        # Treeview Style
        self.style.configure("Treeview", 
                           background=self.colors["entry_bg"], 
                           foreground=self.colors["tree_fg"], 
                           fieldbackground=self.colors["entry_bg"],
                           borderwidth=0,
                           font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", 
                           background=self.colors["tree_heading_bg"], 
                           foreground=self.colors["fg"], 
                           borderwidth=0,
                           font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", self.colors["accent"])])
        
        # Scrollbar
        self.style.configure("Vertical.TScrollbar", background=self.colors["button_bg"], troughcolor=self.colors["bg"], borderwidth=0, arrowcolor=self.colors["fg"])

    def create_widgets(self):
        # Header / Search Bar
        header_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=20, padx=20)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(header_frame, text="PATHFINDER", font=("Segoe UI", 18, "bold"), bg=self.colors["bg"], fg=self.colors["accent"])
        title_label.pack(side=tk.LEFT)

        search_frame = tk.Frame(header_frame, bg=self.colors["bg"], padx=20)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_query, font=("Segoe UI", 12), bg=self.colors["entry_bg"], fg=self.colors["fg"], insertbackground="white", relief=tk.FLAT)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        self.search_entry.bind('<Return>', self.start_search)

        search_btn = tk.Button(search_frame, text="SEARCH", font=("Segoe UI", 10, "bold"), bg=self.colors["accent"], fg="white", activebackground=self.colors["active_accent"], activeforeground="white", relief=tk.FLAT, command=self.start_search)
        search_btn.pack(side=tk.LEFT, padx=5)

        # Content Area
        content_frame = tk.Frame(self.root, bg=self.colors["bg"], padx=20)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Treeview for results
        columns = ("type", "name", "path")
        self.tree = ttk.Treeview(content_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("type", text="Type")
        self.tree.heading("name", text="Name")
        self.tree.heading("path", text="Path")
        
        self.tree.column("type", width=80, anchor=tk.CENTER)
        self.tree.column("name", width=250, anchor=tk.W)
        self.tree.column("path", width=500, anchor=tk.W)

        scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_double_click)

        # Status Bar / Actions
        action_frame = tk.Frame(self.root, bg=self.colors["status_bg"], height=50, padx=20)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(action_frame, text="Ready", bg=self.colors["status_bg"], fg=self.colors["status_fg"], font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, pady=10)

        open_btn = tk.Button(action_frame, text="Open Location", bg=self.colors["action_btn_bg"], fg="white", font=("Segoe UI", 9), relief=tk.FLAT, command=self.open_selected)
        open_btn.pack(side=tk.RIGHT, pady=10, padx=5)

        copy_btn = tk.Button(action_frame, text="Copy Path", bg=self.colors["action_btn_bg"], fg="white", font=("Segoe UI", 9), relief=tk.FLAT, command=self.copy_path)
        copy_btn.pack(side=tk.RIGHT, pady=10, padx=5)

    def start_search(self, event=None):
        query = self.search_query.get().strip()
        if not query:
            return

        # Clear current results
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.status_label.config(text=f"Searching for '{query}'...")
        self.search_engine.search(query)
        self.check_queue()

    def check_queue(self):
        try:
            while True:
                item = self.search_engine.results_queue.get_nowait()
                if item[0] == 'done':
                    if not self.tree.get_children():
                        self.status_label.config(text="File not found")
                    else:
                        self.status_label.config(text="Search completed.")
                    return
                
                type_, name, path = item
                icon = "📁" if type_ == 'folder' else "📄"
                self.tree.insert("", tk.END, values=(icon, name, path))
                
        except queue.Empty:
            pass
        
        # Reschedule check
        if self.search_engine.search_thread and self.search_engine.search_thread.is_alive():
            self.root.after(100, self.check_queue)
        else:
             if self.status_label.cget("text").startswith("Searching"):
                 self.status_label.config(text="Search stopped or completed.")

    def on_double_click(self, event):
        self.open_selected()

    def open_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = self.tree.item(selected[0])
        path = item['values'][2]
        
        try:
            if platform.system() == "Windows":
                os.startfile(path) # Opens file or folder
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open path:\n{e}")

    def copy_path(self):
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        path = item['values'][2]
        pyperclip.copy(path)
        
        original_text = self.status_label.cget("text")
        self.status_label.config(text=f"Copied to clipboard: {path}")
        self.root.after(3000, lambda: self.status_label.config(text=original_text))

    def on_close(self):
        self.search_engine.stop_search()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PathfinderApp(root)
    root.mainloop()
