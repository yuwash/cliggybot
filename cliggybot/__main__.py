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
    for plugin_instance in pm.get_plugins():
        if hasattr(plugin_instance, "commands"):
            for cmd in plugin_instance.commands:
                cli.add_command(cmd)
            
    return cli


async def run_bot(cli_group):
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
    cli_group = build_cli(pm)

    # If any arguments are provided, assume it's a command to be executed directly.
    # Click will handle parsing, validation, and execution.
    # If the command is invalid, Click will print help and exit.
    # If the command is valid, Click will execute it and then exit.
    if len(sys.argv) > 1:
        try:
            # Pass sys.argv[1:] to click to avoid processing the script name itself
            cli_group(sys.argv[1:])
        except SystemExit as e:
            # Click raises SystemExit on success or error.
            # We catch it to ensure our asyncio loop doesn't interfere.
            sys.exit(e.code)
        except Exception as e:
            logging.exception(f"An unexpected error occurred during command execution: {e}")
            sys.exit(1)
    else:
        # No arguments provided, start the XMPP bot.
        try:
            asyncio.run(run_bot(cli_group))
        except KeyboardInterrupt:
            logging.info("Shutting down bot.")
            sys.exit(0)
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            sys.exit(1)
