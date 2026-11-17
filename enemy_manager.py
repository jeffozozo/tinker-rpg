"""Separate editor for enemy types belonging to the current game."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from enemy_editor import EnemyEditor


class EnemyDefinitionForm(EnemyEditor):
    def __init__(self, owner, frame):
        self.owner = owner
        self.selected_enemy_id = None
        self.draft = None
        self.setup_enemy_definition_fields(frame)

    def __getattr__(self, name):
        return getattr(self.owner, name)

    def get_enemy_definitions(self):
        definitions = dict(self.owner.get_enemy_definitions())
        if self.draft is not None and self.selected_enemy_id:
            definitions[self.selected_enemy_id] = self.draft
        return definitions

    def refresh_enemy_editor(self):
        if self.draft is not None:
            self._enemy_loot_choices()
            self._load_enemy_fields(self.draft)

    def remember_editor_form(self, *args):
        pass  # Drafts are guarded by this window, not the area editor.

    def update_properties_display(self):
        pass


class EnemyManager:
    def __init__(self, owner, enemy_id=None):
        self.owner = owner
        self.window = tk.Toplevel(owner.root)
        self.window.title(f'Enemies — {owner.current_game.name}')
        self.window.geometry('850x680')
        self.window.transient(owner.root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        footer = ttk.Frame(self.window, padding=8)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(footer, text='Save Enemy Type', command=self.save).pack(side=tk.LEFT)
        ttk.Button(footer, text='Close', command=self.close).pack(side=tk.RIGHT)
        left = ttk.Frame(self.window, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text='Enemy types in this game').pack(anchor=tk.W)
        self.listbox = tk.Listbox(left, width=28, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.select)
        for label, command in [('New', self.new), ('Duplicate', self.duplicate), ('Rename', self.rename),
                               ('Delete', self.delete), ('Add Example Enemies', self.examples)]:
            ttk.Button(left, text=label, command=command).pack(fill=tk.X, pady=2)
        right = ttk.Frame(self.window, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(right, text='Type changes apply to every instance in this game. Instance loot overrides are preserved.', wraplength=470).pack(anchor=tk.W, pady=5)
        viewport = tk.Canvas(right, highlightthickness=0)
        scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=viewport.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        viewport.pack(fill=tk.BOTH, expand=True)
        viewport.configure(yscrollcommand=scroll.set)
        content = ttk.Frame(viewport)
        item = viewport.create_window((0, 0), window=content, anchor=tk.NW)
        content.bind('<Configure>', lambda event: viewport.configure(scrollregion=viewport.bbox('all')))
        viewport.bind('<Configure>', lambda event: viewport.itemconfigure(item, width=event.width))
        frame = ttk.Frame(content)
        frame.pack(fill=tk.X)
        self.form = EnemyDefinitionForm(owner, frame)
        self.usage = ttk.Label(content, wraplength=470)
        self.usage.pack(anchor=tk.W, pady=12)
        ttk.Label(content, text='Save Enemy Type applies the type and synchronizes placed copies. Use Save All in the editor to save the game.', wraplength=470).pack(anchor=tk.W)
        self.baseline = ()
        self.refresh_list()
        if enemy_id in owner.get_enemy_definitions():
            self.load(enemy_id)
        elif self.identities:
            self.load(self.identities[0])
        else:
            self.new()
        self.window.grab_set()

    def variables(self):
        return [getattr(self.form, 'enemy_' + name + '_var') for name in
                ('name', 'sprite', 'health', 'speed', 'ranged_attack', 'behavior', 'damage', 'loot')]

    def values(self):
        return tuple(variable.get() for variable in self.variables())

    def refresh_list(self):
        definitions = self.owner.get_enemy_definitions()
        self.identities = sorted(definitions, key=lambda key: definitions[key]['name'].casefold())
        self.listbox.delete(0, tk.END)
        for identity in self.identities:
            self.listbox.insert(tk.END, definitions[identity]['name'])
        if self.form.selected_enemy_id in self.identities:
            index = self.identities.index(self.form.selected_enemy_id)
            self.listbox.selection_set(index)
            self.listbox.see(index)

    def confirm_draft(self):
        if self.form.draft is None or self.values() == self.baseline:
            return True
        result = messagebox.askyesnocancel('Unsaved Enemy Type', 'Save changes to this enemy type?', parent=self.window)
        return False if result is None else self.save() if result else True

    def show(self, definition, dirty=False):
        self.form.draft = deepcopy(definition)
        self.form.selected_enemy_id = definition['id']
        self.form.refresh_enemy_editor()
        self.baseline = () if dirty else self.values()
        self.refresh_list()
        self.usage.configure(text='Used at:\n' + ('\n'.join(self.owner.enemy_definition_usage(definition['id'])) or 'No placements yet.'))

    def load(self, identity):
        self.show(self.owner.get_enemy_definitions()[identity])

    def select(self, event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        identity = self.identities[selected[0]]
        if identity == self.form.selected_enemy_id:
            return
        if self.confirm_draft():
            self.load(identity)
        else:
            self.refresh_list()

    def unique_name(self, base):
        names = {d['name'].casefold() for d in self.owner.get_enemy_definitions().values()}
        name = base; number = 2
        while name.casefold() in names:
            name = f'{base} {number}'; number += 1
        return name

    def new(self):
        if not self.confirm_draft():
            return
        sprites = self.owner._available_enemy_sprites()
        if not sprites:
            messagebox.showwarning('New Enemy', 'Add an NPC image before creating an enemy type.', parent=self.window)
            return
        self.show(dict(id=self.owner._next_enemy_id(), name=self.unique_name('Enemy'), sprite=sprites[0],
                       health=10, movement_speed=1.0, behavior='chase', contact_damage=1,
                       loot_object='', ranged_attack='none'), dirty=True)

    def duplicate(self):
        if self.form.draft is None or not self.confirm_draft():
            return
        definition = deepcopy(self.form.draft)
        definition.pop('starter_key', None)
        definition['id'] = self.owner._next_enemy_id()
        definition['name'] = self.unique_name(definition['name'] + ' copy')
        self.show(definition, dirty=True)

    def rename(self):
        if self.form.draft is not None:
            name = simpledialog.askstring('Rename Enemy Type', 'Name:', initialvalue=self.form.enemy_name_var.get(), parent=self.window)
            if name is not None:
                self.form.enemy_name_var.set(name)

    def save(self):
        if self.form.draft is None or not self.form.save_enemy_definition(refresh=False):
            return False
        identity = self.form.selected_enemy_id
        self.owner.get_enemy_definitions()[identity] = deepcopy(self.form.draft)
        self.owner.sync_enemy_instances()
        self.baseline = self.values()
        self.refresh_list()
        self.owner.refresh_enemy_editor()
        self.owner.draw_area()
        return True

    def delete(self):
        identity = self.form.selected_enemy_id
        if not identity:
            return
        if self.owner.enemy_definition_usage(identity):
            messagebox.showwarning('Enemy Type In Use', 'Remove all placed instances and Enemy Placement trigger references before deleting this type.', parent=self.window)
            return
        if not messagebox.askyesno('Delete Enemy Type', 'Delete this enemy type?', parent=self.window):
            return
        self.owner.get_enemy_definitions().pop(identity, None)
        self.form.draft = None
        self.refresh_list()
        if self.identities:
            self.load(self.identities[0])
        else:
            self.new()
        self.owner.refresh_enemy_editor()

    def examples(self):
        if not self.confirm_draft():
            return
        self.owner.add_example_enemy_definitions()
        self.refresh_list()
        if self.owner.selected_enemy_id:
            self.load(self.owner.selected_enemy_id)

    def close(self):
        if not self.confirm_draft():
            return False
        self.window.grab_release()
        self.window.destroy()
        self.owner._enemy_manager = None
        self.owner.refresh_enemy_editor()
        self.owner.canvas.focus_set()
        return True
