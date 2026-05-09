import logging
import os
import sys
import asyncio

import pluggy
import click

# Import your core bot and hookspecs
import cliggybot.bot
import cliggybot.plugins


def load_plugins():
    """
    Uses Pluggy to find and load plugins registered via entry_points
    or manual registration.
    """
    pm = pluggy.PluginManager("cliggybot")
    
    # Add hook specifications
    pm.add_hookspecs(cliggybot.plugins)
    
    # This looks for 'cliggybot_hooks' plugins installed via pip/setuptools
    pm.load_setuptools_entrypoints("cliggybot_hooks")
    
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
    commands_from_plugins = pm.hook.register_commands()
    # Flatten the list of lists into a single list
    flattened_commands = [cmd for cmds in commands_from_plugins for cmd in cmds]
    for cmd in flattened_commands:
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
    # cli_group is the Click group object with all plugin commands attached
    cli_group_with_plugins = build_cli(pm)

    # If any arguments are provided, assume it's a command to be executed directly.
    # Click will handle parsing, validation, and execution.
    # If the command is invalid, Click will print help and exit.
    # If the command is valid, Click will execute it and then exit.
    if len(sys.argv) > 1:
        try:
            # Pass sys.argv[1:] to the *actual* cli_group object that has plugins
            cli_group_with_plugins(sys.argv[1:])
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
            # Pass the cli_group object to run_bot, though it's not strictly used there
            # in the current implementation, it's good practice to pass it if needed later.
            asyncio.run(run_bot(cli_group_with_plugins))
        except KeyboardInterrupt:
            logging.info("Shutting down bot.")
            sys.exit(0)
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            sys.exit(1)
