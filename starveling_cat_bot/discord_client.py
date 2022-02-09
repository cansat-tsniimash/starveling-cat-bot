import logging
import collections
import typing

# noinspection PyPackageRequirements
import discord
# noinspection PyPackageRequirements
from discord import Client
# noinspection PyPackageRequirements
from discord.abc import GuildChannel
# noinspection PyPackageRequirements
from discord import TextChannel, Guild


_log = logging.getLogger(__name__)

CommitInfo = collections.namedtuple("CommitInfo", ["message", "hash", "url"])


class DiscordClient(Client):

    @staticmethod
    def _format_push_commits(github_payload: dict) -> typing.List[CommitInfo]:
        retval = []
        for commit in github_payload["commits"]:
            if not commit:
                continue

            short_hash = str(commit["id"])[0:7]
            url = commit["url"]
            retval.append(
                CommitInfo(commit["message"], short_hash, url)
            )

        return retval

    # noinspection PyUnusedLocal
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.channels_to_post = []  # type: typing.List[TextChannel]

    async def on_ready(self):

        # А то бывает ready случается несколько раз
        self.channels_to_post.clear()

        for guild in self.guilds:  # type: Guild
            for channel in guild.channels:  # type: GuildChannel
                if not isinstance(channel, TextChannel):
                    continue

                # channel.permissions_for(self.user)
                permissions = channel.permissions_for(guild.me)
                if permissions.send_messages:
                    _log.info("adding spam channel \"%s\" on server \"%s\"", channel, guild)
                    self.channels_to_post.append(channel)
                    break

        if not self.channels_to_post:
            _log.error("There is not a single channel to post!")

    async def process_push_hook(self, payload):
        sender_name = payload["sender"]["login"]
        sender_url = payload["sender"]["html_url"]
        sender_pic = payload["sender"]["avatar_url"]
        repo_name = payload["repository"]["full_name"]
        repo_url = payload["repository"]["html_url"]
        commit_infos = self._format_push_commits(payload)
        compare_url = payload["compare"]

        content = f"в [{repo_name}]({repo_url}):"
        content += "\n"
        if commit_infos:
            content += "коммиты:\n"
            for info in commit_infos:
                content += f"* [{info.hash[0:7]}]({info.url}) - {info.message}\n"
        else:
            content += "(что-то тут нет новых коммитов, он бранч пушил чтоли? Вы там разберитесь)"

        content += "\n"
        content += f"[Изменения]({compare_url})"

        embed = discord.Embed(title="Запушил", description=content)
        embed.set_author(name=sender_name, url=sender_url, icon_url=sender_pic)
        for channel in self.channels_to_post:
            _log.info("pushing message to %s", channel)
            await channel.send(embed=embed)

    async def post_error(self, text: str):
        for channel in self.channels_to_post:
            _log.info("pushing error message to %s", channel)
            await channel.send(content="Я сломался, помогите. " + text)
