import discord
from discord.ext import commands
from discord import app_commands
from io import StringIO

from config import settings
from services.permissions import has_staff_role


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="create_ticket"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild

        channel_name = (
            f"ticket-{interaction.user.name}"
            .lower()
            .replace(" ", "-")
        )

        existing = discord.utils.get(
            guild.channels,
            name=channel_name
        )

        if existing:
            await interaction.response.send_message(
                f"You already have {existing.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            )
        }

        for role_id in settings.STAFF_ROLE_IDS:
            role = guild.get_role(role_id)

            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="Ticket Created",
            description=(
                f"{interaction.user.mention}\n"
                "Describe your issue and a staff member will check the ticket shortly."
            ),
            color=0x000000
        )

        await channel.send(
            "@here",
            embed=embed,
            view=TicketView()
        )

        await interaction.response.send_message(
            f"Ticket created: {channel.mention}",
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=CloseConfirmView(),
            ephemeral=True
        )


class CloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.red
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        transcript_lines = []

        async for msg in interaction.channel.history(
            limit=None,
            oldest_first=True
        ):
            content = msg.content if msg.content else "[Embed/Attachment]"

            transcript_lines.append(
                f"[{msg.created_at}] {msg.author}: {content}"
            )

        transcript_text = "\n".join(transcript_lines)

        file = discord.File(
            StringIO(transcript_text),
            filename=f"{interaction.channel.name}.txt"
        )

        log_channel = None
        if settings.TRANSCRIPT_LOG_CHANNEL_ID:
            log_channel = interaction.client.get_channel(
                settings.TRANSCRIPT_LOG_CHANNEL_ID
            )

        if log_channel:
            embed = discord.Embed(
                title="Ticket Closed",
                color=0x000000
            )

            embed.add_field(
                name="Channel",
                value=interaction.channel.name,
                inline=False
            )

            embed.add_field(
                name="Closed By",
                value=interaction.user.mention,
                inline=False
            )

            await log_channel.send(
                embed=embed,
                file=file
            )
        else:
            print(
                "No TRANSCRIPT_LOG_CHANNEL_ID configured - transcript not logged",
                flush=True
            )

        await interaction.response.send_message(
            "Closing ticket...",
            ephemeral=True
        )

        await interaction.channel.delete()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.gray
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Ticket closure cancelled.",
            ephemeral=True
        )


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Persistent views need to be re-registered every startup so the
        # buttons keep working after a restart/redeploy.
        bot.add_view(TicketPanelView())
        bot.add_view(TicketView())
        print("TICKETS COG INITIALIZED", flush=True)

    @app_commands.command(name="panel", description="Post the ticket panel")
    async def panel(self, interaction: discord.Interaction):
        if not has_staff_role(interaction.user):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Support Tickets",
            description="Press the button below to create a ticket.",
            color=0x000000
        )

        await interaction.response.send_message(
            embed=embed,
            view=TicketPanelView()
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))