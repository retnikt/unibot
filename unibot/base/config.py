import json

import discord
import pydantic

from unibot import bot
from unibot._globals import config, credentials
from unibot.command import CommandWithSubCommands, BaseCommand


class Test(config.section, name="test"):
    default: int = 45
    other: str


def _recurse_getitem(obj, segments):
    new = obj
    cumulative = []
    for seg in segments:
        try:
            new = new[seg]
        except IndexError:
            raise IndexError(*cumulative)
        cumulative.append(seg)
    return new


@bot.command
class Config(CommandWithSubCommands):
    name = "config"


@Config.command
class ReloadConfig(BaseCommand):
    name = "reload"

    async def callback(self, message: "discord.Message"):
        config.reload()
        credentials.reload()
        await message.channel.send(f"Successfully reloaded config")


@Config.command
class SetConfig(BaseCommand):
    name = "set"
    help = "sets a config variable"
    description = "sets a config variable"

    async def initialise(self):
        self.add_argument("key", required=True)
        value = self.add_mutually_exclusive_group(required=True)
        value.add_argument(
            "--int",
            "-i",
            type=int,
            dest="value",
            help="specify an integral value",
        )
        value.add_argument(
            "--float",
            "-f",
            type=float,
            dest="value",
            help="specify a floating-point value",
        )
        value.add_argument(
            "--str", "-s", dest="value", help="specify a string value"
        )
        value.add_argument(
            "--bool",
            "-b",
            type=bool,
            dest="value",
            help="specify a boolean value",
        )
        value.add_argument(
            "--null",
            "-n",
            dest="value",
            const=None,
            action="store_const",
            help="specify a null value",
        )
        value.add_argument(
            "--json",
            "-j",
            dest="value",
            help="specify a value as encoded JSON, e.g."
                 + r"""```json
                 {
                     \"something\": [42, true],
                     \"escapes\": \"required\",
                     \"backslash\": \"\\\",
                     \"unicode\": \"🆗\"
                 }```""",
        )

    # noinspection DuplicatedCode
    async def callback(self, message: "discord.Message", key, value):
        *path_segments, name = key.split(".")
        obj = config
        cumulative = []
        for segment in path_segments:
            cumulative.append(segment)
            if not isinstance(obj, dict):
                await message.channel.send(
                    f"{message.author.mention} Key not found"
                    + ".".join(cumulative)
                )
                return
            try:
                obj = obj[segment]
            except IndexError:
                await message.channel.send(
                    f"{message.author.mention} Key not found"
                    + ".".join(cumulative)
                )
                return
        try:
            setattr(obj, name, value)
        except pydantic.ValidationError as e:
            await message.channel.send(
                f"{message.author.mention} Invalid value '{repr(value)}'"
                + "\n".join(e.args)
            )
            return
        await message.channel.send()


@Config.command
class ShowConfig(BaseCommand):
    name = "show"
    help = "shows the value of a config variable"

    async def initialise(self):
        self.add_argument("key", required=True)

    # noinspection DuplicatedCode
    async def callback(self, message: "discord.Message", key):
        value = config
        cumulative = []
        for segment in key.split("."):
            cumulative.append(segment)
            if not isinstance(value, dict):
                await message.channel.send(
                    f"{message.author.mention} Key not found"
                    + ".".join(cumulative)
                )
                return
            try:
                value = value[segment]
            except IndexError:
                await message.channel.send(
                    f"{message.author.mention} Key not found"
                    + ".".join(cumulative)
                )
                return

        if isinstance(value, dict):
            await message.channel.send(
                "object: ```json\n"
                + json.dumps(value, indent=2, ensure_ascii=False)
                + "```"
            )
        if isinstance(value, list):
            await message.channel.send(
                f"{message.author.mention} array:"
                f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}```"
            )
        else:
            await message.channel.send(
                f"{message.author.mention} "
                f"{type(value).__name__}: {repr(value)}"
            )
