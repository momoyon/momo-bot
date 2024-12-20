import os
import logging as log
import aiofile
import asyncio
import discord.ext.commands as cmds
from typing import Callable, Any

log.basicConfig(level=log.INFO)
bot_com_logger: log.Logger = log.getLogger(__file__)

class InsufficientParamsException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        self.message = message
        super().__init__(*args)

    def __repr__(self) -> str:
        if len(self.message): return self.message
        return super().__repr__()

    def __str__(self) -> str:
        return self.__repr__()

class BotComCommand:
    def __init__(self, name: str, callback: Callable[[Any, list[str]], None]) -> None:
        self.name = name
        self.callback = callback

bot_com_commands: dict[str, BotComCommand] = {}

def define_bot_com_command(name: str, callback: Callable[[Any, list[str]], None]) -> BotComCommand:
    if name in bot_com_commands != None:
        bot_com_logger.debug(f"Bot command {name} is already defined!")
        return bot_com_commands[name]

    bot_com_commands[name] = BotComCommand(name, callback)

    return bot_com_commands[name]

def echo(bot_com: Any, params: list[str]) -> None:
    assert(isinstance(bot_com, BotCom)), "Nigger you must pass a BotCom instance to this"
    if len(params) <= 0:
        raise InsufficientParamsException("echo command wants at least one parameter!")
    print(bot_com, *params)

define_bot_com_command("echo", echo)

class BotCom:
    def __init__(self, bot: cmds.Bot, filename: str) -> None:
        self.bot = bot
        self.logger: log.Logger = log.getLogger(f"{os.path.basename(filename)}")
        self.filename = filename

    async def start(self) -> None:
        self.logger.info(f"Started listening on bot com '{self.filename}'")

        # Make sure the file exists
        with open(self.filename, mode="w") as f:
            pass

        async with aiofile.async_open(self.filename, mode='rb') as f:
            while True:
                data: bytes = await f.read(1024)  # Read in chunks to avoid blocking

                data = data.strip()
                data = data.removesuffix(bytes(os.linesep, "utf-8"))
                if len(data) > 0:
                    self.logger.info(f"Got data '{str(data)}'")
                    data_str: str = data.decode()

                    cmd: str = data_str.split(' ')[0]

                    params: list[str] = data_str.split(' ')[1:]

                    if cmd in bot_com_commands:
                        bot_cmd: BotComCommand = bot_com_commands[cmd]
                        try:
                            bot_cmd.callback(self, params)
                        except Exception as e:
                            self.logger.error(str(e))
                    else:
                        self.logger.warning(f"Undefined command '{cmd}'")

                if data == b"STOP":
                    break

                await asyncio.sleep(0.1)  # Add a small delay to avoid busy-waiting
        self.logger.info("Stopped bot com")
