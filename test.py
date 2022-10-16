# import asyncio
# from prisma import Prisma


# async def main() -> None:
#     db = Prisma()
#     await db.connect()

#     # guild = await db.guild.create({"id": "thisisadiscordid"})
#     # print(f"created guild: {guild.json(indent=2, sort_keys=True)}")

#     found = await db.guild.find_unique(
#         where={"id": "thisisadiscordid"},
#         include={"links": True, "voiceGenerator": True},
#     )
#     assert found is not None
#     print(f"found guild: {found.json(indent=2, sort_keys=True)}")

#     await db.disconnect()


# if __name__ == "__main__":
#     asyncio.run(main())
