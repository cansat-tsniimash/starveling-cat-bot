import logging
import itertools
import collections
import typing

import discord
from discord import Client
from discord.abc import GuildChannel
from discord import TextChannel


_log = logging.getLogger(__name__)

CommitInfo = collections.namedtuple("CommitInfo", ["message", "hash", "url"])


class DiscordClient(Client):

    def _format_push_commits(self, github_payload: dict) -> typing.List[CommitInfo]:
        retval = []
        for commit in itertools.chain([github_payload["head_commit"]], github_payload["commits"]):
            if not commit:
                continue

            short_hash = str(commit["id"])[0:7]
            url = commit["url"]
            retval.append(
                CommitInfo(commit["message"], short_hash, url)
            )

        return retval

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.target_channel_name = "ботовник"
        self.channels_to_post = []  # type: typing.List[TextChannel]

    async def on_ready(self):
        for channel in self.get_all_channels():  # type: typing.Iterable[GuildChannel]
            if not isinstance(channel, TextChannel):
                continue

            if channel.name == self.target_channel_name:
                self.channels_to_post.append(channel)
                _log.info("selected channel %s(%s)", channel.name, channel.id)

    async def process_push_hook(self, payload):
        sender_name = payload["sender"]["login"]
        sender_url = payload["sender"]["html_url"]
        sender_pic = payload["sender"]["avatar_url"]
        repo_name = payload["repository"]["full_name"]
        commit_infos = self._format_push_commits(payload)
        compare_url = payload["compare"]

        content = f"{sender_name} запушил в репу {repo_name} количество коммитов: {len(commit_infos)}"
        content += "\n"
        content += "коммиты:\n"
        for info in commit_infos:
            content += f"* [{info.hash[0:7]}]({info.url}) - {info.message}\n"

        content += "\n"
        content += f"[Изменения]({compare_url})"

        for channel in self.channels_to_post:
            embed = discord.Embed(title="Новый пуш", description=content)
            embed.set_author(name=sender_name, url=sender_url, icon_url=sender_pic)
            await channel.send(embed=embed)
