import discord
from discord.ext import commands
from ds import ds
dis = ds()
import time
from time import localtime

class voicestate(commands.Cog):

    def __init__(self, client):
        self.client = client

    # event
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        logging_channels = dis.jopen('logging')
        #LOGGING VARIABLES
        AllRoleLinked = None
        ChannelRoleLinked = None
        ChannelRoleLinked2 = None
        CategoryRoleLinked = None
        CategoryRoleLinked2 = None
        RoleAddSuccess = None
        RoleAddSuccess2 = None
        AllRoleAddSuccess = None
        CatRoleAddSuccess = None
        CatRoleAddSuccess2 = None
        embed_value = ''
        embed_value2 = ''
        embed_value3 = ''
        embed_value4 = ''
        if member.bot == False:

            #joining channel
            if not before.channel and after.channel:

                vcs = dis.jopen(member.guild.id)
                channel = after.channel
                
                #if channel has a role associated
                if str(channel.id) in vcs:
                    rolename = vcs[str(channel.id)]
                    role = discord.utils.get(member.guild.roles, id=int(rolename))
                    ChannelRoleLinked = role #NEEDED FOR LOGGING
                    try:
                        await member.add_roles(role)
                        RoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(869353526546038784)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        RoleAddSuccess = False
                
                
                #if 'all' has been linked
                if 'all' in vcs:
                    rolename = vcs['all']
                    role = discord.utils.get(member.guild.roles, id=int(rolename))
                    AllRoleLinked = role #NEEDED FOR LOGGING
                    try:
                        await member.add_roles(role)
                        AllRoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        AllRoleAddSuccess = False
                
                
                # Category Linked Role
                data = dis.jopen(f'category\\cat{member.guild.id}')
                if str(after.channel.category.id) in data:
                    category = after.channel.category.id
                    role = member.guild.get_role(int(data[str(category)]))
                    CategoryRoleLinked = role
                    try:
                        await member.add_roles(role)
                        CatRoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        CatRoleAddSuccess = False
                
                
                #Logging
                if str(after.channel.guild.id) in logging_channels:
                    logging_channel = logging_channels[str(after.channel.guild.id)]
                    logging_channel = self.client.get_channel(int(logging_channel))
                    logging_embed = discord.Embed(colour=discord.Colour.green(),title='Member Joined voice channel',description=f'{member.name}#{member.discriminator} joined {after.channel.mention}')
                    logging_embed.set_footer(text=f'User ID - {member.id} • {time.strftime("%a %H:%M", localtime())}')
                    logging_embed.set_author(name=f'{member.name}#{member.discriminator}',icon_url=member.avatar_url)

                    if AllRoleLinked != None:
                        if AllRoleAddSuccess == True:
                            embed_value = f'All Channels Role: {AllRoleLinked.mention} added\n'
                        elif AllRoleAddSuccess == False:
                            embed_value = f'Unable to add role: {AllRoleLinked.mention} - Check my permissions\n'
                    if ChannelRoleLinked != None:
                        if RoleAddSuccess == True:
                            embed_value2 = f'Role: {ChannelRoleLinked.mention} added\n'
                        elif RoleAddSuccess == False:
                            embed_value2 = f'Unable to add role: {ChannelRoleLinked.mention} - Check my permissions\n'
                    if CatRoleAddSuccess != None:
                        if CatRoleAddSuccess == True:
                            embed_value3 = f'Category Role: {CategoryRoleLinked.mention} added\n'
                        elif CatRoleAddSuccess == False:
                            embed_value3 = f'Unable to add role {CategoryRoleLinked.mention} - Check my permissions\n'

                    # if embed_value != None:
                    #     if embed_value2 != None:
                    #         logging_embed.add_field(name='__**Roles**__', value=f'{embed_value2}\n{embed_value}')
                    #     else:
                    #         logging_embed.add_field(name='__**Roles**__', value=f'{embed_value}')
                    # else:
                    #     if embed_value2 != None:
                    #         logging_embed.add_field(name='__**Roles**__', value=f'{embed_value2}')
                    #     else:
                    #         pass
                    if embed_value != '' or embed_value2 != '' or embed_value3 != '':
                        logging_embed.add_field(name='__**Roles**__', value=f'{embed_value2}{embed_value}{embed_value3}')
                    await logging_channel.send(embed=logging_embed)

            #leaving channels
            elif before.channel and not after.channel:

                vcs = dis.jopen(member.guild.id)
                channel = before.channel
                
                #if channel has a role associated
                if str(channel.id) in vcs:
                    rolename = vcs[str(channel.id)]
                    role = discord.utils.get(member.guild.roles, id=int(rolename))
                    ChannelRoleLinked = role #NEEDED FOR LOGGING
                    try:
                        await member.remove_roles(role)
                        RoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
                        RoleAddSuccess = False

                    pass
                
                
                #if 'all' has been linked
                if 'all' in vcs:
                    rolename = vcs['all']
                    role = discord.utils.get(member.guild.roles, id=int(rolename))
                    AllRoleLinked = role #NEEDED FOR LOGGING
                    try:
                        await member.remove_roles(role)
                        AllRoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
                        AllRoleAddSuccess = False
                

                # Category Linked Role
                data = dis.jopen(f'category\\cat{member.guild.id}')
                if str(before.channel.category.id) in data:
                    category = before.channel.category.id
                    role = member.guild.get_role(int(data[str(category)]))
                    CategoryRoleLinked = role
                    try:
                        await member.remove_roles(role)
                        CatRoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
                        CatRoleAddSuccess = False

                
                #Logging
                if str(before.channel.guild.id) in logging_channels:
                    logging_channel = logging_channels[str(before.channel.guild.id)]
                    logging_channel = self.client.get_channel(int(logging_channel))
                    logging_embed = discord.Embed(colour=discord.Colour.red(),title='Member Left voice channel',description=f'{member.name}#{member.discriminator} left {before.channel.mention}')
                    logging_embed.set_footer(text=f'User ID - {member.id} • {time.strftime("%a %H:%M", localtime())}')
                    logging_embed.set_author(name=f'{member.name}#{member.discriminator}',icon_url=member.avatar_url)

                    if AllRoleLinked != None:
                        if AllRoleAddSuccess == True:
                            embed_value = f'All Channels Role: {AllRoleLinked.mention} removed\n'
                        elif AllRoleAddSuccess == False:
                            embed_value = f'Unable to remove role: {AllRoleLinked.mention} - Check my permissions\n'
                    if ChannelRoleLinked != None:
                        if RoleAddSuccess == True:
                            embed_value2 = f'Role: {ChannelRoleLinked.mention} removed\n'
                        elif RoleAddSuccess == False:
                            embed_value2 = f'Unable to remove role: {ChannelRoleLinked.mention} - Check my permissions\n'
                    if CatRoleAddSuccess != None:
                        if CatRoleAddSuccess == True:
                            embed_value3 = f'Category Role: {CategoryRoleLinked.mention} removed\n'
                        elif CatRoleAddSuccess == False:
                            embed_value3 = f'Unable to remove role {CategoryRoleLinked.mention} - Check my permissions\n'

                    if embed_value != '' or embed_value2 != '' or embed_value3 != '':
                        logging_embed.add_field(name='__**Roles**__', value=f'{embed_value2}{embed_value}{embed_value3}')
                    await logging_channel.send(embed=logging_embed)

            #changing channels
            elif before.channel != after.channel:

                #removing old role
                vcs = dis.jopen(member.guild.id)
                channel = before.channel
                
                #if channel has a role associated
                if str(channel.id) in vcs:
                    rolename = vcs[str(channel.id)]
                    role = discord.utils.get(member.guild.roles, id=int(rolename))
                    ChannelRoleLinked = role #NEEDED FOR LOGGING
                    try:
                        await member.remove_roles(role)
                        RoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
                        RoleAddSuccess = False
                
                #adding new role
                vcs = dis.jopen(member.guild.id)
                channel = after.channel
                
                #if channel has a role associated
                if str(channel.id) in vcs:
                    rolename = vcs[str(channel.id)]
                    role = discord.utils.get(member.guild.roles, id=int(rolename))
                    ChannelRoleLinked2 = role #NEEDED FOR LOGGING
                    try:
                        await member.add_roles(role)
                        RoleAddSuccess2 = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 106/107: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        RoleAddSuccess2 = False

                        
                # Category Linked Role
                data = dis.jopen(f'category\\cat{member.guild.id}')
                if str(before.channel.category.id) in data:
                    #Removing old role
                    category = before.channel.category.id
                    role = member.guild.get_role(int(data[str(category)]))
                    CategoryRoleLinked = role
                    try:
                        await member.remove_roles(role)
                        CatRoleAddSuccess = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
                        CatRoleAddSuccess = False

                # Category Linked Role
                data = dis.jopen(f'category\\cat{member.guild.id}')
                if str(after.channel.category.id) in data:
                    #Adding new role
                    category = after.channel.category.id
                    role = member.guild.get_role(int(data[str(category)]))
                    CategoryRoleLinked2 = role
                    try:
                        await member.add_roles(role)
                        CatRoleAddSuccess2 = True
                    except:
                        discord_error_terminal = self.client.get_channel(786307729630298157)
                        dev_error_terminal = self.client.get_channel(786307729630298157)
                        await dev_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        await discord_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
                        CatRoleAddSuccess2 = False
                
                #Logging
                if str(before.channel.guild.id) in logging_channels:
                    logging_channel = logging_channels[str(before.channel.guild.id)]
                    logging_channel = self.client.get_channel(int(logging_channel))
                    logging_embed = discord.Embed(colour=discord.Colour.blue(),title='Member Changed voice channel',description=f'**Before:** {before.channel.mention}\n**+After:** {after.channel.mention}')
                    logging_embed.set_footer(text=f'User ID - {member.id} • {time.strftime("%a %H:%M", localtime())}')
                    logging_embed.set_author(name=f'{member.name}#{member.discriminator}',icon_url=member.avatar_url)

                    if ChannelRoleLinked != None:
                        if RoleAddSuccess == True:
                            embed_value = f'Role: {ChannelRoleLinked.mention} removed\n'
                        elif RoleAddSuccess == False:
                            embed_value = f'Unable to remove role: {ChannelRoleLinked.mention} - Check my permissions\n'

                    if ChannelRoleLinked2 != None:
                        if RoleAddSuccess2 == True:
                            embed_value2 = f'Role: {ChannelRoleLinked2.mention} added\n'
                        elif RoleAddSuccess2 == False:
                            embed_value2 = f'Unable to add role: {ChannelRoleLinked2.mention} - Check my permissions\n'

                    if CatRoleAddSuccess != None:
                        if CatRoleAddSuccess == True:
                            embed_value3 = f'Category Role: {CategoryRoleLinked.mention} removed\n'
                        elif CatRoleAddSuccess == False:
                            embed_value3 = f'Unable to remove role {CategoryRoleLinked.mention} - Check my permissions\n'

                    if CatRoleAddSuccess2 != None:
                        if CatRoleAddSuccess2 == True:
                            embed_value4 = f'Category Role: {CategoryRoleLinked2.mention} added\n'
                        elif CatRoleAddSuccess2 == False:
                            embed_value4 = f'Unable to add role {CategoryRoleLinked2.mention} - Check my permissions\n'

                    if embed_value != '' or embed_value2 != '' or embed_value3 != '' or embed_value4 != '':
                        logging_embed.add_field(name='__**Roles**__', value=f'{embed_value}{embed_value2}{embed_value3}{embed_value4}')
                    await logging_channel.send(embed=logging_embed)


            # Private Channel Management

            data = dis.jopen('private')
            
            try:
                guild_data = data[str(member.guild.id)]

                waiting_rooms = guild_data['waiting_rooms']
                waiting_rooms = dict({y:x for x,y in waiting_rooms.items()})
                # Joining Creation Room
                if after.channel and after.channel.id == guild_data['lobby_id']:
                    # Code for making 2 new channels - Private room (locked for all members, maker gets move members perm), Waiting Room (open to all), Move maker to new channel
                    # Save the IDs of all channels made

                    category = guild_data['category']
                    category = discord.utils.get(member.guild.categories, id=category)

                    vcname = f'{member.display_name} [Private Room]'
                    privateoverwrites = {
                        member.guild.get_role(member.guild.id): discord.PermissionOverwrite(connect=False),
                        member: discord.PermissionOverwrite(connect=True, move_members=True)
                    }

                    privatechannel = await member.guild.create_voice_channel(name=vcname, category=category, overwrites=privateoverwrites)

                    vcname = f'Waiting Room [{member.display_name}]'
                    waitingoverwrites = {
                        member: discord.PermissionOverwrite(move_members=True)
                    }

                    waitingroom = await member.guild.create_voice_channel(name=vcname, category=category, overwrites=waitingoverwrites)

                    await member.move_to(privatechannel)

                    open_rooms = guild_data['open_rooms']
                    open_rooms[str(privatechannel.id)] = str(member.id)
                    guild_data['open_rooms'] = open_rooms

                    waiting_rooms = guild_data['waiting_rooms']
                    waiting_rooms[str(privatechannel.id)] = str(waitingroom.id)
                    guild_data['waiting_rooms'] = waiting_rooms

                    data[str(member.guild.id)] = guild_data

                    dis.jdump('private', data)

                # Leaving Private Room
                if before.channel and str(before.channel.id) in guild_data['open_rooms']:
                    # Closing if empty
                    if len(before.channel.members) == 0:
                        await before.channel.delete()

                        waitingrooms = guild_data['waiting_rooms']
                        waitingroom = waitingrooms[str(before.channel.id)]
                        waitingroom = discord.utils.get(member.guild.voice_channels, id=int(waitingroom))
                        # waitingroom = member.guild.get_channel(id=waitingroom)
                        await waitingroom.delete()

                        open_rooms = guild_data['open_rooms']
                        open_rooms.pop(str(before.channel.id))
                        guild_data['open_rooms'] = open_rooms

                        waitingrooms = guild_data['waiting_rooms']
                        waitingrooms.pop(str(before.channel.id))
                        guild_data['waiting_rooms'] = waitingrooms

                        data[str(member.guild.id)] = guild_data

                        dis.jdump('private', data)

                    # If not empty, ignore
                    else:
                        pass
                
                # JOINING WAITING ROOM
                elif after.channel and str(after.channel.id) in waiting_rooms:
                    open_room = waiting_rooms[str(after.channel.id)]
                    open_rooms = guild_data['open_rooms']
                    open_rooms_owner = open_rooms[open_room]
                    open_rooms_owner = discord.utils.get(member.guild.members, id=int(open_rooms_owner))
                    
                    
                    await open_rooms_owner.send(f'User {member.mention} has joined your waiting room. Move them into the private room if you wish')


                data[str(member.guild.id)] = guild_data

                dis.jdump('private', data)
            except:
                pass

            # Voice Generator Management

            data = dis.jopen('generator')
            
            try:
                guild_data = data[str(member.guild.id)]

                # Joining Generator
                if after.channel and after.channel.id == guild_data['lobby_id']:
                    # Code for making the Voice Channel
                    # Save the IDs of the channels made

                    generator = guild_data['category']
                    generator = discord.utils.get(member.guild.categories, id=generator)

                    vcname = f'{member.display_name}'

                    generatorchannel = await member.guild.create_voice_channel(name=vcname, category=generator)

                    await member.move_to(generatorchannel)

                    open_rooms = guild_data['open_rooms']
                    open_rooms[str(generatorchannel.id)] = str(member.id)
                    guild_data['open_rooms'] = open_rooms

                    data[str(member.guild.id)] = guild_data

                    dis.jdump('generator', data)

                # Leaving Generated Voice Channel
                if before.channel and str(before.channel.id) in guild_data['open_rooms']:
                    # Closing if empty
                    if len(before.channel.members) == 0:
                        await before.channel.delete()

                        open_rooms = guild_data['open_rooms']
                        open_rooms.pop(str(before.channel.id))
                        guild_data['open_rooms'] = open_rooms

                        data[str(member.guild.id)] = guild_data

                        dis.jdump('generator', data)


            except:
                pass
        

            # # Category Linked Channels
            # data = dis.jopen(f'category\\cat{member.guild.id}')
            # # Category: Role

            # # Joining AND category has a role linked
            # if not before.channel and after.channel and str(after.channel.category.id) in data:
            #     category = after.channel.category.id
            #     role = member.guild.get_role(int(data[str(category)]))
            #     CategoryRoleLinked = role
            #     try:
            #         await member.add_roles(role)
            #         RoleAddSuccess = True
            #     except:
            #         discord_error_terminal = self.client.get_channel(786307729630298157)
            #         await discord_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
            #         RoleAddSuccess = False
            
            # # Leaving AND category has a role linked
            # elif before.channel and not after.channel and str(before.channel.category.id) in data:
            #     category = before.channel.category.id
            #     role = member.guild.get_role(int(data[str(category)]))
            #     CategoryRoleLinked = role
            #     try:
            #         await member.remove_roles(role)
            #         RoleAddSuccess = True
            #     except:
            #         discord_error_terminal = self.client.get_channel(786307729630298157)
            #         await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
            #         RoleAddSuccess = False

            # # Changing AND category has a role linked
            # elif before.channel != after.channel:
            #     if str(before.channel.category.id) in data:
            #         #Removing old role
            #         category = before.channel.category.id
            #         role = member.guild.get_role(int(data[str(category)]))
            #         CategoryRoleLinked = role
            #         try:
            #             await member.remove_roles(role)
            #             RoleAddSuccess = True
            #         except:
            #             discord_error_terminal = self.client.get_channel(786307729630298157)
            #             await discord_error_terminal.send(f'Error 107: \nBot does not have required permissions to remove role in server: {member.guild.name} ({member.guild.id})')
            #             RoleAddSuccess = False
                
            #     if str(after.channel.category.id) in data:
            #         #Adding new role
            #         category = after.channel.category.id
            #         role = member.guild.get_role(int(data[str(category)]))
            #         CategoryRoleLinked = role
            #         try:
            #             await member.add_roles(role)
            #             RoleAddSuccess = True
            #         except:
            #             discord_error_terminal = self.client.get_channel(786307729630298157)
            #             await discord_error_terminal.send(f'Error 106: \nBot does not have required permissions to add role in server: {member.guild.name} ({member.guild.id})')
            #             RoleAddSuccess = False
                



def setup(client):
    client.add_cog(voicestate(client))
