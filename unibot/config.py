import json
import pathlib
from typing import Optional

from pydantic import BaseModel, BaseConfig


class Config:
    """
    config with sub-configuration sections
    """

    def __init__(self):
        self.path: Optional[pathlib.Path] = None
        self._section_data_raw = {}
        self._section_data = {}
        self._section_classes = {}
        self._section_instances = {}

        self_outer = self

        class Section(BaseModel):
            class Config(BaseConfig):
                validate_assignment = True

            # noinspection PyMethodOverriding
            def __init_subclass__(cls, id: str):
                self._section_classes[id] = cls
                cls.__config_name__ = id

            def __init__(self):
                data = self_outer._section_data[self.__config_name__]
                super(Section, self).__init__(**data)
                self_outer._section_instances[self.__config_name__] = self

            def unload(self):
                del self_outer._section_instances[self.__config_name__]
                del self_outer._section_classes[self.__config_name__]

            def __setattr__(self, key, value):
                super(Section, self).__setattr__(key, value)
                self_outer._section_data_raw[self.__config_name__][key] = value
                self_outer.flush_config()

            __setitem__ = __setattr__

            def __delattr__(self, item):
                super(Section, self).__delattr__(item)
                del self_outer._section_data_raw[self.__config_name__][item]
                self_outer.flush_config()

            __delitem__ = __delattr__

            def __getitem__(self, item):
                try:
                    getattr(self, item)
                except AttributeError as e:
                    raise KeyError from e

        self.section = Section

    def reload(self):
        for k in self._section_data:
            if k not in self._section_instances:
                # has not yet been initialised - new plugin?
                self._section_instances[k] = self._section_classes[k]()
            else:
                # needs reinitialising
                self._section_instances[k].__init__()

    def load(self, path: pathlib.Path):
        self.path = path
        with self.path.open("r") as f:
            self._section_data_raw = json.load(f)

        for key, cls in self._section_classes:
            self._section_data[key] = self._section_data_raw.get(key, {})

    def flush_config(self):
        with self.path.open("w") as f:
            json.dump(f, self._section_data_raw)

    def __getitem__(self, item):
        return self._section_instances[item]
