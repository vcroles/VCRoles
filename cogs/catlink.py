import discord
from discord.ext import commands
import asyncio
from ds import ds
dis = ds()

class catlink_(commands.Cog):

    def __init__(self, client):
        self.client = client

    # Reaction Based commands
    @commands.command(aliases=['Catlink','categorylink','Categorylink'])
    @commands.has_permissions(administrator=True)
    async def catlink(self, ctx, role: discord.Role):
        complete = False
        category_list = ctx.guild.categories

        total_page = len(category_list) // 9 + 1
        cur_page = 1

        link_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'All of the Categorys in {ctx.guild.name}\nPlease react with the category that you want to link.\nUse ◀️ and ▶️ to change pages.'
        )
        if total_page > 1:
            link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
        
        category_ids = []
        for id_ in category_list:
            category_ids.append(id_.id)
        reaction_type = {1:'🔴',2:'🟠',3:'🟡',4:'🟢',5:'🔵',6:'🟣',7:'🟤',8:'⚫',9:'⚪'}
        reaction_list = ["◀️", "▶️", '❌','🔴','🟠','🟡','🟢','🔵','🟣','🟤','⚫','⚪']
        num = 1
        category_num = 1
        category_names = []
        for name_ in category_list: # pgnum * 9 - 8,7,6,5,4,3,2,1,0
            category_names.append(name_.name)
            if cur_page * 9 >= category_num:
                link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{name_.name}', inline=True)
                category_num = category_num + 1

            num = num + 1

        message = await ctx.send(embed=link_embed)
        
        reactions = {1:'🔴',2:'🟠',3:'🟡',4:'🟢',5:'🔵',6:'🟣',7:'🟤',8:'⚫',9:'⚪',0:'❌'}	
        num1 = 1
        # message = await ctx.send(f"Page {cur_page}/{pages}:\n{contents[cur_page-1]}")
        # getting the message object for editing and reacting

        if total_page > 1:
            await message.add_reaction('◀️')
            await message.add_reaction('▶️')
        if category_num <= 9:
            while num1 != category_num:
                await message.add_reaction(reactions[num1])
                num1 = num1 + 1 
        else:
            while num1 != category_num:
                await message.add_reaction(reactions[num1])
                num1 = num1 + 1 
        
        await message.add_reaction('❌')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️", '❌','🔴','🟠','🟡','🟢','🔵','🟣','🟤','⚫','⚪']
            # This makes sure nobody except the command sender can interact with the "menu"

        while True:
            try:
                reaction, user = await self.client.wait_for("reaction_add", timeout=20, check=check)

                complete = False

                if str(reaction.emoji) == "▶️" and cur_page != total_page:
                    cur_page += 1


                    link_embed = discord.Embed(
                        colour=discord.Colour.dark_grey(),
                        description=f'All of the Categorys in {ctx.guild.name}\nPlease react with the categor that you want to link.\nUse ◀️ and ▶️ to change pages.'
                    )
                    if total_page > 1:
                        link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
                    
                    num = 1
                    cur_id = (cur_page-1)*9
                    while cur_id < len(category_ids):
                        if cur_id < cur_page*9:
                            link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{category_names[cur_id]}', inline=True)
                        num += 1
                        cur_id += 1                     

                    await message.edit(embed=link_embed)

                    # await message.edit(content=f"Page {cur_page}/{pages}:\n{contents[cur_page]}")
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and cur_page > 1:
                    cur_page -= 1

                    link_embed = discord.Embed(
                        colour=discord.Colour.dark_grey(),
                        description=f'All of the categorys in {ctx.guild.name}\nPlease react with the category that you want to link.\nUse ◀️ and ▶️ to change pages.'
                    )
                    if total_page > 1:
                        link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
                    
                    num = 1
                    cur_id = (cur_page-1)*9
                    while cur_id < len(category_ids):
                        if cur_id < cur_page*9:
                            link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{category_names[cur_id]}', inline=True)
                        num += 1
                        cur_id += 1                     

                    await message.edit(embed=link_embed)
                    
                    await message.remove_reaction(reaction, user)
                
                elif str(reaction.emoji) == "❌":
                    x=3
                    await ctx.send('Ending Linking Process')
                    await ctx.channel.purge(limit=x)
                    link_end_embed = discord.Embed(
                        colour=discord.Colour.blue(),
                        description='Linking Process Ended'
                    )
                    await ctx.send(embed=link_end_embed,delete_after=10)

                else:
                    for key, value in reactions.items():
                        if value == reaction.emoji:
                            try:
                                id_pos = key - 1 
                                category = category_ids[id_pos+(cur_page-1)*9]
                                jsonname = f"cat{ctx.guild.id}"

                                channels = dis.jopen(jsonname)

                                channels[str(category)] = str(role.id)

                                dis.jdump(jsonname, channels)

                                linked_embed = discord.Embed(
                                    colour=discord.Colour.dark_grey(),
                                    description=f'Linked category {category_names[int(id_pos+(cur_page-1)*9)]} with {role.mention}\nPlease make sure my highest role is above {role.mention} or I can\'t add the role'
                                )
                                id_pos = 0
                                category = 0
                                complete = True
            
                            except:
                                category_embed = discord.Embed(
                                colour=discord.Colour.red(),
                                description=f'**Error 104:** Only click on a reaction if it appears on the embed'
                                )
                                await ctx.send(embed=category_embed)

                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page

            except asyncio.TimeoutError:
                try:
                    await message.delete()

                    if complete == False:
                        channel_embed = discord.Embed(
                            colour=discord.Colour.red(),
                            description=f'**Error 105:** The Linking Process for {ctx.message.author.mention} has timed out'
                        )
                        await ctx.send(embed=channel_embed)
                    else:
                        pass
                except:
                    pass
                break
                # ending the loop if user doesn't react after x seconds

            try:
                await ctx.send(embed=linked_embed)
                await message.delete()
            except:
                pass  

        dis.counter('catlink')      

def setup(client):
    client.add_cog(catlink_(client))