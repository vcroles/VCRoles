from typing import Tuple
import aiohttp
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import config
from utils.client import VCRolesClient
import datetime as dt
from prisma.enums import VoiceGeneratorOption
import discord
from views.url import Premium as PremiumView


class Premium(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.premium_check.start()

    async def cog_unload(self):
        self.premium_check.cancel()

        return await super().cog_unload()

    premium_commands = app_commands.Group(
        name="premium", description="Premium commands"
    )

    async def verify_license(self, license_key: str) -> Tuple[bool, int]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.gumroad.com/v2/licenses/verify",
                json={
                    "license_key": license_key,
                    "product_id": config.GUMROAD_PRODUCT_ID,
                },
            ) as r:
                res = await r.json()
                if res["success"]:
                    if res["purchase"]["variants"] == "(Premium)":
                        return True, 1
                    elif res["purchase"]["variants"] == "(Premium Plus)":
                        return True, 3
                    elif res["purchase"]["variants"] == "(Premium Pro)":
                        return True, 10
                    else:
                        return False, 0
                else:
                    return False, 0

    @premium_commands.command(name="activate")
    async def premium_activate(self, interaction: Interaction, license_key: str):
        """Activate your premium subscription"""
        valid, max_guilds = await self.verify_license(license_key)
        if valid:
            await interaction.response.send_message(
                f"Your license is valid! You can now add up to {max_guilds} guilds to your premium subscription."
            )
            if not await self.client.db.db.premium.find_first(
                where={"licenseKey": license_key}
            ):
                await self.client.db.db.premium.create(
                    data={
                        "licenseKey": license_key,
                        "maxGuilds": max_guilds,
                        "userId": str(interaction.user.id),
                    },
                )
            else:
                await self.client.db.db.premium.update(
                    where={"licenseKey": license_key},
                    data={"userId": str(interaction.user.id), "maxGuilds": max_guilds},
                )
            await self.client.ar.hset("premium", str(interaction.user.id), 1)
        else:
            await interaction.response.send_message("Invalid license key.")

    @premium_commands.command(name="add")
    async def premium_add(self, interaction: Interaction):
        """PREMIUM - Add a guild to your premium subscription"""
        await interaction.response.defer()
        # check if user is premium
        p = await self.client.db.db.premium.find_first(
            where={"userId": str(interaction.user.id)},
            include={"guilds": True},
        )
        if not p:
            await interaction.followup.send(
                "You do not have a premium subscription. Activate one with `/premium activate <license_key>`."
            )
            return
        # check if guild exists
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a guild.")
            return
        guild_id = interaction.guild.id
        d_guild = interaction.guild
        # check if guild is already premium
        guild = await self.client.db.get_guild_data(guild_id)
        if guild.premium:
            await interaction.followup.send("This guild is already premium.")
            return
        # check if user has max guilds
        if p.guilds and len(p.guilds) >= p.maxGuilds:
            await interaction.followup.send(
                "You have reached the maximum number of guilds you can add to your premium subscription."
            )
            return
        # add guild to premium
        await self.client.db.db.guild.update(
            where={"id": str(guild_id)},
            data={
                "premium": True,
                "Premium": {"connect": {"id": p.id}},
            },
        )
        self.client.db.remove_guild_from_cache(guild_id)
        await interaction.followup.send(
            f"Added {d_guild.name} to your premium subscription."
        )

    @premium_commands.command(name="remove")
    async def premium_remove(self, interaction: Interaction):
        """PREMIUM - Remove a guild from premium. CAUTION: Premium features instantly removed."""
        await interaction.response.defer()
        # check if user is premium
        p = await self.client.db.db.premium.find_first(
            where={"userId": str(interaction.user.id)},
            include={"guilds": True},
        )
        if not p:
            await interaction.followup.send(
                "You do not have a premium subscription. Activate one with `/premium activate <license_key>`."
            )
            return
        # check if guild exists
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a guild.")
            return
        guild_id = interaction.guild.id
        d_guild = interaction.guild
        # check if guild is premium
        guild = await self.client.db.get_guild_data(guild_id)
        if not guild.premium:
            await interaction.followup.send("This guild is not premium.")
            return
        # remove guild from premium
        await self.remove_premium(guild_id)
        await interaction.followup.send(
            f"Removed {d_guild.name} from your premium subscription."
        )

    @premium_commands.command(name="list")
    async def premium_list(self, interaction: Interaction):
        """PREMIUM - List all guilds you have added to your premium subscription"""
        # check if user is premium
        p = await self.client.db.db.premium.find_first(
            where={"userId": str(interaction.user.id)},
            include={"guilds": True},
        )
        if not p:
            await interaction.response.send_message(
                "You do not have a premium subscription. Activate one with `/premium activate <license_key>`."
            )
            return
        # list guilds
        if not p.guilds:
            await interaction.response.send_message(
                "You have no guilds added to your premium subscription."
            )
            return
        guilds: list[str] = []
        for guild in p.guilds:
            d_guild = self.client.get_guild(int(guild.id))
            if d_guild:
                guilds.append(d_guild.name)
            else:
                guilds.append(guild.id)
        await interaction.response.send_message(
            f"Guilds you have added to your premium subscription: {', '.join(guilds)}"
        )

    @premium_commands.command(name="info")
    async def premium_info(self, interaction: Interaction):
        """PREMIUM - Get information about your premium subscription"""
        # check if user is premium
        p = await self.client.db.db.premium.find_first(
            where={"userId": str(interaction.user.id)},
            include={"guilds": True},
        )
        if not p:
            await interaction.response.send_message(
                "You do not have a premium subscription. Activate one with `/premium activate <license_key>`."
            )
            return
        # get info
        tier = (
            "Premium"
            if p.maxGuilds == 1
            else "Premium Plus"
            if p.maxGuilds == 3
            else "Premium Pro"
            if p.maxGuilds == 10
            else "Custom Premium"
        )
        await interaction.response.send_message(
            f"Your premium subscription ({tier}) has {p.maxGuilds} slots and you have added {len(p.guilds) if p.guilds else 0} guilds."
        )

    @premium_commands.command(name="buy")
    async def premium_buy(self, interaction: Interaction):
        """Purchase a premium subscription"""
        await interaction.response.send_message(
            "You can purchase a premium subscription at https://premium.vcroles.com/l/vcroles",
            view=PremiumView(),
        )

    async def remove_premium(self, guild_id: int):
        """Remove premium from a guild"""
        await self.client.db.db.guild.update(
            where={"id": str(guild_id)},
            data={
                "premium": False,
                "Premium": {"disconnect": True},
            },
        )
        self.client.db.remove_guild_from_cache(guild_id)
        generators = await self.client.db.db.voicegenerator.find_many(
            where={"guildId": str(guild_id)},
        )
        while len(generators) > 1:
            await self.client.db.db.voicegenerator.delete(
                where={"id": str(generators[0].id)}
            )
            generators.pop(0)
        if not generators:
            return
        generator = generators[0]
        if VoiceGeneratorOption.TEXT in generator.defaultOptions:
            generator.defaultOptions.remove(VoiceGeneratorOption.TEXT)
            await self.client.db.db.voicegenerator.update(
                where={"id": str(generators[0].id)},
                data={
                    "defaultOptions": generator.defaultOptions,
                },
            )
        if generator.hideAtLimit:
            await self.client.db.db.voicegenerator.update(
                where={"id": str(generators[0].id)},
                data={
                    "hideAtLimit": False,
                },
            )

    @tasks.loop(time=[dt.time(hour=0, minute=0)])
    async def premium_check(self):
        """Check if premium subscriptions have expired"""
        # get all premium subscriptions
        premium = await self.client.db.db.premium.find_many(
            include={"guilds": True},
        )
        for p in premium:
            active, max_guilds = await self.verify_license(p.licenseKey)
            if not active:
                if p.strike >= 3:
                    for guild in p.guilds or []:
                        await self.remove_premium(int(guild.id))
                    await self.client.db.db.premium.delete(where={"id": p.id})
                    await self.client.ar.hset(
                        "premium",
                        p.userId,
                        0,
                    )
                    try:
                        user = await self.client.fetch_user(int(p.userId))
                    except discord.NotFound:
                        continue
                    except discord.HTTPException:
                        continue
                    try:
                        await user.send(
                            "Your premium subscription has expired and has been removed. You can reactivate your subscription with `/premium activate <license_key>`. Or you can buy a new subscription with `/premium buy`."
                        )
                    except discord.Forbidden:
                        pass
                else:
                    await self.client.db.db.premium.update(
                        where={"id": p.id},
                        data={"strike": p.strike + 1},
                    )
                    try:
                        user = await self.client.fetch_user(int(p.userId))
                    except discord.NotFound:
                        continue
                    except discord.HTTPException:
                        continue
                    try:
                        await user.send(
                            f"Your premium subscription has expired. You have {3 - p.strike} days left before your guilds are removed from your subscription. This will cause data loss and premium features will stop working. https://cde90.gumroad.com/l/vcroles"
                        )
                    except discord.Forbidden:
                        pass
            else:
                await self.client.db.db.premium.update(
                    where={"id": p.id},
                    data={"maxGuilds": max_guilds, "strike": 0},
                )

    @premium_check.before_loop
    async def before_premium_check(self):
        await self.client.wait_until_ready()


async def setup(client: VCRolesClient):
    await client.add_cog(Premium(client))
