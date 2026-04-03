# Change bot status
@bot.command()
async def setstatus(ctx, *, text):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"Status updated to: {text}")

# Set bot to idle
@bot.command()
async def idle(ctx):
    await bot.change_presence(status=discord.Status.idle)
    await ctx.send("Status set to idle")

# Set bot to do not disturb
@bot.command()
async def dnd(ctx):
    await bot.change_presence(status=discord.Status.dnd)
    await ctx.send("Status set to Do Not Disturb")

# Set bot to online
@bot.command()
async def online(ctx):
    await bot.change_presence(status=discord.Status.online)
    await ctx.send("Status set to online")


# Say command
@bot.command()
async def say(ctx, *, text):
    await ctx.message.delete()  # deletes your command message (optional)
    await ctx.send(text)
