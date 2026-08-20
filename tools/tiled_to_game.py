#!/usr/bin/env python3
"""
Tiled Map Editor Converter
Converts .tmx files from Tiled Map Editor to game JSON format.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

def convert_tmx_to_json(tmx_path: Path, output_path: Path, tileset_def_path: Path = Path("assets/tiles/tileset_def.json")) -> None:
    """
    Convert a Tiled .tmx file to game JSON format.
    
    Args:
        tmx_path: Path to input .tmx file
        output_path: Path to output JSON file
        tileset_def_path: Path to tileset definition JSON
    """
    # Load tileset definition for tile ID mapping
    if tileset_def_path.exists():
        with open(tileset_def_path) as f:
            tileset_defs = json.load(f)
    else:
        tileset_defs = {"tiles": {}}
        print(f"Warning: {tileset_def_path} not found, using empty tile definitions")
    
    # Parse the TMX file
    tree = ET.parse(tmx_path)
    root = tree.getroot()
    
    # Get map properties
    width = int(root.attrib.get("width", 0))
    height = int(root.attrib.get("height", 0))
    tile_width = int(root.attrib.get("tilewidth", 16))
    tile_height = int(root.attrib.get("tileheight", 16))
    
    # Initialize map data
    map_data: Dict[str, Any] = {
        "width": width,
        "height": height,
        "tile_width": tile_width,
        "tile_height": tile_height,
        "layers": [],
        "objectgroups": []
    }
    
    # Process each layer
    for child in root:
        if child.tag == "layer":
            layer_data = parse_layer(child, width, height)
            if layer_data:
                map_data["layers"].append(layer_data)
        elif child.tag == "objectgroup":
            objectgroup_data = parse_objectgroup(child)
            if objectgroup_data:
                map_data["objectgroups"].append(objectgroup_data)
    
    # Write output JSON
    with open(output_path, 'w') as f:
        json.dump(map_data, f, indent=2)
    
    print(f"Converted {tmx_path} -> {output_path}")

def parse_layer(layer_elem: ET.Element, map_width: int, map_height: int) -> Optional[Dict[str, Any]]:
    """Parse a tile layer from TMX element."""
    name = layer_elem.attrib.get("name", "layer")
    width = int(layer_elem.attrib.get("width", map_width))
    height = int(layer_elem.attrib.get("height", map_height))
    
    # Initialize tile data array (2D)
    data: List[List[int]] = [[-1 for _ in range(width)] for _ in range(height)]
    
    # Find the data element
    data_elem = layer_elem.find("data")
    if data_elem is None:
        return None
    
    # Handle CSV or base64 encoding
    encoding = data_elem.attrib.get("encoding", "")
    if encoding == "csv":
        # Parse CSV data
        text = data_elem.text.strip()
        if text:
            values = [int(x.strip()) for x in text.split(",") if x.strip()]
            idx = 0
            for y in range(height):
                for x in range(width):
                    if idx < len(values):
                        gid = values[idx]
                        # Convert GID to tile ID (accounting for tileset firstgid)
                        # For now, we'll store the raw GID and convert later during loading
                        # In a full implementation, we'd use the tileset information
                        data[y][x] = gid
                        idx += 1
    elif encoding == "":
        # XML format (less common but supported)
        tile_elements = data_elem.findall("tile")
        for tile_elem in tile_elements:
            x = int(tile_elem.attrib.get("x", 0))
            y = int(tile_elem.attrib.get("y", 0))
            gid = int(tile_elem.attrib.get("gid", 0))
            if 0 <= x < width and 0 <= y < height:
                data[y][x] = gid
    
    # Convert GIDs to tile IDs using a simple approach
    # In a full implementation, we'd parse the tileset elements to know firstgid, tile width/height, etc.
    # For now, we'll assume a simple mapping or leave as GIDs for later conversion
    
    layer_data: Dict[str, Any] = {
        "name": name,
        "type": "tilelayer",
        "width": width,
        "height": height,
        "data": data,
        "properties": parse_properties(layer_elem.find("properties"))
    }
    
    return layer_data

def parse_objectgroup(objgroup_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """Parse an object group from TMX element."""
    name = objgroup_elem.attrib.get("name", "objectgroup")
    
    objects: List[Dict[str, Any]] = []
    for obj_elem in objgroup_elem.findall("object"):
        obj_data = parse_object(obj_elem)
        if obj_data:
            objects.append(obj_data)
    
    objectgroup_data: Dict[str, Any] = {
        "name": name,
        "type": "objectgroup",
        "objects": objects,
        "properties": parse_properties(objgroup_elem.find("properties"))
    }
    
    return objectgroup_data

def parse_object(obj_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """Parse an object from TMX element."""
    name = obj_elem.attrib.get("name", "")
    obj_type = obj_elem.attrib.get("type", "")
    x = float(obj_elem.attrib.get("x", 0))
    y = float(obj_elem.attrib.get("y", 0))
    width = float(obj_elem.attrib.get("width", 0))
    height = float(obj_elem.attrib.get("height", 0))
    
    # Parse properties
    properties = parse_properties(obj_elem.find("properties"))
    
    obj_data: Dict[str, Any] = {
        "name": name,
        "type": obj_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "properties": properties
    }
    
    # Handle optional gid (for tile objects)
    gid = obj_elem.attrib.get("gid")
    if gid is not None:
        obj_data["gid"] = int(gid)
    
    # Handle point objects (no width/height)
    if obj_elem.attrib.get("point") == "1":
        obj_data["point"] = True
        # Remove width/height for point objects
        if "width" in obj_data:
            del obj_data["width"]
        if "height" in obj_data:
            del obj_data["height"]
    
    return obj_data

def parse_properties(properties_elem: Optional[ET.Element]) -> Dict[str, Any]:
    """Parse properties element."""
    properties: Dict[str, Any] = {}
    if properties_elem is not None:
        for prop in properties_elem.findall("property"):
            name = prop.attrib.get("name")
            value = prop.attrib.get("value")
            prop_type = prop.attrib.get("type", "string")
            
            # Convert value based on type
            if prop_type == "int":
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = 0
            elif prop_type == "float":
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    value = 0.0
            elif prop_type == "bool":
                value = value.lower() == "true" if isinstance(value, str) else bool(value)
            # For string type, keep as is (default)
            
            if name is not None:
                properties[name] = value
    
    return properties

def main():
    parser = argparse.ArgumentParser(description="Convert Tiled .tmx files to game JSON format")
    parser.add_argument("input", type=Path, help="Input .tmx file or directory")
    parser.add_argument("output", type=Path, help="Output JSON file or directory")
    parser.add_argument("--tileset-def", type=Path, default=Path("assets/tiles/tileset_def.json"),
                       help="Path to tileset definition JSON")
    parser.add_argument("--recursive", action="store_true",
                       help="Process directories recursively")
    
    args = parser.parse_args()
    
    if args.input.is_file():
        # Single file conversion
        if args.output.is_dir():
            output_file = args.output / f"{args.input.stem}.json"
        else:
            output_file = args.output
        convert_tmx_to_json(args.input, output_file, args.tileset_def)
    elif args.input.is_dir():
        # Directory conversion
        if args.output.is_file():
            print("Error: Output must be a directory when input is a directory")
            return
        
        args.output.mkdir(parents=True, exist_ok=True)
        
        pattern = "**/*.tmx" if args.recursive else "*.tmx"
        tmx_files = list(args.input.glob(pattern))
        
        if not tmx_files:
            print(f"No .tmx files found in {args.input}")
            return
        
        for tmx_file in tmx_files:
            # Maintain directory structure in output
            relative_path = tmx_file.relative_to(args.input)
            output_file = args.output / relative_path.with_suffix('.json')
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            convert_tmx_to_json(tmx_file, output_file, args.tileset_def)
    else:
        print(f"Error: Input path {args.input} does not exist")

if __name__ == "__main__":
    main()