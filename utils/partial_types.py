from prisma.models import Guild

Guild.create_partial("GuildOnlyData", exclude_relational_fields=True)
