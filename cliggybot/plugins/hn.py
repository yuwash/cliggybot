import click
import httpx
import pluggy

hookimpl = pluggy.HookimplMarker("cliggybot")

@click.command()
@click.option('--limit', default=5, help='Number of stories to show')
async def hn(limit):
    """Fetches the top stories from Hacker News via Microlink."""
    params = {
        "url": "https://news.ycombinator.com",
        "data.story.selector": ".athing",
        "data.story.attr.title.selector": ".titleline > a",
        "data.story.attr.title.attr": "text",
        "data.story.attr.href.selector": ".titleline > a",
        "data.story.attr.href.attr": "href",
        "meta": "false"
    }
    
    click.echo(f"Searching for the top {limit} stories...")
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://api.microlink.io", params=params)
            r.raise_for_status()
            data = r.json().get('data', {}).get('story', [])
            
            for item in data[:limit]:
                title = item.get('title')
                href = item.get('href')
                click.echo(f"• {title}\n  {href}")
        except Exception as e:
            click.echo(f"Failed to fetch news: {e}")

@hookimpl
def register_commands():
    return [hn]
