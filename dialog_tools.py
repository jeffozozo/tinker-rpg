"""
Dialog and tool methods for the Tinker RPG Editor
"""

import tkinter as tk
from tkinter import ttk, messagebox

class DialogTools:
    """Mixin class containing dialog and tool methods"""
    
    def show_game_properties(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Game Properties")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        
        # Game name
        ttk.Label(dialog, text="Game Name:").pack(pady=5)
        game_name_var = tk.StringVar(value=self.current_game.name)
        ttk.Entry(dialog, textvariable=game_name_var, width=40).pack(pady=5)
        
        # Areas in game
        ttk.Label(dialog, text="Areas in Game:").pack(pady=(10,5))
        areas_frame = ttk.Frame(dialog)
        areas_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        areas_listbox = tk.Listbox(areas_frame)
        areas_scrollbar = ttk.Scrollbar(areas_frame, orient=tk.VERTICAL, command=areas_listbox.yview)
        areas_listbox.configure(yscrollcommand=areas_scrollbar.set)
        
        for area_file in self.current_game.areas:
            areas_listbox.insert(tk.END, area_file)
        
        areas_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        areas_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_properties():
            self.current_game.name = game_name_var.get()
            self.game_name_label.config(text=self.current_game.name)
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_properties).pack(side=tk.RIGHT, padx=(5,0))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def show_resize_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Canvas")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text=f"Current: {self.current_area.width} x {self.current_area.height}").pack(pady=10)
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=10)
        
        ttk.Label(frame, text="Width:").grid(row=0, column=0, padx=5)
        width_var = tk.StringVar(value=str(self.current_area.width))
        ttk.Entry(frame, textvariable=width_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(frame, text="Height:").grid(row=0, column=2, padx=5)
        height_var = tk.StringVar(value=str(self.current_area.height))
        ttk.Entry(frame, textvariable=height_var, width=10).grid(row=0, column=3, padx=5)
        
        def apply():
            try:
                new_w, new_h = int(width_var.get()), int(height_var.get())
                if new_w > 0 and new_h > 0:
                    self.resize_canvas(new_w, new_h)
                    dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        ttk.Button(dialog, text="Apply", command=apply).pack(pady=10)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack()
    
    def resize_canvas(self, new_width, new_height):
        from data_classes import Tile
        old_w, old_h = self.current_area.width, self.current_area.height
        new_tiles = [[Tile() for _ in range(new_width)] for _ in range(new_height)]
        
        copy_w, copy_h = min(old_w, new_width), min(old_h, new_height)
        for y in range(copy_h):
            for x in range(copy_w):
                new_tiles[y][x] = self.current_area.tiles[y][x]
        
        self.current_area.width, self.current_area.height = new_width, new_height
        self.current_area.tiles = new_tiles
        self.current_area.objects = [obj for obj in self.current_area.objects 
                                   if 0 <= obj.x < new_width and 0 <= obj.y < new_height]
        self.current_area.triggers = [trig for trig in self.current_area.triggers 
                                    if 0 <= trig.x < new_width and 0 <= trig.y < new_height]
        
        self.cursor_x = min(self.cursor_x, new_width - 1)
        self.cursor_y = min(self.cursor_y, new_height - 1)
        
        self.draw_area()
        self.update_properties_display()
        messagebox.showinfo("Resize", f"Canvas resized to {new_width}x{new_height}")
    
    def crop_canvas_to_room(self):
        from data_classes import Tile
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        found_content = False
        
        for y in range(self.current_area.height):
            for x in range(self.current_area.width):
                if self.current_area.tiles[y][x].type != "empty":
                    min_x, max_x = min(min_x, x), max(max_x, x)
                    min_y, max_y = min(min_y, y), max(max_y, y)
                    found_content = True
        
        for obj in self.current_area.objects:
            min_x, max_x = min(min_x, obj.x), max(max_x, obj.x)
            min_y, max_y = min(min_y, obj.y), max(max_y, obj.y)
            found_content = True
        
        for trig in self.current_area.triggers:
            min_x, max_x = min(min_x, trig.x), max(max_x, trig.x)
            min_y, max_y = min(min_y, trig.y), max(max_y, trig.y)
            found_content = True
        
        if not found_content:
            messagebox.showinfo("Crop", "No content found to crop to.")
            return
        
        new_width, new_height = int(max_x - min_x + 1), int(max_y - min_y + 1)
        new_tiles = [[Tile() for _ in range(new_width)] for _ in range(new_height)]
        
        for y in range(int(min_y), int(max_y + 1)):
            for x in range(int(min_x), int(max_x + 1)):
                new_tiles[y - int(min_y)][x - int(min_x)] = self.current_area.tiles[y][x]
        
        for obj in self.current_area.objects:
            obj.x -= int(min_x)
            obj.y -= int(min_y)
        
        for trig in self.current_area.triggers:
            trig.x -= int(min_x)
            trig.y -= int(min_y)
        
        self.current_area.width, self.current_area.height = new_width, new_height
        self.current_area.tiles = new_tiles
        self.cursor_x = max(0, self.cursor_x - int(min_x))
        self.cursor_y = max(0, self.cursor_y - int(min_y))
        
        self.draw_area()
        self.update_properties_display()
        messagebox.showinfo("Crop", f"Canvas cropped to {new_width}x{new_height}")