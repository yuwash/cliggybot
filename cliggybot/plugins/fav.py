import os
import click
import pathlib
import pluggy
from datetime import datetime
from typing import List, Tuple

class FavManager:
    def __init__(self, fav_root):
        self.fav_root = fav_root
        self.marks_file = os.path.join(fav_root, '.fav', 'marks')
        
    def ensure_marks_dir(self):
        """Ensure the .fav directory exists."""
        marks_dir = os.path.dirname(self.marks_file)
        os.makedirs(marks_dir, exist_ok=True)
    
    def mark_file(self, relative_path):
        """Mark a file by adding its relative path to the marks file."""
        self.ensure_marks_dir()
        
        # Add the path to the marks file
        with open(self.marks_file, 'a') as f:
            f.write(relative_path + '\n')
    
    def get_marks(self):
        """Get all marked files in reverse order (most recent first)."""
        if not os.path.exists(self.marks_file):
            return []
        
        with open(self.marks_file, 'r') as f:
            lines = f.readlines()
        
        # Return lines in reverse order (most recent first)
        return [line.strip() for line in reversed(lines) if line.strip()]
    
    def clear_marks(self):
        """Clear all marks by removing the marks file."""
        if os.path.exists(self.marks_file):
            os.remove(self.marks_file)
    
    def pop_mark(self):
        """Remove the latest mark from the marks file."""
        if not os.path.exists(self.marks_file):
            return None
        
        # Read all marks
        with open(self.marks_file, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return None
        
        # Remove the last line (latest mark)
        latest_mark = lines.pop()
        
        # Write back all but the last line
        with open(self.marks_file, 'w') as f:
            f.writelines(lines)
        
        return latest_mark.strip()
    
    def remove_marked_files(self, marked_files):
        """Remove successfully moved files from marks."""
        if not os.path.exists(self.marks_file):
            return
        
        # Read all current marks
        with open(self.marks_file, 'r') as f:
            lines = f.readlines()
        
        # Filter out the successfully moved files
        remaining_lines = [line for line in lines if line.strip() not in marked_files]
        
        # Write back the remaining marks
        with open(self.marks_file, 'w') as f:
            f.writelines(remaining_lines)

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

@fav.command()
@click.argument('path', nargs=-1)
def mkdir(path):
    """Create directories recursively under FAV_ROOT with optional path."""
    try:
        fav_path = FavPath()
        
        if not path:
            raise click.BadParameter("A directory path is required")
        
        # Convert tuple to list for easier handling
        path_parts = list(path)
        
        # Validate the path
        fav_path.validate_path(path_parts)
        
        # Construct the full path
        resolved_path = os.path.join(fav_path.fav_root, *path_parts)
        
        # Create the directory recursively
        os.makedirs(resolved_path, exist_ok=True)
        
        click.echo(f"Created directory: {resolved_path}")
        
    except Exception as e:
        click.echo(f"Error creating directory: {e}")

@fav.command()
@click.argument('path', nargs=-1)
@click.option('--clear', is_flag=True, help='Clear all marks')
@click.option('--pop', is_flag=True, help='Remove the latest mark')
def m(path, clear, pop):
    """Mark files or list marks."""
    try:
        fav_path = FavPath()
        fav_manager = FavManager(fav_path.fav_root)
        
        if clear:
            fav_manager.clear_marks()
            click.echo("Marks cleared.")
            return
        
        if pop:
            popped_mark = fav_manager.pop_mark()
            if popped_mark:
                click.echo(f"Popped: {popped_mark}")
            else:
                click.echo("No marks to pop.")
            return
        
        if not path:
            # Print marks in reverse order (most recent first)
            marks = fav_manager.get_marks()
            if marks:
                for mark in marks:
                    click.echo(mark)
            else:
                click.echo("No marks found.")
            return
        
        # Handle path with potential index
        path_parts = list(path)
        resolved_path, index = fav_path.resolve_path_with_index(path_parts)
        
        # If we have an index, resolve to the actual file
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
        
        # Validate the final resolved path
        fav_path.validate_path(list(os.path.relpath(resolved_path, fav_path.fav_root).split(os.sep)))
        
        # Construct the relative path for marking
        relative_path = os.path.relpath(resolved_path, fav_path.fav_root)
        
        # Mark the file
        fav_manager.mark_file(relative_path)
        click.echo(f"Marked: {relative_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}")

@fav.command()
@click.argument('destination', nargs=-1)
def mv(destination):
    """Move all marked files to the specified directory."""
    try:
        fav_path = FavPath()
        fav_manager = FavManager(fav_path.fav_root)
        
        # Handle nested directory paths properly
        # Convert tuple to list for easier handling
        dest_parts = list(destination)
        
        # Validate destination path
        fav_path.validate_path(dest_parts)
        
        # Resolve destination path
        dest_path = os.path.join(fav_path.fav_root, *dest_parts)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Check if destination exists and is a directory
        if not os.path.exists(dest_path):
            raise click.BadParameter(f"Destination directory does not exist: {dest_path}")
        
        if not os.path.isdir(dest_path):
            raise click.BadParameter(f"Destination is not a directory: {dest_path}")
        
        # Get all marked files
        marked_files = fav_manager.get_marks()
        if not marked_files:
            click.echo("No marked files to move.")
            return
        
        # Move each marked file/directory
        successfully_moved = []
        for relative_path in marked_files:
            source_path = os.path.join(fav_path.fav_root, relative_path)
            
            # Check if source file/directory exists
            if not os.path.exists(source_path):
                click.echo(f"Skipping {relative_path}: File/directory does not exist")
                continue
            
            # Construct destination path
            filename = os.path.basename(relative_path)
            dest_file_path = os.path.join(dest_path, filename)
            
            # Check if file/directory with same name already exists in destination
            if os.path.exists(dest_file_path):
                click.echo(f"Skipping {relative_path}: File/directory already exists in destination")
                continue
            
            try:
                # Move the file/directory
                os.rename(source_path, dest_file_path)
                successfully_moved.append(relative_path)
                click.echo(f"Moved: {relative_path}")
            except Exception as e:
                click.echo(f"Failed to move {relative_path}: {e}")
                continue
        
        # Remove successfully moved files from marks
        if successfully_moved:
            fav_manager.remove_marked_files(successfully_moved)
            click.echo(f"Removed {len(successfully_moved)} files from marks")
        else:
            click.echo("No files were successfully moved.")
            
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
