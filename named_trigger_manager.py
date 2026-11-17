"""Separate, game-scoped definition editor; map placements stay in the area pane."""
from copy import deepcopy
from uuid import uuid4
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from data_classes import Trigger
from editor_methods import EditorMethods
from trigger_library import definitions_for, resolve_trigger


class NamedTriggerForm(EditorMethods):
    def __init__(self, owner, frame):
        self.owner = owner
        self.trigger_form_frame = frame
        self.selected_mode = 'trigger'
        self.editing_named_definition = True
        self._trigger_editor_vars = {}
        self._trigger_editor_tile_labels = {}

    def __getattr__(self, name):
        return getattr(self.owner, name)

    def remember_editor_form(self, *args):
        pass  # The manager guards its draft separately from the area editor.

    def refresh_trigger_editor(self):
        pass

    def update_properties_display(self):
        pass

    def _begin_trigger_position_pick(self, *args, **kwargs):
        messagebox.showinfo('Named Trigger Coordinates',
            'Enter the target coordinates in this definition. Blank Area means the area of each placement.',
            parent=self.trigger_form_frame.winfo_toplevel())


class NamedTriggerManager:
    def __init__(self, owner, identity=None):
        self.owner = owner
        self.window = tk.Toplevel(owner.root)
        self.window.title(f'Named Triggers — {owner.current_game.name}')
        self.window.geometry('850x760')
        self.window.transient(owner.root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        actions = ttk.Frame(self.window, padding=8)
        actions.pack(side=tk.BOTTOM, fill=tk.X)
        left = ttk.Frame(self.window, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text='Named triggers in this game').pack(anchor=tk.W)
        self.listbox = tk.Listbox(left, width=28, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.select)
        for label, command in [('New', self.new), ('Duplicate', self.duplicate), ('Rename', self.rename), ('Delete', self.delete)]:
            ttk.Button(left, text=label, command=command).pack(fill=tk.X, pady=2)
        right = ttk.Frame(self.window, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(right, text='Editing a definition changes every placement in this game.', wraplength=480).pack(anchor=tk.W)
        viewport = tk.Canvas(right, highlightthickness=0)
        scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=viewport.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        viewport.pack(fill=tk.BOTH, expand=True)
        viewport.configure(yscrollcommand=scroll.set)
        content = ttk.Frame(viewport)
        item = viewport.create_window((0, 0), window=content, anchor=tk.NW)
        content.bind('<Configure>', lambda event: viewport.configure(scrollregion=viewport.bbox('all')))
        viewport.bind('<Configure>', lambda event: viewport.itemconfigure(item, width=event.width))
        form_frame = ttk.Frame(content)
        form_frame.pack(fill=tk.X)
        self.form = NamedTriggerForm(owner, form_frame)
        self.usage = ttk.Label(content, wraplength=470)
        self.usage.pack(anchor=tk.W, pady=8)
        ttk.Button(actions, text='Save', command=self.save).pack(side=tk.LEFT)
        ttk.Button(actions, text='Close', command=self.close).pack(side=tk.RIGHT)
        self.trigger = None
        self.baseline = ()
        self.refresh_list()
        if identity in definitions_for(owner.current_game):
            self.load(identity)
        elif self.identities:
            self.load(self.identities[0])
        else:
            self.new()
        self.window.grab_set()

    def refresh_list(self):
        definitions = definitions_for(self.owner.current_game)
        self.identities = sorted(definitions, key=lambda key: definitions[key]['name'].casefold())
        self.listbox.delete(0, tk.END)
        for key in self.identities:
            self.listbox.insert(tk.END, definitions[key]['name'])
        if self.trigger and self.trigger.definition_id in self.identities:
            index = self.identities.index(self.trigger.definition_id)
            self.listbox.selection_set(index)
            self.listbox.see(index)

    def values(self):
        return self.owner._editor_form_values(self.form._trigger_editor_vars.values())

    def confirm_draft(self):
        if not self.trigger or self.values() == self.baseline:
            return True
        result = messagebox.askyesnocancel('Unsaved Named Trigger', 'Save changes to this named trigger?', parent=self.window)
        return False if result is None else self.save() if result else True

    def show(self, trigger):
        self.trigger = trigger
        for child in self.form.trigger_form_frame.winfo_children():
            child.destroy()
        self.form._trigger_editor_vars = {}
        self.form._trigger_editor_tile_labels = {}
        self.form._build_trigger_editor(trigger)
        self.baseline = self.values()
        self.refresh_list()
        self.usage.configure(text='Used at:\n' + ('\n'.join(self.owner.named_trigger_usage(trigger.definition_id)) or 'No placements yet.'))

    def load(self, identity):
        trigger = Trigger(definition_id=identity)
        resolve_trigger(trigger, definitions_for(self.owner.current_game))
        self.show(trigger)

    def select(self, event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        identity = self.identities[selected[0]]
        if self.trigger and identity == self.trigger.definition_id:
            return
        if self.confirm_draft():
            self.load(identity)
        else:
            self.refresh_list()

    def new(self):
        if not self.confirm_draft():
            return
        name = self.unique_name('named_trigger')
        self.show(Trigger(trigger_type='show_message', name=name, parameters={'message': '', 'charges': 0}, definition_id='trigger_' + uuid4().hex))

    def unique_name(self, base):
        name = base; number = 2
        while not self.owner.reusable_name_available(name):
            name = f'{base}_{number}'; number += 1
        return name

    def duplicate(self):
        if not self.trigger or not self.confirm_draft():
            return
        trigger = deepcopy(self.trigger)
        trigger.definition_id = 'trigger_' + uuid4().hex
        trigger.name = self.unique_name(trigger.name + '_copy')
        self.show(trigger)
        self.baseline = ()  # A duplicate must be saved or explicitly discarded.

    def rename(self):
        if self.trigger:
            name = simpledialog.askstring('Rename Named Trigger', 'Name:', initialvalue=self.form._trigger_editor_vars['name'].get(), parent=self.window)
            if name is not None:
                self.form._trigger_editor_vars['name'].set(name)

    def save(self):
        if not self.trigger or not self.form.save_selected_trigger(refresh=False):
            return False
        self.baseline = self.values()
        self.refresh_list()
        self.owner.refresh_trigger_editor()
        self.owner.update_properties_display()
        return True

    def delete(self):
        if not self.trigger:
            return
        identity = self.trigger.definition_id
        if self.owner.named_trigger_usage(identity, include_controls=True):
            messagebox.showwarning('Named Trigger In Use', 'Remove its placements and Trigger Control references before deleting this definition.', parent=self.window)
            return
        if not messagebox.askyesno('Delete Named Trigger', 'Delete this named trigger definition?', parent=self.window):
            return
        definitions_for(self.owner.current_game).pop(identity, None)
        self.trigger = None
        self.baseline = ()
        self.form._trigger_editor_vars = {}
        self.refresh_list()
        if self.identities:
            self.load(self.identities[0])
        else:
            self.new()
        self.owner.refresh_trigger_editor()

    def close(self):
        if not self.confirm_draft():
            return False
        self.window.grab_release()
        self.window.destroy()
        self.owner._named_trigger_manager = None
        self.owner.refresh_trigger_editor()
        self.owner.canvas.focus_set()
        return True
