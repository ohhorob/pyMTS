import collections
import io
import logging
import ujson


class Settings(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self._logger = logging.getLogger('Settings')
        self.store = dict()
        self.update(dict(*args, **kwargs))
        if 'path' in kwargs:
            self.load(kwargs['path'])

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def load(self, path):
        try:
            js = io.open(
                path,
                mode='rb',
                buffering=io.DEFAULT_BUFFER_SIZE
            )
            self.update(ujson.load(js))
            self._logger.info('Loaded from {}', path)
        except IOError as e:
            self._logger.warn('Failed to open path={}; {}', path, e.message)

    def save(self, path=None):
        if path is None:
            if 'path' in self.store:
                path = self.store['path']
            else:
                raise KeyError('path must be specified')
        js = io.open(path, mode='w', encoding='UTF-8')
        ujson.dump(self, js)
        js.flush()
        js.close()