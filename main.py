#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Robert Dale (Mistyhands)
#
# This is a bot to manage the discord server for /r/vexillologycirclejerk.
# It also mirrors posts from that subreddit.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import asyncio
import pickle
import re
import signal
import sys
import toml
import os.path
import os
from discord.commands import Option, slash_command, message_command
from discord.ui import Button, View, Item
from tabnanny import check
import psutil
from discord.ext import tasks
import pathlib
from datetime import datetime
from collections import deque
import discord
import asyncpraw as praw
import asyncprawcore

global reddit, subreddit
subreddit = None

base_dir = str(pathlib.Path(__file__).parent.resolve()) + '/'
recent_posts_msgs = deque([])
VCJ_GUILD = 847495460385849384

cfg = ""
with open(base_dir + "config.toml") as t:
    cfg = toml.loads(t.read())


class ChannelNotFound(Exception):
    """Exception for not finding a channel ID.
    """
    pass


class Channels():
    """Named Discord channels to post to.
    """
    TESTING = 929365821908738080
    REDDIT_POSTS = 939616386962030592
    BOT_DEBUG = 939571508467073044
    MISTYHANDS = 240903336717582337
    BANS = 939598756523933777
    MOD_ONLY = 939615965140893766


class Roles():
    MODERATOR = 939571086562050119


def post_is_new(post_id: str) -> bool:
    """Check whether a reddit post has already been posted by the Discord bot.

    Args:
        `post_id` (`str`): the reddit post ID

    Returns:
        `bool`: whether the post has been posted
    """
    for r_id, d_id in list(recent_posts_msgs):
        if r_id == post_id or d_id == post_id:
            return False
    return True


def get_recent_entry(index: int) -> tuple:
    """Get a tuple of (`reddit id`, `discord message id`)

    Args:
        index (int): which index of `recent_posts_msgs` to get

    Returns:
        tuple: the entry
    """
    return recent_posts_msgs[index]


def remember(post: praw.models.Submission, message: discord.Message):
    """Persist a post ID and message ID so we can
    * update the score in the message
    * not submit the same post twice

    Args:
        `post` (`praw.models.Submission`): the reddit post
        `message` (`discord.Message`): the discord message of the reddit post
    """
    if len(recent_posts_msgs) > 50:
        recent_posts_msgs.popleft()

    post_message_tuple = (post.id, message.id)
    if post_message_tuple not in recent_posts_msgs:
        recent_posts_msgs.append(post_message_tuple)
    store()


def store():
    """Serialise the current state to a persistent file.
    """
    fname = base_dir + 'data.bin'
    with open(fname, 'wb') as f:
        pickle.dump(recent_posts_msgs, f)


def load():
    """Load our state from the last session.
    """
    global recent_posts_msgs
    fname = base_dir + 'data.bin'
    if os.path.isfile(fname):
        with open(fname, 'rb') as f:
            recent_posts_msgs = pickle.load(f)
    else:
        print("No persistent storage exists. Didn't load.")


async def submission_from_id(post_id: str) -> praw.models.Submission:
    """Get praw submission object from reddit post ID.

    Args:
        `post_id` (`str`): the reddit post ID

    Returns:
        `praw.models.Submission`: the corresponding submission
    """
    try:
        post = await reddit.submission(id=post_id)
        return post
    except Exception as exception:
        print(
            f"Failed to fetch a post by ID {post_id}: \n\t{str(exception)}\n")
        return None


def extract_url(input_string: str) -> str:
    """Extract the first URL from a string, or an empty string if
    no url found.

    Args:
        `input_string` (str): the string to search

    Returns:
        `str`: the extracted string, or an empty string
    """
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, input_string)
    return url[0][0] if url else ""


class BannedUserButtonView(discord.ui.View):
    def __init__(self):
        # making None is important if you want the button work after restart!
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.red, custom_id="user_appeal:deny", label="Confirm", emoji='❌'
    )
    async def deny_appeal(self, button, interaction: discord.Interaction):
        m: discord.Message = interaction.message
        emb = interaction.message.embeds[0]
        emb = "Ban (confirmed)"
        await interaction.response.edit_message(view=None, embed=emb)

    @discord.ui.button(
        style=discord.ButtonStyle.green, custom_id="user_appeal:approve", label="Unban user", emoji='✔️'
    )
    async def approve_appeal(self, button, interaction):
        m: discord.Message = interaction.message.content
        u_id = int(m.split('\n')[-1])
        u = await client.fetch_user(u_id)
        g: discord.Guild = client.get_guild(VCJ_GUILD)
        await g.unban(u)
        emb = interaction.message.embeds[0]
        emb.title = 'Unbanned'
        emb.colour = discord.Colour.dark_green()
        await interaction.response.edit_message(content="User unbanned.\nMake sure to notify them.", view=None, embed=emb)


