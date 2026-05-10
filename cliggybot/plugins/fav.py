import os
import click
import pathlib
import pluggy
from datetime import datetime
from typing import List, Tuple

class FavPath:
    def __init__(self):
        # Get the FAV_ROOT environment variable or default to ~/.fav
        self.fav_root = os.environ['CLIGGYBOT_FAV_ROOT']
        if not self.fav_root:
            raise ValueError("CLIGGYBOT_FAV_ROOT is not set")
        if not os.path.isdir(self.fav_root):
            raise ValueError("CLIGGYBOT_FAV_ROOT is not a directory")

    def validate_path(self, path_parts: List[str]) -> None:
        """Validate and construct a path from parts, ensuring it stays within FAV_ROOT."""
        if not path_parts:
            return  # It will just be the fav_root.
        
        # Construct the path
        full_path = os.path.join(self.fav_root, *path_parts)
        
        # Ensure the path is within self.fav_root
        try:
            abs_path = os.path.abspath(full_path)
            abs_fav_root = os.path.abspath(self.fav_root)
            
            if not abs_path.startswith(abs_fav_root):
                raise click.BadParameter("Path must be within FAV_ROOT")
        except Exception:
            raise click.BadParameter("Invalid path")
        
    def get_file_info(self, file_path: str) -> Tuple[str, datetime, int]:
        """Get file information: name, modification time, and size."""
        stat = os.stat(file_path)
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        size = stat.st_size
        return os.path.basename(file_path), mod_time, size

    def format_file_info(self, name: str, mod_time: datetime, size: int) -> str:
        """Format file information for display."""
        formatted_time = mod_time.strftime("%Y-%m-%d %H:%M")
        formatted_size = f"{size}B"
        if size >= 1024:
            formatted_size = f"{size/1024:.1f}KB"
        if size >= 1024*1024:
            formatted_size = f"{size/(1024*1024):.1f}MB"
        
        return f"{formatted_time} {formatted_size} {name}"

    def resolve_path_with_index(self, path_parts: List[str]) -> Tuple[str, int]:
        """Resolve path and determine if last part is an index."""
        if not path_parts:
            return self.fav_root, None
        
        # Check if the last part is a number
        last_part = path_parts[-1]
        try:
            index = int(last_part)
        except ValueError:
            resolved_path = os.path.join(self.fav_root, *path_parts)
            return resolved_path, None
        else:
            # Remove the index from path parts
            resolved_path = os.path.join(self.fav_root, *path_parts[:-1])
            return resolved_path, index


@click.group()
def fav():
    """Manage files under FAV_ROOT."""
    pass

@fav.command()
@click.argument('path', nargs=-1)
def ls(path):
    """List files and directories under FAV_ROOT with optional path."""
    try:
        fav_path = FavPath()
        
        # Handle path with potential index
        if path:
            # Convert tuple to list for easier handling
            path_parts = list(path)
            
            # Validate the path
            fav_path.validate_path(path_parts)
            
            # Resolve path with index
            resolved_path, index = fav_path.resolve_path_with_index(path_parts)
        else:
            resolved_path = fav_path.fav_root
            index = None
        
        # Ensure the path exists
        if not os.path.exists(resolved_path):
            click.echo(f"Path does not exist: {resolved_path}")
            return
        
        # Check if it's a file
        if os.path.isfile(resolved_path):
            name, mod_time, size = fav_path.get_file_info(resolved_path)
            click.echo(fav_path.format_file_info(name, mod_time, size))
            return
            
        # List directory contents
        items = []
        for item in os.listdir(resolved_path):
            item_path = os.path.join(resolved_path, item)
            # Skip hidden files/directories
            if item.startswith('.'):
                continue
                
            # Skip directories that consist only of numbers
            if os.path.isdir(item_path) and item.isdigit():
                continue
                
            stat = os.stat(item_path)
            items.append((item, stat.st_mtime, stat.st_size))
        
        # Sort by modification time (newest first)
        items.sort(key=lambda x: x[1], reverse=True)
        
        # If an index was specified, show only that item
        if index is not None:
            if index < 0 or index >= len(items):
                message_suffix = (
                    f" Available items: 0-{len(items)-1}"
                    if items else
                    " Directory is empty."
                )
                click.echo(f"Index {index} out of range.{message_suffix}")
                return
            item_name, mod_time, size = items[index]
            item_path = os.path.join(resolved_path, item_name)
            name, mod_time, size = fav_path.get_file_info(item_path)
            click.echo(fav_path.format_file_info(name, mod_time, size))
        else:
            # Show all items with numbering
            for i, (name, mod_time, size) in enumerate(items):
                item_path = os.path.join(resolved_path, name)
                formatted_name = name
                if os.path.isdir(item_path):
                    formatted_name = f"[{name}]"
                click.echo(f"{i}: {fav_path.format_file_info(formatted_name, datetime.fromtimestamp(mod_time), size)}")
                
    except Exception as e:
        click.echo(f"Error: {e}")

