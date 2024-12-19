import discord as ds
from discord import FFmpegPCMAudio
import discord.ext.commands as cmds
import sys, time, os, random
import yt_dlp
from typing import *
from dotenv import load_dotenv
import asyncio

import my_logging

my_logging.init()

MIN_HTTP_BODY_LEN=2000

SOURCE_CODE_FILENAME=f"{os.path.splitext(os.path.basename(__file__))[0]}.stable.py"

# TODO: Remove song from queue when current song ends; Have to !!stop to remove from queue rn.
# TODO: Implement something on on_member_join
# TODO: Implement command parsing on_message_edit

# Helpers
intents = ds.Intents.default()
intents.members = True
intents.message_content = True
# intents.manage_messages = True

bot = cmds.Bot('!!', intents=intents)

# COGS ###########################################
class MiscCog(cmds.Cog, name="Miscellaneous"):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command
        embed = ds.Embed(title="Error")
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original
        embed.description = f"Error: {error}"

        embed.description += f"\nUsage: {ctx.command.usage}"
        my_logging.bot_error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)

    @cmds.command("swapcase", help="Inverts the case of the input.", usage="swap <text>")
    async def swapcase(self, ctx: cmds.Context, *, text: str):
        if ctx.author == bot.user:
            return
        await ctx.send(text.swapcase())

    @cmds.command("ping", help="Command for testing if the bot is online; bot should reply with 'pong!'", usage="ping")
    async def ping(self, ctx):
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
                my_logging.bot_info(f"Length of '{SOURCE_CODE_FILENAME}': {filesize}")
                f.seek(0)

                # Send the whole file as a file
                file = ds.File(f, filename=SOURCE_CODE_FILENAME)
                await ctx.send(file=file)
        except FileNotFoundError:
            my_logging.bot_error(f"File '{SOURCE_CODE_FILENAME}' doesn't exist!")
            my_logging.bot_info("Please run build.sh to copy bot.py -> bot.stable.py")
            await ctx.send("ERROR: It seems like i was deployed improperly...", silent=True)

    @cmds.command("poop", help="Hehe poop.", usage="poop")
    async def poop(self, ctx):
        if ctx.author == bot.user:
            return
        await ctx.reply("Shit yourself nigger")

    @cmds.command("av", help="Displays the given user's avatar.", usage="av <member> [server_avatar = false]", aliases=["avatar"])
    async def av(self, ctx, member: ds.Member, server_avatar: bool = False):
        if ctx.author == bot.user:
            return

        if server_avatar:
            await ctx.send(member.display_avatar)
        else:
            await ctx.send(member.avatar)
    
