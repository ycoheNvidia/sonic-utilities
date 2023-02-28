#!/usr/bin/env python

from abc import ABC
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from sonic_package_manager.constraint import (
    ComponentConstraints,
    PackageConstraint
)
from sonic_package_manager.errors import ManifestError
from sonic_package_manager.version import Version


class ManifestSchema:
    """ ManifestSchema class describes and provides marshalling
    and unmarshalling methods.
    """

    class Marshaller:
        """ Base class for marshaling and un-marshaling. """

        def marshal(self, value):
            """ Validates and returns a valid manifest dictionary.

            Args:
                value: input value to validate.
            Returns: valid manifest node.
            """

            raise NotImplementedError

        def unmarshal(self, value):
            """ Un-marshals the manifest to a dictionary.

            Args:
                value: input value to validate.
            Returns: valid manifest node.
            """

            raise NotImplementedError

    @dataclass
    class ParsedMarshaller(Marshaller):
        """ Marshaller used on types which support class method "parse" """

        type: Any

        def marshal(self, value):
            try:
                return self.type.parse(value)
            except ValueError as err:
                raise ManifestError(f'Failed to marshal {value}: {err}')

        def unmarshal(self, value):
            try:
                if hasattr(value, 'deparse'):
                    return value.deparse()
                return str(value)
            except Exception as err:
                raise ManifestError(f'Failed to unmarshal {value}: {err}')

    @dataclass
    class DefaultMarshaller(Marshaller):
        """ Default marshaller that validates if the given
        value is instance of given type. """

        type: type

        def marshal(self, value):
            if not isinstance(value, self.type):
                raise ManifestError(f'{value} is not of type {self.type.__name__}')
            return value

        def unmarshal(self, value):
            return value

    @dataclass
    class ManifestNode(Marshaller, ABC):
        """
        Base class for any manifest object.

        Attrs:
            key: String representing the key for this object.
        """

        key: str

    @dataclass
    class ManifestRoot(ManifestNode):
        items: List

        def marshal(self, value: Optional[dict]):
            result = {}
            value = value or {}

            if not isinstance(value, dict):
                raise ManifestError(f'"{self.key}" field has to be a dictionary')

            for item in self.items:
                next_value = value.get(item.key)
                result[item.key] = item.marshal(next_value)
            return result

        def unmarshal(self, value):
            return_value = {}
            for item in self.items:
                return_value[item.key] = item.unmarshal(value[item.key])
            return return_value

    @dataclass
    class ManifestField(ManifestNode):
        type: Any
        default: Optional[Any] = None

        def marshal(self, value):
            if value is None:
                if self.default is not None:
                    return self.default
                raise ManifestError(f'"{self.key}" is a required field but it is missing')
            try:
                return_value = self.type.marshal(value)
            except Exception as err:
                raise ManifestError(f'Failed to marshal {self.key}: {err}')
            return return_value

        def unmarshal(self, value):
            return self.type.unmarshal(value)

    @dataclass
    class ManifestArray(ManifestNode):
        type: Any

        def marshal(self, value):
            return_value = []
            value = value or []

            if not isinstance(value, list):
                raise ManifestError(f'"{self.key}" has to be of type list')

            try:
                for item in value:
                    return_value.append(self.type.marshal(item))
            except Exception as err:
                raise ManifestError(f'Failed to convert {self.key}={value} to array: {err}')

            return return_value

        def unmarshal(self, value):
            return [self.type.unmarshal(item) for item in value]

    # TODO: add description for each field
    SCHEMA = ManifestRoot('root', [
        ManifestField('version', ParsedMarshaller(Version), Version.parse('1.0.0')),
        ManifestRoot('package', [
            ManifestField('version', ParsedMarshaller(Version)),
            ManifestField('name', DefaultMarshaller(str)),
            ManifestField('description', DefaultMarshaller(str), ''),
            ManifestField('base-os', ParsedMarshaller(ComponentConstraints), ComponentConstraints()),
            ManifestArray('depends', ParsedMarshaller(PackageConstraint)),
            ManifestArray('breaks', ParsedMarshaller(PackageConstraint)),
            ManifestField('init-cfg', DefaultMarshaller(dict), dict()),
            ManifestField('changelog', DefaultMarshaller(dict), dict()),
            ManifestField('debug-dump', DefaultMarshaller(str), ''),
        ]),
        ManifestRoot('service', [
            ManifestField('name', DefaultMarshaller(str)),
            ManifestArray('requires', DefaultMarshaller(str)),
            ManifestArray('requisite', DefaultMarshaller(str)),
            ManifestArray('wanted-by', DefaultMarshaller(str)),
            ManifestArray('after', DefaultMarshaller(str)),
            ManifestArray('before', DefaultMarshaller(str)),
            ManifestArray('dependent', DefaultMarshaller(str)),
            ManifestArray('dependent-of', DefaultMarshaller(str)),
            ManifestField('post-start-action', DefaultMarshaller(str), ''),
            ManifestField('pre-shutdown-action', DefaultMarshaller(str), ''),
            ManifestField('asic-service', DefaultMarshaller(bool), False),
            ManifestField('host-service', DefaultMarshaller(bool), True),
            ManifestField('delayed', DefaultMarshaller(bool), False),
            ManifestField('check_up_status', DefaultMarshaller(bool), False),
            ManifestRoot('warm-shutdown', [
                ManifestArray('after', DefaultMarshaller(str)),
                ManifestArray('before', DefaultMarshaller(str)),
            ]),
            ManifestRoot('fast-shutdown', [
                ManifestArray('after', DefaultMarshaller(str)),
                ManifestArray('before', DefaultMarshaller(str)),
            ]),
            ManifestRoot('syslog', [
                ManifestField('support-rate-limit', DefaultMarshaller(bool), False),
            ]),
        ]),
        ManifestRoot('container', [
            ManifestField('privileged', DefaultMarshaller(bool), False),
            ManifestArray('volumes', DefaultMarshaller(str)),
            ManifestArray('mounts', ManifestRoot('mounts', [
                ManifestField('source', DefaultMarshaller(str)),
                ManifestField('target', DefaultMarshaller(str)),
                ManifestField('type', DefaultMarshaller(str)),
            ])),
            ManifestField('environment', DefaultMarshaller(dict), dict()),
            ManifestArray('tmpfs', DefaultMarshaller(str)),
        ]),
        ManifestArray('processes', ManifestRoot('processes', [
            ManifestField('name', DefaultMarshaller(str)),
            ManifestField('reconciles', DefaultMarshaller(bool), False),
        ])),
        ManifestRoot('cli', [
            ManifestField('mandatory', DefaultMarshaller(bool), False),
            ManifestField('show', DefaultMarshaller(str), ''),
            ManifestField('config', DefaultMarshaller(str), ''),
            ManifestField('clear', DefaultMarshaller(str), ''),
            ManifestField('auto-generate-show', DefaultMarshaller(bool), False),
            ManifestField('auto-generate-config', DefaultMarshaller(bool), False),
        ])
    ])


class Manifest(dict):
    """ Manifest object. """

    SCHEMA = ManifestSchema.SCHEMA

    @classmethod
    def marshal(cls, input_dict: dict):
        return Manifest(cls.SCHEMA.marshal(input_dict))

    def unmarshal(self) -> Dict:
        return self.SCHEMA.unmarshal(self)
