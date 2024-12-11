import discord as ds
from discord import FFmpegPCMAudio
import discord.ext.commands as cmds
import sys, time, os, random
import yt_dlp
from typing import *
from dotenv import load_dotenv
import asyncio
import coloredlogs, logging

logging.basicConfig(level=logging.DEBUG)

coloredlogs.install()
logger: logging.Logger = logging.getLogger("bot")

running = True

FFMPEG_OPTS = {'options': '-vn'}

MIN_HTTP_BODY_LEN=2000

# TODO: Get this file's name dynamically instead of hardcoding.
SOURCE_CODE_FILENAME="bot.stable.py"

# TODO: Use Context.current_parameter, etc for parsing of arguments
# TODO: Remove song from queue when current song ends; Have to !!stop to remove from queue rn.
# TODO: Implement something on on_member_join

DOWNLOAD_PATH = "./songs/"
DOWNLOAD_ARCHIVE_PATH = f".download_archive"
options = {
    "outtmpl": f"{DOWNLOAD_PATH}%(id)s.mp3",
    "format": "bestaudio",
    "cookiefile": "cookies.txt",
    # "extract_audio": True,
    "windowsfilenames": False,
    "overwrites": True,
    "cachedir": f"{DOWNLOAD_PATH}/cache",
    # "default_search": "auto",
    # "no_warnings": True,
    # "quiet": True,
    "logger": logging.getLogger("yt_dlp")
}
music_queue : List[dict] = []
ytdlp = yt_dlp.YoutubeDL(options)

def log_info(msg: str):
    logger.info(msg)
    # print(f"INFO: {msg}")

def log_error(msg: str):
    logger.error(msg)
    # print(f"ERROR: {msg}", file=sys.stderr)

# Helpers
async def play_audio(ctx, player, title: str, id: str):
    log_info(f"Playing '{title}'...")
    await ctx.send(f"Playing '{title}'...", silent=True)

    try:
        src = f"{DOWNLOAD_PATH}{id}.mp3"
        player.play(FFmpegPCMAudio(src, **FFMPEG_OPTS))
    except Exception as err:
        await ctx.send(f"ERROR: Failed to play {title}: {err}", silent=True)
        log_error(f"{err}")
        return


# TODO: check if file exists in disk
def is_video_downloaded(id: str) -> bool:
    checking_id = id
    try:
        with open(DOWNLOAD_ARCHIVE_PATH) as f:
            for line in f.read().split('\n'):
                if line.split(' ')[0] == checking_id:
                    return True
        return False

    except Exception:
        with open(DOWNLOAD_ARCHIVE_PATH, 'w') as f:
            pass
        log_info(f"Created download_archive: {DOWNLOAD_ARCHIVE_PATH}")
        return False

def download(link: str, title: str, id: str) -> bool:
    log_info(f"Trying to download '{link}'")
    try:
        ytdlp.download(link)
    except yt_dlp.utils.DownloadError:
        log_error(f"Invalid youtube link '{link}'")
        return False
    with open(DOWNLOAD_ARCHIVE_PATH, 'a') as f:
        f.write(f"{id} {title}\n")
    log_info(F"Downloaded {title}...")
    return True

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
                filesize: int = f.tell()
                log_info(f"Length of '{SOURCE_CODE_FILENAME}': {filesize}")
                f.seek(0)

                # Send file in chunks as a message
                # await ctx.send("`", silent=True)
                # while f.tell() < filesize:
                #     chunk: str = f.read(MIN_HTTP_BODY_LEN).decode('utf-8')
                #     log_info(f"Read {len(chunk)} bytes")
                #     await ctx.send(chunk, silent=True)
                # await ctx.send("`", silent=True)


                # Send the whole file as a file
                file = ds.File(f, filename=SOURCE_CODE_FILENAME)
                await ctx.send(file=file)
        except FileNotFoundError:
            log_error(f"File '{SOURCE_CODE_FILENAME}' doesn't exist!")
            log_info("Please run build.sh to copy bot.py -> bot.stable.py")
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

        log_info(f"fetching {user_id}...")

        user: user = await bot.fetch_user(user_id)

        log_info(f"fetched {user}")

        log_info(f"avatar for {user}: {user.display_avatar}")

        await ctx.send(user.display_avatar)

