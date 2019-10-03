from typing import *

from unibot import bot

if TYPE_CHECKING:
    import argparse

_SUBCOMMAND_DEST_PREFIX = "_subcommand_"


def require_permission(name):
    def decorator(cls: "BaseCommand"):
        cls.required_permissions.append(name)
        return cls

    return decorator


class BaseCommand:
    name: str
    help: Optional[str] = None
    description: Optional[str] = None

    callback: Callable[..., None]

    def __init__(self, parser: "argparse.ArgumentParser"):
        self.parser = parser
        self.required_permissions = []
        if not isinstance(self, CommandWithSubCommands):
            self.initialise()

    @classmethod
    def new(cls, name, **kwargs) -> Type["BaseCommand"]:
        # noinspection PyTypeChecker
        return type(name, (cls,), {"name": name, **kwargs})

    # convenience wrapper functions
    def add_argument(self, *args, **kwargs):
        """
        convenience wrapper function for self.parser.add_argument
        """
        return self.parser.add_argument(*args, **kwargs)

    def add_argument_group(self, *args, **kwargs):
        """
        convenience wrapper function for self.parser.add_argument_group
        """
        return self.parser.add_argument_group(*args, **kwargs)

    def add_mutually_exclusive_group(self, **kwargs):
        """
        convenience wrapper function for self.parser.add_mutually_exclusive_group
        """
        return self.parser.add_mutually_exclusive_group(**kwargs)

    def initialise(self):
        # here is where subclasses should add arguments
        ...

    def __call__(self, message, namespace):
        for permission in self.required_permissions:
            if permission not in bot.get_user_permissions(message.author):
                message.add_reaction('⛔⛔⛔⛔⛔⛔🚫\N{prohibited}')
                message.channel.send(f"{message.author.mention} "
                                     f"You do not have the required permission '{permission}' "
                                     "to execute this command")
                return
        return self.callback(message, **vars(namespace))


class CommandWithSubCommands(BaseCommand):
    description: Optional[str] = None
    required: bool = True
    help: Optional[str] = None
    metavar: Optional[str] = None

    commands: List[Type[BaseCommand]] = []

    @classmethod
    def command(cls, command):
        cls.commands.append(command)

    def __init__(self, parser):
        super(CommandWithSubCommands, self).__init__(parser)
        # generate a unique subcommand ID
        self._dest = _SUBCOMMAND_DEST_PREFIX + str(id(self))

        self.subparsers = self.parser.add_subparsers(
            description=self.description,
            dest=self._dest,
            required=self.required,
            help=self.help,
            metavar=self.metavar
        )

        self._commands_callbacks = {}
        for command in self.commands:
            new = self.subparsers.add_parser(command.name)
            self._commands_callbacks[command.name] = command(new)

    def callback(self, message, **kwargs):
        command_name = kwargs.pop(self._dest)
        return self._commands_callbacks[command_name].callback(message, **kwargs)
