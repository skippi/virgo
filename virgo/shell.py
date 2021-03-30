import sys
import aioboto3
from botocore.config import Config
from discord.ext import commands

AWS_CONFIG = Config(region_name="us-east-2")
BOT = commands.Bot(command_prefix="v!")


@BOT.event
async def on_command_completion(ctx: commands.Context) -> None:
    await ctx.message.add_reaction("✅")


@BOT.event
async def on_command_error(ctx: commands.Context, _: Exception) -> None:
    await ctx.message.add_reaction("❌")


@BOT.group(name="game")
async def game_group(ctx: commands.Context) -> None:
    """Manage game instances."""
    if not ctx.invoked_subcommand:
        await ctx.send_help(game_group)


@game_group.command(name="create")
async def game_create_command(_: commands.Context, name: str) -> None:
    """Create a new game instance."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        runInstanceResult = await ec2.run_instances(
            ImageId=name, InstanceType="t4g.micro", MinCount=1, MaxCount=1
        )
        await ec2.create_tags(
            Resources=[i["InstanceId"] for i in runInstanceResult["Instances"]],
            Tags=[{"Key": "virgo:game", "Value": name}],
        )


@game_group.command(name="list")
async def game_list_command(ctx: commands.Context) -> None:
    """List game instances."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        instancesResult = await ec2.describe_instances(
            Filters=[
                {"Name": "instance-state-name", "Values": ["pending", "running"]},
                {"Name": "tag:virgo:game", "Values": ["*"]},
            ]
        )
        instances = [i for r in instancesResult["Reservations"] for i in r["Instances"]]
        msg = "\n".join(map(_instance_format_for_listing, instances))
        if msg:
            await ctx.send(msg)


def _instance_format_for_listing(instance) -> str:
    _id = instance["InstanceId"]
    ip_addr = instance.get("PublicIpAddress", "pending")
    return f"{_instance_get_game(instance)}-{_id}: {ip_addr}"


def _instance_get_game(instance) -> str:
    return next((t["Value"] for t in instance["Tags"] if t["Key"] == "virgo:game"), "")


@BOT.command(name="exit")
@commands.has_permissions(administrator=True)
async def exit_command(_: commands.Context) -> None:
    """Exit virgo bot."""
    await BOT.logout()


def main():
    token = sys.argv[1]
    BOT.run(token)


if __name__ == "__main__":
    main()
