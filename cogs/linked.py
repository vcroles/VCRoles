import discord
from discord.commands import slash_command
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class Linked(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @slash_command(description="Displays the linked roles, channels & categories")
    @Permissions.has_permissions(administrator=True)
    async def linked(self, ctx: discord.ApplicationContext):

        linked_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"The linked roles, channels & categories in {ctx.guild.name}:",
        )
        va = ""

        v_dict = self.client.redis.get_linked("voice", ctx.guild.id)

        for v in v_dict:
            if v != "format":
                try:
                    channel = self.client.get_channel(int(v))
                    va += f"{channel.mention}: "
                    for role in v_dict[v]["roles"]:
                        try:
                            role = ctx.guild.get_role(int(role))
                            va += f"{role.mention} "
                        except:
                            pass
                    if v_dict[v]["suffix"]:
                        va += f"`{v_dict[v]['suffix']}`"
                    va += "\n"
                except:
                    va += f"Not Found - ID `{v}`\n"

        s_dict = self.client.redis.get_linked("stage", ctx.guild.id)

        for s in s_dict:
            if s != "format":
                try:
                    channel = self.client.get_channel(int(s))
                    va += f"{channel.mention}: "
                    for role in s_dict[s]["roles"]:
                        try:
                            role = ctx.guild.get_role(int(role))
                            va += f"{role.mention} "
                        except:
                            pass
                    if s_dict[s]["suffix"]:
                        va += f"`{s_dict[s]['suffix']}`"
                    va += "\n"
                except:
                    va += f"Not Found - ID `{s}`\n"

        c_dict = self.client.redis.get_linked("category", ctx.guild.id)

        for c in c_dict:
            if c != "format":
                try:
                    channel = self.client.get_channel(int(c))
                    va += f"Category {channel.mention}: "
                    for role in c_dict[c]["roles"]:
                        try:
                            role = ctx.guild.get_role(int(role))
                            va += f"{role.mention} "
                        except:
                            pass
                    if c_dict[c]["suffix"]:
                        va += f"`{c_dict[c]['suffix']}`"
                    va += "\n"
                except:
                    va += f"Not Found - ID `{c}`\n"

        p_dict = self.client.redis.get_linked("permanent", ctx.guild.id)

        for p in p_dict:
            if p != "format":
                try:
                    channel = self.client.get_channel(int(p))
                    va += f"Permanent {channel.mention}: "
                    for role in p_dict[p]["roles"]:
                        try:
                            role = ctx.guild.get_role(int(role))
                            va += f"{role.mention} "
                        except:
                            pass
                    if p_dict[p]["suffix"]:
                        va += f"`{p_dict[p]['suffix']}`"
                    va += "\n"
                except:
                    va += f"Not Found - ID `{p}`\n"

        a_dict = self.client.redis.get_linked("all", ctx.guild.id)
        a_list = a_dict["roles"]
        if a_list:
            va += "All: "
            for role in a_list:
                try:
                    role = ctx.guild.get_role(int(role))
                    va += f"{role.mention} "
                except:
                    pass
            va += "\n"

        a_list_e = a_dict["except"]
        if a_list_e:
            va += "All-link exceptions: "
            for channel in a_list_e:
                try:
                    channel = self.client.get_channel(int(channel))
                    va += f"{channel.mention} "
                except:
                    va += f"Not Found - ID `{channel}`"
            va += "\n"

        a_list_s = a_dict["suffix"]
        if a_list_s:
            va += f"All-link suffix: `{a_list_s}`\n"

        if va:
            va = va[:-1]
            linked_embed.add_field(name="Linked:", value=va)
            await ctx.respond(embed=linked_embed)
        else:
            await ctx.respond("Nothing is linked")


def setup(client: MyClient):
    client.add_cog(Linked(client))
