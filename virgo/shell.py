import aioboto3
import sys
from botocore.exceptions import ClientError
from botocore.config import Config
from discord.ext import commands

AWS_CONFIG = Config(region_name="us-east-2")
BOT = commands.Bot(command_prefix="v!")

class InvalidGameError(Exception):
    pass


class InvalidModeError(Exception):
    pass


class ModeNotFoundError(Exception):
    pass


class UnknownError(Exception):
    pass


@BOT.event
async def on_command_completion(ctx: commands.Context) -> None:
    await ctx.message.add_reaction("✅")


@BOT.event
async def on_command_error(ctx: commands.Context, e: Exception) -> None:
    await ctx.message.add_reaction("❌")
    if isinstance(e, commands.CommandInvokeError):
        orig = e.original
        await ctx.send(f"```virgo: ({type(orig).__name__}) {orig}```")
    else:
        await ctx.send(f"```virgo: ({type(e).__name__}) {e}```")


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
            tmp_check = await ec2.describe_launch_templates(
                LaunchTemplateNames=[name],
                Filters=[{"Name": "tag:virgo:game", "Values": ["*"]},],
            )
            if not tmp_check["LaunchTemplates"]:
                raise InvalidModeError(f"`{name}` is not a virgo game mode")
            response = await ec2.run_instances(
                LaunchTemplate={"LaunchTemplateName": name}, MinCount=1, MaxCount=1,
            )
            await ec2.create_tags(
                Resources=[i["InstanceId"] for i in response["Instances"]],
                Tags=[{"Key": "virgo:game", "Value": name}],
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in [
                "InvalidLaunchTemplateName.NotFound",
                "InvalidLaunchTemplateName.NotFoundException",
            ]:
                raise ModeNotFoundError(f"mode `{name}` does not exist")
            else:
                raise UnknownError(str(e))


@game_group.command(name="list")
async def game_list_command(ctx: commands.Context) -> None:
    """List game instances."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        response = await ec2.describe_instances(
            Filters=[
                {"Name": "instance-state-name", "Values": ["running"]},
                {"Name": "tag:virgo:game", "Values": ["*"]},
            ]
        )
        instances = [i for r in response["Reservations"] for i in r["Instances"]]
        status_res = await ec2.describe_instance_status(
            InstanceIds=[i["InstanceId"] for i in instances]
        )
        statuses = {s["InstanceId"]: s for s in status_res["InstanceStatuses"]}
        msg = "\n".join(
            _instance_format_for_listing(i, statuses.get(i["InstanceId"]))
            for i in instances
        )
        if msg:
            await ctx.send(f"```{msg}```")


def _instance_format_for_listing(instance, status) -> str:
    _id = instance["InstanceId"]
    ip_addr = instance.get("PublicIpAddress", "pending")
    result = f"{_instance_get_game(instance)}-{_id}: {ip_addr}"
    if status:
        status_mode = status["InstanceStatus"]["Status"]
        if status_mode != "ok":
            result += f" ({status_mode})"
    return result


def _instance_get_game(instance) -> str:
    return next((t["Value"] for t in instance["Tags"] if t["Key"] == "virgo:game"), "")


@BOT.group(name="mode")
async def mode_group(ctx: commands.Context) -> None:
    """Manage game modes."""
    if not ctx.invoked_subcommand:
        await ctx.send_help(mode_group)


@mode_group.command(name="list")
async def mode_list_command(ctx: commands.Context) -> None:
    """List game modes."""
    async with aioboto3.client("ec2", config=AWS_CONFIG) as ec2:
        response = await ec2.describe_launch_templates(
            Filters=[{"Name": "tag:virgo:game", "Values": ["*"]},]
        )
        msg = "\n".join(t["LaunchTemplateName"] for t in response["LaunchTemplates"])
        if msg:
            await ctx.send(f"```{msg}```")


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
                raise UnknownError(f"one of instance id(s) {list(ids)} does not exist")
            else:
                raise UnknownError(str(e))


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
