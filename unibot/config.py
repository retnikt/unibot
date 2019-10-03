from __future__ import annotations

import inspect
import json
from typing import *

from pydantic.dataclasses import dataclass


class ConfigError(Exception):
    pass


def config_section(identifier: str, frozen: bool = False) -> Callable[
    [Type], Type]:
    """
    Decorator to turn a class in to a config section dataclass.
    It adds the following methods:
    * `__init__` which gets the config from the cache, and copies it into the
    config object

    * `__repr__` which gives something like this: `Config(foo=12, eggs="spam", ...)`, recursively stepping in to
        contained dataclasses (this is the same as a vanilla Python dataclass)

    * `__eq__` which simply checks equality on all attributes (this is the same as a vanilla Python dataclass)

    * `__setattr__` which checks you're not using any illegal types
        (you can only use str, int, float, list, dict, bool, None)

    * `update` which re-copies the config from the Config object's cache. Note that this does not actually reload
        the file - this must be done manually using the `load` method on the Config object itself (not the config
        dataclass) (this method is not added when `frozen` is True)

    :param identifier: string to identify this section in a config file
    :param frozen: whether to make the resulting dataclass immutable
    :return: decorated config section dataclass

    Example usage:
    >>> @config_section()
    ... class MyConfigSection:
    ...     value: str
    ...     value_with_default: bool = True
    ...     you_can_use_any_combination_of_the_basic_types: Dict[str, List[[Union[int, float]]]]
    ...     but_not_functions: Callable  # will cause strange unexpected behaviour
    ...     nor_anything_else_strange: Set[bytes, ...]  # also not ok
    ...
    >>> my_config = JSONConfig("my_config.json")
    >>> my_config_section = MyConfigSection(my_config)
    >>> print(my_config_section.value)
    "hello world"
    """

    def decorator(cls):
        cls = dataclass(cls, frozen=frozen)
        super_init = cls.__init__

        def sub_init(self_inner, config, *args):
            if config.full_config is None:
                import warnings
                warnings.warn(
                    "Config has not yet been loaded. Load it with load_config_file(path)")
                return
            kwargs = config.full_config.get(identifier) or {}
            # get all the parameters
            parameters = dict(inspect.signature(super_init).parameters)
            # remove the self parameter
            del parameters['self']
            # parameters
            # which parameters do not have default values?
            required = {k for k, v in parameters.items() if
                        v.default is v.empty}
            # are any parameters required but not specified?
            missing = set(required) - set(kwargs.keys())
            if missing:
                # error!
                raise ConfigError(
                    f"Missing required configuration values: {', '.join(map(str, missing))}")

            try:
                super_init(self_inner, *args, **kwargs)
            except ValueError as e:
                raise ConfigError(*e.args)

        def update(self_inner):
            # this just calls __init__ again on the object
            # (which you're not technically supposed to do in python)
            self_inner.__init__()

        # we can't just extend the class because it would mess up the MRO, class hierarchy, and special attributes
        #  so we just set the new attributes on to the class individually. (curse you, multiple inheritance!)
        cls.__init__ = sub_init
        if not frozen:
            cls.update = update
        return cls

    return decorator


class BaseConfig:
    """
    A class for storing and loading various configuration sections from one file.
    Each section has its own dataclass
    """

    def __init__(self, path, auto_load: bool = True):
        """
        :param auto_load: whether load the config immediately (default)
        :param path: filesystem path to load config from
        """
        self.path = path
        self.full_config = None
        if auto_load:
            self.load()

    def load(self, path=None):
        """
        load or reload the config from a file
        THIS METHOD SHOULD NOT BE OVERRIDDEN!
        If you want to change how the config loads from a file, override the `_load` method, NOT this one!
        :param path: path to load from, or the default path stored in the object if not specified
        """
        path = path or self.path
        with open(path) as f:
            self.full_config = self._load(f)

    def _load(self, path) -> Mapping[str, Mapping[str, Any]]:
        """
        load the config from a file-like object and return it
        :param path:
        :return: config as a mapping of section names to dicts of config keys to values
        """
        return NotImplemented


class JSONConfig(BaseConfig):
    """
    loads config in JSON format where top-level keys represent sections
    E.G.
    ```json
        {
            "section1": {...},
            ...
        }
    ```
    """

    def _load(self, f):
        return json.load(f)
