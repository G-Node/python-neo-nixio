


class ProxyList(object):
    """ An enhanced list that can load its members on demand. Behaves exactly
    like a regular list for members that are Neo objects.
    """

    def __init__(self, io, child_type, parent_id):
        """
        :param io:          IO instance that can load items
        :param child_type:  a type of the children, like 'segment' or 'event'
        :param parent_id:   id of the parent object
        """
        self._io = io
        self._child_type = child_type
        self._parent_id = parent_id
        self._cache = None

    @property
    def _data(self):
        if self._cache is None:
            args = (self._parent_id, self._child_type)
            self._cache = self._io.read_multiple(*args)
        return self._cache

    def __getitem__(self, index):
        return self._data.__getitem__(index)

    def __delitem__(self, index):
        self._data.__delitem__(index)

    def __len__(self):
        return self._data.__len__()

    def __setitem__(self, index, value):
        self._data.__setitem__(index, value)

    def insert(self, index, value):
        self._data.insert(index, value)

    def append(self, value):
        self._data.append(value)

    def reverse(self):
        self._data.reverse()

    def extend(self, values):
        self._data.extend(values)

    def remove(self, value):
        self._data.remove(value)

    def __str__(self):
        return '<' + self.__class__.__name__ + '>' + self._data.__str__()

    def __repr__(self):
        return '<' + self.__class__.__name__ + '>' + self._data.__repr__()