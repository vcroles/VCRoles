import discord
from discord.ext import commands
from ds import ds
import os
dis = ds()

class utilities(commands.Cog):

    def __init__(self, client):
        self.client = client

    #@commands.Cog.listener()

    @commands.command(aliases=['Info','support','Support','Website','website','invite','Invite','links','Links','server','Server','inv','Inv','Serverinfo','serverinfo'])
    async def info(self, ctx):
        info_embed = discord.Embed(
            colour=discord.Colour.green(),
            description=f'Join the discord support server [here](https://discord.gg/yHU6qcgNPy)\nView the bot\'s website [here](https://bit/ly/vcrole)\nInvite the bot [here](http://bit.ly/39VMGIo)\nIf you like this bot, and want to support us further, consider supporting us on [patreon](https://www.patreon.com/CDESamBots)'
        )
        await ctx.send(embed=info_embed)
        
        dis.counter('info')

    @commands.command(aliases=['Help','commands','Commands','vc','HELP'])
    async def help(self, ctx, commands='general'):
        
        prefix = dis.get_prefix(ctx.message)

        embed = discord.Embed(
            colour = discord.Colour.dark_grey(),
            title = f'__VC Roles Help - {commands}__',
            description = 'Commands and how to use them:\nYou do not need to include \'[]\' in any commands\nFor a more detailed overview of the commands, visit our [website](https://sites.google.com/view/vc-discord-bot/commands)'
        )

        utility_alias = ['changeprefix', 'prefix', 'Changeprefix', 'Prefix','Logging','logging','audits','Audits','Utility','utility','logs','Logs', 'linked', 'Linked', 'list']
        link_alias = ['vclink', 'vcunlink', 'link', 'unlink', 'Vclink', 'Vcunlink', 'Link', 'Unlink','linkall','unlinkall','Linking','linking','Unlinking','unlinking']
        mute_alias = ['mute', 'vcmute', 'unmute', 'vcunmute', 'Mute', 'Unmute', 'Vcmute', 'Vcunmute']
        deafen_alias = ['deafen', 'vcdeafen', 'undeafen', 'vcundeafen', 'Deafen', 'Vcdeafen', 'Undeafen', 'Vcundeafen']
        private_alias = ['Private','private','Room','room','Privateroom','privateroom']
        tts_alias = ['tts','TTS','Tts','ttsetup','Ttssetup']
        generator_alias = ['generator', 'generatorsetup', 'Generator', 'voicegen']
        category_alias = ['catlink', 'Catlink', 'catunlink', 'Catunlink', 'category', 'Category']
        

        if commands == 'general':
            embed.add_field(name=f'**{prefix}help**', value=f'Brings up this message, and information about other commands\nUsage: **{prefix}help [topic]**\n**Topics:** link, utility, vcmute, vcdeafen, privateroom, tts, linked, generator, category', inline=False)
            embed.add_field(name=f'**{prefix}ping**', value=f'The bot responds with its ping, can be used to see if the bot is online', inline=False)
            embed.add_field(name=f'**{prefix}info**', value=f'Gives the link to the support server, the bot\'s website, and invite link', inline=False)
            embed.add_field(name=f'**{prefix}stats**', value=f'Will give you some stats about the bot',inline=False)
            # embed.add_field(name=f'**{prefix}logging**', value=f'Use this command to set the channel for voice channel connection logs to be sent to.\nUsage: **{prefix}logging set #channel** - Used to set the logging channel \n**{prefix}logging remove #channel-mention** - Used to remove the logging channel', inline=False)
            # embed.add_field(name=f'**{prefix}changeprefix**', value=f'Allows you to change the bot prefix\nUsage: **{prefix}changeprefix [prefix]**', inline=False)
            # embed.add_field(name=f'**{prefix}vclink**', value=f'Links a voice channel and a role, so when you join the VC you get the role\nUsage: **{prefix}vclink @role-mention**', inline=False)
            # embed.add_field(name=f'**{prefix}vcunlink**', value=f'Unlinks a voice channel from a role\nUsage: **{prefix}vcunlink**', inline=False)
            # embed.add_field(name=f'**{prefix}linkall**', value=f'Links all voice channels with a role, so when you join any VC you get the role\nUsage:**{prefix}linkall @role-mention**', inline=False)
            # embed.add_field(name=f'**{prefix}unlinkall**', value=f'Unlinks all voice channels from the role linked with the **{prefix}linkall** command', inline=False)
            # embed.add_field(name=f'**{prefix}vcmute / {prefix}vcunmute**', value=f'Mutes/Unmutes everyone in a voice channel', inline=False)
            # embed.add_field(name=f'**{prefix}vcdeafen / {prefix}vcundeafen**', value=f'Deafens/Undeafens everyone in a voice channel', inline=False)
        
        elif commands in utility_alias:
            embed.add_field(name=f'**{prefix}changeprefix**', value=f'Allows you to change the bot prefix to anything\nUsage: **{prefix}changeprefix [prefix]**', inline=False)
            embed.add_field(name=f'**{prefix}logging**', value=f'Use this command to set the channel for voice channel logs to go to\nUsage: \n**{prefix}logging set #channel** - Used to set the logging channel \n**{prefix}logging remove #channel-mention** - Used to remove the logging channel', inline=False)
            embed.add_field(name=f'**{prefix}linked**', value=f'Lists all the linked channels, and their roles', inline=False)

        elif commands in link_alias:
            embed.add_field(name=f'**{prefix}vclink**', value=f'Links a voice channel and a role, so when you join the VC you get the role\nUsage:**{prefix}vclink @role-mention**\nThe command will send an embed message with instructions', inline=False)
            embed.add_field(name=f'**{prefix}vcunlink**', value=f'Unlinks a voice channel from a role\nUsage: **{prefix}vcunlink**\nThe command will send an embed message with instructions', inline=False)
            embed.add_field(name=f'**{prefix}linkall**', value=f'Links all voice channels with a role, so when you join any VC you get the role\nUsage:**{prefix}linkall @role-mention**', inline=False)
            embed.add_field(name=f'**{prefix}unlinkall**', value=f'Unlinks all voice channels from the role linked with the **{prefix}linkall** command', inline=False)
            embed.add_field(name=f'Old commands:', value=f'We still support linking and unlinking with the old commands (if you want to), these can be accessed by using **{prefix}oldvclink** or **{prefix}oldvcunlink**', inline=False)

        elif commands in mute_alias:
            embed.add_field(name=f'**{prefix}vcmute**', value=f'Mutes everyone in a voice channel\nUsage: **{prefix}vcmute** - mutes everyone but you in the vc channel\n **{prefix}vcmute all** - mutes everyone in the vc channel\n **{prefix}vcmute [channel_id]** - mutes everyone in the voice channel, you dont have to be in the voice channel', inline=False)
            embed.add_field(name=f'**{prefix}vcunmute**', value=f'Unmutes everyone in a voice channel\nUsage: **{prefix}vcunmute** - unmutes everyone in the vc channel\n **{prefix}vcunmute [channel_id]** - unmutes everyone in the voice channel, you dont have to be in the voice channel', inline=False)

        elif commands in deafen_alias:
            embed.add_field(name=f'**{prefix}vcdeafen**', value=f'Deafens everyone in a voice channel\nUsage: **{prefix}vcdeafen** - deafen everyone but you in the vc channel\n **{prefix}vcdeafen all** - deafens everyone in the vc channel\n **{prefix}vcdeafen [channel_id]** - deafens everyone in the voice channel, you dont have to be in the voice channel', inline=False)
            embed.add_field(name=f'**{prefix}vcundeafen**', value=f'Undeafens everyone in a voice channel\nUsage: **{prefix}vcundeafen** - undeafens everyone in the vc channel\n **{prefix}vcundeafen [channel_id]** - undeafens everyone in the voice channel, you dont have to be in the voice channel', inline=False)

        elif commands in private_alias:
            embed.add_field(name='** **', value=f'Private Rooms can be used to create a private voice call where the owner/creator can accept people to join the call. To use this join the lobby voice call and you will be moved to your own private room. When someone joins your waiting room reply to the bots dm with accept and they will be moved to the room.', inline=False)
            embed.add_field(name=f'**{prefix}privatesetup**', value=f'Will create the category and lobby Voice Channel for the private rooms.', inline=False)
            embed.add_field(name=f'**{prefix}privateremove**', value=f'Will remove all setup information and category and channels assosiated with the private rooms', inline=False)

        elif commands in tts_alias:
            embed.add_field(name='** **', value=f'The TTS command can be used to allow users to send messages which the bot will speak in the voice channel the command was called from.', inline=False)
            embed.add_field(name=f'**{prefix}ttssetup**', value=f'Use this to setup TTS and enable it\nUsage: **{prefix}ttssetup** - brings up the help message', inline=False)
            embed.add_field(name=f'**{prefix}tts**', value=f'Use this command to speak a message.\nUsage: **{prefix}tts [message]**', inline=False)
            embed.add_field(name=f'**{prefix}stop**', value=f'Use this command to stop the current tts message.', inline=False)
        
        elif commands in generator_alias:
            embed.add_field(name=f'**{prefix}generator**', value=f'Creates a voice channel generator & category\nUsage: **{prefix}generator [optional-name]**', inline=False)
        
        elif commands in category_alias:
            embed.add_field(name=f'**{prefix}catlink**', value=f'Links all channels in a category to a role\nUsage: **{prefix}catlink @role-mention**', inline=False)
            embed.add_field(name=f'**{prefix}catunlink**', value=f'Unlinks a category from a role\nUsage: **{prefix}catunlink**', inline=False)

        else:
            commands = ('general')
            embed = discord.Embed(
                colour = discord.Colour.dark_grey(),
                title = f'__VC Roles Help - {commands}__',
                description = 'Commands and how to use them:'
            )
            embed.add_field(name=f'**{prefix}help**', value=f'Brings up this message, and information about other commands\nUsage: **{prefix}help [topic]**\n**Topics:** link, utility, vcmute, vcdeafen, privateroom, tts, linked, generator, category', inline=False)
            embed.add_field(name=f'**{prefix}ping**', value=f'The bot responds with its ping, can be used to see if the bot is online', inline=False)
            embed.add_field(name=f'**{prefix}info**', value=f'Gives the link to the support server, the bot\'s website, and invite link', inline=False)
            embed.add_field(name=f'**{prefix}stats**', value=f'Will give you some stats about the bot',inline=False)
            # embed.add_field(name=f'**{prefix}logging**', value=f'Use this command to set the channel for voice channel connection logs to be sent to.\nUsage: **{prefix}logging set #channel** - Used to set the logging channel \n**{prefix}logging remove #channel-mention** - Used to remove the logging channel', inline=False)
            # embed.add_field(name=f'**{prefix}changeprefix**', value=f'Allows you to change the bot prefix\nUsage: **{prefix}changeprefix [prefix]**', inline=False)
            # embed.add_field(name=f'**{prefix}vclink**', value=f'Links a voice channel and a role, so when you join the VC you get the role\nUsage: **{prefix}vclink @role-mention**', inline=False)
            # embed.add_field(name=f'**{prefix}vcunlink**', value=f'Unlinks a voice channel from a role\nUsage: **{prefix}vcunlink**', inline=False)
            # embed.add_field(name=f'**{prefix}linkall**', value=f'Links all voice channels with a role, so when you join any VC you get the role\nUsage:**{prefix}linkall @role-mention**', inline=False)
            # embed.add_field(name=f'**{prefix}unlinkall**', value=f'Unlinks all voice channels from the role linked with the **{prefix}linkall** command', inline=False)
            # embed.add_field(name=f'**{prefix}vcmute / {prefix}vcunmute**', value=f'Mutes/Unmutes everyone in a voice channel', inline=False)
            # embed.add_field(name=f'**{prefix}vcdeafen / {prefix}vcundeafen**', value=f'Deafens/Undeafens everyone in a voice channel', inline=False)

        embed.add_field(name='** **',value='Thank you for using this bot, if you need any help, ask in our [support server](https://discord.gg/yHU6qcgNPy)\nFeel free to take a look at our [website](https://bit.ly/vcrole)\nTo invite the bot [click here](http://bit.ly/39VMGIo)', inline=False)

        await ctx.send(embed=embed)

        dis.counter('help')

    @commands.command(aliases=['Ping'])
    async def ping(self, ctx):
        ping_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Pong! {round(self.client.latency *1000)} ms'
        )
        await ctx.send(embed=ping_embed)
        # await ctx.send(f'Pong! {round(client.latency *1000)} ms')

        dis.counter('ping')
    
    @commands.command(aliases=['cde','dev','Dev'])
    async def CDE(self, ctx):
        CDE_embed = discord.Embed(colour=0x03f8fc,title='CDE The Dev',description='Congratulations You Found an easter egg! Join the discord [support server](https://discord.gg/yHU6qcgNPy) to get a special role and a well done from me!')
        CDE_embed.set_footer(text='P.S. I heard that CDE is the best dev (much better than that Sam bloke)',icon_url='https://cdn.discordapp.com/attachments/758392649979265028/802269078312058910/body_10.png')
        await ctx.send(embed=CDE_embed)
        
        if ctx.author.id == 652797071623192576 or ctx.author.id == 602235481459261440:
            pass
        else:
            dis.counter('CDE')

    @commands.command(aliases=['Sam','BestDev','BetterDev','CDEDoesSmell'])
    async def sam(self, ctx):
        Sam_embed = discord.Embed(
            colour=0x00BEFF,
            title='Sam The Dev',
            description='Congratulations You Found my secret command! Join the discord [support server](https://discord.gg/yHU6qcgNPy) to get custom role and a well done from me!'
        )
        Sam_embed.set_footer(text='<- Spinny Logo ooooo (cde doesn\'t have one)',icon_url='https://cdn.discordapp.com/avatars/602235481459261440/a_0067c1df6ab1e300db01d9d4762f8fa1.gif?size=1024')
        await ctx.send(embed=Sam_embed)

        if ctx.author.id == 602235481459261440 or ctx.author.id == 652797071623192576:
            pass
        else:
            dis.counter('sam')

    @commands.command(aliases=['Changeprefix','prefix'])
    @commands.has_permissions(administrator=True)
    async def changeprefix(self, ctx, prefix):
        prefixes = dis.jopen("prefixes")
        
        prefixes[str(ctx.guild.id)] = prefix

        dis.jdump("prefixes", prefixes)

        pre_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Command prefix changed to {prefix}'
        )
        await ctx.send(embed=pre_embed)

        # await ctx.send(f'Command prefix changed to: {prefix}')
        print(f'Command prefix on server {ctx.guild.id} changed to {prefix}')
        discord_terminal = self.client.get_channel(791253552139206667)
        await discord_terminal.send(f'Command prefix on server {ctx.guild.name} ({ctx.guild.id}) changed to **{prefix}**')

        dis.counter('prefix')

    @commands.command(aliases=['Linked', 'list', 'List'])
    @commands.has_permissions(administrator=True)
    async def linked(self, ctx):
        data = dis.jopen(ctx.guild.id)
        link_embed = discord.Embed(colour=discord.Color.blue(),title=f'The linked Voice Channels in {ctx.guild.name}:')
        # Voice Channels
        voice_channel_list, values = zip(*data.items())
        voice_channel_list = list(voice_channel_list)
        if 'all' in voice_channel_list:
            role_ = data["all"]
            role_ = ctx.guild.get_role(int(role_))
            link_embed.add_field(name=f'  All Linked Role', value=f'Role - {role_.mention}', inline=False)
        try:
            for name_ in voice_channel_list:
                role_ = data[name_]
                name_ = self.client.get_channel(int(name_))
                role_ = ctx.guild.get_role(int(role_))
                link_embed.add_field(name=f'  {name_.name}', value=f'Role - {role_.mention}', inline=True)
        except:
            pass
        #Categories
        data = dis.jopen(f'category/cat{ctx.guild.id}')
        voice_channel_list, values = zip(*data.items())
        voice_channel_list = list(voice_channel_list)
        link_embed.add_field(name='__Linked Categories__',value= '** **',inline=False)
        for name_ in voice_channel_list:
                role_ = data[name_]
                name_ = self.client.get_channel(int(name_))
                role_ = ctx.guild.get_role(int(role_))
                link_embed.add_field(name=f'  {name_.name}', value=f'Role - {role_.mention}', inline=True)


        await ctx.send(embed=link_embed)
        

def setup(client):
    client.add_cog(utilities(client))