import os
import logging as log
import aiofile
import asyncio
import discord.ext.commands as cmds
from typing import Callable, Any, Type
from enum import IntEnum

log.basicConfig(level=log.DEBUG)
bot_com_logger: log.Logger = log.getLogger(__file__)

class ParamCount(IntEnum):
    ATLEAST = 0
    EXACT = 1
    NOMORE_THAN = 2
    COUNT = 3

def param_count_as_str(v: ParamCount) -> str:
    match(v):
        case ParamCount.ATLEAST: return "at least"
        case ParamCount.EXACT: return "exactly"
        case ParamCount.NOMORE_THAN: return "no more than"
        case ParamCount.COUNT: pass
    assert False, "This musn't run!"

# Exceptions
class InsufficientParamsException(Exception):
    def __init__(self, funcname: str, param_count_type: ParamCount, expected_args_count: int, *args: object) -> None:
        self.funcname = funcname
        self.param_count_type = param_count_type
        self.expected_args_count = expected_args_count
        super().__init__(*args)

    def __repr__(self) -> str:
        return f"{self.funcname} expects {param_count_as_str(self.param_count_type)} {self.expected_args_count} argument(s)!"

    def __str__(self) -> str:
        return self.__repr__()

class InvalidParamTypeException(Exception):
    def __init__(self, wanted_type: Type, got_type: Type, funcname: str, *args: object) -> None:
        self.wanted_type = wanted_type
        self.got_type = got_type
        self.funcname = funcname
        super().__init__(*args)

    def __repr__(self) -> str:
        return f"{self.funcname} wanted {self.wanted_type} but got {self.got_type}"

    def __str__(self) -> str:
        return self.__repr__()

# Classes
class BotComCommand:
    def __init__(self, name: str, callback: Callable[[Any, list[Any]], None]) -> None:
        self.name = name
        self.callback = callback

bot_com_commands: dict[str, BotComCommand] = {}

def define_bot_com_command(name: str, callback: Callable[[Any, list[Any]], None]) -> BotComCommand:
    if name in bot_com_commands != None:
        bot_com_logger.debug(f"Bot command {name} is already defined!")
        return bot_com_commands[name]

    bot_com_commands[name] = BotComCommand(name, callback)

    return bot_com_commands[name]

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

        async with aiofile.async_open(self.filename, mode='rb+') as f:
            while True:
                data: bytes = await f.read(1024)  # Read in chunks to avoid blocking

                data = data.strip()
                data = data.removesuffix(bytes(os.linesep, "utf-8"))
                if len(data) > 0:
                    data_str: str = data.decode()

                    cmd: str = data_str.split(' ')[0]

                    params: list[str] = data_str.split(' ')[1:]

                    if cmd in bot_com_commands:
                        bot_cmd: BotComCommand = bot_com_commands[cmd]
                        try:
                            # self.logger.info(f"Running command `{cmd}`...")
                            bot_cmd.callback(self, params)
                        except Exception as e:
                            self.logger.error(str(e))
                    else:
                        self.logger.warning(f"Undefined command '{cmd}'")

                if data == b"stop":
                    break

                await asyncio.sleep(0.1)  # Add a small delay to avoid busy-waiting
        self.logger.info("Stopped bot com")

# Defined Bot Com Commands
# TODO: Find a way to make a decorator that will define a BotComCommand and add it to the map
def echo(bot_com: Any, params: list[Any]) -> None:
    """
    Just echos the given parameters to the stdout. Useful for testing BotComCommand
    """
    assert(isinstance(bot_com, BotCom)), "Nigger you must pass a BotCom instance to this"
    if len(params) <= 0:
        raise InsufficientParamsException("echo", ParamCount.ATLEAST, 1)
    print("ECHO:", *params)
define_bot_com_command("echo", echo)

def say(bot_com: Any, params: list[Any]) -> None:
    """
    Sends a message via the discord bot in the `bot_com`.

    The first argument in the params is the message.
    The second is the channel to send to.
    """
    assert(isinstance(bot_com, BotCom)), "Nigger you must pass a BotCom instance to this"
    if len(params) <= 0:
        raise InsufficientParamsException("say", ParamCount.EXACT, 2)
    if not isinstance(params[0], str):
        raise InvalidParamTypeException(type(str), type(params[0]), "say")

    msgs: list[str] = params

    bot: cmds.Bot = bot_com.bot

    print(f"TODO: Send to bot:", *msgs)
define_bot_com_command("say", say)
