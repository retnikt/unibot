import json
import pathlib

from pydantic import BaseModel


class Config:
    """
    config with sub-configuration sections
    """

    def __init__(self):
        self._section_data = {}
        self._section_classes = {}
        self._section_instances = {}

        self_outer = self

        class Section(BaseModel):
            # noinspection PyMethodOverriding
            def __init_subclass__(cls, name: str):
                self._section_classes[name] = cls
                cls.__config_name__ = name

            def __init__(self):
                data = self_outer._section_data[self.__config_name__]
                super(Section, self).__init__(**data)
                self_outer._section_instances[self.__config_name__] = self

            def unload(self):
                del self_outer._section_instances[self.__config_name__]
                del self_outer._section_classes[self.__config_name__]

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
        with path.open("r") as f:
            data = json.load(f)

        for key, cls in self._section_classes:
            self._section_data[key] = data.get(key, {})
