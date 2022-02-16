#!/usr/bin/env python3
# -*- coding: utf-8 -*-#
# Copyright (c) 2022 Mistyhands
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
import sys
from time import time
import sys
from discord import Colour, Forbidden, HTTPException, Reaction
import toml
import os.path
import os
from discord.commands import Option
import psutil
from discord.ext import tasks
import pathlib
from datetime import datetime
from collections import deque
import discord
import asyncpraw as praw
import asyncprawcore
from data import Data

from ids import Channels, Roles, emoji_to_role

global reddit, subreddit
subreddit = None

base_dir = str(pathlib.Path(__file__).parent.resolve()) + '/'
recent_posts_msgs = deque([])
VCJ_GUILD = 847495460385849384
if '-t' in sys.argv:
    VCJ_GUILD = 929365821208272948

REACT_THRESHOLD = 5

cfg = ""

d = Data()

with open(base_dir + "config.toml") as t:
    cfg = toml.loads(t.read())


class ChannelNotFound(Exception):
    """Exception for not finding a channel ID.
    """
    pass


def post_is_new(post_id: str) -> bool:
    """Check whether a reddit post has already been posted by the Discord bot.

    Args:
        `post_id` (`str`): the reddit post ID

    Returns:
        `bool`: whether the post has been posted
    """
    for r_id, _ in d.get_recently_posted():
        if r_id == post_id:
            return False
    return True


def get_recent_entry(index: int) -> tuple:
    """Get a tuple of (`reddit id`, `discord message id`)

    Args:
        index (int): which index of `recent_posts_msgs` to get

    Returns:
        tuple: the entry
    """
    return d.get_recently_posted[index]


