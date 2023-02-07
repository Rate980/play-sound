from typing import cast

import discord
from discord.ext.commands import Context, check

from jsons import Jsons
from play_sound import PlaySound


@check
async def is_dj(ctx: Context):
    if ctx.cog is None:
        return False
    if not isinstance(ctx.cog, PlaySound):
        return False

    data = cast(Jsons, ctx.cog.data)
    if ctx.guild is None:
        return False
    option = data.get_option(ctx.guild.id)
    if (dj_id := option["dj_id"]) is None:
        return True
    if not isinstance(ctx.author, discord.Member):
        return False

    for x in ctx.author.roles:
        if x.id == dj_id:
            return True
    else:
        return False


@check
def is_mod(ctx: Context):
    if not isinstance(ctx.author, discord.Member):
        return False
    return ctx.author.guild_permissions.manage_roles
