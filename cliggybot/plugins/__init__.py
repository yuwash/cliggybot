import pluggy

hookspec = pluggy.HookspecMarker("cliggybot")

@hookspec
def register_commands():
    """Register commands from plugins."""
    pass
