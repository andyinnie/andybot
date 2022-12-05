# app_commands.py

from discord import app_commands, Interaction

from util import core


def load(_):
    @app_commands.command()
    async def ping(interaction: Interaction) -> None:
        await interaction.response.send_message("pong!")

    core.bot.tree.add_command(ping)
