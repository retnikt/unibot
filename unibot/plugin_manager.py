import asyncio
import importlib.machinery
import importlib.util
import logging
import pathlib
import pkgutil
import types
from typing import Optional, Sequence, Mapping, Union

import unibot.config


class PluginManifest:
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    docs: Optional[str] = None
    source: Optional[str] = None
    issues: Optional[str] = None
    requirements: Sequence[Mapping[str, str]] = ()


class PluginsConfig(unibot._globals.config.section, id="plugins"):
    plugin_search_directories: Sequence[str] = ("plugins",)
    plugins_enabled: Sequence[str] = ()
    plugin_unload_timeout: Union[float, int] = 5


class _PluginModule(types.ModuleType):
    __manifest__: PluginManifest


class PluginManager:
    PLUGIN_NAME = "unibot._loaded_plugin_{name}"

    def __init__(self, bot):
        self.bot = bot
        self.plugins = {}
        self.logger = logging.getLogger("unibot.plugins")
        self.config = PluginsConfig(self.bot.config_config)

    def load_plugins(self):
        for finder, name, _ in pkgutil.iter_modules(
                self.config.plugin_search_directories
        ):
            spec = finder.find_spec(name)
            if spec is None:
                self.logger.debug(
                    f"Ignoring plugin {name}" f"with no module spec available"
                )
                continue
            else:
                if name in self.plugins:
                    self.logger.warning(
                        f"Skipping plugin with duplicate name"
                        f"'{name}' from '{spec.origin}'."
                    )
                self.load_plugin_from_spec(spec)

    async def unload_plugin(self, name, force: bool = False) -> bool:
        """
        unloads a plugin
        :param name: name of the plugin to unload
        :param force: if True, then continue trying to unload even if there is
        a failure. Always returns true in this case.
        :return: True if unload was successful, False otherwise.
        """
        plugin = self.plugins.get(name)
        if plugin is None:
            raise NameError("Plugin is not loaded")

        if hasattr(plugin, "unload_hook"):
            try:
                if asyncio.iscoroutinefunction(plugin.unload_hook):
                    await asyncio.wait_for(
                        plugin.unload_hook(plugin),
                        self.config.plugin_unload_timeout
                    )
                else:
                    plugin.unload_hook(plugin)
            except Exception as e:
                self.logger.error(
                    f"Exception in plugin unload hook for plugin '{name}':",
                    exc_info=e
                )
            if not force:
                return False

        for hook in self.bot.plugin_unload_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    asyncio.create_task(hook(plugin))
                else:
                    hook(plugin)
            except Exception as e:
                self.logger.error(
                    f"Exception in plugin unload hook '{hook.__name__}'"
                    f"for plugin {name}:",
                    exc_info=e,
                )
                if not force:
                    return False

        return True

    async def reload_plugin(self, name):
        await self.unload_plugin(name)
        path = pathlib.Path(self.plugins[name].__file__)
        importlib.reload(self.plugins[name])
        self.load_plugin_from_path(path.parent)

    def load_plugin_from_path(self, path: Union[str, pathlib.Path]):
        spec = importlib.util.spec_from_file_location(str(path))
        return self.load_plugin_from_spec(spec)

    def load_plugin_from_module_name(self, module_name: str):
        module = importlib.import_module(module_name)
        return self._add_plugin(module)

    def load_plugin_from_spec(self, spec: importlib.machinery.ModuleSpec):
        module = spec.loader.load_module()
        return self._add_plugin(module)

    def _add_plugin(self, module: _PluginModule):
        if not hasattr(module, "__manifest__"):
            self.logger.error(f"Plugin '{module.__name__}' has no manifest")
        else:
            self.plugins[module.__manifest__.name] = module
            return module
