"""ZIP file parsing utilities"""
import zipfile
import io

def parse_zip_structure(zip_content):
    """Parse ZIP file and return its structure as a tree with dashes"""
    structure = []
    
    try:
        zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
        file_list = sorted(zip_file.namelist())
        
        # Build a tree structure
        tree = {}
        file_sizes = {}
        
        # Collect file sizes
        for file_path in file_list:
            if not file_path.endswith('/'):
                try:
                    info = zip_file.getinfo(file_path)
                    file_sizes[file_path] = info.file_size
                except:
                    file_sizes[file_path] = 0
        
        # Build directory tree
        for file_path in file_list:
            if file_path.endswith('/'):
                continue
            
            parts = file_path.split('/')
            current = tree
            
            # Navigate/create directory structure
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {'type': 'dir', 'children': {}}
                elif current[part].get('type') != 'dir':
                    # Convert to directory if it was a file
                    current[part] = {'type': 'dir', 'children': {}}
                elif 'children' not in current[part]:
                    current[part]['children'] = {}
                current = current[part]['children']
            
            # Add file (handle root level files)
            filename = parts[-1]
            if len(parts) == 1:
                # Root level file
                if filename not in tree:
                    tree[filename] = {
                        'type': 'file',
                        'size': file_sizes.get(file_path, 0),
                        'path': file_path
                    }
            else:
                # File in a directory
                if filename not in current:
                    current[filename] = {
                        'type': 'file',
                        'size': file_sizes.get(file_path, 0),
                        'path': file_path
                    }
        
        # Convert tree to flat list with dashes
        def traverse_tree(node, depth=0, parent_path=''):
            result = []
            items = sorted(node.items(), key=lambda x: (x[1].get('type') == 'file', x[0].lower()))
            
            for name, item in items:
                dashes = '--' * depth
                prefix = f"{dashes} " if dashes else ""
                
                if item['type'] == 'dir':
                    display = f"{prefix}{name}/"
                    result.append({
                        'name': name,
                        'path': f"{parent_path}/{name}" if parent_path else name,
                        'display': display,
                        'depth': depth,
                        'is_file': False,
                        'size': 0
                    })
                    
                    # Add children
                    if 'children' in item:
                        result.extend(traverse_tree(item['children'], depth + 1, 
                                                   f"{parent_path}/{name}" if parent_path else name))
                else:
                    # It's a file
                    size_str = f" ({format_size(item['size'])})" if item['size'] > 0 else ""
                    display = f"{prefix}{name}{size_str}"
                    result.append({
                        'name': name,
                        'path': item.get('path', name),
                        'display': display,
                        'depth': depth,
                        'is_file': True,
                        'size': item['size']
                    })
            
            return result
        
        structure = traverse_tree(tree)
        zip_file.close()
        
    except Exception as e:
        print(f"Error parsing ZIP: {e}")
        import traceback
        traceback.print_exc()
        structure = []
    
    return structure

def format_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"

