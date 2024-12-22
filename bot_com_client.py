import logging, coloredlogs
import sys, os

logging.basicConfig(level=logging.INFO)
coloredlogs.install(level=logging.INFO)
l: logging.Logger = logging.getLogger("bot_com_client")

def usage(program: str) -> None:
    l.info(f"Usage: {program} <bot_com>")

def send(f, *args) -> None:
    f.write(*args)
    f.flush()

def main() -> None:
    program: str = sys.argv.pop(0)

    if len(sys.argv) <= 0:
        usage(program)
        l.error(f"Please provide the bot_com to connect to!")
        exit(1)

    bot_com_file: str = sys.argv.pop(0)

    l.info(f"Started bot_com_client")
    l.info(f"Connecting to bot_com '{bot_com_file}'")


    if not os.path.exists(bot_com_file):
        l.error(f"bot_com '{bot_com_file}' doesn't exist!")
        exit(1)

    l.info("OK")

    f = open(bot_com_file, 'a+')

    send(f, f"echo 'Bot Client connected!'")
    while True:
        try:
            cmd: str = input("> ")
            send(f, cmd)
        except KeyboardInterrupt:
            break

    f.close()

if __name__ == '__main__':
    main()
