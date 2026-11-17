"""Shared, game-scoped trigger definitions; placements retain their own charges."""
from copy import deepcopy
from data_classes import trigger_charges


def definitions_for(game):
    properties = game['properties'] if isinstance(game, dict) else game.properties
    return properties.setdefault('trigger_definitions', {})


def validate_definitions(definitions, types):
    if not isinstance(definitions, dict):
        raise ValueError('Trigger definitions must be an object.')
    names = set()
    for identity, definition in definitions.items():
        if not isinstance(identity, str) or not identity or not isinstance(definition, dict):
            raise ValueError('Trigger definitions need valid IDs and settings.')
        name = definition.get('name', '')
        if not isinstance(name, str) or not name.strip() or name.strip().casefold() in names:
            raise ValueError('Reusable trigger names must be nonempty and unique in this game.')
        names.add(name.strip().casefold())
        if (not isinstance(definition.get('trigger_type'), str) or definition['trigger_type'] not in types
                or not isinstance(definition.get('parameters'), dict)):
            raise ValueError(f'{name}: invalid trigger type or parameters.')
        if type(definition.get('enabled', True)) is not bool:
            raise ValueError(f'{name}: enabled must be true or false.')
        trigger_charges(definition['parameters'])
    for definition in definitions.values():
        if definition['trigger_type'] == 'trigger_control':
            validate_control(definition['parameters'], definitions)


def validate_control(parameters, definitions):
    if not isinstance(parameters.get('target'), str) or parameters['target'] not in definitions:
        raise ValueError('Choose an existing named trigger to control.')
    if parameters.get('action') not in ('enable', 'disable'):
        raise ValueError('Trigger Control action must be enable or disable.')


def resolve_trigger(trigger, definitions):
    if not trigger.definition_id:
        return
    definition = definitions.get(trigger.definition_id)
    if definition is None:
        raise ValueError(f'Trigger definition {trigger.definition_id!r} is missing.')
    trigger.name = definition['name']
    trigger.trigger_type = definition['trigger_type']
    trigger.parameters = deepcopy(definition['parameters'])
    trigger.enabled = definition.get('enabled', True)
