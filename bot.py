import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
FEEDBACK_CHANNEL_ID = int(os.getenv("FEEDBACK_CHANNEL_ID", "0") or 0)
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "0") or 0)
BRAND_NAME = os.getenv("BRAND_NAME", "Clash Design")
MAX_IMAGE_BYTES = 10 * 1024 * 1024

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


class ReviewModal(discord.ui.Modal, title="Leave a Review"):
    review = discord.ui.Label(
        text="Your Review",
        description="Share your experience and thoughts.",
        component=discord.ui.TextInput(
            custom_id="review_text",
            style=discord.TextStyle.paragraph,
            placeholder="Share your experience and thoughts...",
            min_length=3,
            max_length=3500,
            required=True,
        ),
    )
    image = discord.ui.Label(
        text="Add Image (optional)",
        description="Upload one image to include with your review.",
        component=discord.ui.FileUpload(
            custom_id="review_image", required=False, min_values=0, max_values=1
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(
                "Please submit your review inside the server.", ephemeral=True
            )
        target = interaction.guild.get_channel(FEEDBACK_CHANNEL_ID)
        if not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message(
                "The feedback channel is not configured correctly. Please contact an administrator.",
                ephemeral=True,
            )

        review_text = str(self.review.component.value).strip()
        if not review_text:
            return await interaction.response.send_message(
                "Please enter your review before submitting.", ephemeral=True
            )

        uploaded = self.image.component.values
        file_to_send = None
        image_name = None
        if uploaded:
            attachment = uploaded[0]
            if not (attachment.content_type or "").lower().startswith("image/"):
                return await interaction.response.send_message(
                    "Please upload an image file (PNG, JPG, JPEG, GIF, or WEBP).",
                    ephemeral=True,
                )
            if attachment.size > MAX_IMAGE_BYTES:
                return await interaction.response.send_message(
                    "Your image is larger than 10 MB. Please upload a smaller image.",
                    ephemeral=True,
                )
            try:
                file_to_send = await attachment.to_file()
                image_name = file_to_send.filename
            except (discord.HTTPException, OSError):
                return await interaction.response.send_message(
                    "I couldn't process that image. Please try uploading it again.",
                    ephemeral=True,
                )

        embed = discord.Embed(
            title="♛ Customer Review",
            description=review_text,
            color=discord.Color.from_rgb(139, 64, 255),
        )
        embed.add_field(name="Rating", value="⭐ ⭐ ⭐ ⭐ ⭐", inline=False)
        embed.set_footer(text=f"{BRAND_NAME} • Feedback")
        if file_to_send and image_name:
            embed.set_image(url=f"attachment://{image_name}")

        try:
            await target.send(
                embed=embed, file=file_to_send,
                allowed_mentions=discord.AllowedMentions.none()
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "I can't post in the feedback channel. Please contact a server administrator.",
                ephemeral=True,
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "The review could not be published. Please try again or contact an administrator.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            "💜 Thank you! Your review has been posted in the feedback channel.",
            ephemeral=True,
        )


class ReviewPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Leave Review", style=discord.ButtonStyle.primary,
        emoji="✍️", custom_id="clashdesign:leave_review"
    )
    async def leave_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal())


@bot.event
async def on_ready():
    bot.add_view(ReviewPanel())
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
        else:
            await bot.tree.sync()
            print("Synced global application commands.")
    except Exception as exc:
        print(f"Command sync failed: {exc}")
    print(f"Logged in as {bot.user}.")


@bot.tree.command(name="setup_feedback", description="Post the Clash Design feedback panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_feedback(interaction: discord.Interaction):
    channel = (
        interaction.guild.get_channel(PANEL_CHANNEL_ID)
        if interaction.guild and PANEL_CHANNEL_ID
        else interaction.channel
    )
    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message(
            "Set PANEL_CHANNEL_ID in your .env file to a text channel ID.",
            ephemeral=True,
        )

    embed = discord.Embed(
        title="📣 Clash Design Feedback",
        description=(
            "We value your feedback! 💜\n\n"
            "Share your experience with our bases and services. Your feedback helps us improve and grow.\n\n"
          
            "Click **Leave Review** to open the review form. Write your feedback Thank You. "
            
        ),
        color=discord.Color.from_rgb(139, 64, 255),
    )
    embed.set_footer(text=f"{BRAND_NAME} • Your Feedback Builds Us!")
    await channel.send(embed=embed, view=ReviewPanel())
    await interaction.response.send_message(
        f"Feedback panel posted in {channel.mention}.", ephemeral=True
    )


@setup_feedback.error
async def setup_feedback_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    message = (
        "You need the **Manage Server** permission to set up the feedback panel."
        if isinstance(error, app_commands.MissingPermissions)
        else "Something went wrong while setting up the feedback panel."
    )
    if not isinstance(error, app_commands.MissingPermissions):
        print(f"/setup_feedback error: {error}")
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")
bot.run(TOKEN)