class KeisatsuBot(discord.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        load()
        print(recent_posts_msgs)
        self.update_post_scores.start()
        self.check_memory_usage.start()
        self.check_new_posts.start()

        self.persistent_views_added = False

    def _gen_embed(self, reddit_post: praw.models.Submission) -> discord.Embed:
        """Generate the embed for post notifications.

        Args:
            `reddit_post`: the post to generate the embed for

        Returns:
            `discord.Embed`: the complete embed
        """
        img = reddit_post.url

        if reddit_post.selftext:
            img = extract_url(reddit_post.selftext)

        if reddit_post.over_18:
            colour = discord.Colour.brand_red()
            img = "https://www.redditstatic.com/interstitial-image-over18.png"
        else:
            colour = discord.Colour.og_blurple()

        date_string = datetime.utcfromtimestamp(
            reddit_post.created_utc).strftime("%H:%M %a %-d %b, %Y")
        embed = discord.Embed(
            title=reddit_post.title,
            colour=colour,
            url=f"https://reddit.com{reddit_post.permalink}"
        )

        try:
            avatar = reddit_post.author.icon_img
        except:
            avatar = None

        if avatar:
            embed.set_author(
                name=f'/u/{reddit_post.author.name}', icon_url=avatar)
        else:
            embed.set_author(name=f'/u/{reddit_post.author.name}')
        embed.set_thumbnail(url=img)
        embed.add_field(name="Submitted", value=date_string)
        embed.add_field(name="Upvotes", value=reddit_post.score)
        embed.set_footer(text=f"{reddit_post.upvote_ratio * 100}% upvoted")
        return embed

    async def on_ready(self):
        self.add_view(BannedUserButtonView())
        await self.get_channel(Channels.BOT_DEBUG).send(f"Bot started.")
        print(f"Connected: {self.user}")

        self.persistent_views_added = True

    async def submit_post(self, post: praw.models.Submission):
        embed = self._gen_embed(post)
        return await self.get_channel(Channels.REDDIT_POSTS).send(embed=embed)

    async def _message_from_id(self, message_id: int, channel_id: int) -> discord.Message:
        try:
            ch = self.get_channel(channel_id)
            if not ch:
                raise(ChannelNotFound(f"Couldn't find channel: {channel_id}"))
            msg = await ch.fetch_message(message_id)
            return msg
        except ChannelNotFound as e:
            print(f"Invalid channel ID!")
            return None
        except discord.NotFound as e:
            print(f"Invalid message ID!")
            return None

    async def autoban_user(self, user: discord.Member, reason: str):
        u: discord.Member = user

        view = BannedUserButtonView()

        embed = discord.Embed(
            title="Ban",
            colour=discord.Colour.brand_red(),
        )

        if u.avatar is not None:
            embed.set_author(
                name=f'{u.name}#{u.discriminator}', icon_url=u.avatar.url)
        else:
            embed.set_author(name=f'{u.name}#{u.discriminator}')
        embed.add_field(name="Reason", value=reason)
        dt_string = datetime.now().strftime("%H:%M %a %-d %b, %Y")
        embed.set_footer(text=f"Time: {dt_string}")

        ch_bans = client.get_channel(Channels.BANS)
        await ch_bans.send(view=view, embed=embed, content=f"ID:\n{u.id}")
        await user.send(f"You have been automatically banned.\nIf this was in error, you will be unbanned and notified.\n\nReason:\n{reason}")
        await user.ban(delete_message_days=3, reason=reason)

    @tasks.loop(hours=1)
    async def check_memory_usage(self):
        mem_mib = get_memory_use()
        if mem_mib > 256:
            await self.get_channel(Channels.BOT_DEBUG).send(f"<@{Channels.MISTYHANDS}> Memory usage high!  (`{mem_mib}MiB`)\nIs there a leak?")

    @tasks.loop(minutes=15)
    async def update_post_scores(self):
        print("Updating post messages.")
        for r_id, d_id in list(recent_posts_msgs):
            post: praw.models.Submission = await submission_from_id(r_id)
            message = await self._message_from_id(d_id, Channels.REDDIT_POSTS)

            if post and message:
                if (post.author is None) or not (post.is_robot_indexable):
                    await message.delete()
                    print(
                        f"Deleted message ID {message.id} due to removed reddit post {post.id}.")
                else:
                    await message.edit(embed=self._gen_embed(post))

    @tasks.loop(minutes=5)
    async def check_new_posts(self):
        print("Checking for posts.")
        try:
            subreddit = await reddit.subreddit("VexillologyCirclejerk")
            async for post in subreddit.new(limit=15):
                if post_is_new(post):
                    msg = await self.submit_post(post)
                    remember(post, msg)
        except asyncprawcore.exceptions.ResponseException:
            print("Reddit error.")

    @check_new_posts.before_loop
    async def before_checking_posts(self):
        await self.wait_until_ready()

    @check_memory_usage.before_loop
    async def before_checking_mem(self):
        await self.wait_until_ready()

    @update_post_scores.before_loop
    async def before_updating_scores(self):
        await self.wait_until_ready()


intents = discord.Intents.default()
intents.messages = True
client = KeisatsuBot(intents=intents)


def get_memory_use():
    proc = psutil.Process(os.getpid())
    mem_usage_mb = proc.memory_info().rss / pow(1024, 2)
    return round(mem_usage_mb)


@client.slash_command(guild_ids=[VCJ_GUILD], name="mod_help", description="Notify moderators privately for help.")
async def hello(
    ctx: discord.ApplicationContext,
    message: Option(str, "Enter your message to be forwarded privately."),
):
    u: discord.Member = ctx.author
    await client.get_channel(Channels.MOD_ONLY).send(f"<@{Roles.MODERATOR}>Request from {u.name}#{u.discriminator}:\n\n`{message.strip('`')}`")
    await ctx.respond(f"Your request has been forwarded privately.", ephemeral=True)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    their_message = message.content
    word = ""
    for word in cfg["options"]["badwords"]:
        if word.lower() in their_message.lower():
            await client.autoban_user(message.author, f"Message contained: `{word.lower()}` in `{their_message}`.")
            break


reddit = praw.Reddit(
    client_id=cfg["keys"]["reddit_id"],
    client_secret=cfg["keys"]["reddit_secret"],
    user_agent="/r/vexillologycirclejerk post scraper",
)


client.run(cfg["keys"]["discord"])
