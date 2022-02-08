import discord
from discord import ApplicationContext
from discord.ext import commands
from bot import MyClient


class Linked(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(
        description="Displays the linked roles, channels & categories"
    )
    @commands.has_permissions(administrator=True)
    async def linked(self, ctx: ApplicationContext):

        linked_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"The linked roles, channels & categories in {ctx.guild.name}:",
        )
        va = ""

        v_dict = self.client.redis.get_linked("voice", ctx.guild.id)

        for v_list in v_dict:
            try:
                channel = self.client.get_channel(int(v_list))
                va += f"{channel.mention}: "
                for role in v_dict[v_list]:
                    try:
                        role = ctx.guild.get_role(int(role))
                        va += f"{role.mention} "
                    except:
                        pass
                va += "\n"
            except:
                va += f"Not Found - ID `{v_list}`\n"

        s_dict = self.client.redis.get_linked("stage", ctx.guild.id)

        for s_list in s_dict:
            try:
                channel = self.client.get_channel(int(s_list))
                va += f"{channel.mention}: "
                for role in s_dict[s_list]:
                    try:
                        role = ctx.guild.get_role(int(role))
                        va += f"{role.mention} "
                    except:
                        pass
                va += "\n"
            except:
                va += f"Not Found - ID `{s_list}`\n"

        c_dict = self.client.redis.get_linked("category", ctx.guild.id)

        for c_list in c_dict:
            try:
                channel = self.client.get_channel(int(c_list))
                va += f"Category {channel.mention}: "
                for role in c_dict[c_list]:
                    try:
                        role = ctx.guild.get_role(int(role))
                        va += f"{role.mention} "
                    except:
                        pass
                va += "\n"
            except:
                va += f"Not Found - ID `{c_list}`\n"

        p_dict = self.client.redis.get_linked("permanent", ctx.guild.id)

        for p_list in p_dict:
            try:
                channel = self.client.get_channel(int(p_list))
                va += f"Permanent {channel.mention}: "
                for role in p_dict[p_list]:
                    try:
                        role = ctx.guild.get_role(int(role))
                        va += f"{role.mention} "
                    except:
                        pass
                va += "\n"
            except:
                va += f"Not Found - ID `{p_list}`\n"

        a_list = self.client.redis.get_linked("all", ctx.guild.id)["roles"]
        if a_list:
            va += "All: "
            for role in a_list:
                try:
                    role = ctx.guild.get_role(int(role))
                    va += f"{role.mention} "
                except:
                    pass
            va += "\n"

        a_list_e = self.client.redis.get_linked("all", ctx.guild.id)["except"]
        if a_list_e:
            va += "All-link exceptions: "
            for channel in a_list_e:
                try:
                    channel = self.client.get_channel(int(channel))
                    va += f"{channel.mention} "
                except:
                    va += f"Not Found - ID `{channel}`"
            va += "\n"

        if va:
            va = va[:-1]
            linked_embed.add_field(name="Linked:", value=va)
            await ctx.respond(embed=linked_embed)
        else:
            await ctx.respond("Nothing is linked")


def setup(client: MyClient):
    client.add_cog(Linked(client))
