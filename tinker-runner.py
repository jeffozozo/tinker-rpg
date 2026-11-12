#!/usr/bin/env python3
"""Tkinter game runner for Tinker RPG projects."""

import argparse
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from runner_engine import RunnerEngine, RunnerError
from project_paths import asset_root, project_root


TILE_SIZE = 32


class TinkerRunner:
    def __init__(self, root, engine):
        self.root = root
        self.engine = engine
        self.engine.dialog_handler = self.show_dialog
        self.project_root = engine.project_root
        self.image_cache = {}
        self.warned_assets = set()
        self.inventory_window = None
        self.save_path = None
        self.save_name = self.engine.game.get("name", "Saved Game")
        self.dirty = False

        self.root.title(self.engine.game.get("name", "Tinker Runner"))
        self.root.geometry("1000x740")
        self._set_app_icon()
        self._build_ui()
        self._size_window_to_start_area()
        self.root.bind_all("<KeyPress>", self.on_key_press)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_game)
        self.root.after(100, self.canvas.focus_set)
        self.root.after(50, self.start_game)

    def _size_window_to_start_area(self):
        self.root.update_idletasks()
        area = self.engine.current_area
        canvas_width = max(1, self.canvas.winfo_reqwidth())
        canvas_height = max(1, self.canvas.winfo_reqheight())
        chrome_width = self.root.winfo_reqwidth() - canvas_width
        chrome_height = self.root.winfo_reqheight() - canvas_height
        requested_width = max(
            self.root.winfo_reqwidth(), area.width * TILE_SIZE + chrome_width
        )
        requested_height = max(
            self.root.winfo_reqheight(), area.height * TILE_SIZE + chrome_height
        )
        screen_width = max(320, self.root.winfo_screenwidth() - 80)
        screen_height = max(240, self.root.winfo_screenheight() - 120)
        width = min(requested_width, screen_width)
        height = min(requested_height, screen_height)
        self.root.geometry(f"{width}x{height}")

    def _set_app_icon(self):
        icon_path = asset_root() / "objects" / "gargoyle_object.png"
        try:
            with Image.open(icon_path) as source:
                icon = source.convert("RGBA").resize(
                    (64, 64), Image.Resampling.NEAREST
                )
            self.app_icon = ImageTk.PhotoImage(icon, master=self.root)
            self.root.iconphoto(True, self.app_icon)
        except (OSError, ValueError):
            self.app_icon = None
            self.engine._validation_issue(f"Missing or invalid app icon: {icon_path}")

    def _build_ui(self):
        menu_bar = tk.Menu(self.root)
        game_menu = tk.Menu(menu_bar, tearoff=False)
        game_menu.add_command(label="Save", command=self.save_game)
        game_menu.add_command(label="Load", command=self.load_game)
        game_menu.add_separator()
        game_menu.add_command(label="Restart", command=self.restart_game)
        game_menu.add_command(label="Quit", command=self.quit_game)
        menu_bar.add_cascade(label="Game", menu=game_menu)

        player_menu = tk.Menu(menu_bar, tearoff=False)
        player_menu.add_command(
            label="Inventory", command=self.toggle_inventory, accelerator="I"
        )
        menu_bar.add_cascade(label="Player", menu=player_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(
            label="Instructions", command=self.show_instructions, accelerator="H"
        )
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self.root.configure(menu=menu_bar)
        self.menu_bar = menu_bar

        status = ttk.Frame(self.root, padding=(8, 6))
        status.pack(fill=tk.X)
        self.health_label = ttk.Label(status)
        self.health_label.pack(side=tk.LEFT, padx=(0, 16))
        self.energy_label = ttk.Label(status)
        if self.engine.stats["max_energy"] > 0:
            self.energy_label.pack(side=tk.LEFT, padx=(0, 16))
        self.gold_label = ttk.Label(status)
        self.gold_label.pack(side=tk.LEFT, padx=(0, 16))
        self.area_label = ttk.Label(status, anchor=tk.E)
        self.area_label.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        map_frame = ttk.Frame(self.root)
        map_frame.pack(fill=tk.BOTH, expand=True, padx=8)
        self.canvas = tk.Canvas(
            map_frame, background="#202020", highlightthickness=0, takefocus=True
        )
        vertical = ttk.Scrollbar(
            map_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        horizontal = ttk.Scrollbar(
            self.root, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        self.canvas.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set
        )
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vertical.pack(side=tk.RIGHT, fill=tk.Y)
        horizontal.pack(fill=tk.X, padx=8)

        footer = ttk.Frame(self.root, padding=8)
        footer.pack(fill=tk.X)
        self.message_log = tk.Text(footer, height=6, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(
            footer, orient=tk.VERTICAL, command=self.message_log.yview
        )
        self.message_log.configure(yscrollcommand=scrollbar.set)
        self.message_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        controls = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        controls.pack(fill=tk.X)
        ttk.Label(
            controls,
            text="Move: WASD / arrows    Inventory: I    Interact: Space    Help: H / ?    Quit: Q",
        ).pack(side=tk.LEFT)

        self.redraw()
        self.refresh_status()

    def start_game(self):
        intro = self.engine.game.get("intro_message", "")
        if intro:
            self.show_dialog(intro)
        if any(
            "enemy_id" in obj.properties or "enemy_data" in obj.properties
            for area in self.engine.areas.values()
            for obj in area.objects
        ):
            self._append_log(
                "Enemies are visible and block movement, but enemy movement and "
                "combat are not implemented yet."
            )
        self.engine.process_entry_triggers()
        self._after_action()

    def _asset_path(self, category, name):
        extension = ".png"
        return asset_root() / category / f"{name}{extension}"

    def _get_image(self, category, name):
        key = (category, name)
        if key in self.image_cache:
            return self.image_cache[key]
        path = self._asset_path(category, name)
        try:
            with Image.open(path) as source:
                image = source.convert("RGBA").resize(
                    (TILE_SIZE, TILE_SIZE), Image.Resampling.NEAREST
                )
            photo = ImageTk.PhotoImage(image, master=self.root)
        except (OSError, ValueError):
            photo = None
            if key not in self.warned_assets:
                self.warned_assets.add(key)
                self.engine._report(f"Missing or invalid image: {path}")
        self.image_cache[key] = photo
        return photo

    def redraw(self):
        area = self.engine.current_area
        origin_x, origin_y = self._map_origin()
        self.canvas.delete("all")
        for y, row in enumerate(area.tiles):
            for x, tile in enumerate(row):
                x1 = origin_x + x * TILE_SIZE
                y1 = origin_y + y * TILE_SIZE
                image = None if tile.type == "empty" else self._get_image(
                    "tiles", tile.type
                )
                if image is not None:
                    self.canvas.create_image(x1, y1, image=image, anchor=tk.NW)
                else:
                    fill = "#303030" if tile.type == "empty" else "#777777"
                    self.canvas.create_rectangle(
                        x1, y1, x1 + TILE_SIZE, y1 + TILE_SIZE,
                        fill=fill, outline="#505050",
                    )

        for obj in area.objects:
            x1 = origin_x + obj.x * TILE_SIZE
            y1 = origin_y + obj.y * TILE_SIZE
            is_enemy = "enemy_id" in obj.properties or "enemy_data" in obj.properties
            enemy_data = obj.properties.get("enemy_data", {})
            sprite = (
                enemy_data.get("sprite", obj.type)
                if is_enemy and isinstance(enemy_data, dict)
                else obj.type
            )
            category = "npcs" if is_enemy or sprite in self.engine.npc_names else "objects"
            image = self._get_image(category, sprite)
            if image is not None:
                self.canvas.create_image(x1, y1, image=image, anchor=tk.NW)
            else:
                color = "#9c3030" if is_enemy else "#d7a940"
                self.canvas.create_rectangle(
                    x1 + 4, y1 + 4, x1 + 28, y1 + 28,
                    fill=color, outline="black",
                )
                self.canvas.create_text(
                    x1 + 16, y1 + 16,
                    text="E" if is_enemy else obj.type[:2].upper(),
                    fill="white",
                )

        player = self.engine.player_settings
        sprite = player.get("sprite", "fighter_npc")
        image = self._get_image("npcs", sprite)
        x1 = origin_x + self.engine.player_x * TILE_SIZE
        y1 = origin_y + self.engine.player_y * TILE_SIZE
        if image is not None:
            self.canvas.create_image(x1, y1, image=image, anchor=tk.NW)
        else:
            self.canvas.create_oval(
                x1 + 4, y1 + 4, x1 + 28, y1 + 28,
                fill="#20b9b0", outline="white", width=2,
            )
        viewport_width = max(1, self.canvas.winfo_width())
        viewport_height = max(1, self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(
            0,
            0,
            max(area.width * TILE_SIZE, viewport_width),
            max(area.height * TILE_SIZE, viewport_height),
        ))
        self.root.after_idle(self.center_player)
        self.refresh_status()

    def _map_origin(self):
        area = self.engine.current_area
        viewport_width = max(1, self.canvas.winfo_width())
        viewport_height = max(1, self.canvas.winfo_height())
        return (
            max(0, (viewport_width - area.width * TILE_SIZE) // 2),
            max(0, (viewport_height - area.height * TILE_SIZE) // 2),
        )

    def _on_canvas_configure(self, _event):
        self.redraw()

    def center_player(self):
        area = self.engine.current_area
        content_width = area.width * TILE_SIZE
        content_height = area.height * TILE_SIZE
        viewport_width = self.canvas.winfo_width()
        viewport_height = self.canvas.winfo_height()
        max_x = max(0, content_width - viewport_width)
        max_y = max(0, content_height - viewport_height)
        left = min(
            max(0, (self.engine.player_x + 0.5) * TILE_SIZE - viewport_width / 2),
            max_x,
        )
        top = min(
            max(0, (self.engine.player_y + 0.5) * TILE_SIZE - viewport_height / 2),
            max_y,
        )
        self.canvas.xview_moveto(left / content_width if max_x else 0)
        self.canvas.yview_moveto(top / content_height if max_y else 0)

    def refresh_status(self):
        self.health_label.config(
            text=f"Health: {self.engine.health}/{self.engine.stats['max_health']}"
        )
        if self.engine.stats["max_energy"] > 0:
            self.energy_label.config(
                text=f"Energy: {self.engine.energy}/{self.engine.stats['max_energy']}"
            )
        self.gold_label.config(text=f"${self.engine.stats['gold']}")
        result = (
            f"  |  YOU {self.engine.end_result.upper()}"
            if self.engine.ended and self.engine.end_result
            else ""
        )
        self.area_label.config(
            text=f"{self.engine.area_name}  |  Turn {self.engine.turn_count}{result}"
        )

    def _append_log(self, message):
        self.message_log.configure(state=tk.NORMAL)
        self.message_log.insert(tk.END, message.rstrip() + "\n")
        self.message_log.see(tk.END)
        self.message_log.configure(state=tk.DISABLED)

    def _flush_events(self):
        while self.engine.events:
            self._append_log(self.engine.events.pop(0))

    def _after_action(self):
        self.redraw()
        self._flush_events()
        self.refresh_inventory()

    def show_dialog(self, message):
        if self.engine.events and self.engine.events[-1] == message:
            self.engine.events.pop()
        self._append_log(message)

    def _show_dialog(self, message, title):
        self._append_log(f"{title}: {message}")

    @staticmethod
    def _save_name_from_path(path):
        name = Path(path).name
        if name.endswith(".save.json"):
            return name[:-len(".save.json")]
        return Path(name).stem

    def save_game(self):
        saves_directory = self.project_root / "saves"
        try:
            saves_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self._show_dialog(
                f"Could not open the saves directory {saves_directory}: {error}",
                "Save Failed",
            )
            return

        initial_name = (
            self.save_path.name
            if self.save_path is not None
            else f"{self.save_name.strip() or 'Saved Game'}.json"
        )
        filename = filedialog.asksaveasfilename(
            title="Save Game",
            initialdir=saves_directory,
            initialfile=initial_name,
            defaultextension=".json",
            filetypes=[
                ("Saved games", "*.json"),
                ("All files", "*"),
            ],
            parent=self.root,
        )
        if not filename:
            return

        save_name = self._save_name_from_path(filename)
        if not save_name:
            self._show_dialog("Choose a name for this saved game.", "Save Game")
            return
        try:
            saved_path = self.engine.save_to_file(filename, save_name)
        except RunnerError as error:
            self._show_dialog(str(error), "Save Failed")
            return
        self.save_path = saved_path
        self.save_name = save_name
        self.engine.save_name = save_name
        self.dirty = False
        self.root.title(f"{self.engine.game.get('name', 'Tinker Runner')} - {save_name}")
        self._append_log(f"Saved game as {save_name} ({saved_path}).")

    def load_game(self):
        saves_directory = self.project_root / "saves"
        try:
            saves_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self._show_dialog(
                f"Could not open the saves directory {saves_directory}: {error}",
                "Load Failed",
            )
            return

        filename = filedialog.askopenfilename(
            title="Load Saved Game",
            initialdir=saves_directory,
            filetypes=[
                ("Saved games", "*.json"),
                ("All files", "*"),
            ],
            parent=self.root,
        )
        if not filename:
            return
        if self.dirty and not messagebox.askyesno(
            "Load Saved Game",
            "Loading a saved game will discard unsaved progress. Continue?",
            parent=self.root,
        ):
            return
        try:
            engine = RunnerEngine.load_save(
                filename,
                project_root=self.project_root,
                dialog_handler=self.show_dialog,
            )
        except (RunnerError, json.JSONDecodeError) as error:
            self._show_dialog(str(error), "Load Failed")
            return

        self.engine = engine
        self.save_path = Path(filename).resolve()
        self.save_name = engine.save_name
        self.dirty = False
        self.root.title(f"{engine.game.get('name', 'Tinker Runner')} - {self.save_name}")
        self._append_log(f"Loaded saved game: {self.save_name}.")
        for warning in engine.validation_issues:
            self._append_log(f"Warning: {warning}")
        self._after_action()

    def show_instructions(self):
        instructions = self.engine.game.get("instructions_message", "")
        self.show_dialog(instructions or "No instructions were provided for this game.")

    def restart_game(self):
        if self.dirty and not messagebox.askyesno(
            "Restart Game",
            "Restart from the beginning and discard unsaved progress?",
            parent=self.root,
        ):
            return
        try:
            engine = RunnerEngine(
                self.engine.game_path,
                project_root=self.project_root,
                dialog_handler=self.show_dialog,
            )
        except RunnerError as error:
            self._show_dialog(str(error), "Restart Failed")
            return

        if self.inventory_window is not None and self.inventory_window.winfo_exists():
            self.inventory_window.destroy()
        self.inventory_window = None
        self.engine = engine
        self.save_path = None
        self.save_name = engine.game.get("name", "Saved Game")
        self.dirty = False
        self.root.title(engine.game.get("name", "Tinker Runner"))
        self._clear_log()
        self.start_game()

    def toggle_inventory(self):
        if self.inventory_window is not None and self.inventory_window.winfo_exists():
            self.inventory_window.destroy()
            self.inventory_window = None
            return
        window = tk.Toplevel(self.root)
        window.title("Inventory")
        window.transient(self.root)
        self.inventory_window = window
        ttk.Label(
            window,
            text=f"Inventory ({len(self.engine.inventory)} slots)",
            font=("", 12, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(10, 4))
        self.inventory_rows = []
        for index in range(len(self.engine.inventory)):
            row = ttk.Label(window)
            row.pack(anchor=tk.W, padx=12, pady=2)
            self.inventory_rows.append(row)
        ttk.Button(
            window, text="Close", command=self.toggle_inventory
        ).pack(anchor=tk.E, padx=12, pady=10)
        self.refresh_inventory()

    def refresh_inventory(self):
        if self.inventory_window is None or not self.inventory_window.winfo_exists():
            return
        for index, row in enumerate(self.inventory_rows):
            item = self.engine.inventory[index]
            row.config(text=f"Slot {index + 1}: {item or '(empty)'}")

    def on_key_press(self, event):
        if self.engine.ended and event.keysym.lower() not in ("q", "i", "h", "question"):
            return "break"
        key = event.keysym.lower()
        movement = {
            "w": "up", "up": "up",
            "s": "down", "down": "down",
            "a": "left", "left": "left",
            "d": "right", "right": "right",
        }
        if key in movement:
            previous_turn = self.engine.turn_count
            self.engine.move(movement[key])
            self.dirty = self.dirty or self.engine.turn_count != previous_turn
            self._after_action()
        elif key == "i":
            self.toggle_inventory()
        elif key == "space":
            previous_turn = self.engine.turn_count
            self.engine.interact()
            self.dirty = self.dirty or self.engine.turn_count != previous_turn
            self._after_action()
        elif key in ("h", "question"):
            self.show_instructions()
        elif key == "q":
            self.quit_game()
        return "break"

    def quit_game(self):
        if self.dirty and not messagebox.askyesno(
            "Quit Game",
            "This run has unsaved progress. Quit the game?",
            parent=self.root,
        ):
            return
        self.root.destroy()

    def _clear_log(self):
        self.message_log.configure(state=tk.NORMAL)
        self.message_log.delete("1.0", tk.END)
        self.message_log.configure(state=tk.DISABLED)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Play a game created with Tinker RPG Editor."
    )
    parser.add_argument(
        "game",
        nargs="?",
        help="game JSON path, name, or filename stem; choose a game if omitted",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the game and report errors without starting it",
    )
    args = parser.parse_args(argv)
    if args.game is None:
        chooser = tk.Tk()
        chooser.withdraw()
        args.game = filedialog.askopenfilename(
            title="Choose a Game",
            initialdir=project_root() / "games",
            filetypes=[
                ("Game files", "*.json"),
                ("All files", "*"),
            ],
            parent=chooser,
        )
        chooser.destroy()
        if not args.game:
            return 0

    try:
        engine = RunnerEngine(args.game)
    except RunnerError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if args.check:
        print(f"Checking {engine.game_path}...")
        if engine.validation_issues:
            for issue in engine.validation_issues:
                print(f"ERROR: {issue}")
            print(f"Found {len(engine.validation_issues)} error(s).")
            return 1
        print("No errors found.")
        return 0

    root = tk.Tk()
    TinkerRunner(root, engine)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
