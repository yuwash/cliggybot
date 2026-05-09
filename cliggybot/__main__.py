import logging
import os
import sys
import asyncio

import pluggy
import click

# Import your core bot and hookspecs
import cliggybot.bot


def load_plugins():
    """
    Uses Pluggy to find and load plugins registered via entry_points
    or manual registration.
    """
    pm = pluggy.PluginManager("cliggybot")
    
    # This looks for 'cliggybot' plugins installed via pip/setuptools
    pm.load_setuptools_entrypoints("cliggybot")
    
    return pm


def build_cli(pm):
    """
    Creates a Click group and attaches all commands provided by plugins.
    """
    @click.group()
    def cli():
        """A simple bot framework with plugins."""
        pass

    # Ask plugins for their commands
    # The hook returns a list of lists, so we flatten it
    commands = []
    for plugin_instance in pm.get_plugins():
        if hasattr(plugin_instance, "commands"):
            for cmd in plugin_instance.commands:
                cli.add_command(cmd)
                commands.append(cmd)
            
    return cli, commands


async def run_bot(cli_group, plugin_commands):
    # Check if any plugin command was invoked
    # Click's main() will handle parsing and execution if a subcommand is given
    # We need to check if the command was executed and if it's a plugin command
    
    # This is a bit of a workaround. Click's default behavior is to run the command
    # and exit. We want to intercept this for plugin commands.
    # A more robust solution might involve inspecting sys.argv before calling cli()
    # or using a custom Click runner.
    
    # For now, we'll assume if a plugin command is present in sys.argv,
    # it's intended to be run directly.
    
    if len(sys.argv) > 1 and sys.argv[1] in [cmd.name for cmd in plugin_commands]:
        # If a plugin command is specified, run it and exit
        # Click's cli() will handle the execution and exit
        logging.info(f"Executing command: {sys.argv[1]}")
        # We need to call the cli group to parse arguments and run the command
        # This will naturally exit after the command is done.
        cli_group() 
        return # This return is technically unreachable due to sys.exit in click

    # 1. Configuration (In a real app, use env vars or a config file)
    jid = os.environ.get("CLIGGYBOT_XMPP_JID")
    password = os.environ.get("CLIGGYBOT_XMPP_PASSWORD")

    if not jid or not password:
        logging.error("CLIGGYBOT_XMPP_JID and CLIGGYBOT_XMPP_PASSWORD must be set.")
        sys.exit(1)

    # 2. Initialize the Bot
    bot = cliggybot.bot.XMPPBot(jid, password, cli_group)

    # 3. Connect and Run
    # Slixmpp handles the event loop integration
    logging.info("Starting XMPP bot...")
    bot.connect()
    await bot.start()
    await bot.disconnected  # Keeps the script running until the bot quits


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    pm = load_plugins()
    cli_group, plugin_commands = build_cli(pm)

    try:
        asyncio.run(run_bot(cli_group, plugin_commands))
    except KeyboardInterrupt:
        logging.info("Shutting down bot.")
        sys.exit(0)
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)
