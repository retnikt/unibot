import sys

if sys.version_info < (3, 7):
    print("unsupported python version! please use 3.7+")
    sys.exit(1)
else:
    from unibot.bot import Bot

    bot = Bot()
    bot.run()
