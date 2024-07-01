# app_commands.py

from discord import app_commands, Interaction

from util import core, iferror, ifsuccess


def load(_):
    @app_commands.command()
    async def ping(interaction: Interaction) -> None:
        await interaction.response.send_message("pong!")

    for command in [ping]:
        try:
            core.bot.tree.add_command(command)
        except app_commands.errors.CommandAlreadyRegistered:
            pass
