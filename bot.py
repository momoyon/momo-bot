import discord as ds
from discord import FFmpegPCMAudio
import discord.ext.commands as cmds
import discord.ext.tasks as tasks
import os, random
from typing import List, Any, cast
from dotenv import load_dotenv
import asyncio

import logging, coloredlogs

import bot_com

logging.basicConfig(level=logging.INFO)
coloredlogs.install(level=logging.INFO)

CONFIG_PATH="./config"

RUN_DISCORD_BOT=True

SOURCE_CODE_FILENAME=f"{os.path.splitext(os.path.basename(__file__))[0]}.stable.py"

MOMOYON_USER_ID=610964132899848208

DISCORD_HTTP_BODY_MAX_LEN=2000

MAX_LOREM_N = 3

# TODO: Implement RPC

# TODO: Check for file change in CONFIG_PATH and reload if so

# Helpers
def debug_log_context(ctx: cmds.Context):
    bot_logger.info(f'''Context:
                    subcommand_passed: {ctx.subcommand_passed}
                    command:           {ctx.command}
                    command_failed:    {ctx.command_failed}
                    current_argument:  {ctx.current_argument}
                    current_parameter: {ctx.current_parameter}
                    ''')


def read_config(filepath: str):
    with open(filepath, "r") as f:
        current_section = None
        config = {}
        for l in f.readlines():
            l = l.removesuffix("\n")
            # Ignore comments
            if l.startswith("#") or len(l) <= 0:
                continue
            if l.startswith("["):
                current_section = l.removeprefix("[").removesuffix("]")
                # print(f"{current_section=}")
            else:
                if current_section == None:
                    logging.error("Data cannot be outside sections!")
                    exit(1)
                else:
                    if current_section not in config:
                        config[current_section] = []
                    config[current_section].append(l)
        return config

def copy_file(a: str, b: str):
    with open(a, "r") as og:
        with open(b, "w") as old:
            old.write(og.read())

def write_config(config, filepath):
    if os.path.exists(filepath):
        copy_file(filepath, filepath+".old")

    f = open(filepath, "w")
    for section in config:
        f.write(f"[{section}]\n")
        for data in config[section]:
            f.write(data + "\n")
    f.close()
config = {}
intents = ds.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True
# intents.manage_messages = True

class BotState:
    def __init__(self, bot: cmds.Bot, working_guild_id: int, working_channel_idx: int) -> None:
        self.bot = bot
        self.working_guild_idx: int = working_guild_id
        self.working_channel_idx: int = working_channel_idx

    def guild(self) -> ds.Guild:
        return self.bot.guilds[self.working_guild_idx]

    def channel(self) -> ds.TextChannel:
        return self.guild().text_channels[self.working_channel_idx]

bot_state: BotState | None = None
bot = cmds.Bot('!!', intents=intents)
bot_logger: logging.Logger = logging.getLogger("bot")

# COGS ###########################################
class MiscCog(cmds.Cog, name="Miscellaneous"):
    def __init__(self, bot):
        self.bot = bot
        self.github_link = config['github_link'][0]
        self.lorem_ipsums = config['lorem_ipsums']

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command
        embed = ds.Embed(title="Error")
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original
        embed.description = f"Error: {error}"

        embed.description += f"\nUsage: {ctx.command.usage}"
        bot_logger.error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)

    @cmds.command("lorem", help="Spams a bunch of text *n* times to block off shit you don't wanna see.", usage="lorem [n] [force]")
    async def lorem(self, ctx: cmds.Context, n: int = MAX_LOREM_N, force: bool = False):
        if n > MAX_LOREM_N and not force:
            await ctx.send(f"WARNING: Sending bunch of text {n} times is a lot! pass `true` to make sure!")
            return
        for i in range(n):
            await ctx.send(random.choice(self.lorem_ipsums))

    @cmds.command("github", help="Github repo link of myself", usage="github")
    async def github(self, ctx: cmds.Context):
        await ctx.send(f"{self.github_link}")

    @cmds.command("swapcase", help="Inverts the case of the input.", usage="swap <text>")
    async def swapcase(self, ctx: cmds.Context, *, text: str):
        if ctx.author == bot.user:
            return
        await ctx.send(text.swapcase())

    @cmds.command("ping", help="Command for testing if the bot is online; bot should reply with 'pong!'", usage="ping")
    async def ping(self, ctx: cmds.Context):
        if ctx.author == bot.user:
            return
        await ctx.channel.send("pong!")

    @cmds.command("src", help="Prints the source code for this bot.", usage="src")
    async def src(self, ctx):
        if ctx.author == bot.user:
            return

        try:
            with open(SOURCE_CODE_FILENAME, 'rb') as f:
                f.seek(0, os.SEEK_END)
                filesize = f.tell()
                bot_logger.info(f"Length of '{SOURCE_CODE_FILENAME}': {filesize}")
                f.seek(0)

                # Send the whole file as a file
                file = ds.File(f, filename=SOURCE_CODE_FILENAME)
                await ctx.send(file=file)
        except FileNotFoundError:
            bot_logger.error(f"File '{SOURCE_CODE_FILENAME}' doesn't exist!")
            bot_logger.info("Please run build.sh to copy bot.py -> bot.stable.py")
            await ctx.send("ERROR: It seems like i was deployed improperly...", silent=True)

    @cmds.command("poop", help="Hehe poop.", usage="poop")
    async def poop(self, ctx):
        if ctx.author == bot.user:
            return
        await ctx.reply("Shit yourself nigger")

    @cmds.command("av", help="Displays the given user's avatar.", usage="av [member] [server_avatar = false]", aliases=["avatar", "pfp"])
    async def av(self, ctx, member: ds.Member | None = None, server_avatar: bool = False):
        if ctx.author == bot.user:
            return

        if member == None:
            member = ctx.author

        if server_avatar:
            await ctx.send(member.display_avatar)
        else:
            await ctx.send(member.avatar)

