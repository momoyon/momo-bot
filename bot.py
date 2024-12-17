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

# TODO: Get this file's name dynamically instead of hardcoding.
SOURCE_CODE_FILENAME="bot.stable.py"

# TODO: Use Context.current_parameter, etc for parsing of arguments
# TODO: Remove song from queue when current song ends; Have to !!stop to remove from queue rn.
# TODO: Implement something on on_member_join
# TODO: Look at 'https://github.com/yt-dlp/yt-dlp/wiki/FAQ'
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

    @cmds.command("ping", help="Command for testing if the bot is online; bot should reply with 'pong!'")
    async def ping(self, ctx):
        if ctx.author == bot.user:
            return
        await ctx.channel.send("pong!")

    @cmds.command("src", help="Prints the source code for this bot.")
    async def src(self, ctx):
        if ctx.author == bot.user:
            return

        try:
            with open(SOURCE_CODE_FILENAME, 'rb') as f:
                f.seek(0, os.SEEK_END)
                filesize = f.tell()
                my_logging.bot_info(f"Length of '{SOURCE_CODE_FILENAME}': {filesize}")
                f.seek(0)

                # Send file in chunks as a message
                # await ctx.send("`", silent=True)
                # while f.tell() < filesize:
                #     chunk: str = f.read(MIN_HTTP_BODY_LEN).decode('utf-8')
                #     my_logging.bot_info(f"Read {len(chunk)} bytes")
                #     await ctx.send(chunk, silent=True)
                # await ctx.send("`", silent=True)


                # Send the whole file as a file
                file = ds.File(f, filename=SOURCE_CODE_FILENAME)
                await ctx.send(file=file)
        except FileNotFoundError:
            my_logging.bot_error(f"File '{SOURCE_CODE_FILENAME}' doesn't exist!")
            my_logging.bot_info("Please run build.sh to copy bot.py -> bot.stable.py")
            await ctx.send("ERROR: It seems like i was deployed improperly...", silent=True)



    @cmds.command("poop", help="Command for testing if the bot is online; bot should reply with 'pong!'")
    async def poop(self, ctx):
        if ctx.author == bot.user:
            return
        await ctx.reply("Shit yourself nigger")

    @cmds.command("av", help="Displays the given user's avatar.")
    async def av(self, ctx, *args):
        if ctx.author == bot.user:
            return
        if len(args) < 1:
            await ctx.send("ERROR: Please provide the user to display the avatar!", delete_after=5.0, silent=True)
            return

        user_id = args[0]

        # renove non-digits
        user_id = user_id.removeprefix('<')
        user_id = user_id.removeprefix('@')
        user_id = user_id.removesuffix('>')

        # convert user id from str -> int
        user_id = int(user_id)

        my_logging.bot_info(f"fetching {user_id}...")

        user = await bot.fetch_user(user_id)

        my_logging.bot_info(f"fetched {user}")

        my_logging.bot_info(f"avatar for {user}: {user.display_avatar}")

        await ctx.send(user.display_avatar)

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

    async def play_audio(self, ctx, player: ds.VoiceClient, info_dict):
        title: str = info_dict['title']
        my_logging.bot_info(f"Playing '{title}'...")
        await ctx.send(f"Playing '{title}'...", silent=True)

        try:
            player.play(FFmpegPCMAudio(info_dict["url"], options="-vn"))
        except Exception as err:
            await ctx.send(f"ERROR: Failed to play {title}: {err}", silent=True)
            my_logging.bot_error(f"{err}")
            return

    @cmds.command("queue", help="Lists the songs in the queue.")
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
    @cmds.command("play", help="Play youtube videos")
    async def play(self, ctx, *args):
        async with ctx.typing():
            if (len(args) < 1):
                await ctx.send("ERROR: Please provide the youtube link of the song!", silent=True)
                return

            link = args[0]

            if not ctx.author.voice:
                await ctx.send("Please join a Voice Channel and run the command!", silent=True)
                return

            try:
                info_dict = self.ytdlp.extract_info(link, download=False)
            except yt_dlp.utils.UnsupportedError:
                my_logging.bot_error(f"Invalid youtube link '{link}'")
                await ctx.send(f"ERROR: Invalid youtube link '{link}'", silent=True)
                return

            id = info_dict["id"]
            title = info_dict["title"]

            # The song is in the queue
            for m in self.music_queue:
                if title == m['info']['title']:
                    await ctx.send("Song is already in the queue!", silent=True)
                    return

            # make the bot join vc
            if not ctx.guild.voice_client: # error would be thrown if bot already connected, this stops the error
                player: ds.VoiceClient = await ctx.author.voice.channel.connect()
            else:
                player: ds.VoiceClient = ctx.guild.voice_client

            if player.is_playing():
                assert(len(self.music_queue) > 0)

                await ctx.send(f"Another song is already playing, added to queue", silent=True)
                self.music_queue.append({"info": info_dict, "link": link})
            else:
                self.music_queue.insert(0, {"info": info_dict, "link": link})

                await self.play_audio(ctx, player, info_dict)

    @cmds.command("stop", help="Stops the currently playing song, if any.")
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
                await play(self, ctx, next_song_link)
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

    @cmds.command("pause", help="Paused the currently playing song, if any.")
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

    @cmds.command("resume", help="Resumes the currently paused song, if any.")
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


    @cmds.command("marisad", help="Marisa. 1% Chance for something special :D")
    async def marisad(self, ctx):
        # TODO: Make it so we dynamically search "marisad" on tenor and pick a random link
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            if random.random() <= 0.1:
                await ctx.send('https://cdn.discordapp.com/attachments/906230633540485164/1316329779624153118/caption.gif?ex=675aa723&is=675955a3&hm=1826753181d4dc7bb5bd79442b2a74b824fee9b7c03ea1242a5386612e3e74aa&')
            else:
                await ctx.send(random.choice(self.MARISAD_GIFS))


class DevCog(cmds.Cog, name='Dev'):
    def __init__(self, bot):
        self.bot = bot

    @cmds.command("kys", help="I will KYS :)")
    async def kys(self, ctx):
        KYS_REPONSES = [
                "Wai-",
                "Fuck yo-",
                "Nig-",
                "AARGh-",
                ":skull:",
        ]
        if ctx.author.name != '.momoyon':
            await ctx.send("What about *YOU* kys?")
            return
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
    my_logging.bot_info(f"[{msg.created_at}][{msg.guild.name}::{msg.channel.name}] {msg.author}: '{msg.content}'")
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
