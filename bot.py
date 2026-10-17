import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
FEEDBACK_CHANNEL_ID = int(os.getenv("FEEDBACK_CHANNEL_ID", "0") or 0)
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "0") or 0)
PRIVATE_CATEGORY_ID = int(os.getenv("PRIVATE_CATEGORY_ID", "0") or 0)
BRAND_NAME = os.getenv("BRAND_NAME", "Clash Design")
MAX_IMAGE_BYTES = 10 * 1024 * 1024

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def configured(value: int) -> bool:
    return value > 0


class ReviewPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Leave Review",
        style=discord.ButtonStyle.primary,
        emoji="✍️",
        custom_id="clashdesign:leave_review",
    )
    async def leave_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not interaction.user:
            return await interaction.response.send_message(
                "Please use this button inside the server.", ephemeral=True
            )

        if not configured(FEEDBACK_CHANNEL_ID):
            return await interaction.response.send_message(
                "The feedback channel is not configured yet. Ask a server administrator.", ephemeral=True
            )

        guild = interaction.guild
        existing = discord.utils.get(
            guild.text_channels, name=f"review-{interaction.user.id}"
        )
        if existing:
            return await interaction.response.send_message(
                f"You already have a private review channel: {existing.mention}",
                ephemeral=True,
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                manage_channels=True, manage_messages=True, attach_files=True, embed_links=True
            ),
        }

        category = guild.get_channel(PRIVATE_CATEGORY_ID) if configured(PRIVATE_CATEGORY_ID) else None
        try:
            private_channel = await guild.create_text_channel(
                name=f"review-{interaction.user.id}",
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                topic="review submission. Do not share this channel publicly.",
                reason="feedback submission",
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "I don't have permission to create private channels. Please contact a server administrator.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            f"Your submission channel is ready: {private_channel.mention}\n"
            "Only you and the bot can see it. Send **one message** containing your review text "
            "and optionally attach an image, then press **Publish Review** below. "
            "Your Discord identity will not be included in the public post.",
            ephemeral=True,
        )

        embed = discord.Embed(
            title="Submit Your Review",
            description=(
                f"Share your honest feedback about **{BRAND_NAME}** bases and services.\n\n"
                "**How to submit**\n"
                "1. Send your review as a message in this private channel.\n"
                "2. You may attach one image (optional, max 10 MB).\n"
                "3. Press **Publish Review** below.\n\n"
                
            ),
            color=discord.Color.from_rgb(139, 64, 255),
        )
        embed.set_footer(text=f"{BRAND_NAME} •  Feedback")
        await private_channel.send(embed=embed, view=PrivateReviewControls())
        await private_channel.send(
            f"{interaction.user.mention} **Send your review in your next message.** "
            "If you need to change it, send a new message before publishing."
        )


class PrivateReviewControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Publish Review",
        style=discord.ButtonStyle.success,
        emoji="📨",
        custom_id="clashdesign:publish_review",
    )
    async def publish_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("review-"):
            return await interaction.response.send_message(
                "This button only works in a private review channel.", ephemeral=True
            )

        expected_name = f"review-{interaction.user.id}"
        if channel.name != expected_name:
            return await interaction.response.send_message(
                "This is not your private review channel.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        submission = None
        async for message in channel.history(limit=50, oldest_first=False):
            if message.author.id == interaction.user.id and (message.content.strip() or message.attachments):
                submission = message
                break

        if submission is None:
            return await interaction.followup.send(
                "I couldn't find your review. Send a message with your feedback first.", ephemeral=True
            )

        review_text = submission.content.strip()
        if not review_text:
            review_text = " "
        image_url = None
        for attachment in submission.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                if attachment.size > MAX_IMAGE_BYTES:
                    return await interaction.followup.send(
                        "Your image is over 10 MB. Please upload a smaller image and submit again.",
                        ephemeral=True,
                    )
                image_url = attachment.url
                break

        if len(review_text) > 3900:
            return await interaction.followup.send(
                "Your review is too long. Please keep it under 3,900 characters.", ephemeral=True
            )

        target = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID) if interaction.guild else None
        if not isinstance(target, discord.TextChannel):
            return await interaction.followup.send(
                "The public feedback channel isn't configured correctly. Please contact an administrator.",
                ephemeral=True,
            )

        public_embed = discord.Embed(
            title="♛ Customer Review",
            description=review_text,
            color=discord.Color.from_rgb(139, 64, 255),
        )
        if image_url:
            public_embed.set_image(url=image_url)
        public_embed.set_footer(text=f"{BRAND_NAME} • Feedback")

        try:
            await target.send(
                embed=public_embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                "I can't post in the feedback channel. Please contact an administrator.", ephemeral=True
            )

        await interaction.followup.send(
            "Your review has been published anonymously. Thank you for supporting the community!",
            ephemeral=True,
        )
        await asyncio.sleep(3)
        try:
            await channel.delete(reason="Review submitted successfully")
        except discord.HTTPException:
            pass

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="✖️",
        custom_id="clashdesign:cancel_review",
    )
    async def cancel_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if isinstance(channel, discord.TextChannel) and channel.name == f"review-{interaction.user.id}":
            await interaction.response.send_message(
                "Your private review channel will be closed.", ephemeral=True
            )
            await asyncio.sleep(2)
            try:
                await channel.delete(reason="User cancelled review")
            except discord.HTTPException:
                pass
        else:
            await interaction.response.send_message(
                "This is not your private review channel.", ephemeral=True
            )


@bot.event
async def on_ready():
    bot.add_view(ReviewPanel())
    bot.add_view(PrivateReviewControls())
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global command(s).")
    except Exception as exc:
        print(f"Command sync failed: {exc}")
    print(f"Logged in as {bot.user}.")


@bot.tree.command(name="setup_feedback", description="Post the Clash Design feedback panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_feedback(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(PANEL_CHANNEL_ID) if interaction.guild and configured(PANEL_CHANNEL_ID) else interaction.channel
    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message(
            "Set PANEL_CHANNEL_ID to a text channel ID in .env first.", ephemeral=True
        )

    embed = discord.Embed(
        title="📣 Clash Design Feedback",
        description=(
            "We value your feedback! 💜\n\n"
            "Share your experience with our bases and services. Your feedback helps us improve and grow.\n\n"
           
            "Click **Leave Review** to submit your review . You can attach an image if you want. "
            "The  feedback channel will show only your review and image."
        ),
        color=discord.Color.from_rgb(139, 64, 255),
    )
    embed.set_footer(text=f"{BRAND_NAME} • Your Feedback Builds Us!")
    await channel.send(embed=embed, view=ReviewPanel())
    await interaction.response.send_message(f"Feedback panel posted in {channel.mention}.", ephemeral=True)


@setup_feedback.error
async def setup_feedback_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You need the **Manage Server** permission to set up the feedback panel."
    else:
        message = "Something went wrong while setting up the feedback panel."
        print(f"/setup_feedback error: {error}")
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")

bot.run(TOKEN)
