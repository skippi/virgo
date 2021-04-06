import sys
import aioboto3
from botocore.exceptions import ClientError
from botocore.config import Config
from discord.ext import commands

AWS_CONFIG = Config(region_name="us-east-2")
BOT = commands.Bot(command_prefix="v!")


@BOT.event
async def on_command_completion(ctx: commands.Context) -> None:
    await ctx.message.add_reaction("✅")


@BOT.event
async def on_command_error(ctx: commands.Context, e: Exception) -> None:
    await ctx.message.add_reaction("❌")
    await ctx.send(f"```{e}```")


@BOT.group(name="game")
async def game_group(ctx: commands.Context) -> None:
    """Manage game instances."""
    if not ctx.invoked_subcommand:
        await ctx.send_help(game_group)


@game_group.command(name="create")
async def game_create_command(ctx: commands.Context, name: str) -> None:
    """Create a new game instance."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        try:
            response = await ec2.run_instances(
                LaunchTemplate={"LaunchTemplateName": name},
                MinCount=1,
                MaxCount=1,
            )
            await ec2.create_tags(
                Resources=[i["InstanceId"] for i in response["Instances"]],
                Tags=[{"Key": "virgo:game", "Value": name}],
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "InvalidLaunchTemplateName.NotFound":
                await ctx.send(f"```virgo: game `{name}` does not exist```")
            else:
                await ctx.send(f"```virgo: unknown error {str(e)}```")


@game_group.command(name="list")
async def game_list_command(ctx: commands.Context) -> None:
    """List game instances."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        response = await ec2.describe_instances(
            Filters=[
                {"Name": "instance-state-name", "Values": ["pending", "running"]},
                {"Name": "tag:virgo:game", "Values": ["*"]},
            ]
        )
        instances = [i for r in response["Reservations"] for i in r["Instances"]]
        msg = "\n".join(map(_instance_format_for_listing, instances))
        if msg:
            await ctx.send(f"```{msg}```")


def _instance_format_for_listing(instance) -> str:
    _id = instance["InstanceId"]
    ip_addr = instance.get("PublicIpAddress", "pending")
    return f"{_instance_get_game(instance)}-{_id}: {ip_addr}"


def _instance_get_game(instance) -> str:
    return next((t["Value"] for t in instance["Tags"] if t["Key"] == "virgo:game"), "")


@game_group.command(name="kill")
@commands.has_permissions(administrator=True)
async def game_kill_command(ctx: commands.Context, *ids) -> None:
    """Kill a game instance."""
    if not ids:
        return
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        try:
            await ec2.terminate_instances(InstanceIds=ids)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "InvalidInstanceID.Malformed":
                await ctx.send(
                    f"```virgo: instance with one of id(s) `{list(ids)}` does not exist```"
                )
            else:
                await ctx.send(f"```virgo: unknown error {str(e)}```")


@game_group.command(name="clear")
@commands.has_permissions(administrator=True)
async def game_clear_command(_: commands.Context) -> None:
    """Clear a game instance."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        res = await ec2.describe_instances(
            Filters=[
                {"Name": "instance-state-name", "Values": ["pending", "running"]},
                {"Name": "tag:virgo:game", "Values": ["*"]},
            ]
        )
        ids = [i["InstanceId"] for r in res["Reservations"] for i in r["Instances"]]
        await ec2.terminate_instances(InstanceIds=ids)


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
