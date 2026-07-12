from discord.ext import commands

from services.processor import process_message


class Router(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        if ctx.valid:
            return

        await process_message(message)


async def setup(bot):
    await bot.add_cog(Router(bot))