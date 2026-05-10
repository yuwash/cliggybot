import click
import pluggy

hookimpl = pluggy.HookimplMarker("cliggybot")

@click.command()
@click.argument('message')
async def echo(message):
    """Echo back the message provided by the user."""
    click.echo(message)

@hookimpl
def register_commands():
    return [echo]
