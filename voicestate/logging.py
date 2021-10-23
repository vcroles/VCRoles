import json
import discord
import datetime
from bot import MyClient

class logging():

    def __init__(self, client: MyClient):
        self.client = client

    async def log_join(self, after: discord.VoiceState, member: discord.Member, v, s, c, a, p):
        data = self.client.jopen('Data/guild_data',str(member.guild.id))

        if data[str(member.guild.id)]['logging']:
            try:
                channel = data[str(member.guild.id)]['logging']
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(title=f'Member joined voice channel', description=f'{member} joined {after.channel.mention}',color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
                logging_embed.set_footer(text=f'User ID - {member.id}')
                logging_embed.set_author(name=f'{member.name}#{member.discriminator}',icon_url=member.avatar.url)
                
                va = ''

                if v:
                    va += 'Channel: '
                    for role in v:
                        va += role.mention + ' '
                    va += '\n'
                
                if s:
                    va += 'Channel: '
                    for role in s:
                        va += role.mention + ' '
                    va += '\n'
                
                if c:
                    va += 'Category: '
                    for role in c:
                        va += role.mention + ' '
                    va += '\n'
                
                if a:
                    va += 'All: '
                    for role in a:
                        va += role.mention + ' '
                    va += '\n'

                if p:
                    va += 'Permanent: '
                    for role in p:
                        va += role.mention + ' '
                    va += '\n'

                if va:
                    va = va[:-1] # Removes trailing newline

                if v or s or c or a or p:
                    logging_embed.add_field(name='Roles Added:', value=va, inline=False)

                await channel.send(embed=logging_embed)
            except:
                return

    async def log_leave(self, before: discord.VoiceState, member: discord.Member, v, s, c, a):
        data = self.client.jopen('Data/guild_data',str(member.guild.id))


        if data[str(member.guild.id)]['logging']:
            try:
                channel = data[str(member.guild.id)]['logging']
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(title=f'Member left voice channel', description=f'{member} left {before.channel.mention}',color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
                logging_embed.set_footer(text=f'User ID - {member.id}')
                logging_embed.set_author(name=f'{member.name}#{member.discriminator}',icon_url=member.avatar.url)
                
                va = ''

                if v:
                    va += 'Channel: '
                    for role in v:
                        va += role.mention + ' '
                    va += '\n'
                
                if s:
                    va += 'Channel: '
                    for role in s:
                        va += role.mention + ' '
                    va += '\n'
                
                if c:
                    va += 'Category: '
                    for role in c:
                        va += role.mention + ' '
                    va += '\n'
                
                if a:
                    va += 'All: '
                    for role in a:
                        va += role.mention + ' '
                    va += '\n'

                if va:
                    va = va[:-1] # Removes trailing newline

                if v or s or c or a:
                    logging_embed.add_field(name='Roles Removed:', value=va, inline=False)

                await channel.send(embed=logging_embed)
            except:
                return

    async def log_change(self, before: discord.VoiceState, after:discord.VoiceState, member: discord.Member, v, s, c, v2, s2, c2):
        data = self.client.jopen('Data/guild_data',str(member.guild.id))
        
        if data[str(member.guild.id)]['logging']:
            try:
                channel = data[str(member.guild.id)]['logging']
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(title=f'Member moved voice channel', description=f'**Before:** {before.channel.mention}\n**+After:** {after.channel.mention}',color=discord.Color.blue(), timestamp=datetime.datetime.utcnow())
                logging_embed.set_footer(text=f'User ID - {member.id}')
                logging_embed.set_author(name=f'{member.name}#{member.discriminator}',icon_url=member.avatar.url)
                
                va = ''

                if v:
                    va += 'Channel: '
                    for role in v:
                        va += role.mention + ' '
                    va += '\n'
                
                if s:
                    va += 'Channel: '
                    for role in s:
                        va += role.mention + ' '
                    va += '\n'
                
                if c:
                    va += 'Category: '
                    for role in c:
                        va += role.mention + ' '
                    va += '\n'
                
                if va:
                    va = va[:-1] # Removes trailing newline

                if v or s or c:
                    logging_embed.add_field(name='Roles Removed:', value=va, inline=False)

                va = ''

                if v2:
                    va += 'Channel: '
                    for role in v2:
                        va += role.mention + ' '
                    va += '\n'
                
                if s2:
                    va += 'Channel: '
                    for role in s2:
                        va += role.mention + ' '
                    va += '\n'
                
                if c2:
                    va += 'Category: '
                    for role in c2:
                        va += role.mention + ' '
                    va += '\n'
                
                if va:
                    va = va[:-1] # Removes trailing newline

                if v or s or c:
                    logging_embed.add_field(name='Roles Added:', value=va, inline=False)

                await channel.send(embed=logging_embed)
            except:
                return