"""Editor controls for named reusable triggers and their placements."""
from copy import deepcopy
from uuid import uuid4
import tkinter as tk
from tkinter import ttk, messagebox
from data_classes import Trigger
from trigger_library import definitions_for, resolve_trigger


class ReusableTriggerEditor:
    def import_clipboard_triggers(self, clipboard, triggers):
        definitions = definitions_for(self.current_game)
        source = clipboard.get('definitions', {})
        needed = {trigger.definition_id for trigger in triggers if trigger.definition_id}
        needed.update(trigger.parameters.get('target') for trigger in triggers
                      if trigger.trigger_type == 'trigger_control' and trigger.parameters.get('target'))
        pending = list(needed)
        while pending:
            identity = pending.pop()
            definition = source.get(identity)
            if definition and definition['trigger_type'] == 'trigger_control':
                target = definition['parameters'].get('target')
                if target and target not in needed:
                    needed.add(target); pending.append(target)
        mapping = {}
        for identity in needed:
            if identity in definitions:
                mapping[identity] = identity
            elif identity in source:
                mapping[identity] = identity
        for identity in needed:
            if identity in definitions or identity not in source:
                continue
            definition = deepcopy(source[identity])
            base = definition['name']; name = base; suffix = 2
            while not self.reusable_name_available(name):
                name = f'{base}_{suffix}'; suffix += 1
            definition['name'] = name
            if definition['trigger_type'] == 'trigger_control':
                definition['parameters']['target'] = mapping.get(definition['parameters'].get('target'), definition['parameters'].get('target'))
            definitions[mapping[identity]] = definition
        for trigger in triggers:
            if trigger.definition_id:
                trigger.definition_id = mapping.get(trigger.definition_id, trigger.definition_id)
                resolve_trigger(trigger, definitions)
            elif trigger.trigger_type == 'trigger_control':
                target = trigger.parameters.get('target')
                trigger.parameters['target'] = mapping.get(target, target)

    def setup_reusable_triggers(self):
        # The palette chooses a name; editing lives exclusively in the manager.
        self.named_trigger_picker_frame = ttk.LabelFrame(self.tile_frame, text="Named Trigger")
        self.reusable_trigger_var = tk.StringVar()
        self.reusable_trigger_selector = ttk.Combobox(self.named_trigger_picker_frame, textvariable=self.reusable_trigger_var, state="readonly")
        self.reusable_trigger_selector.pack(fill=tk.X, padx=3, pady=3)
        ttk.Button(self.named_trigger_picker_frame, text="Manage Named Triggers…", command=self.open_named_trigger_manager).pack(fill=tk.X, padx=3, pady=3)

    def update_named_trigger_picker(self):
        if not hasattr(self, 'named_trigger_picker_frame'):
            return
        if self.selected_mode == 'trigger' and self.selected_tile == 'named_trigger':
            self.named_trigger_picker_frame.pack(before=self.tile_canvas_frame, fill=tk.X, padx=5, pady=5)
            self.refresh_reusable_triggers()
        else:
            self.named_trigger_picker_frame.pack_forget()

    def open_named_trigger_manager(self, identity=None):
        if not self.save_selected_trigger(refresh=False):
            return
        manager = getattr(self, '_named_trigger_manager', None)
        if manager is not None and manager.window.winfo_exists():
            manager.window.lift()
            if identity and manager.confirm_draft():
                manager.load(identity)
            return
        from named_trigger_manager import NamedTriggerManager
        self._named_trigger_manager = NamedTriggerManager(self, identity)

    def finish_named_trigger_edit(self):
        manager = getattr(self, '_named_trigger_manager', None)
        return manager.close() if manager is not None and manager.window.winfo_exists() else True

    def named_trigger_usage(self, identity, include_controls=False):
        import json
        import os
        from dataclasses import asdict
        locations = []
        current = getattr(self, 'current_area_file', None)
        sources = [(os.path.basename(current) if current else 'Current area', asdict(self.current_area))]
        for name in self.current_game.areas:
            path = self._project_path('areas', name)
            if current and os.path.realpath(path) == os.path.realpath(current):
                continue
            try:
                with open(path) as file:
                    sources.append((name, json.load(file)))
            except (OSError, ValueError):
                continue
        for name, area in sources:
            for trigger in area.get('triggers', []):
                if trigger.get('definition_id') == identity:
                    locations.append(f"{name} ({trigger['x']}, {trigger['y']})")
                if include_controls and trigger.get('trigger_type') == 'trigger_control' and trigger.get('parameters', {}).get('target') == identity:
                    locations.append(f"{name}: Trigger Control reference")
        if include_controls:
            for definition in definitions_for(self.current_game).values():
                if definition['trigger_type'] == 'trigger_control' and definition['parameters'].get('target') == identity:
                    locations.append(f"{definition['name']}: Trigger Control reference")
        return locations

    def show_named_trigger_summary(self, trigger):
        frame = self.trigger_form_frame
        self._trigger_editor_trigger = None
        ttk.Label(frame, text=trigger.name, font=('TkDefaultFont', 11, 'bold'), wraplength=245).pack(anchor=tk.W)
        ttk.Label(frame, text='Named Trigger — placement only', wraplength=245).pack(anchor=tk.W, pady=3)
        ttk.Label(frame, text=trigger.get_description(), wraplength=245).pack(anchor=tk.W, pady=3)
        charges = trigger.parameters.get('charges', 1 if trigger.parameters.get('once') else 0)
        ttk.Label(frame, text=f"Initially {'enabled' if trigger.enabled else 'disabled'}; charges per placement: {charges or 'unlimited'}", wraplength=245).pack(anchor=tk.W, pady=3)
        ttk.Button(frame, text='Edit Named Trigger…', command=lambda: self.open_named_trigger_manager(trigger.definition_id)).pack(anchor=tk.W, pady=5)

    def refresh_reusable_triggers(self):
        definitions = definitions_for(self.current_game)
        self._reusable_trigger_labels = {d['name']: identity for identity, d in sorted(definitions.items(), key=lambda item: item[1]['name'].casefold())}
        if hasattr(self, 'reusable_trigger_selector'):
            self.reusable_trigger_selector.configure(values=tuple(self._reusable_trigger_labels))
            if self.reusable_trigger_var.get() not in self._reusable_trigger_labels:
                self.reusable_trigger_var.set(next(iter(self._reusable_trigger_labels), ''))
        for trigger in self.current_area.triggers:
            if trigger.definition_id:
                try:
                    resolve_trigger(trigger, definitions)
                except ValueError:
                    pass  # Missing definitions remain visible so the designer can repair them.

    def reusable_name_available(self, name, identity=''):
        return bool(name.strip()) and all(key == identity or definition['name'].casefold() != name.strip().casefold()
                                         for key, definition in definitions_for(self.current_game).items())

    def make_trigger_reusable(self):
        if not self.save_selected_trigger(refresh=False):
            return False
        triggers = self._triggers_at_cursor()
        if not triggers:
            return False
        trigger = triggers[self.selected_trigger_index]
        if trigger.definition_id:
            return True
        if not self.reusable_name_available(trigger.name):
            messagebox.showerror('Named Trigger', 'Choose a unique, nonempty name for this game.')
            return False
        identity = 'trigger_' + uuid4().hex
        definitions_for(self.current_game)[identity] = dict(name=trigger.name.strip(), trigger_type=trigger.trigger_type,
                                                         parameters=deepcopy(trigger.parameters), enabled=trigger.enabled)
        trigger.definition_id = identity
        self.refresh_reusable_triggers()
        self.reusable_trigger_var.set(trigger.name)
        self.refresh_trigger_editor()
        self.draw_area()
        return True

    def place_reusable_trigger(self):
        if not self.save_selected_trigger(refresh=False):
            return False
        self.refresh_reusable_triggers()
        identity = self._reusable_trigger_labels.get(self.reusable_trigger_var.get())
        if not identity:
            return False
        trigger = Trigger(self.cursor_x, self.cursor_y, definition_id=identity)
        resolve_trigger(trigger, definitions_for(self.current_game))
        self.current_area.triggers.append(trigger)
        self.selected_trigger_index = len(self._triggers_at_cursor()) - 1
        self.refresh_trigger_editor()
        self.draw_area()
        self.update_properties_display()
        return True

    def save_reusable_trigger(self, trigger):
        if not trigger.definition_id:
            return
        definitions_for(self.current_game)[trigger.definition_id] = dict(
            name=trigger.name, trigger_type=trigger.trigger_type,
            parameters=deepcopy(trigger.parameters), enabled=trigger.enabled)
        self.refresh_reusable_triggers()
