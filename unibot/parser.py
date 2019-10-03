import argparse
import asyncio
from typing import *

import discord


class CommandError(Exception):
    pass


class UnibotParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.context_message: Optional[discord.Message] = None
        kwargs["prog"] = "unibot"
        kwargs["add_help"] = False
        super(UnibotParser, self).__init__(*args, **kwargs)

    def error(self, message):
        self._print_message(message)
        raise CommandError(message)

    def _print_message(self, message, file=None):
        asyncio.create_task(self.context_message.channel.send(message))

    def add_subparsers(self, *args, **kwargs):
        return super(UnibotParser, self).add_subparsers(*args, **kwargs)
