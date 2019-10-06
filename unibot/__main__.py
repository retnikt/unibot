import sys

assert sys.version_info >= (3, 7), "unsupported python version! please use 3.7+"

if __name__ == "__main__":
    from unibot.bot import Bot

    bot = Bot()
    bot.run()
