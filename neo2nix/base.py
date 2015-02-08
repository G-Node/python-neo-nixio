__author__ = 'andrey'

from datetime import datetime


class NixBase(object):

    _default_metadata_attr_names = ('description', 'file_origin')

    def __init__(self, nix_object):
        self.__nix_object = nix_object

    # --------------------------------
    # The following methods proxy setters/getters for attributes that should be
    # stored in the related metadata '_base' section.
    # --------------------------------

    def __getattr__(self, name):
        if name in self._get_metadata_attr_names():
            md = self._metadata['_base']
            return md[name] if name in md else None
        else:
            return super(NixBase, self).__getattribute__(name)

    def __setattr__(self, key, value):
        if key in self._get_metadata_attr_names():
            self._metadata['_base'][key] = value
        else:
            super(NixBase, self).__setattr__(key, value)

    @staticmethod
    def _get_metadata_attr_names():
        raise NotImplementedError

    @property
    def _nix_object(self):
        return self.__nix_object

    @property
    def _metadata(self):
        return self._nix_object.metadata

    # --------------------------------
    # default NIX attributes
    # --------------------------------

    @property
    def uuid(self):
        """ Object ID in the File """
        return str(self._nix_object.id)

    @property
    def name(self):
        """ Object name """
        return str(self._nix_object.name)

    @property
    def type(self):
        """ Object type """
        return self._nix_object.type

    @property
    def created_at(self):
        """ Timestamp of object initial creation """
        return datetime.fromtimestamp(self._nix_object.created_at)

    # --------------------------------
    # annotations
    # --------------------------------

    @property
    def annotations(self):
        """ Neo annotations TODO build separate class? """
        properties = {}

        if not self._nix_object.metadata:
            return {}

        for p in self._nix_object.metadata:
            key = p.name
            if len(p.values) == 1:
                value = p.values[0].value
            else:
                value = [x.value for x in p.values]

            properties[key] = value

        return properties

    @annotations.setter
    def annotations(self, annotations):
        pass

    # --------------------------------
    # building real Neo objects from NIX entities
    # --------------------------------

    def as_neo(self, lazy=True, recursive=True):
        """
        Get this object as corresponding Neo object.

        :param lazy:        keep Neo object attached to the NIX backend
        :param recursive:   if detached, whether to load children recursively
        :return:            corresponding (instance of) Neo object
        """
        raise NotImplementedError