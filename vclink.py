import discord
from discord.ext import commands
import asyncio
from ds import ds
dis = ds()

class vclink_(commands.Cog):

    def __init__(self, client):
        self.client = client

    # Reaction Based commands
    @commands.command(aliases=['Vclink','link'])
    @commands.has_permissions(administrator=True)
    async def vclink(self, ctx, role: discord.Role):
        complete = False
        voice_channel_list = ctx.guild.voice_channels

        total_page = len(voice_channel_list) // 9 + 1
        cur_page = 1

        link_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'All of the voice channels in {ctx.guild.name}\nPlease react with the channel that you want to link.\nUse ◀️ and ▶️ to change pages.'
        )
        if total_page > 1:
            link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
        
        channel_ids = []
        for id_ in voice_channel_list:
            channel_ids.append(id_.id)
        # await ctx.send(channel_ids)
        reaction_type = {1:'🔴',2:'🟠',3:'🟡',4:'🟢',5:'🔵',6:'🟣',7:'🟤',8:'⚫',9:'⚪'}
        reaction_list = ["◀️", "▶️", '❌','🔴','🟠','🟡','🟢','🔵','🟣','🟤','⚫','⚪']
        num = 1
        channel_num = 1
        channel_names = []
        for name_ in voice_channel_list: # pgnum * 9 - 8,7,6,5,4,3,2,1,0
            channel_names.append(name_.name)
            if cur_page * 9 >= channel_num:
                link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{name_.name}', inline=True)
                channel_num = channel_num + 1

            num = num + 1
        # await ctx.send(channel_names)

        message = await ctx.send(embed=link_embed)
        
        reactions = {1:'🔴',2:'🟠',3:'🟡',4:'🟢',5:'🔵',6:'🟣',7:'🟤',8:'⚫',9:'⚪',0:'❌'}	
        num1 = 1
        # message = await ctx.send(f"Page {cur_page}/{pages}:\n{contents[cur_page-1]}")
        # getting the message object for editing and reacting

        if total_page > 1:
            await message.add_reaction('◀️')
            await message.add_reaction('▶️')
        if channel_num <= 9:
            while num1 != channel_num:
                await message.add_reaction(reactions[num1])
                num1 = num1 + 1 
        else:
            while num1 != channel_num:
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
                        description=f'All of the voice channels in {ctx.guild.name}\nPlease react with the channel that you want to link.\nUse ◀️ and ▶️ to change pages.'
                    )
                    if total_page > 1:
                        link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
                    
                    num = 1
                    cur_id = (cur_page-1)*9
                    while cur_id < len(channel_ids):
                        if cur_id < cur_page*9:
                            link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{channel_names[cur_id]}', inline=True)
                        num += 1
                        cur_id += 1                     

                    await message.edit(embed=link_embed)

                    # await message.edit(content=f"Page {cur_page}/{pages}:\n{contents[cur_page]}")
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and cur_page > 1:
                    cur_page -= 1

                    link_embed = discord.Embed(
                        colour=discord.Colour.dark_grey(),
                        description=f'All of the voice channels in {ctx.guild.name}\nPlease react with the channel that you want to link.\nUse ◀️ and ▶️ to change pages.'
                    )
                    if total_page > 1:
                        link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
                    
                    num = 1
                    cur_id = (cur_page-1)*9
                    while cur_id < len(channel_ids):
                        if cur_id < cur_page*9:
                            link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{channel_names[cur_id]}', inline=True)
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
                                channel = channel_ids[id_pos+(cur_page-1)*9]

                                vcs = dis.jopen(ctx.guild.id)

                                vcs[str(channel)] = str(role.id)

                                dis.jdump(ctx.guild.id, vcs)

                                linked_embed = discord.Embed(
                                    colour=discord.Colour.dark_grey(),
                                    description=f'Linked voice channel {channel_names[int(id_pos+(cur_page-1)*9)]} with {role.mention}\nPlease make sure my highest role is above {role.mention} or I can\'t add the role'
                                )
                                id_pos = 0
                                channel = 0
                                complete = True
            
                            except:
                                channel_embed = discord.Embed(
                                colour=discord.Colour.red(),
                                description=f'**Error 104:** Only click on a reaction if it appears on the embed'
                                )
                                await ctx.send(embed=channel_embed)

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

        dis.counter('vclink')      

    @commands.command(aliases=['Vcunlink','unlink'])
    @commands.has_permissions(administrator=True)
    async def vcunlink(self, ctx):
        complete = False
        voice_channel_list = []
        vcs = {}
        all_linked_bool = False

        vcs = dis.jopen(ctx.guild.id)

        if 'all' in vcs:
            all_linked_bool = True
            all_linked = vcs['all']
            vcs.pop('all')

        try:        
            voice_channel_list, values = zip(*vcs.items())
        
            voice_channel_list = list(voice_channel_list)

            # print(voice_channel_list)

            total_page = len(voice_channel_list) // 9 + 1
            cur_page = 1

            link_embed = discord.Embed(
                colour=discord.Colour.dark_grey(),
                description=f'All of the linked voice channels in {ctx.guild.name}\nPlease react with the channel that you would like to unlink.'
            )
            if total_page > 1:
                link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
            
            reaction_type = {1:'🔴',2:'🟠',3:'🟡',4:'🟢',5:'🔵',6:'🟣',7:'🟤',8:'⚫',9:'⚪'}
            reaction_list = ["◀️", "▶️", '❌','🔴','🟠','🟡','🟢','🔵','🟣','🟤','⚫','⚪']
            num = 1
            channel_num = 1
            channel_names = []
            name_ = 0

            for name_ in voice_channel_list:
                try:
                    name_ = self.client.get_channel(int(name_))
                    channel_names.append(name_.name)
                    if cur_page * 9 >= channel_num:
                        link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{name_.name}', inline=True)
                        channel_num = channel_num + 1
                except:
                    pass

                num = num + 1
            # await ctx.send(channel_names)

            message = await ctx.send(embed=link_embed)
            
            reactions = {1:'🔴',2:'🟠',3:'🟡',4:'🟢',5:'🔵',6:'🟣',7:'🟤',8:'⚫',9:'⚪',0:'❌'}	
            num1 = 1
            # message = await ctx.send(f"Page {cur_page}/{pages}:\n{contents[cur_page-1]}")
            # getting the message object for editing and reacting

            if total_page > 1:
                await message.add_reaction('◀️')
                await message.add_reaction('▶️')
            if channel_num <= 9:
                while num1 != channel_num:
                    await message.add_reaction(reactions[num1])
                    num1 = num1 + 1 
            else:
                while num1 != channel_num:
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
                            description=f'All of the linked voice channels in {ctx.guild.name}\nPlease react with the channel that you would like to unlink.'
                        )
                        if total_page > 1:
                            link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
                        
                        num = 1
                        cur_id = (cur_page-1)*9
                        while cur_id < len(voice_channel_list):
                            if cur_id < cur_page*9:
                                link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{channel_names[cur_id]}', inline=True)
                            num += 1
                            cur_id += 1                     

                        await message.edit(embed=link_embed)

                        # await message.edit(content=f"Page {cur_page}/{pages}:\n{contents[cur_page]}")
                        await message.remove_reaction(reaction, user)

                    elif str(reaction.emoji) == "◀️" and cur_page > 1:
                        cur_page -= 1

                        link_embed = discord.Embed(
                            colour=discord.Colour.dark_grey(),
                            description=f'All of the linked voice channels in {ctx.guild.name}\nPlease react with the channel that you would like to unlink.'
                        )
                        if total_page > 1:
                            link_embed.set_footer(text=f'Page {cur_page}/{total_page}')
                        
                        num = 1
                        cur_id = (cur_page-1)*9
                        while cur_id < len(voice_channel_list):
                            if cur_id < cur_page*9:
                                link_embed.add_field(name=f'  {reaction_type[num]}', value=f'{channel_names[cur_id]}', inline=True)
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
                                    channel = voice_channel_list[id_pos+(cur_page-1)*9]

                                    vcs = dis.jopen(ctx.guild.id)

                                    vcs.pop(str(channel))

                                    dis.jdump(ctx.guild.id, vcs)

                                    unlink_embed = discord.Embed(
                                        colour=discord.Colour.dark_grey(),
                                        description=f'Unlinked voice channel {channel_names[int(id_pos+(cur_page-1)*9)]} from it\'s role'
                                    )
                                    
                                    id_pos = 0
                                    channel = 0
                                    complete = True
                                except:
                                    channel_embed = discord.Embed(
                                    colour=discord.Colour.red(),
                                    description=f'**Error 104:** Only click on a reaction if it appears on the embed'
                                    )
                                    await ctx.send(embed=unlink_embed)

                        await message.remove_reaction(reaction, user)
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
                except asyncio.TimeoutError:
                    try:
                        await message.delete()

                        if complete == False:
                            channel_embed = discord.Embed(
                                colour=discord.Colour.red(),
                                description=f'**Error 105:** The Unlinking Process for {ctx.message.author.mention} has timed out'
                            )
                            await ctx.send(embed=channel_embed)
                        else:
                            pass
                    except:
                        pass
                    break
                    # ending the loop if user doesn't react after x seconds

                try:
                    await ctx.send(embed=unlink_embed)
                    await message.delete()
                except:
                    pass
        
        except:
            error_embed = discord.Embed(
                colour=discord.Colour.red(),
                description='**Error 108:** You do not have voice channels available to unlink'
            )
            await ctx.send(embed=error_embed)

        if all_linked_bool == True:
            vcs = dis.jopen(ctx.guild.id)
            
            vcs['all'] = all_linked

            dis.jdump(ctx.guild.id, vcs)

        dis.counter('vcunlink')

    # ID Based Commands
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def oldvclink(self, ctx, channel : discord.VoiceChannel, role : discord.Role):
        vcs = dis.jopen(ctx.guild.id)

        vcs[str(channel.id)] = str(role.id)

        dis.jdump(ctx.guild.id, vcs)

        link_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Linked voice channel {channel.name} with {role.mention}\nPlease make sure my highest role is above {role.mention} or I won\'t work'
        )
        await ctx.send(embed=link_embed)
        # await ctx.send(f'VC {channel.name} has been paired with role {role.name}.')

        dis.counter('oldvclink')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def oldvcunlink(self, ctx, channel : discord.VoiceChannel, role: discord.Role):
        vcs = dis.jopen(ctx.guild.id)

        vcs.pop(str(channel.id))

        dis.jdump(ctx.guild.id, vcs)

        unlink_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Unlinked voice channel {channel.name} and {role.mention}'
        )
        await ctx.send(embed=unlink_embed)

        # await ctx.send(f'VC {channel.name} has been unpaired from role {role.name}')#
        
        dis.counter('oldvcunlink')

def setup(client):
    client.add_cog(vclink_(client))