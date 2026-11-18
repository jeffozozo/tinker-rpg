"""Shared WAV library and gameplay sound settings for the editor."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4
import wave

from ambient_music import AmbientMusic
from project_paths import project_root
from sound_effects import SOUND_NAMES
from wav_assets import (
    import_wav, read_sound_defaults, replace_wav, save_sound_defaults,
    sound_library, split_sound_reference, wav_path,
)


CUE_LABELS = {
    "step": "Walking",
    "attack": "Attacking",
    "hit": "Hitting",
    "miss": "Missing",
    "hurt": "Taking damage",
    "step_hurt": "Walking and taking damage",
}


class SoundEditor:
    def setup_area_ambience(self, parent):
        frame = ttk.LabelFrame(parent, text="Area Ambience")
        frame.pack(fill=tk.X, padx=5, pady=5)
        self.area_ambience = tk.StringVar(master=frame)
        self.area_ambience_selector = ttk.Combobox(
            frame, state="readonly", textvariable=self.area_ambience,
            postcommand=self.refresh_area_ambience_choices,
        )
        self.area_ambience_selector.pack(fill=tk.X, padx=5, pady=5)
        self.area_ambience_selector.bind("<<ComboboxSelected>>", self.set_area_ambience)
        self.sync_area_ambience()
        self.refresh_area_ambience_choices()

    def sync_area_ambience(self):
        self.area_ambience.set(self._current_ambience_choice())

    def refresh_area_ambience_choices(self):
        choices = ["None", *sound_library(project_root())]
        selected = self.area_ambience.get()
        if selected not in choices:
            choices.append(selected)
        self.area_ambience_selector.configure(values=choices)

    def set_area_ambience(self, _event):
        selected = self.area_ambience.get()
        if selected == "None":
            self.current_area.ambient_music = ""
        elif selected != self._current_ambience_choice():
            self.current_area.ambient_music = selected if selected.startswith("music/") else f"sounds/{selected}"

    def _current_ambience_choice(self):
        reference = self.current_area.ambient_music
        if not reference:
            return "None"
        try:
            directory, name = split_sound_reference(reference, "music")
        except ValueError:
            return reference
        return name if directory == "sounds" else f"music/{name}"

    def open_sound_editor(self):
        root = project_root()
        try:
            settings = read_sound_defaults(root)
        except (OSError, ValueError) as error:
            messagebox.showerror("Sound Defaults", str(error), parent=self.root)
            return

        window = tk.Toplevel(self.root)
        window.title("Sounds & Music")
        window.transient(self.root)
        window.grab_set()
        window.minsize(520, 470)
        content = ttk.Frame(window, padding=12)
        content.pack(fill=tk.BOTH, expand=True)

        library = ttk.LabelFrame(content, text="WAV Library", padding=8)
        library.pack(fill=tk.BOTH, expand=True)
        list_frame = ttk.Frame(library)
        list_frame.pack(fill=tk.BOTH, expand=True)
        tracks = tk.Listbox(list_frame, height=8, exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, command=tracks.yview)
        tracks.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tracks.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview = AmbientMusic(
            window, lambda error: messagebox.showerror("Preview Sound", error, parent=window),
            alias="tinker_preview_" + uuid4().hex,
        )
        window.bind("<Destroy>", lambda event: preview.close() if event.widget is window else None)

        defaults = ttk.LabelFrame(content, text="Default Gameplay Sounds", padding=8)
        defaults.pack(fill=tk.X, pady=(10, 8))
        defaults.columnconfigure(1, weight=1)
        selectors = {}
        default_labels = {cue: f"Built-in ({cue}.wav)" for cue in SOUND_NAMES}
        default_labels.update(attack="No separate attack sound", step_hurt="Automatic")

        for row, (cue, label) in enumerate(CUE_LABELS.items()):
            ttk.Label(defaults, text=label).grid(row=row, column=0, sticky=tk.W, padx=(0, 8), pady=2)
            selection = tk.StringVar(master=window, value=settings.get(cue, default_labels[cue]))
            selector = ttk.Combobox(defaults, state="readonly", textvariable=selection)
            selector.grid(row=row, column=1, sticky=tk.EW, pady=2)
            selectors[cue] = selection, selector

        def selected_track():
            indices = tracks.curselection()
            return tracks.get(indices[0]) if indices else ""

        def refresh(selected=""):
            choices = sound_library(root)
            tracks.delete(0, tk.END)
            if choices:
                tracks.insert(tk.END, *choices)
            if selected in choices:
                index = choices.index(selected)
                tracks.selection_set(index)
                tracks.see(index)
            for cue, (selection, selector) in selectors.items():
                values = [default_labels[cue], *choices]
                if selection.get() not in values:
                    values.append(selection.get())
                selector.configure(values=values)
            self.refresh_area_ambience_choices()
            update_controls()

        def update_controls(_event=None):
            reference = selected_track()
            play_button.state(["!disabled"] if reference else ["disabled"])
            replaceable = bool(reference)
            if reference:
                directory, name = split_sound_reference(reference)
                if directory == "sounds" and name in {f"{cue}.wav" for cue in SOUND_NAMES}:
                    replaceable = False
            replace_button.state(["!disabled"] if replaceable else ["disabled"])

        def select_file(title):
            return filedialog.askopenfilename(
                parent=window, title=title, filetypes=[("WAV audio", "*.wav")],
            )

        def import_sound():
            filename = select_file("Import WAV")
            if filename:
                try:
                    refresh(import_wav(filename, root / "sounds"))
                except (OSError, ValueError, wave.Error, EOFError) as error:
                    messagebox.showerror("Import WAV", str(error), parent=window)

        def replace_sound():
            reference = selected_track()
            if not reference:
                return
            filename = select_file(f"Replace {reference}")
            if filename and messagebox.askyesno(
                "Replace WAV", f"Replace {reference} everywhere it is used?", parent=window,
            ):
                try:
                    preview.close()
                    replace_wav(root, reference, filename)
                except (OSError, ValueError, wave.Error, EOFError) as error:
                    messagebox.showerror("Replace WAV", str(error), parent=window)

        def play():
            reference = selected_track()
            if reference:
                preview.close()
                preview.update(root, reference, loop=False, directory="sounds")

        def save_defaults():
            updated = dict(settings)
            try:
                for cue, (selection, _) in selectors.items():
                    reference = selection.get()
                    if reference == default_labels[cue]:
                        updated.pop(cue, None)
                    else:
                        wav_path(root, reference)
                        updated[cue] = reference
                save_sound_defaults(root, updated)
            except (OSError, ValueError) as error:
                messagebox.showerror("Sound Defaults", str(error), parent=window)
                return
            window.destroy()

        actions = ttk.Frame(library)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Import WAV…", command=import_sound).pack(side=tk.LEFT)
        replace_button = ttk.Button(actions, text="Replace WAV…", command=replace_sound)
        replace_button.pack(side=tk.LEFT, padx=4)
        play_button = ttk.Button(actions, text="Preview", command=play)
        play_button.pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Stop", command=preview.close).pack(side=tk.LEFT)
        ttk.Button(content, text="Save Defaults", command=save_defaults).pack(side=tk.RIGHT)
        ttk.Button(content, text="Close", command=window.destroy).pack(side=tk.RIGHT, padx=6)
        tracks.bind("<<ListboxSelect>>", update_controls)
        tracks.bind("<Double-1>", lambda _event: play())
        refresh()