class MusicCog(cmds.Cog, name="Music"):
    def __init__(self, bot) -> None:
        self.bot = bot
        yt_dlp_options: yt_dlp.YDLOpts = {
            "format": "bestaudio",
            "cookiefile": "cookies.txt",
            # "extract_audio": True,
            "windowsfilenames": False,
            "overwrites": True,
            # "default_search": "auto",
            # "no_warnings": True,
            # "quiet": True,
            "logger": my_logging.logging.getLogger("yt_dlp")
        }
        self.music_queue : List[dict] = []
        self.ytdlp = yt_dlp.YoutubeDL(yt_dlp_options)

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command

        embed = ds.Embed(title="Error")
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original
        if isinstance(error, yt_dlp.utils.UnsupportedError) or isinstance(error, yt_dlp.utils.DownloadError):
            embed.description = f"Error: That is not a valid youtube link!"
        else:
            embed.description = f"Error: {error}"

        embed.description += f"\nUsage: {ctx.command.usage}"
        my_logging.bot_error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)

    async def play_audio(self, ctx, player: ds.VoiceClient, info_dict):
        title: str = info_dict['title']
        my_logging.bot_info(f"Playing '{title}'...")
        await ctx.send(f"Playing '{title}'...", silent=True)

        player.play(FFmpegPCMAudio(info_dict["url"], options="-vn"))

    @cmds.command("queue", help="Lists the songs in the queue.", usage="queue")
    async def queue(self, ctx):
        if ctx.author == bot.user:
            return

        if len(self.music_queue) <= 0:
            await ctx.send("Music queue is empty!", silent=True)
            return

        msg: str = "Music: Queue: "
        for m in self.music_queue:
            msg += f"\n- {m['info']['title']}"

        await ctx.send(msg, silent=True)

    # TODO: Find a way to check if the supplied song is already in the queue WITHOUT querying for the video info because that takes time.
    @cmds.command("play", help="Play youtube videos", usage="play <youtube-link>")
    async def play(self, ctx, link: str):
        async with ctx.typing():
            if not ctx.author.voice:
                await ctx.send("Please join a Voice Channel and run the command!", silent=True)
                return

            info_dict = self.ytdlp.extract_info(link, download=False)

            id = info_dict["id"]
            title = info_dict["title"]

            # The song is in the queue
            for m in self.music_queue:
                if title == m['info']['title']:
                    await ctx.send("Song is already in the queue!", silent=True)
                    return

            # make the bot join vc
            player: ds.VoiceClient = ctx.guild.voice_client if ctx.guild.voice_client else await ctx.author.voice.channel.connect()

            if player.is_playing():
                assert(len(self.music_queue) > 0)

                await ctx.send(f"Another song is already playing, added to queue", silent=True)
                self.music_queue.append({"info": info_dict, "link": link})
            else:
                self.music_queue.insert(0, {"info": info_dict, "link": link})

                await self.play_audio(ctx, player, info_dict)

    @cmds.command("stop", help="Stops the currently playing song, if any.", usage="stop")
    async def stop(self, ctx):
        if ctx.guild.voice_client:
            ctx.guild.voice_client.stop()
            if len(self.music_queue) > 0:
                top = self.music_queue.pop()
                title = top["info"]["title"]
                await ctx.send(f"Stopped playing '{title}'...", silent=True)
            if len(self.music_queue) <= 0:
                await ctx.send("No song left in queue, leaving VC", silent=True)
                await ctx.guild.voice_client.disconnect()
            else:
                await ctx.send("Playing next song in queue...", silent=True)
                next_song_link = self.music_queue[0]["link"]
                await self.play(ctx, next_song_link)
        else:
            await ctx.send(f"No song is playing!", silent=True)

    @cmds.command("next", help="Skips the current song and plays the next song, if any.")
    async def next(self, ctx):
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            async def no_next_song() -> bool:
                if len(self.music_queue) <= 0:
                    if ctx.guild.voice_client:
                        await ctx.send("No song in queue; Exiting from VC", silent=True)
                        await ctx.guild.voice_client.disconnect()
                    else:
                        await ctx.send("No song in queue", silent=True)
                    return True
                else:
                    return False

            if await no_next_song(): return

            if not ctx.guild.voice_client:
                await ctx.send("No song is currently playing!", silent=True)
                return
            if ctx.guild.voice_client:
                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()

            current_song = self.music_queue.pop(0)['info']['title']
            my_logging.bot_info(f"Stopped playing {current_song}")

            if await no_next_song(): return

            next_song = self.music_queue[0]

            assert ctx.guild.voice_client
            player = ctx.guild.voice_client

            await self.play_audio(ctx, player, next_song['info'])

    @cmds.command("pause", help="Paused the currently playing song, if any.", usage="pause")
    async def pause(self, ctx):
        if ctx.guild.voice_client:
            assert(len(self.music_queue) > 0)
            if not ctx.guild.voice_client.is_playing():
                await ctx.send("The song is already paused dummy!", delete_after=10.0, silent=True)
            else:
                ctx.guild.voice_client.pause()
                title = self.music_queue[0]["info"]["title"]
                await ctx.send(f"Paused {title}...", delete_after=10.0, silent=True)
        else:
            await ctx.send(f"No song is currently playing", delete_after=10.0, silent=True)

    @cmds.command("resume", help="Resumes the currently paused song, if any.", usage="resume")
    async def resume(self, ctx):
        if ctx.guild.voice_client:
            # Disconnect from VC instead of asserting
            assert(len(self.music_queue) > 0)
            if ctx.guild.voice_client.is_playing():
                await ctx.send("The song is already playing dummy!", delete_after=10.0, silent=True)
            else:
                ctx.guild.voice_client.resume()
                title = self.music_queue[0]["info"]["title"]
                await ctx.send(f"Resumed {title}...", delete_after=10.0, silent=True)
        else:
            await ctx.send(f"No song is currently paused/playing", delete_after=10.0, silent=True)

