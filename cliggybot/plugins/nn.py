import click
import httpx
import pluggy

hookimpl = pluggy.HookimplMarker("cliggybot")

@click.command()
@click.argument('message')
async def nn(message):
    """Pass a message to nanobot."""
    click.echo(f"Passing message to nanobot: {message}")
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                "http://127.0.0.1:8900/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer dummy",
                },
                json={
                    "model": "z-ai/glm-4.5-air:free",
                    "messages": [{"role": "user", "content": message}],
                    "extra_body": {"session_id": "errbot-default"},
                },
                timeout=180,
            )
            r.raise_for_status()
            message = r.json()["choices"][0]["message"]
            # Only expecting one choice.
            click.echo(message['content'])
        except Exception as e:
            click.echo(f"Failed to pass message to nanobot: {e}")
    

@hookimpl
def register_commands():
    return [nn]
