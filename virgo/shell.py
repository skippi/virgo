import sys
import boto3
from botocore.config import Config
from discord.ext import commands

AWS = boto3.client("ec2", config=Config(region_name="us-east-2"))
BOT = commands.Bot(command_prefix="v!")


@BOT.event
async def on_command_completion(ctx: commands.Context) -> None:
    await ctx.message.add_reaction("✅")


@BOT.event
async def on_command_error(ctx: commands.Context, exception: Exception) -> None:
    await ctx.message.add_reaction("❌")


@BOT.group(name="game")
async def game_group(ctx: commands.Context) -> None:
    """Manage game instances."""
    if not ctx.invoked_subcommand:
        await ctx.send_help(game_group)


@game_group.command(name="create")
async def game_create_command(ctx: commands.Context, name: str) -> None:
    """Create a new game instance."""
    runInstanceResult = AWS.run_instances(
        ImageId=name, InstanceType="t4g.micro", MinCount=1, MaxCount=1
    )
    AWS.create_tags(
        Resources=[i["InstanceId"] for i in runInstanceResult["Instances"]],
        Tags=[{"Key": "virgo:id", "Value": "foo"}],
    )


@BOT.command(name="kill")
@commands.has_permissions(administrator=True)
async def kill_command(_: commands.Context) -> None:
    """Kill virgo bot."""
    await BOT.logout()


def main():
    token = sys.argv[1]
    BOT.run(token)


if __name__ == "__main__":
    main()
