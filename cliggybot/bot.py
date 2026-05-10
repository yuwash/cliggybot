import asyncio
import shlex
import io
import logging
from contextlib import redirect_stdout

import slixmpp


class XMPPBot(slixmpp.ClientXMPP):
    def __init__(self, jid, password, click_group, allowed_jid=None):
        super().__init__(jid, password)
        self.cli = click_group
        self.allowed_jid = allowed_jid
        # Register the event handler
        self.add_event_handler("message", self.handle_message)

    async def start(self):
        """
        This is triggered when the session is established.
        Without sending presence, the bot stays 'offline' to the world.
        """
        # 1. Broadcast that we are online
        self.send_presence()
        
        # 2. Request the roster (contact list)
        # Some servers require this to fully 'activate' the session
        logging.info("Requesting Roster...")
        await self.get_roster()

    def handle_message(self, msg):
        """
        The XMPP Entry Point. 
        Slixmpp calls this every time a message is received.
        """
        # Only respond to direct 'chat' messages and ignore our own messages
        if msg['type'] in ('chat', 'normal') and msg['from'] != self.boundjid:
            # Check if allowed JID restriction is enabled and sender is not allowed
            if self.allowed_jid and str(msg['from']).split('/')[0] != self.allowed_jid:
                logging.info(f"Ignoring message from unauthorized JID: {msg['from']}")
                return
            
            # We schedule the command processing on the event loop
            # so the XMPP connection remains responsive.
            asyncio.create_task(self.process_command(msg))

    async def process_command(self, msg):
        """
        The Bridge to Click.
        This handles the transformation from Chat String -> Click Command -> Chat Response.
        """
        body = msg['body'].strip()
        if not body:
            return

        # Use shlex to handle quotes correctly: !echo "hello world" -> ['echo', 'hello world']
        try:
            args = shlex.split(body)
        except ValueError as e:
            msg.reply(f"Parser Error: {e}").send()
            return

        # Capture anything that would normally go to the terminal (stdout)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            try:
                # 1. Create the Click context
                ctx = self.cli.make_context('!', args)
                with ctx:
                    # 2. Invoke the command (could be sync or async)
                    result = self.cli.invoke(ctx)
                    
                    # 3. If the plugin is 'async def', we await it here
                    if asyncio.iscoroutine(result):
                        await result
                        
            except Exception as e:
                # Handle Click errors (like missing arguments or 'command not found')
                buffer.write(str(e))

        # 4. Get the result from the buffer and send it back to the user
        response = buffer.getvalue().strip()
        if response:
            msg.reply(response).send()
