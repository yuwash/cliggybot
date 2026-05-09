import sys
import asyncio
import pluggy
import click

# Import your core bot and hookspecs
from cliggybot import bot


def load_plugins():
    """
    Uses Pluggy to find and load plugins registered via entry_points
    or manual registration.
    """
    pm = pluggy.PluginManager("cliggybot")
    
    # This looks for 'cliggybot' plugins installed via pip/setuptools
    pm.load_setuptools_entry_points("cliggybot")
    
    return pm


def build_cli(pm):
    """
    Creates a Click group and attaches all commands provided by plugins.
    """
    @click.group()
    def cli():
        pass

    # Ask plugins for their commands
    # The hook returns a list of lists, so we flatten it
    commands_lists = pm.hook.register_commands()
    for cmd_list in commands_lists:
        for cmd in cmd_list:
            cli.add_command(cmd)
            
    return cli


async def run_bot():
    # 1. Setup Pluggy and Click
    pm = load_plugins()
    cli_group = build_cli(pm)

    # 2. Configuration (In a real app, use env vars or a config file)
    jid = "bot@example.com"
    password = "yourpassword"

    # 3. Initialize the Bot
    bot = bot.XMPPBot(jid, password, cli_group)

    # 4. Connect and Run
    # Slixmpp handles the event loop integration
    bot.connect()
    await bot.disconnected  # Keeps the script running until the bot quits


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        sys.exit(0)
