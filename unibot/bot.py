import asyncio
import logging
import shlex
import sys
from pathlib import Path
from platform import platform
from typing import *

import discord

import unibot._globals
import unibot._utils
import unibot.config
import unibot.parser
import unibot.plugin_manager
from unibot import command, __VERSION__

EVENT_NAMES = [
    "connect",
    "disconnect",
    "ready",
    "shard_ready",
    "resumed",
    "error",
    "socket_raw_receive",
    "socket_raw_send",
    "typing",
    "message",
    "message_delete",
    "bulk_message_delete",
    "raw_message_delete",
    "raw_bulk_message_delete",
    "message_edit",
    "raw_message_edit",
    "reaction_add",
    "raw_reaction_add",
    "reaction_remove",
    "raw_reaction_remove",
    "reaction_clear",
    "raw_reaction_clear",
    "private_channel_delete",
    "private_channel_create",
    "private_channel_update",
    "private_channel_pins_update",
    "guild_channel_delete",
    "guild_channel_create",
    "guild_channel_update",
    "guild_channel_pins_update",
    "guild_integrations_update",
    "webhooks_update",
    "member_join",
    "member_remove",
    "member_update",
    "user_update",
    "guild_join",
    "guild_remove",
    "guild_update",
    "guild_role_create",
    "guild_role_delete",
    "guild_role_update",
    "guild_emojis_update",
    "guild_available",
    "guild_unavailable",
    "voice_state_update",
    "member_ban",
    "member_unban",
    "group_join",
    "group_remove",
    "relationship_add",
    "relationship_remove",
    "relationship_update",
]


class CoreConfig(unibot._globals.config.section, name="core"):
    prefix: str = "~"
    debug: bool = False
    debug_channel: Optional[str] = None
    load_base: bool = True
    safe_mode: bool = False
    reconnect: bool = True


class CoreCredentials(unibot._globals.credentials.section, name="core"):
    client_id: str
    bot_token: str


