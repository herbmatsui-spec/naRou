#!/usr/bin/env python3
"""
Generate theme.css from design_tokens.json
Creates CSS custom properties for web theme consistency.
"""

import json
import os
from pathlib import Path

def load_design_tokens(filepath: str = "design_tokens.json") -> dict:
    """Load design tokens from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_css_variables(tokens: dict) -> str:
    """Generate CSS custom properties from design tokens."""
    css_lines = [":root {"]
    
    # Process colors
    if "color" in tokens:
        if "semantic" in tokens["color"]:
            for name, value in tokens["color"]["semantic"].items():
                if isinstance(value, dict):  # Nested objects like text, background, border
                    for subname, subvalue in value.items():
                        css_lines.append(f"  --color-{name}-{subname}: {subvalue};")
                else:
                    css_lines.append(f"  --color-{name}: {value};")
        
        if "system" in tokens["color"]:
            for name, value in tokens["color"]["system"].items():
                css_lines.append(f"  --color-{name}: {value};")
    
    # Process spacing
    if "spacing" in tokens:
        for name, value in tokens["spacing"].items():
            css_lines.append(f"  --spacing-{name}: {value};")
    
    # Process radius
    if "radius" in tokens:
        for name, value in tokens["radius"].items():
            css_lines.append(f"  --radius-{name}: {value};")
    
    # Process typography
    if "typography" in tokens:
        if "fontFamily" in tokens["typography"]:
            for name, value in tokens["typography"]["fontFamily"].items():
                css_lines.append(f"  --font-{name}: {value};")
        
        if "fontSize" in tokens["typography"]:
            for name, value in tokens["typography"]["fontSize"].items():
                css_lines.append(f"  --font-size-{name}: {value};")
        
        if "fontWeight" in tokens["typography"]:
            for name, value in tokens["typography"]["fontWeight"].items():
                css_lines.append(f"  --font-weight-{name}: {value};")
        
        if "lineHeight" in tokens["typography"]:
            for name, value in tokens["typography"]["lineHeight"].items():
                css_lines.append(f"  --line-height-{name}: {value};")
    
    # Process shadow
    if "shadow" in tokens:
        for name, value in tokens["shadow"].items():
            css_lines.append(f"  --shadow-{name}: {value};")
    
    # Process zIndex
    if "zIndex" in tokens:
        for name, value in tokens["zIndex"].items():
            css_lines.append(f"  --zindex-{name}: {value};")
    
    # Process animation
    if "animation" in tokens:
        if "duration" in tokens["animation"]:
            for name, value in tokens["animation"]["duration"].items():
                css_lines.append(f"  --animation-duration-{name}: {value};")
        
        if "easing" in tokens["animation"]:
            for name, value in tokens["animation"]["easing"].items():
                css_lines.append(f"  --animation-easing-{name}: {value};")
    
    css_lines.append("}")
    return "\n".join(css_lines)

def main():
    """Main function to generate theme.css."""
    try:
        tokens = load_design_tokens()
        css_content = generate_css_variables(tokens)
        
        # Ensure web directory exists
        Path("web").mkdir(exist_ok=True)
        
        # Write theme.css
        with open("web/theme.css", "w") as f:
            f.write(css_content)
        
        print("Generated web/theme.css from design_tokens.json")
        return True
    except Exception as e:
        print(f"Error generating theme.css: {e}")
        return False

if __name__ == "__main__":
    main()