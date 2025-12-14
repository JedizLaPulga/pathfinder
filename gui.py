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
        # Colors
        bg_color = "#1e1e1e"
        fg_color = "#ffffff"
        accent_color = "#007acc"
        button_bg_color = "#333333"
        entry_bg_color = "#252526"
        
        self.style.configure(".", background=bg_color, foreground=fg_color)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.configure("TButton", background=button_bg_color, foreground=fg_color, font=("Segoe UI", 9), borderwidth=0)
        self.style.map("TButton", background=[("active", accent_color)])
        
        self.style.configure("TEntry", fieldbackground=entry_bg_color, foreground=fg_color, borderwidth=0)
        
        # Treeview Style
        self.style.configure("Treeview", 
                           background="#252526", 
                           foreground="#cccccc", 
                           fieldbackground="#252526",
                           borderwidth=0,
                           font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", 
                           background="#333333", 
                           foreground="#ffffff", 
                           borderwidth=0,
                           font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", accent_color)])
        
        # Scrollbar
        self.style.configure("Vertical.TScrollbar", background="#333333", troughcolor=bg_color, borderwidth=0, arrowcolor="#ffffff")

    def create_widgets(self):
        # Header / Search Bar
        header_frame = tk.Frame(self.root, bg="#1e1e1e", pady=20, padx=20)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(header_frame, text="PATHFINDER", font=("Segoe UI", 18, "bold"), bg="#1e1e1e", fg="#007acc")
        title_label.pack(side=tk.LEFT)

        search_frame = tk.Frame(header_frame, bg="#1e1e1e", padx=20)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_query, font=("Segoe UI", 12), bg="#252526", fg="#ffffff", insertbackground="white", relief=tk.FLAT)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        self.search_entry.bind('<Return>', self.start_search)

        search_btn = tk.Button(search_frame, text="SEARCH", font=("Segoe UI", 10, "bold"), bg="#007acc", fg="white", activebackground="#005f9e", activeforeground="white", relief=tk.FLAT, command=self.start_search)
        search_btn.pack(side=tk.LEFT, padx=5)

        # Content Area
        content_frame = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=(0, 20))
        content_frame.pack(fill=tk.BOTH, expand=True)

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
        action_frame = tk.Frame(self.root, bg="#2d2d2d", height=50, padx=20)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(action_frame, text="Ready", bg="#2d2d2d", fg="#aaaaaa", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, pady=10)

        open_btn = tk.Button(action_frame, text="Open Location", bg="#3e3e42", fg="white", font=("Segoe UI", 9), relief=tk.FLAT, command=self.open_selected)
        open_btn.pack(side=tk.RIGHT, pady=10, padx=5)

        copy_btn = tk.Button(action_frame, text="Copy Path", bg="#3e3e42", fg="white", font=("Segoe UI", 9), relief=tk.FLAT, command=self.copy_path)
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