class TouhouCog(cmds.Cog, name='Touhou'):
    def __init__(self, bot):
        self.bot = bot
        self.MARISAD_GIFS = [
                'https://tenor.com/view/marisa-kirisame-touhou-project-sad-crying-gif-24418828',
                'https://tenor.com/view/marisad-touhou-marisa-kirisame-sad-gif-20456205',
                'https://tenor.com/view/marisa-cry-spin-rain-touhou-gif-22503177',
                'https://media.tenor.com/eYM3tar4rtkAAAAM/marisa-touhou.gif',
                'https://tenor.com/view/touhou-touhou-project-2hu-marisa-marisa-kirisame-gif-22639972',
                'https://tenor.com/view/touhou-touhou-project-kirisame-marisa-marisa-kirisame-gif-11936097800016515634',
                'https://media.tenor.com/raHKUM94bmoAAAAM/marisa-marisa-fumo.gif',
                'https://media.tenor.com/I-eNMAa65gMAAAAM/marisad-potto.gif',
                'https://media.tenor.com/xMK8WwNBVuIAAAAM/marisa-marisakirisame.gif',
                'https://media.tenor.com/kZ2En0Slm28AAAAM/marisa-touhou.gif',
                'https://media.tenor.com/v5oS9ZOVq0cAAAAM/marisa-kirisame-touhou.gif',
        ]

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command

        embed = ds.Embed(title="Error")
        embed.description = ""
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original

        embed.description += f"\nUsage: {ctx.command.usage}"
        my_logging.bot_error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)


    @cmds.command("marisad", help="Marisa. 1% Chance for something special :D", usage="marisad")
    async def marisad(self, ctx: cmds.Context) -> None:
        # TODO: Make it so we dynamically search "marisad" on tenor and pick a random link
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            if random.random() <= 0.1:
                await ctx.send('https://tenor.com/view/bouncing-marisa-fumo-marisa-kirisame-touhou-fumo-gif-16962360816851147092')
            else:
                await ctx.send(random.choice(self.MARISAD_GIFS))

class DevCog(cmds.Cog, name='Dev'):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: cmds.Context): # type: ignore
        MOMOYON_USER_ID: int = int(os.environ["MOMOYON_USER_ID"])
        return ctx.author.id == MOMOYON_USER_ID

    async def cog_command_error(self, ctx: cmds.Context, error: Exception) -> None:
        assert type(ctx.command) == cmds.Command
        embed = ds.Embed(title="Error")
        if isinstance(error, cmds.CommandInvokeError):
            error = error.original
        embed.description = f"Error: {error}"

        embed.description += f"\nUsage: {ctx.command.usage}"
        momoyon: ds.User = await bot.fetch_user(int(os.environ["MOMOYON_USER_ID"]))
        await ctx.send(f"Only {momoyon.mention} can use dev commands")
        my_logging.bot_error(f"{self.qualified_name}Cog :: {type(error)}")
        await ctx.send(embed=embed)

    @cmds.command("kys", help="I will KYS :)", usage="kys")
    async def kys(self, ctx):
        KYS_REPONSES = [
                "Wai-",
                "Fuck yo-",
                "Nig-",
                "AARGh-",
                ":skull:",
        ]
        await ctx.send(random.choice(KYS_REPONSES))
        await ctx.bot.close()

##################################################

@bot.event
async def on_ready():
    my_logging.bot_info(f'{bot.user} logged in!')

@bot.event
async def on_message(msg):
    if msg.author == bot.user:
        return

    # TODO: Handle msg.guild == None case
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

    my_logging.bot_info(text)

    await bot.process_commands(msg)

async def add_cogs():
    await bot.add_cog(MiscCog(bot))
    await bot.add_cog(MusicCog(bot))
    await bot.add_cog(TouhouCog(bot))
    await bot.add_cog(DevCog(bot))

def main():
    asyncio.run(add_cogs())

    load_dotenv()
    token = os.environ["TOKEN"]
    bot.run(token, log_handler=None)

if __name__ == '__main__':
    main()