def remember(post: praw.models.Submission, message: discord.Message):
    """Persist a post ID and message ID so we can
    * update the score in the message
    * not submit the same post twice

    Args:
        `post` (`praw.models.Submission`): the reddit post
        `message` (`discord.Message`): the discord message of the reddit post
    """
    d.insert_reddit_post(post.id, message.id)


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
    """A template for a View which is used when prompting mods whether to ban a user.

    Args:
        (`discord.ui.View`): the View
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.red, custom_id="user_appeal:deny", label="Confirm", emoji='❌'
    )
    async def confirm_ban(self, _, interaction: discord.Interaction):
        """Confirm a user ban.

        Args:
            _ (`discord.User`): the user; discarded
            `interaction` (`discord.Interaction`): the interaction of the message sent to the mod channel
        """
        m: discord.Message = interaction.message
        emb = interaction.message.embeds[0]
        emb.title = "Banned"
        reason = m.embeds[0].fields[0].value
        u_id = int(m.content.split('\n')[-1])
        u = await client.fetch_user(u_id)
        g: discord.Guild = client.get_guild(VCJ_GUILD)
        try:
            await g.ban(u, reason=reason)
            await interaction.response.edit_message(view=None, embed=emb)
        except (Forbidden, HTTPException) as e:
            emb.title = "Failed to ban"
            await interaction.response.edit_message(view=None, embed=emb, content="Couldn't ban, please ban manually.")

    @discord.ui.button(
        style=discord.ButtonStyle.green, custom_id="user_appeal:approve", label="Ignore", emoji='✔️'
    )
    async def dismiss_ban(self, _, interaction):
        """Ignore a message warning and do not ban the user

        Args:
            _ (`discord.User`): the user; discarded
            `interaction` (`discord.Interaction`): the interaction of the message sent to the mod channel
        """
        m: discord.Message = interaction.message.content
        emb = interaction.message.embeds[0]
        emb.title = 'Ignored'
        emb.colour = discord.Colour.dark_green()
        await interaction.response.edit_message(content="OK, ignored.", view=None, embed=emb)


class KeisatsuBot(discord.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        #load()
        print(recent_posts_msgs)
        self.update_post_scores.start()
        self.check_memory_usage.start()
        self.check_new_posts.start()

        self.persistent_views_added = False

        # TODO - make it clear which message is which
        self.role_messages = [
            940046766827528212,
            940047479292964884,
            940048241712566333,
            940350126864625705,
            943492168528592977
        ]
        self.emoji_to_role = emoji_to_role

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
        """Print to console when bot started.
        Re-add previous buttons so their references aren't stale.
        """
        self.add_view(BannedUserButtonView())
        print(f"Connected: {self.user}")

        self.persistent_views_added = True

    async def submit_post(self, post: praw.models.Submission):
        """Submit the post to #reddit-posts.

        Args:
            `post` (`praw.models.Submission`): the reddit post object

        Returns:
            `Coroutine[Any, Any, discord.Message]`: the message we just sent
        """
        embed = self._gen_embed(post)
        return await self.get_channel(Channels.REDDIT_POSTS).send(embed=embed)

    async def _message_from_id(self, message_id: int, channel_id: int) -> discord.Message:
        """Transform a message ID and a channel ID into a message object
        that we can manipulate.

        Args:
            `message_id` (`int`): the message ID
            `channel_id` (`int`): the channel ID

        Returns:
            discord.Message: the message object
        """
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
            try:
                for p_id, m_id in recent_posts_msgs:
                    if m_id == message_id:
                        recent_posts_msgs.remove(p_id, m_id)
                        store()
            except:
                pass
            return None

    async def prompt_user_ban(self, user: discord.Member, reason: str):
        """Send a messge to the mod-only channel with buttons prompting
        whether to ban a use for a message based on context. 

        Args:
            `user` (`discord.Member`): the user who sent a questionable message
            `reason` (`str`): the reason the user would be banned for, as shown to the user
                              currently: 'Message contained `bad_word` in `message containing bad_word`'.
        """
        u: discord.Member = user

        view = BannedUserButtonView()

        embed = discord.Embed(
            title="Ban?",
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

    @tasks.loop(minutes=5)
    async def check_memory_usage(self):
        try:
            mem_mib = get_memory_use()
            if mem_mib > 256:
                await self.get_channel(Channels.BOT_DEBUG).send(f"<@{Channels.MISTYHANDS}> Memory usage high!  (`{mem_mib}MiB`)\nIs there a leak?")
                restart()

        except Exception as e:
            pass

    @tasks.loop(minutes=30)
    async def update_post_scores(self):
        print("Updating post messages.")
        for r_id, d_id in d.get_recently_posted():
            post: praw.models.Submission = await submission_from_id(r_id)
            message = await self._message_from_id(d_id, Channels.REDDIT_POSTS)

            if post and message:
                if (post.author is None) or not (post.is_robot_indexable):
                    await message.delete()
                    print(
                        f"Deleted message ID {message.id} due to removed reddit post {post.id}.")
                else:
                    await message.edit(embed=self._gen_embed(post))
            await asyncio.sleep(8)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Gives a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about.
        if payload.message_id not in self.role_messages and payload.emoji.name != 'sun':
            return

        msg = await self._message_from_id(payload.message_id, payload.channel_id)
        for r in msg.reactions:  # we have to iterate all reacts to find the amount : - (
            if (r.count >= REACT_THRESHOLD and r.emoji == 'sun') \
                and payload.emoji.name == 'sun' \
                    and not d.exists_sunboard(payload.message_id):
                u = msg.author
                try:
                    c = u.roles[0].colour
                    if c is None:
                        c = Colour.light_grey()
                except:
                    c = Colour.light_grey()

                embed = discord.Embed(
                    title=f'#{msg.channel.name}',
                    colour=c,
                    description=msg.content
                )

                n = u.nick if u.nick else u.name

                if u.avatar is not None:
                    embed.set_author(
                        name=f'{n}', icon_url=u.avatar.url)
                else:
                    embed.set_author(name=f'{u.name}#{u.discriminator}')
                dt_string = datetime.now().strftime("%H:%M %a %-d %b, %Y")
                embed.set_footer(text=f"Time: {dt_string}")
                if d.insert_sunboard(payload.message_id):
                    await self.get_channel(Channels.SUNBOARD).send(embed=embed)

        guild = self.get_guild(payload.guild_id)
        if guild is None:
            return

        try:
            role_id = self.emoji_to_role[payload.emoji]
        except KeyError:
            return

        role = guild.get_role(role_id)
        if role is None:
            return

        try:
            await payload.member.add_roles(role)

        except discord.HTTPException:
            pass

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Removes a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about.
        if payload.message_id not in self.role_messages:
            return

        guild = self.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return

        try:
            role_id = self.emoji_to_role[payload.emoji]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return

        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return

        # The payload for `on_raw_reaction_remove` does not provide `.member`
        # so we must get the member ourselves from the payload's `.user_id`.
        member = guild.get_member(payload.user_id)
        if member is None:
            return

        try:
            await member.remove_roles(role)
        except discord.HTTPException:
            pass

    @tasks.loop(minutes=15)
    async def check_new_posts(self):
        print("Checking for posts.")
        try:
            subreddit = await reddit.subreddit("VexillologyCirclejerk")
            async for post in subreddit.new(limit=15):
                if post_is_new(post):
                    msg = await self.submit_post(post)
                    remember(post, msg)
                await asyncio.sleep(10)
        except asyncprawcore.exceptions.ResponseException:
            print("Reddit error.")
            await asyncio.sleep(30)
        except Exception as e:
            client.get_channel(Channels.BOT_DEBUG).send(str(e))

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
intents.members = True
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


@client.slash_command(guild_ids=[929365821208272948], name="restart", description="restart")
async def restart_cmd(
    ctx: discord.ApplicationContext
):
    await ctx.respond(f"Restarting...", ephemeral=True)
    restart()


@client.slash_command(guild_ids=[929365821208272948, VCJ_GUILD], name="ping", description="Ping!")
async def restart_cmd(
    ctx: discord.ApplicationContext
):
    await ctx.respond(f"Pong!", ephemeral=True)


@client.event
async def on_message(message: discord.Message):
    """Scan each message for a banned word.

    Args:
        `message` (`discord.Message`): the message that was sent
    """

    # Ignore our own messages
    if message.author == client.user:
        return

    their_message = message.content
    word = ""
    for word in cfg["options"]["badwords"]:
        if word.lower() in their_message.lower():
            await client.prompt_user_ban(message.author, f"Message contained: `{word.lower()}` in `{their_message}`.")
            break


def restart():
    """Soft-restart the script so we don't need to reboot the entire VPS.
    """
    import sys
    import os
    os.execv(sys.executable, ['python3'] + sys.argv)


reddit = praw.Reddit(
    client_id=cfg["keys"]["reddit_id"],
    client_secret=cfg["keys"]["reddit_secret"],
    user_agent="/r/vexillologycirclejerk post scraper",
)


try:
    client.run(cfg["keys"]["discord"])

except Exception as e:
    try:
        client.get_channel(Channels.BOT_DEBUG).send(str(e))
        restart()
    except:
        pass
    time.sleep(30)
print("Here!")
