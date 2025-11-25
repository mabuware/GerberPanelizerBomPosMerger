import xml.etree.ElementTree as ET
import csv
import math
import os
import sys
import tkinter as tk
from tkinter import filedialog

# Initialize tkinter root for file dialogs
root = tk.Tk()
root.withdraw()

def select_file(title, filetypes):
    """Opens a file selection dialog."""
    print(f"Please select: {title}")
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    if not path:
        print("No file selected. Exiting.")
        sys.exit(0)
    print(f"Selected: {path}")
    return path

def rotate_point(x, y, angle_degrees):
    """Rotates a point (x, y) around (0, 0) by angle_degrees (CCW)."""
    rad = math.radians(angle_degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    # Standard 2D rotation matrix
    # x' = x cos(a) - y sin(a)
    # y' = x sin(a) + y cos(a)
    new_x = x * cos_a - y * sin_a
    new_y = x * sin_a + y * cos_a
    return new_x, new_y

def normalize_angle(angle):
    """Normalizes angle to 0-360 range."""
    return angle % 360

def load_bom(filepath):
    """Loads BOM, splits grouped designators, returns list of components."""
    components = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle grouped designators like "C1, C2, C3"
            designators_raw = row.get('Designator', '')
            # Split by comma, strip whitespace
            designators = [d.strip() for d in designators_raw.split(',') if d.strip()]
            
            qty_str = row.get('Quantity', '1')
            try:
                qty_per_ref = 1 # Usually 1 per designator split
            except:
                qty_per_ref = 1

            for ref in designators:
                # Create a clean copy for each designator
                comp = row.copy()
                comp['Designator'] = ref
                comp['Quantity'] = 1 # Normalized to 1 per split item
                components.append(comp)
    return components

def load_positions(filepath):
    """Loads Pick and Place file."""
    positions = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Attempt to parse coordinates as floats immediately to ensure validity
            try:
                row['Mid X'] = float(row['Mid X'])
                row['Mid Y'] = float(row['Mid Y'])
                row['Rotation'] = float(row['Rotation'])
                positions.append(row)
            except ValueError:
                continue # Skip header repetition or invalid lines
    return positions

def main():
    print("--- Gerber Panelizer Data Merger ---")
    
    # 1. Load Gerberset
    gerberset_path = select_file("Select .gerberset file", [("GerberLayoutSet", "*.gerberset *.txt *.xml")])
    
    try:
        tree = ET.parse(gerberset_path)
        xml_root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    # 2. Extract Instances and identify unique Source Paths
    instances = []
    unique_paths = set()
    
    # Namespace handling might be required depending on XML, usually strip it for simple logic
    # or search generically.
    for instance in xml_root.findall(".//GerberInstance"):
        path = instance.find("GerberPath").text
        
        # Get Center (Offset)
        center = instance.find("Center")
        x_off = float(center.find("X").text)
        y_off = float(center.find("Y").text)
        
        # Get Rotation
        angle = float(instance.find("Angle").text)
        
        instances.append({
            "path": path,
            "x_off": x_off,
            "y_off": y_off,
            "angle": angle
        })
        unique_paths.add(path)

    print(f"Found {len(instances)} board instances from {len(unique_paths)} unique source designs.")

    # 3. Ask user for BOM and P&P for each unique path
    # source_data = { "path": { "bom": [], "pos": [] } }
    source_data = {}
    
    for src_path in unique_paths:
        filename = os.path.basename(src_path)
        print(f"\n--- Configuration for design: {filename} ---")
        print(f"Original path: {src_path}")
        
        bom_path = select_file(f"Select BOM for {filename}", [("CSV Files", "*.csv")])
        pos_path = select_file(f"Select Pick&Place for {filename}", [("CSV Files", "*.csv")])
        
        source_data[src_path] = {
            "bom": load_bom(bom_path),
            "pos": load_positions(pos_path)
        }

    # 4. Process Instances
    merged_bom_rows = []
    merged_pos_rows = []
    
    print("\nProcessing instances...")
    
    for i, inst in enumerate(instances):
        # Create a prefix like B1, B2, etc.
        prefix = f"B{i+1}_" 
        
        src = source_data[inst["path"]]
        
        # Transform Position Data
        for pos in src["pos"]:
            original_ref = pos["Designator"]
            new_ref = prefix + original_ref
            
            # 1. Rotate coordinate around (0,0)
            # Note: Check if your P&P origin is center or corner. 
            # Standard assumption: P&P is relative to design origin, 
            # XML Center is where design origin moves to.
            rx, ry = rotate_point(pos["Mid X"], pos["Mid Y"], inst["angle"])
            
            # 2. Translate
            final_x = rx + inst["x_off"]
            final_y = ry + inst["y_off"]
            
            # 3. Rotate Component Angle
            final_rot = normalize_angle(pos["Rotation"] + inst["angle"])
            
            new_pos_row = {
                "Designator": new_ref,
                "Mid X": f"{final_x:.4f}",
                "Mid Y": f"{final_y:.4f}",
                "Rotation": f"{final_rot:.1f}",
                "Layer": pos["Layer"]
            }
            merged_pos_rows.append(new_pos_row)

        # Transform BOM Data
        for bom in src["bom"]:
            new_bom_row = bom.copy()
            new_bom_row["Designator"] = prefix + bom["Designator"]
            merged_bom_rows.append(new_bom_row)

    # 5. Aggregating BOM
    # Group by: Footprint, Value, LCSC Part # (and maybe others like Comment/Description if they exist)
    # We will dynamically find keys to group by, excluding Designator and Quantity
    print("Merging BOM...")
    
    bom_grouped = {}
    
    for row in merged_bom_rows:
        # Create a unique key for the part type
        # Using tuple of relevant fields
        key_fields = ["Footprint", "Value", "LCSC Part #"]
        # Add any other columns found in the csv that define uniqueness (e.g. Manufacturer)
        # We stick to the standard ones found in your example
        
        key = tuple(row.get(k, "") for k in key_fields)
        
        if key not in bom_grouped:
            bom_grouped[key] = {
                "data": row, # Keep one copy of metadata
                "refs": [],
                "qty": 0
            }
        
        bom_grouped[key]["refs"].append(row["Designator"])
        bom_grouped[key]["qty"] += int(float(row["Quantity"])) # Handle float strings safely

    # Flatten back to list
    final_bom_list = []
    bom_fieldnames = ["Designator"] + ["Footprint", "Value", "Quantity", "LCSC Part #"] 
    # Ensure we preserve other columns if they exist
    if merged_bom_rows:
        all_keys = merged_bom_rows[0].keys()
        for k in all_keys:
            if k not in bom_fieldnames:
                bom_fieldnames.append(k)

    for key, group in bom_grouped.items():
        row = group["data"].copy()
        row["Designator"] = ", ".join(group["refs"])
        row["Quantity"] = str(group["qty"])
        final_bom_list.append(row)

    # 6. Write Outputs
    
    # Write Position File
    out_pos_file = "merged_positions.csv"
    pos_headers = ["Designator", "Mid X", "Mid Y", "Rotation", "Layer"]
    with open(out_pos_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=pos_headers)
        writer.writeheader()
        writer.writerows(merged_pos_rows)
    
    # Write BOM File
    out_bom_file = "merged_bom.csv"
    with open(out_bom_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=bom_fieldnames)
        writer.writeheader()
        writer.writerows(final_bom_list)

    print(f"\nSuccess!")
    print(f"Generated: {os.path.abspath(out_pos_file)}")
    print(f"Generated: {os.path.abspath(out_bom_file)}")

if __name__ == "__main__":
    main()