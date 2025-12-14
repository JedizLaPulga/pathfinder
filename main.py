from gui import PathfinderApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    # Set icon if available, otherwise just run
    try:
        # root.iconbitmap('icon.ico') 
        pass
    except:
        pass
        
    app = PathfinderApp(root)
    root.mainloop()
