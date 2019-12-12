import asyncio

THUMBS_EMOJI = ("\N{thumbs up sign}", "\N{thumbs down sign}")
TICK_CROSS_EMOJI = ("\N{check mark}", "\N{cross mark}")


class _SelfMapper:
    def __getitem__(self, item):
        return item


class Menu:
    def __init__(
        self, bot, question, options, emoji=TICK_CROSS_EMOJI, mapper=None
    ):
        if len(options) > len(emoji):
            raise ValueError("too many options")
        self.text = self.create_text(question, options, emoji)
        self.options = options
        self.emoji = emoji
        self.bot = bot
        self.mapper = mapper or _SelfMapper()

    def create_text(self, question, options, emoji):
        return question + "\n" + "\n".join(map(": ".join, zip(emoji, options)))

    def _check(self, target_user, message):
        return (
            lambda reaction, user: reaction.message == message
            and user == target_user
            and reaction.emoji in self.emoji
        )

    async def _run(self, channel, target_user):
        message = await channel.send(self.text)
        await asyncio.gather(
            (
                message.add_reaction(emoji)
                for emoji in self.emoji[: len(self.options) - 1]
            )
        )
        reaction = await self.bot.wait_for(
            "reaction_add", check=self._check(message, target_user)
        )
        return reaction

    async def run(self, channel, target_user):
        reaction = await self._run(channel, target_user)
        return self.mapper[self.options[self.emoji.index(reaction.emoji)]]


class YesNoMenu(Menu):
    _options = ["Yes", "No"]

    def __init__(self, bot, question, emoji=THUMBS_EMOJI):
        super(YesNoMenu, self).__init__(bot, question, self._options, emoji)

    def run(self, channel, target_user):
        reaction = self._run(channel, target_user)
        return reaction == self.emoji[0]