@fav.command()
@click.argument('path', nargs=-1)
def head(path):
    """Show the first 5 lines or first 256 bytes of a file, whichever is less."""
    try:
        fav_path = FavPath()
        
        if not path:
            raise click.BadParameter("A file path is required")
        
        # Convert tuple to list for easier handling
        path_parts = list(path)
        
        # Validate the path
        fav_path.validate_path(path_parts)
        
        # Resolve path with index
        resolved_path, index = fav_path.resolve_path_with_index(path_parts)
        
        # If we have an index, we need to resolve the actual file path
        if index is not None:
            # The resolved_path points to the directory, we need to find the file at the index
            try:
                items = []
                for item in os.listdir(resolved_path):
                    item_path = os.path.join(resolved_path, item)
                    if item.startswith('.'):
                        continue
                    if os.path.isdir(item_path) and item.isdigit():
                        continue
                    stat = os.stat(item_path)
                    items.append((item, stat.st_mtime))
                
                items.sort(key=lambda x: x[1], reverse=True)
                
                if index < 0 or index >= len(items):
                    click.echo(f"Index {index} out of range. Available items: 0-{len(items)-1}")
                    return
                
                # Get the actual file path
                resolved_path = os.path.join(resolved_path, items[index][0])
            except Exception:
                click.echo(f"Error resolving indexed path: {resolved_path}")
                return
        
        # Ensure the path exists and is a file
        if not os.path.exists(resolved_path):
            click.echo(f"File does not exist: {resolved_path}")
            return
        
        if not os.path.isfile(resolved_path):
            click.echo(f"Path is not a file: {resolved_path}")
            return
        
        # Read configuration from environment variables
        default_lines = int(os.environ.get('CLIGGYBOT_FAV_HEAD_LINES', '5'))
        default_bytes = int(os.environ.get('CLIGGYBOT_FAV_HEAD_BYTES', '256'))
        
        # Read file content
        with open(resolved_path, 'rb') as f:
            content = f.read(default_bytes)
        
        # Decode to text for line counting
        try:
            content_text = content.decode('utf-8')
        except UnicodeDecodeError:
            # If we can't decode as UTF-8, just show the raw bytes
            click.echo(content)
            return
        
        # Split into lines
        lines = content_text.splitlines(keepends=True)
        
        # If we have fewer lines than the limit, show all lines
        if len(lines) <= default_lines:
            # Show all lines
            click.echo(content_text.rstrip('\n'))
        else:
            # Show up to default_lines
            result = ''.join(lines[:default_lines])
            click.echo(result.rstrip('\n'))
            
    except Exception as e:
        click.echo(f"Error: {e}")

# Helper function to resolve item by index
def resolve_item_by_index(path: str, index: int) -> str:
    """Resolve an item by index in a given path."""
    try:
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if item.startswith('.'):
                continue
            if os.path.isdir(item_path) and item.isdigit():
                continue
            stat = os.stat(item_path)
            items.append((item, stat.st_mtime))
        
        items.sort(key=lambda x: x[1], reverse=True)
        
        if index < 0 or index >= len(items):
            raise IndexError("Index out of range")
            
        return os.path.join(path, items[index][0])
    except Exception:
        raise click.BadParameter(f"Item at index {index} not found")

hookimpl = pluggy.HookimplMarker("cliggybot")

@hookimpl
def register_commands():
    return [fav]
