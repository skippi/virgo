import sys
from discord.ext import commands

BOT = commands.Bot(command_prefix="v!")


@BOT.group(name="game")
async def game_group(ctx: commands.Context) -> None:
    """Manage game instances."""
    if not ctx.invoked_subcommand:
        await ctx.send_help(game_group)


@game_group.command(name="create")
async def game_create_command(ctx: commands.Context) -> None:
    """Create a new game instance."""
    await ctx.send("hello world")


def main():
    token = sys.argv[1]
    BOT.run(token)


if __name__ == "__main__":
    main()
