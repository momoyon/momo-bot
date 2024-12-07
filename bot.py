import discord as ds
from discord import FFmpegPCMAudio
import discord.ext.commands as cmds
import sys, time, os, random
import yt_dlp
from typing import *
from dotenv import load_dotenv

import logging

running = True

FFMPEG_OPTS = {'options': '-vn'}

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
    "logger": logging.Logger("yt_dlp")
}
queue : List[dict] = []
ytdlp = yt_dlp.YoutubeDL(options)

def log_info(msg: str):
    print(f"INFO: {msg}")

def log_error(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)

# TODO: check if file exists in disk
def is_video_downloaded(id: str) -> bool:
    checking_id = id
    try:
        with open(DOWNLOAD_ARCHIVE_PATH) as f:
            for line in f.read().split('\n'):
                if line.split(' ')[0] == checking_id:
                    return True
        return False

    except Exception as err:
        with open(DOWNLOAD_ARCHIVE_PATH, 'w') as f:
            pass
        log_info(f"Created download_archive: {DOWNLOAD_ARCHIVE_PATH}")
        return False

def download(link: str, title: str, id: str) -> bool:
    log_info(f"Trying to download '{link}'")
    try:
        ytdlp.download(link)
    except:
        log_error(f"Invalid youtube link '{link}'")
        return False

    with open(DOWNLOAD_ARCHIVE_PATH, 'a') as f:
        f.write(f"{id} {title}\n")
    log_info(F"Downloaded {title}...")
    return True

intents = ds.Intents.default()
intents.message_content = True
# intents.manage_messages = True

bot = cmds.Bot('!!', intents=intents)

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
    log_info(f"[{msg.guild.name}::{msg.channel.name}]{msg.author}: '{msg.content}'")
    await bot.process_commands(msg)

@bot.command("poop", help="Command for testing if the bot is online; bot should reply with 'pong!'")
async def poop(ctx):
    if ctx.author == bot.user:
        return
    await ctx.reply("Shit yourself nigger")

@bot.command("ping", help="Command for testing if the bot is online; bot should reply with 'pong!'")
async def ping(ctx):
    if ctx.author == bot.user:
        return
    await ctx.channel.send("pong!")

@bot.command("play", help="Play youtube videos; Only certain videos are playable because i have to download the whole file to play it... (i dont have infinite storage)")
async def play(ctx, *args):
    if (len(args) < 1):
        await ctx.send("ERROR: Please provide the youtube link of the song!", delete_after=5.0, silent=True)
        return

    link = args[0]

    if not ctx.author.voice:
        await ctx.send("Please join a Voice Channel and run the command!", silent=True)
        return

    try:
        info_dict = ytdlp.extract_info(link, download=False)
    except yt_dlp.utils.DownloadError:
        log_error(f"Invalid youtube link '{link}'")
        await ctx.send(f"ERROR: Invalid youtube link '{link}'")
        return
    id = info_dict["id"]
    title = info_dict["title"]

    # Download if not cached
    if not is_video_downloaded(id):
        await ctx.send("Song is not cached, downloading...", silent=True)
        log_info("Song is not cached, downloading...")
        if not download(link, title, id):
            await ctx.send(f"Invalid youtube link '{link}'", silent=True)
            return
    else:
        # await ctx.send("Song is cached, playing...", delete_after=10.0, silent=True)
        log_info("Song is cached, playing...")

    # make the bot join vc
    if not ctx.guild.voice_client: # error would be thrown if bot already connected, this stops the error
        player = await ctx.author.voice.channel.connect()
    else:
        player = ctx.guild.voice_client

    src = f"{DOWNLOAD_PATH}{id}.mp3"

    queue.insert(0, {"info": info_dict, "link": link})

    if player.is_playing():
        assert(len(queue) >= 2)
        await ctx.send(f"Song already playing, added to queue", silent=True)
    else:
        log_info(f"Playing '{title}'...")
        await ctx.send(f"Playing '{title}'...", silent=True)

        try:
            player.play(FFmpegPCMAudio(src, **FFMPEG_OPTS), after=lambda e: stop(ctx))
        except Exception as err:
            log_error(f"{err}")
            return

@bot.command("stop", help="Stops the currently playing song, if any.")
async def stop(ctx):
    if ctx.guild.voice_client:
        ctx.guild.voice_client.stop()
        if len(queue) > 0:
            top = queue.pop()
            title = top["info"]["title"]
            await ctx.send(f"Stopped playing '{title}'...", delete_after=10.0, silent=True)
        if len(queue) <= 0:
            await ctx.send("No song left in queue, leaving VC", delete_after=10.0, silent=True)
            await ctx.guild.voice_client.disconnect()
        else:
            await ctx.send("Playing next song in queue...", delete_after=10.0, silent=True)
            next_song_link = queue[0]["link"]
            await play(ctx, next_song_link)
    else:
        await ctx.send(f"No song is playing!", delete_after=10.0, silent=True)

@bot.command("pause", help="Paused the currently playing song, if any.")
async def pause(ctx):
    if ctx.guild.voice_client:
        assert(len(queue) > 0)
        if not ctx.guild.voice_client.is_playing():
            await ctx.send("The song is already paused dummy!", delete_after=10.0, silent=True)
        else:
            ctx.guild.voice_client.pause()
            title = queue[0]["info"]["title"]
            await ctx.send(f"Paused {title}...", delete_after=10.0, silent=True)
    else:
        await ctx.send(f"No song is currently playing", delete_after=10.0, silent=True)

@bot.command("resume", help="Resumes the currently paused song, if any.")
async def resume(ctx):
    if ctx.guild.voice_client:
        assert(len(queue) > 0)
        if ctx.guild.voice_client.is_playing():
            await ctx.send("The song is already playing dummy!", delete_after=10.0, silent=True)
        else:
            ctx.guild.voice_client.resume()
            title = queue[0]["info"]["title"]
            await ctx.send(f"Resumed {title}...", delete_after=10.0, silent=True)
    else:
        await ctx.send(f"No song is currently paused/playing", delete_after=10.0, silent=True)

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
        await msg.channel.send(content=f"{msg.author.mention} shared {convert_insta_reel_link(msg.content)}")
        await ctx.message.delete()

KYS_REPONSES = [
        "Wai-",
        "Fuck yo-",
        "Nig-",
        "AARGh-",
        ":skull:",
        ]
@bot.command("kys", help="I will KYS :)")
async def kys(ctx):
    await ctx.send(random.choice(KYS_REPONSES))
    running = False
    await ctx.bot.close()

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

def main():
    load_dotenv()
    token = os.environ["TOKEN"]
    bot.run(token)

if __name__ == '__main__':
    main()
    # p = mp.Process(target=main)
    # p.start()
    # pipe_eater()
    # p.join()
