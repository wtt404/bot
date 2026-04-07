@bot.event
async def on_message(message):
    if message.author.bot or message.author == bot.user:
        return

    urls = list(set(re.findall(r"(https?://\S+)", message.content)))

    for url in urls:
        if "twitter.com" in url or "x.com" in url or "fxtwitter.com" in url:
            text = get_text(url)
            translated = translate(text)

            # Only send translation if NOT English
            if translated:
                embed = discord.Embed(description=translated, color=0x000000)
                await message.channel.send(embed=embed)

            return  # stop after first valid link

    await bot.process_commands(message)
