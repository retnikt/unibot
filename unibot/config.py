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

        class Section(BaseModel):
            # noinspection PyMethodOverriding
            def __init_subclass__(cls, name: str):
                self._section_classes[name] = cls

        self.register = Section

    def load(self, path: pathlib.Path):
        with path.open("r") as f:
            data = json.load(f)

        for key, cls in self._section_classes:
            self._section_data[key] = cls(**data.get(key, {}))

    def get(self, name):
        return self._section_data[name]

    __getitem__ = get
