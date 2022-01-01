from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import json
from uuid import uuid4
from copy import deepcopy

import compas

from compas.data.encoders import DataEncoder
from compas.data.encoders import DataDecoder


# ==============================================================================
# If you ever feel tempted to use ABCMeta in your code: don't, just DON'T.
# Assigning __metaclass__ = ABCMeta to a class causes a severe memory leak/performance
# degradation on IronPython 2.7.

# See these issues for more details:
# - https://github.com/compas-dev/compas/issues/562
# - https://github.com/compas-dev/compas/issues/649

# ==============================================================================


class Data(object):
    """Abstract base class for all COMPAS data objects.

    Parameters
    ----------
    name : str, optional
        The name of the object.

    Attributes
    ----------
    dtype : str, read-only
        The type of the object in the form of a fully qualified module name and a class name, separated by a forward slash ("/").
        For example: ``"compas.datastructures/Mesh"``.
    data : dict
        The representation of the object as a dictionary containing only native Python data.
        The structure of the dict is described by the data schema.
    jsonstring : str, read-only
        The object's data dict in JSON string format.
    guid : str, read-only
        The globally unique identifier of the object.
        The guid is generated with ``uuid.uuid4()``.
    name : str
        The name of the object.
        This name is not necessarily unique and can be set by the user.
        The default value is the object's class name: ``self.__class__.__name__``.

    """

    def __init__(self, name=None):
        self._guid = None
        self._name = None
        self._jsondefinitions = None
        self._JSONSCHEMA = None
        self._jsonvalidator = None
        if name:
            self.name = name

    def __getstate__(self):
        """Return the object data for state serialization with older pickle protocols."""
        return {'__dict__': self.__dict__, 'dtype': self.dtype, 'data': self.data}

    def __setstate__(self, state):
        """Assign a deserialized state to the object data to support older pickle protocols."""
        self.__dict__.update(state['__dict__'])
        self.data = state['data']

    @property
    def DATASCHEMA(self):
        """:class:`schema.Schema` - The schema of the data of this object."""
        raise NotImplementedError

    @property
    def JSONSCHEMANAME(self):
        """str - The schema of the data of this object in JSON format."""
        raise NotImplementedError

    @property
    def JSONSCHEMA(self):
        """dict - The schema of the JSON representation of the data of this object."""
        if not self._JSONSCHEMA:
            schema_filename = '{}.json'.format(self.JSONSCHEMANAME.lower())
            schema_path = os.path.join(os.path.dirname(__file__), 'schemas', schema_filename)
            with open(schema_path, 'r') as fp:
                self._JSONSCHEMA = json.load(fp)
        return self._JSONSCHEMA

    @property
    def jsondefinitions(self):
        """dict - Reusable schema definitions."""
        if not self._jsondefinitions:
            schema_path = os.path.join(os.path.dirname(__file__), 'schemas', 'compas.json')
            with open(schema_path, 'r') as fp:
                self._jsondefinitions = json.load(fp)
        return self._jsondefinitions

    @property
    def jsonvalidator(self):
        """:class:`jsonschema.Draft7Validator` - JSON schema validator for draft 7."""
        if not self._jsonvalidator:
            from jsonschema import RefResolver, Draft7Validator
            resolver = RefResolver.from_schema(self.jsondefinitions)
            self._jsonvalidator = Draft7Validator(self.JSONSCHEMA, resolver=resolver)
        return self._jsonvalidator

    @property
    def dtype(self):
        return '{}/{}'.format('.'.join(self.__class__.__module__.split('.')[:2]), self.__class__.__name__)

    @property
    def data(self):
        raise NotImplementedError

    @data.setter
    def data(self, data):
        raise NotImplementedError

    @property
    def jsonstring(self):
        return compas.json_dumps(self.data)

    @property
    def guid(self):
        if not self._guid:
            self._guid = uuid4()
        return self._guid

    @property
    def name(self):
        if not self._name:
            self._name = self.__class__.__name__
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @classmethod
    def from_data(cls, data):
        """Construct an object of this type from the provided data.

        Parameters
        ----------
        data : dict
            The data dictionary.

        Returns
        -------
        :class:`compas.data.Data`
            An instance of this object type if the data contained in the dict has the correct schema.
        """
        obj = cls()
        obj.data = data
        return obj

    def to_data(self):
        """Convert an object to its native data representation.

        Returns
        -------
        dict
            The data representation of the object as described by the schema.
        """
        return self.data

    @classmethod
    def from_json(cls, filepath):
        """Construct an object from serialized data contained in a JSON file.

        Parameters
        ----------
        filepath : path string, file-like object or URL string
            The path, file or URL to the file for serialization.

        Returns
        -------
        :class:`compas.data.Data`
            An instance of this object type if the data contained in the JSON file has the correct schema.
        """
        data = compas.json_load(filepath)
        return cls.from_data(data)

    def to_json(self, filepath, pretty=False):
        """Serialize the data representation of an object to a JSON file.

        Parameters
        ----------
        filepath : path string or file-like object
            The path or file-like object to the file containing the data.
        pretty : bool, optional
            If ``True`` serialize a pretty representation of the data.
            Default is ``False``.

        Returns
        -------
        None
        """
        compas.json_dump(self.data, filepath, pretty)

    @classmethod
    def from_jsonstring(cls, string):
        """Construct an object from serialized data contained in a JSON string.

        Parameters
        ----------
        string : str
            The object JSON string.

        Returns
        -------
        :class:`compas.data.Data`
            An instance of this object type if the data contained in the JSON file has the correct schema.
        """
        data = compas.json_loads(string)
        return cls.from_data(data)

    def to_jsonstring(self, pretty=False):
        """Serialize the data representation of an object to a JSON string.

        Parameters
        ----------
        pretty : bool, optional
            If ``True`` serialize a pretty representation of the data.

        Returns
        -------
        str
            The object's data dict in JSON string format.
        """
        return compas.json_dumps(self.data, pretty)

    def copy(self, cls=None):
        """Make an independent copy of the data object.

        Parameters
        ----------
        cls : Type[:class:`compas.data.Data`], optional
            The type of data object to return.
            Defaults to the type of the current data object.

        Returns
        -------
        :class:`compas.data.Data`
            An independent copy of this object.
        """
        if not cls:
            cls = type(self)
        return cls.from_data(deepcopy(self.data))

    def validate_data(self):
        """Validate the object's data against its data schema (``self.DATASCHEMA``).

        Returns
        -------
        dict
            The validated data.

        Raises
        ------
        :class:`schema.SchemaError`
        """
        import schema
        try:
            data = self.DATASCHEMA.validate(self.data)
        except schema.SchemaError as e:
            print("Validation against the data schema of this object failed.")
            raise e
        return data

    def validate_json(self):
        """Validate the object's data against its json schema (``self.JSONSCHEMA``).

        Returns
        -------
        str
            The validated JSON representation of the data.

        Raises
        ------
        :class:`jsonschema.exceptions.ValidationError`
        """
        import jsonschema
        jsonstring = json.dumps(self.data, cls=DataEncoder)
        jsondata = json.loads(jsonstring, cls=DataDecoder)
        try:
            self.jsonvalidator.validate(jsondata)
        except jsonschema.exceptions.ValidationError as e:
            print("Validation against the JSON schema of this object failed.")
            raise e
        return jsonstring