class BoopCog(cmds.Cog, name='Boop'):
    def __init__(self, bot):
        self.bot = bot
        self.MARISAD_GIFS = config['marisad_gifs']
        self.TETO_GIFS = config['teto_gifs']
        self.DORO = config['doro']

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command

        embed = ds.Embed(title="Error")
        embed.description = ""
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original

        embed.description += f"\nUsage: {ctx.command.usage}"
        bot_logger.error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)


    @cmds.command("marisad", help="Marisa. 1% Chance for something special :D", usage="marisad")
    async def marisad(self, ctx: cmds.Context) -> None:
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            # TODO:Put seeds to each gif
            if random.random() <= 0.1:
                await ctx.send('https://tenor.com/view/bouncing-marisa-fumo-marisa-kirisame-touhou-fumo-gif-16962360816851147092')
            else:
                await ctx.send(random.choice(self.MARISAD_GIFS))
    @cmds.command("doro", help="Doro :3", usage="doro")
    async def doro(self, ctx: cmds.Context) -> None:
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            await ctx.send(random.choice(self.DORO))

    @cmds.command("teto", help="fatass teto", usage="teto")
    async def teto(self, ctx: cmds.Context) -> None:
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            await ctx.send(random.choice(self.TETO_GIFS))

class DevCog(cmds.Cog, name='Dev'):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: cmds.Context): # type: ignore
        return ctx.author.id == MOMOYON_USER_ID

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command
        embed = ds.Embed(title="Error")
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original
        embed.description = f"Error: {error}"

        embed.description += f"\nUsage: {ctx.command.usage}"
        momoyon: ds.User = await bot.fetch_user(MOMOYON_USER_ID)
        if ctx.author.id != MOMOYON_USER_ID:
            await ctx.send(f"Only {momoyon.mention} can use dev commands")
        bot_logger.error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)

    # TODO: This kills the discord bot, but doesnt kill the script itself.
    @cmds.command("kys", help="I will Krill Myself :)")
    async def kys(self, ctx):
        KYS_REPONSES = [
                "Wai-",
                "Fuck yo-",
                "Nig-",
                "AARGh-",
                ":skull:",
        ]
        await ctx.send(random.choice(KYS_REPONSES))
        try:
            await ctx.bot.close()
            bot_logger.info(f"Bot connection closed")
        except Exception as e:
            bot_logger.error(f"Bot failed to close: {e}")


    @cmds.command("react", help="Reacts to a message with an emoji", usage="react <message_id> <emoji>")
    async def react(self, ctx: cmds.Context, message_id: int, emoji: str):
        msg = None
        try:
            msg: ds.Message = await ctx.fetch_message(message_id)
        except Exception as e:
            logging.error(f"Failed to fetch message: {e}")
            return

        if msg != None:
            try:
                await msg.add_reaction(emoji)
            except Exception as e:
                logging.error(f"Failed to react to message: {e}")
                return

        try:
            await ctx.message.delete()
        except Exception as e:
            logging.error(f"Failed to delete message: {e}")
            return

    @cmds.command("acd", help="Add data to a section in config", usage="acd <section> <data>")
    async def acd(self, ctx: cmds.Context, section: str, data: str):

        if section not in config:
            config[section] = []

        if data in config[section]:
            await ctx.send(f"`{data}` is already in `{section}`!")
            return
        else:
            config[section].append(data)

        write_config(config, CONFIG_PATH)

        await ctx.send(f"Added `{data}` to `{section}`")

    @cmds.command("rcd", help="Remove data from a section in config", usage="rcd <section> <data>")
    async def rcd(self, ctx: cmds.Context, section: str, data: str):

        if section not in config:
            await ctx.send(f"`{section}` is not in config!")
            return

        if data not in config[section]:
            await ctx.send(f"`{data}` is not in section `{section}`!")
            return

        config[section].remove(data)

        if len(config[section]) <= 0:
            config.pop(section)

        write_config(config, CONFIG_PATH)

        await ctx.send(f"Removed `{data}` from `{section}`")

    @cmds.command("lsconfig", help="List the configuration", usage="lsconfig")
    async def lsconfig(self, ctx: cmds.Context):
        try:
            with open(CONFIG_PATH, 'rb') as f:
                f.seek(0, os.SEEK_END)
                filesize = f.tell()
                bot_logger.info(f"Length of '{CONFIG_PATH}': {filesize}")
                f.seek(0)

                file = ds.File(f, filename="config")
                await ctx.send(file=file)
        except FileNotFoundError:
            bot_logger.error(f"File '{CONFIG}' doesn't exist!")
            await ctx.send("ERROR: Cannot find a valid config file in CWD...", silent=True)

    @cmds.command("chan_id", help="Gets the id of the channel.", usage="chan_id")
    async def chan_id(self, ctx: cmds.Context) -> None:
        # TODO: Add this as a check for all commands?
        if ctx.author == bot.user:
            return
        channel_name: str = "Look at the client"
        if isinstance(ctx.channel, ds.TextChannel):
            channel_name = ctx.channel.name

        bot_logger.info(f"Channel id for '{channel_name}': {ctx.channel.id}")
        await ctx.send(f"{ctx.channel.id}")

