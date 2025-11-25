# Gerber Panelizer Data Merger

A Python utility to merge **Bill of Materials (BOM)** and **Pick & Place (CPL/Position)** files (as exported by Fabrication Toolkit from KiCAD) for PCB panels created with [ThisIsNotRocketScience/GerberTools](https://github.com/ThisIsNotRocketScience/GerberTools).

While the Gerber Panelizer tool is excellent for merging Gerber files, it does not natively support merging assembly data. This script reads the `.gerberset` file to calculate the precise rotation and offsets of every board in the panel, automatically generating a unified BOM and Pick & Place file ready for assembly (e.g., JLCPCB).

## Features

*   **Geometry Calculation**: Parses the XML `.gerberset` file to apply accurate X/Y offsets and rotations to component coordinates.
*   **Designator Management**: Renames components to avoid duplicates (e.g., `C1` on Board 1 becomes `B1_C1`, `C1` on Board 2 becomes `B2_C1`).
*   **BOM Aggregation**: Merges identical parts across the entire panel into single line items, summing quantities and concatenating designators.
*   **Unique File Handling**: Intelligently asks for source files only once per unique design, even if the design is repeated multiple times on the panel.
*   **Standard Library Only**: Written using only Python standard libraries (no `pip install` required).

## Prerequisites

*   **Python 3.x** installed on your system.
*   **Source Files**:
    *   The `.gerberset` file saved from Gerber Panelizer.
    *   The BOM `.csv` file for each distinct board design.
    *   The Pick & Place `.csv` file for each distinct board design.

## Input File Requirements

The script expects CSV files formatted similarly to KiCad/JLCPCB exports:

### BOM File (`.csv`)
Must contain headers:
*   `Designator`
*   `Quantity`
*   `Footprint`
*   `Value`
*   `LCSC Part #` (Optional, used for grouping if present)

### Pick & Place File (`.csv`)
Must contain headers:
*   `Designator`
*   `Mid X`
*   `Mid Y`
*   `Rotation`
*   `Layer`

## Usage

1.  Download `merge_panel_data.py` to your computer.
2.  Open a terminal or command prompt.
3.  Run the script:
    ```bash
    python merge_panel_data.py
    ```
4.  **Select the Layout**: A file dialog will appear. Select your `.gerberset` file.
5.  **Select Source Data**: The script will detect the unique boards in your panel. For each board, it will ask you to select:
    *   The BOM CSV file.
    *   The Pick & Place CSV file.
6.  **Done**: The script will generate two files in the script's directory:
    *   `merged_bom.csv`
    *   `merged_positions.csv`

## How it Works

1.  **Parsing**: The script reads the XML structure of the `.gerberset` file to find the center coordinates `(X, Y)` and `Angle` for every instance of a board.
2.  **Transformation**: 
    *   It rotates the original component coordinates around the board's (0,0) origin based on the panel rotation.
    *   It translates (shifts) the coordinates based on the instance's location in the panel.
    *   It adds the panel rotation to the component's individual rotation.
3.  **Merging**: It combines the data into a single list, generating unique designators (Prefix `B[InstanceNumber]_`) and aggregating BOM quantities.