class MusicCog(cmds.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot

    @cmds.command("queue", help="Lists the songs in the queue.")
    async def queue(self, ctx):
        if ctx.author == bot.user:
            return

        if len(music_queue) <= 0:
            await ctx.send("Music queue is empty!", silent=True)
            return

        msg: str = "Music: Queue: "
        for m in music_queue:
            msg += f"\n- {m['info']['title']}"

        await ctx.send(msg, silent=True)

    # TODO: Find a way to check if the supplied song is already in the queue WITHOUT querying for the video info because that takes time.
    @cmds.command("play", help="Play youtube videos; Only certain videos are playable because i have to download the whole file to play it... (i dont have infinite storage)")
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
                info_dict = ytdlp.extract_info(link, download=False)
            except yt_dlp.utils.DownloadError:
                log_error(f"Invalid youtube link '{link}'")
                await ctx.send(f"ERROR: Invalid youtube link '{link}'", silent=True)
                return
            id = info_dict["id"]
            title = info_dict["title"]

            # The song is in the queue
            for m in music_queue:
                if title == m['info']['title']:
                    await ctx.send("Song is already in the queue!", silent=True)
                    return

            # make the bot join vc
            if not ctx.guild.voice_client: # error would be thrown if bot already connected, this stops the error
                player = await ctx.author.voice.channel.connect()
            else:
                player = ctx.guild.voice_client

            if player.is_playing():
                assert(len(music_queue) > 0)

                await ctx.send(f"Another song is already playing, added to queue", silent=True)
                music_queue.append({"info": info_dict, "link": link})
            else:
                # Download if not cached
                if not is_video_downloaded(id):
                    await ctx.send("Song is not cached, downloading...", silent=True)
                    log_info("Song is not cached, downloading...")
                    if not download(link, title, id):
                        await ctx.send(f"ERROR: Invalid youtube link '{link}'", silent=True)
                        log_info(f"ERROR: Invalid youtube link '{link}'")
                        return

                music_queue.insert(0, {"info": info_dict, "link": link})

                await play_audio(self, ctx, player, title, id)

    @cmds.command("stop", help="Stops the currently playing song, if any.")
    async def stop(self, ctx):
        if ctx.guild.voice_client:
            ctx.guild.voice_client.stop()
            if len(music_queue) > 0:
                log_info("MUSIC POPPED FROM QUEUE in stop")
                top = music_queue.pop()
                title = top["info"]["title"]
                await ctx.send(f"Stopped playing '{title}'...", silent=True)
            if len(music_queue) <= 0:
                await ctx.send("No song left in queue, leaving VC", silent=True)
                await ctx.guild.voice_client.disconnect()
            else:
                await ctx.send("Playing next song in queue...", silent=True)
                next_song_link = music_queue[0]["link"]
                await play(self, ctx, next_song_link)
        else:
            await ctx.send(f"No song is playing!", silent=True)

    @cmds.command("next", help="Skips the current song and plays the next song, if any.")
    async def next(self, ctx):
        if ctx.author == bot.user:
            return
        async with ctx.typing():
            async def no_next_song() -> bool:
                if len(music_queue) <= 0:
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

            log_info("MUSIC POPPED FROM QUEUE in next")
            current_song = music_queue.pop(0)['info']['title']
            log_info(f"Stopped playing {current_song}")

            if await no_next_song(): return

            next_song = music_queue[0]
            title: str = next_song['info']['title']
            id: str = next_song['info']['id']

            assert ctx.guild.voice_client
            player = ctx.guild.voice_client

            await play_audio(self, ctx, player, title, id)

    @cmds.command("pause", help="Paused the currently playing song, if any.")
    async def pause(self, ctx):
        if ctx.guild.voice_client:
            assert(len(music_queue) > 0)
            if not ctx.guild.voice_client.is_playing():
                await ctx.send("The song is already paused dummy!", delete_after=10.0, silent=True)
            else:
                ctx.guild.voice_client.pause()
                title = music_queue[0]["info"]["title"]
                await ctx.send(f"Paused {title}...", delete_after=10.0, silent=True)
        else:
            await ctx.send(f"No song is currently playing", delete_after=10.0, silent=True)

    @cmds.command("resume", help="Resumes the currently paused song, if any.")
    async def resume(self, ctx):
        if ctx.guild.voice_client:
            # Disconnect from VC instead of asserting
            assert(len(music_queue) > 0)
            if ctx.guild.voice_client.is_playing():
                await ctx.send("The song is already playing dummy!", delete_after=10.0, silent=True)
            else:
                ctx.guild.voice_client.resume()
                title = music_queue[0]["info"]["title"]
                await ctx.send(f"Resumed {title}...", delete_after=10.0, silent=True)
        else:
            await ctx.send(f"No song is currently paused/playing", delete_after=10.0, silent=True)


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
        running = False
        await ctx.bot.close()


##################################################

def is_already_ddd_converted_link(msg_content: str) -> bool:
    return msg_content.find('d.ddinstagram') >= 0

def convert_insta_reel_link(msg_content: str) -> str:
    msg_content = msg_content.replace('www.', '')
    insta_id: int = msg_content.find('instagram')
    assert(insta_id >= 0)
    return msg_content.replace('instagram', 'd.ddinstagram')

def is_insta_reel_link(msg_content: str) -> bool:
    return msg_content.find('instagram') >= 0 and msg_content.find('reel') >= 0

@bot.event
async def on_ready():
    log_info(f'{bot.user} logged in!')

@bot.event
async def on_message(msg):
    if msg.author == bot.user:
        return
    if is_insta_reel_link(msg.content):
        if not is_already_ddd_converted_link(msg.content):
            await msg.reply(content=f"{msg.author.mention} shared {convert_insta_reel_link(msg.content)}")

    # TODO: Handle msg.guild == None case
    log_info(f"[{msg.created_at}][{msg.guild.name}::{msg.channel.name}] {msg.author}: '{msg.content}'")
    await bot.process_commands(msg)

# TODO: Make it so we dynamically search "marisad" on tenor and pick a random link
MARISAD_GIFS = [
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
@bot.command("marisad", help="Marisa. 1% Chance for something special :D")
async def marisad(ctx):
    if ctx.author == bot.user:
        return
    async with ctx.typing():
        if random.random() <= 0.1:
            await ctx.send('https://cdn.discordapp.com/attachments/906230633540485164/1316329779624153118/caption.gif?ex=675aa723&is=675955a3&hm=1826753181d4dc7bb5bd79442b2a74b824fee9b7c03ea1242a5386612e3e74aa&')
        else:
            await ctx.send(random.choice(MARISAD_GIFS))

@bot.command("ddinsta", help="Diddify a instagram reel link with the provided message id.")
async def ddinsta(ctx):
    ref = ctx.message.reference
    if not ref:
        await ctx.send("ERROR: Please reply to the message you want to diddify!", silent=True)
        return

    msg = await ctx.fetch_message(ref.message_id)
    if is_already_ddd_converted_link(msg.content):
        await ctx.send("That is already a diddy link nigger", silent=True)
        return
    else:
        await msg.channel.send(content=f"{msg.author.mention} shared {convert_insta_reel_link(msg.content)}", silent=True)
        await ctx.message.delete()

# PIPE_FILE="./bot.pipe"
# def pipe_eater():
#     while running:
#         time.sleep(1)
#         try:
#             with open(PIPE_FILE) as pipe:
#                 line = pipe.readline()
#                 line.strip()
#                 if len(line) > 0:
#                     print(f"[PIPE] {line}")
#             with open(PIPE_FILE, mode='w') as pipe:
#                 pass
#         except FileNotFoundError:
#             with open(PIPE_FILE, mode='w') as pipe:
#                 pass


async def add_cogs():
    await bot.add_cog(MiscCog(bot))
    await bot.add_cog(MusicCog(bot))
    await bot.add_cog(DevCog(bot))

def main():
    asyncio.run(add_cogs())

    load_dotenv()
    token = os.environ["TOKEN"]
    bot.run(token)

if __name__ == '__main__':
    main()
    # p = mp.Process(target=main)
    # p.start()
    # pipe_eater()
    # p.join()