##################################################


@bot.event
async def on_member_join(member: ds.Member):
    bot_logger.info(f"New user joined to guild '{member.name}'")

    embed = ds.Embed(title="Greetings")
    embed.description = "What's up nigger"

    await member.send(embed=embed, mention_author=True)

# TODO: Documentation says this event may be called more than once, do we care about that?
@bot.event
async def on_ready():
    bot_logger.info(f'{bot.user} logged in!')

    global bot_state
    # NOTE: Hard-coded guild and channel ids of my private server...
    SPAWN_GUILD_ID: int = 906230633540485161
    SPAWN_CHANNEL_ID: int = 1319686983131467946
    spawn_guild_idx: int = -1
    spawn_channel_idx: int = -1
    try:
        spawn_guild_idx = bot.guilds.index(bot.get_guild(SPAWN_GUILD_ID))
    except ValueError:
        bot_logger.warning(f"Spawn Guild with id'{SPAWN_GUILD_ID}' not found!")

    try:
        spawn_channel_idx = bot.guilds[spawn_guild_idx].text_channels.index(cast(ds.TextChannel, bot.get_channel(SPAWN_CHANNEL_ID)))
    except ValueError:
        bot_logger.warning(f"Spawn Channel with id'{SPAWN_CHANNEL_ID}' not found!")

    if spawn_guild_idx != -1 and spawn_channel_idx != -1:

        bot_state = BotState(bot, spawn_guild_idx, spawn_channel_idx)
        guild: ds.Guild = bot.guilds[spawn_guild_idx]
        channel: ds.TextChannel = guild.text_channels[spawn_channel_idx]
        bot_logger.info(f"Bot spawned in '{channel.name}' of guild '{guild.name}'")
        await channel.send("Spawned!", delete_after=10.0)

    for g in bot.guilds:
        bot_logger.info(f"    - Bot in {g.name} with id {g.id}")

@bot.event
async def on_message(msg):
    if msg.author == bot.user:
        return

    if msg.guild == None:
        logger.error("msg.guild == None in on_message(); This should not happen!")
        return

    text: str = f"[{msg.created_at}][{msg.guild.name}::{msg.channel.name}] {msg.author}: "
    if len(msg.content) > 0:
        text += f"'{msg.content}'"
        if len(msg.attachments) > 0:
            text += " With attachment(s):"
        for attachment in msg.attachments:
            text += "\n"
            text += f"{attachment.content_type}: {attachment.url}"
    else:
        if len(msg.attachments) > 0:
            text += "Sent attachment(s):"

            for attachment in msg.attachments:
                text += "\n"
                text += f"{attachment.content_type}: {attachment.url}"

    bot_logger.info(text)

    await bot.process_commands(msg)

async def add_cogs():
    coroutines = []
    coroutines.append(bot.add_cog(MiscCog(bot)))
    coroutines.append(bot.add_cog(BoopCog(bot)))
    coroutines.append(bot.add_cog(DevCog(bot)))

    tasks = [asyncio.create_task(coroutine) for coroutine in coroutines]

    await asyncio.gather(*tasks)

async def main():
    global MOMOYON_USER_ID

    await add_cogs()

    load_dotenv()
    token = os.environ["TOKEN"]

    if not MOMOYON_USER_ID:
        try:
            MOMOYON_USER_ID = int(os.environ["MOMOYON_USER_ID"])
        except Exception:
            logger.error("Please set `MOMOYON_USER_ID` envar!")
            exit(1)

    _tasks = []

    if RUN_DISCORD_BOT:
        await bot.login(token)
        _tasks.append(asyncio.create_task(bot.connect()))

    await bot.wait_until_ready()

    activity = ds.Activity(
        type=ds.ActivityType.watching,
        state="locked in",
        details="Watching Serial Experiments Lain",
        platform="NASA SuperComputer",
        start={"start": 0}
    )
    await bot.change_presence(status=None, activity=activity)

    await asyncio.sleep(1)
    com = bot_com.BotCom(bot, bot_state, 'bot.com')
    _tasks.append(com.start())

    await asyncio.gather(*_tasks)

if __name__ == '__main__':
    config = read_config(CONFIG_PATH)

    try:
        asyncio.run(main())
    except KeyboardInterrupt as ki:
        exit(0)
