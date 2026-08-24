import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if '# TODO: handle exception properly' not in content:
        return False

    # Check if logging is imported
    has_logging = 'import logging' in content or 'from logging' in content
    
    # We will replace:
    # except Exception:
    #     # TODO: handle exception properly
    #     pass
    # OR
    # except Exception as e:
    #     # TODO: handle exception properly
    #     pass
    
    # First, let's just find the TODOs and remove them, and if there is a 'pass' on the next line, replace it with logging.
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    modified = False
    
    while i < len(lines):
        line = lines[i]
        if '# TODO: handle exception properly' in line:
            indent = line[:len(line) - len(line.lstrip())]
            modified = True
            
            # Check if next line is pass
            if i + 1 < len(lines) and lines[i+1].strip() == 'pass':
                new_lines.append(indent + 'import logging')
                new_lines.append(indent + 'logging.getLogger(__name__).exception("Unhandled exception")')
                i += 1 # skip 'pass'
            elif i + 1 < len(lines) and 'logger.exception' in lines[i+1]:
                # just skip the TODO
                pass
            else:
                # Add logging just in case, but keep the rest
                new_lines.append(indent + 'import logging')
                new_lines.append(indent + 'logging.getLogger(__name__).exception("Unhandled exception")')
        else:
            new_lines.append(line)
        i += 1

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        return True
    return False

if __name__ == '__main__':
    count = 0
    for root, _, files in os.walk('e:\\narou4\\naRou'):
        for file in files:
            if file.endswith('.py'):
                if process_file(os.path.join(root, file)):
                    count += 1
    print(f"Fixed exceptions in {count} files.")