class Bot(discord.Client):
    FORMAT = "[ {levelname:<7} ] [ {name:<20} ]  {message}"

    def __init__(self, config_file="config.json",
                 credentials_file="credentials.json"):
        super(Bot, self).__init__()

        self.config: Optional[CoreConfig] = None
        self.credentials: Optional[CoreCredentials] = None
        self.config_file = config_file
        self.credentials_file = credentials_file

        self._listener_coros = {event_name: [] for event_name in EVENT_NAMES}
        self.commands = []

        self.logger = logging.getLogger("unibot")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(self.FORMAT, style="{"))
        self.logger.addHandler(handler)

        self.plugin_manager = unibot.plugin_manager.PluginManager(self)

        self.root_parser = unibot.parser.UnibotParser()
        self.subcommands_class = command.CommandWithSubCommands.new("root")
        self.subcommands: Optional[command.CommandWithSubCommands] = None

        self._planned_disconnect = False

        self.plugin_unload_hooks = [self._recursively_remove_commands]

        self.global_bot_context = self._GlobalBotContext(self)

        @self.event_listener("message")
        async def on_message(message):
            if message.author == self.user or not message.content.startswith(
                    self.config.prefix
            ):
                return
            # remove prefix
            content = message.content[len(self.config.prefix):]
            args = shlex.split(content)
            self.root_parser.context_message = message
            try:
                namespace = self.root_parser.parse_args(args)
            except unibot.parser.CommandError:
                return
            self.logger.debug(f"Executing command: '{message.content}'")
            try:
                await self.subcommands(message, **vars(namespace))
            except Exception as e:
                await message.exception_handler(e, message)
            finally:
                self.root_parser.context_message = None

        @self.event_listener("ready")
        async def on_ready():
            self.logger.info("Ready.")

        @self.event_listener("disconnect")
        async def on_disconnect():
            if self._planned_disconnect:
                self.logger.info("Disconnected.")
            else:
                self.logger.error("Disconnected.")

    async def exception_handler(self, e, message):
        self.logger.error(
            f"Exception in command '{message.content}'", exc_info=e
        )
        if self.config.debug:
            import traceback

            tb = traceback.format_exc()
            await message.channel.send(f"Error:\n```{tb}```")
        else:
            await message.channel.send(
                "Oops! An error occurred while executing your command."
                "Please contact the server administrator. If you are"
                "the bot administrator, check the server logs"
                + (
                    f" and debug channel ({self.config.debug_channel})"
                    if self.config.debug_channel
                    else ""
                )
                + " for more details."
            )

    async def ask_question(
            self,
            channel: discord.TextChannel,
            question,
            options,
            target_user,
            reaction_emoji=LETTER_EMOJI,
    ):
        if len(options) > len(reaction_emoji):
            raise ValueError("too many options")
        text = question + "\n" + "\n".join(map(" ".join,
                                               zip(reaction_emoji, options)))

        def check(m):
            return m.author == target_user

        message = await channel.send(text)
        await asyncio.gather(
            [
                message.add_reaction(emoji)
                for emoji in reaction_emoji[: len(options) - 1]
            ]
        )
        reaction = await self.wait_for("reaction_add", check=check)

    async def close(self):
        self.logger.info("Logging out")
        self._planned_disconnect = True
        return super(Bot, self).close()

    def event(self, coro):
        raise NotImplementedError(
            "the event method is not supported on a Bot. "
            "Use the @event_listener decorator instead"
        )

    def event_listener(self, name: str):
        if name not in EVENT_NAMES:
            raise ValueError(f"no such event '{name}'")

        def decorator(coro: Coroutine):
            self._listener_coros[name].append(coro)
            return coro

        return decorator

    def dispatch(self, event, *args, **kwargs):
        for listener in self._listener_coros.get(event, []):
            asyncio.create_task(listener(*args, **kwargs))
        return super(Bot, self).dispatch(event, *args, **kwargs)

    def plugin_unload_hook(self, fn):
        self.plugin_unload_hooks.append(fn)

    def _recursively_remove_commands(self, plugin, subcommands=None):
        subcommands = subcommands or self.subcommands
        for i, cmd in enumerate(subcommands.commands):
            if cmd.__module__ is plugin:
                del subcommands.commands[i]
            elif isinstance(command, unibot.command.CommandWithSubCommands):
                self._recursively_remove_commands(plugin, cmd)

    def command(self, cls):
        return self.subcommands_class.command(cls)

    def generate_add_url(self):
        return (
            "https://discordapp.com/oauth2/authorize?&client_id="
            f"{self.credentials.client_id}&scope=bot&permissions=8"
        )

    class _GlobalBotContext:
        def __init__(self, bot):
            self.bot = bot

        def __enter__(self):
            unibot._globals.bot = self.bot
            return self.bot

        def __exit__(self, exc_type, exc_val, exc_tb):
            unibot._globals.bot = None

    def run(self):
        with self.global_bot_context:
            self.logger.info("Starting bot.")
            self.logger.debug(f"Unibot version: {__VERSION__:08x}")
            self.logger.debug(f"Python version: {sys.hexversion:08x}")
            self.logger.debug(f"Platform: {platform()}")
            self.logger.info("Loading config.")
            self.config = self.config.load(Path(self.config_file))
            self.credentials = unibot._globals.credentials.load(
                Path(self.credentials_file)
            )
            if self.config.load_base:
                self.logger.info("Loading base.")
                from unibot import base

                self.plugin_manager.plugins["unibot.base"] = base
            if self.config.safe_mode:
                self.logger.info("Skipping loading plugins (safe mode "
                                 "enabled).")
                return
            else:
                self.logger.info("Loading plugins.")
                self.plugin_manager.load_plugins()
            self.subcommands = self.subcommands_class(self.root_parser)
            self.logger.info("Logging in.")

            loop = asyncio.get_event_loop()
            if sys.version_info < (3, 7, 4):
                # a bug between python 3.7 and 3.7.3 causes some weird SSL error
                # which causes crashes (see docstring)
                unibot._utils.ignore_aiohttp_ssl_error(loop)
            try:
                loop.run_until_complete(
                    self.start(self.credentials.bot_token,
                               reconnect=self.config.reconnect)
                )
            except KeyboardInterrupt or SystemExit:
                loop.run_until_complete(self.logout())
            # cancel all tasks lingering
            finally:
                self.logger.info("Shutting down.")
                loop.close()
