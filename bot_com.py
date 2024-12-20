# import os
import logging as log
# import aiofile
# import asyncio
import discord.ext.commands as cmds
from typing import Callable, Any

log.basicConfig(level=log.INFO)
bot_com_logger: log.Logger = log.getLogger(__file__)

class BotComCommand:
    def __init__(self, name: str, callback: Callable[[cmds.Context, dict[str, Any]], None]) -> None:
        self.name = name
        self.callback = callback

bot_com_commands: dict[str, BotComCommand] = {}

def define_bot_com_command(name: str, callback: Callable[[cmds.Context, dict[str, Any]], None]) -> BotComCommand:
    if bot_com_commands.get(name) != None:
        bot_com_logger.debug(f"Bot command {name} is already defined!")
        return bot_com_commands[name]

    bot_com_commands[name] = BotComCommand(name, callback)

    return bot_com_commands[name]

def echo(cmd: cmds.Context, params: dict[str, Any]) -> None:
    print(cmd, params)

define_bot_com_command("echo", echo)

class BotCom:
    def __init__(self, filename: str) -> None:
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
                    data_str: str = str(data)

                    cmd: str = data_str.split(' ')[0]

                    bot_cmd: BotComCommand | None = bot_com_commands.get(cmd)
                    if bot_cmd == None:
                        self.logger.warning(f"Undefined command '{cmd}'")
                    else:
                        bot_cmd.callback(None)


                if data == b"STOP":
                    break

                await asyncio.sleep(0.1)  # Add a small delay to avoid busy-waiting
        self.logger.info("Stopped bot com")
