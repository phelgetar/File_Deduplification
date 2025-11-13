#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: gui.py
# Purpose: Interactive GUI preview for file organization plans
#
# Description:
# Provides a graphical user interface for previewing and reviewing
# file organization plans before execution. Uses PySimpleGUI for
# cross-platform compatibility.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.6.0
# Last Modified: 2025-11-12 by Tim Canady
#
# Revision History:
# - 0.6.0 (2025-11-12): Updated statistics to show all 10 file categories — Tim Canady
# - 0.5.0 (2025-11-12): Implemented full GUI with file tree view — Tim Canady
# - 0.1.0 (2025-09-28): Initial placeholder — Tim Canady
###################################################################

try:
    import PySimpleGUI as sg
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    sg = None

from pathlib import Path
from typing import List, Tuple

def launch_gui(plan: List[Tuple] = None):
    """
    Launch interactive GUI to preview file organization plan.

    Args:
        plan: List of tuples containing (FileInfo, destination_path)
    """
    if not GUI_AVAILABLE:
        print("⚠️ PySimpleGUI not available. Install with:")
        print("   python -m pip install --upgrade --extra-index-url https://PySimpleGUI.net/install PySimpleGUI")
        print("   Skipping GUI preview...")
        return

    if not plan:
        print("⚠️ No plan data provided to GUI")
        return

    # Set theme - handle both old and new PySimpleGUI API
    try:
        sg.theme('DarkBlue3')
    except (AttributeError, Exception):
        # Fallback if theme() doesn't exist or fails
        try:
            sg.ChangeLookAndFeel('DarkBlue3')
        except:
            pass  # Continue without theme

    try:
        # Build file tree data
        tree_data = []
        for idx, (file_info, dest_path) in enumerate(plan, 1):
            source = str(file_info.path)
            destination = str(dest_path)
            file_type = file_info.type or "unknown"
            size_mb = f"{file_info.size / 1_000_000:.2f}" if file_info.size else "0"

            tree_data.append([
                idx,
                Path(source).name,
                file_type,
                f"{size_mb} MB",
                source,
                destination
            ])

        # Define layout
        headings = ['#', 'File Name', 'Type', 'Size', 'Source Path', 'Destination Path']

        layout = [
            [sg.Text('📁 File Organization Preview', font=('Helvetica', 16, 'bold'))],
            [sg.Text(f'Total files to organize: {len(plan)}', font=('Helvetica', 12))],
            [sg.HorizontalSeparator()],
            [sg.Table(
                values=tree_data,
                headings=headings,
                auto_size_columns=False,
                col_widths=[5, 30, 10, 10, 50, 50],
                justification='left',
                num_rows=min(25, len(tree_data)),
                key='-TABLE-',
                enable_events=True,
                expand_x=True,
                expand_y=True
            )],
            [sg.HorizontalSeparator()],
            [
                sg.Text('Statistics:', font=('Helvetica', 10, 'bold')),
                sg.Text(f"  Images: {sum(1 for f, _ in plan if f.type == 'image')}"),
                sg.Text(f"  Videos: {sum(1 for f, _ in plan if f.type == 'video')}"),
                sg.Text(f"  Audio: {sum(1 for f, _ in plan if f.type == 'audio')}"),
            ],
            [
                sg.Text(''),
                sg.Text(f"  Documents: {sum(1 for f, _ in plan if f.type == 'document')}"),
                sg.Text(f"  Spreadsheets: {sum(1 for f, _ in plan if f.type == 'spreadsheet')}"),
                sg.Text(f"  Presentations: {sum(1 for f, _ in plan if f.type == 'presentation')}"),
            ],
            [
                sg.Text(''),
                sg.Text(f"  Code: {sum(1 for f, _ in plan if f.type == 'code')}"),
                sg.Text(f"  Archives: {sum(1 for f, _ in plan if f.type == 'archive')}"),
                sg.Text(f"  Data: {sum(1 for f, _ in plan if f.type == 'data')}"),
            ],
            [
                sg.Text(''),
                sg.Text(f"  Fonts: {sum(1 for f, _ in plan if f.type == 'font')}"),
                sg.Text(f"  Installers: {sum(1 for f, _ in plan if f.type == 'installer')}"),
                sg.Text(f"  Certificates: {sum(1 for f, _ in plan if f.type == 'certificate')}"),
            ],
            [
                sg.Text(''),
                sg.Text(f"  Shortcuts: {sum(1 for f, _ in plan if f.type == 'shortcut')}"),
                sg.Text(f"  Scientific: {sum(1 for f, _ in plan if f.type == 'scientific')}"),
                sg.Text(f"  System: {sum(1 for f, _ in plan if f.type == 'system')}"),
            ],
            [
                sg.Text(''),
                sg.Text(f"  Backup: {sum(1 for f, _ in plan if f.type == 'backup')}"),
                sg.Text(f"  Temporary: {sum(1 for f, _ in plan if f.type == 'temporary')}"),
                sg.Text(f"  Other: {sum(1 for f, _ in plan if f.type in ['other', 'unknown'])}"),
            ],
            [sg.HorizontalSeparator()],
            [
                sg.Button('Close', size=(10, 1)),
                sg.Push(),
                sg.Text('💡 Tip: Review the plan before executing with --execute', font=('Helvetica', 9, 'italic'))
            ]
        ]

        # Create window
        window = sg.Window(
            'File Deduplication Preview',
            layout,
            resizable=True,
            size=(1200, 600),
            finalize=True
        )

        # Event loop
        while True:
            event, values = window.read()

            if event == sg.WIN_CLOSED or event == 'Close':
                break

        window.close()
        print("✅ GUI closed")

    except Exception as e:
        print(f"⚠️ GUI error: {e}")
        print("   Continuing without GUI preview...")
        print("   To fix PySimpleGUI issues, run:")
        print("   python -m pip uninstall PySimpleGUI")
        print("   python -m pip install --upgrade --extra-index-url https://PySimpleGUI.net/install PySimpleGUI")
