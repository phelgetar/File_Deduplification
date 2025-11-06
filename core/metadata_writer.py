#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: metadata_writer.py
# Purpose: Embed metadata into supported file types.
#
# Description of code and how it works:
# Updates metadata for PDF, DOCX, and MP3 files using libraries like
# PyMuPDF, python-docx, and mutagen. Unsupported types are skipped.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial metadata logic — Tim Canady
###################################################################

from pathlib import Path
from models.file_info import FileInfo

# PDF
import fitz  # PyMuPDF
# DOCX
from docx import Document
# MP3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TDRC


def write_metadata(file_info: FileInfo):
    ext = file_info.path.suffix.lower()

    if ext == ".pdf":
        try:
            doc = fitz.open(file_info.path)
            doc.set_metadata({
                "title": file_info.type or "",
                "author": file_info.owner or "",
                "keywords": f"{file_info.type},{file_info.owner},{file_info.year}"
            })
            doc.save(file_info.path, incremental=True)
        except Exception as e:
            print(f"[PDF] Failed to update {file_info.path}: {e}")

    elif ext == ".docx":
        try:
            doc = Document(file_info.path)
            core = doc.core_properties
            core.title = file_info.type or ""
            core.author = file_info.owner or ""
            doc.save(file_info.path)
        except Exception as e:
            print(f"[DOCX] Failed to update {file_info.path}: {e}")

    elif ext == ".mp3":
        try:
            audio = EasyID3(file_info.path)
            audio["title"] = file_info.type or ""
            audio["artist"] = file_info.owner or ""
            if file_info.year:
                audio["date"] = file_info.year
            audio.save()
        except Exception as e:
            print(f"[MP3] Failed to update {file_info.path}: {e}")

    else:
        print(f"Unsupported file type for metadata: {file_info.path}")