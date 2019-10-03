import asyncio
from datetime import datetime

import discord

from unibot.bot import bot
from unibot.command import BaseCommand

__VERSION__ = 0x000100D


@bot.command
class Help(BaseCommand):
    name = "help"
    help = "provides help for the bot's commands"

    async def callback(self, message: "discord.Message"):
        # DM the user help
        if not message.author.dm_channel:
            await message.author.create_dm()
        asyncio.create_task(message.author.dm_channel.send(bot.root_parser.format_help()))


@bot.command
class Restart(BaseCommand):
    name = "restart"

    async def callback(self, message: "discord.Message"):
        import os
        import sys
        os.execl(sys.executable, sys.executable, *sys.argv)


@bot.command
class Embed(BaseCommand):
    name = "embed"

    async def callback(self, message: "discord.Message"):
        await message.channel.send("message", embed=discord.Embed(title="title", type="rich", description="description",
                                                                  url="https://google.com/", timestamp=datetime.now(),
                                                                  colour=discord.Colour.red()))


@bot.command
class ReloadBase(BaseCommand):
    name = "reload_base"

    async def callback(self, message):
        bot.plugin_manager.reload_plugin("base")
