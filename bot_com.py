import os
import logging as log
import aiofile
import asyncio

log.basicConfig(level=log.INFO)

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

                if data == b"STOP":
                    break

                await asyncio.sleep(0.1)  # Add a small delay to avoid busy-waiting
        self.logger.info("Stopped bot com")
