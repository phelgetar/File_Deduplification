#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: classifier.py
# Purpose: Classify files using AI model (e.g., GPT) for sorting.
#
# Description of code and how it works:
# Uses OpenAI's GPT API to determine file type, owner, and year
# from content or file name patterns. Results populate FileInfo.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial classifier logic — Tim Canady
###################################################################

import openai
import os
from models.file_info import FileInfo

openai.api_key = os.getenv("OPENAI_API_KEY")


def classify_file(file_info: FileInfo) -> FileInfo:
    prompt = f"""
    You are an intelligent file classifier. Given the filename and metadata, extract:
    - File type (financial, legal, medical, image, audio, etc.)
    - Owner's name
    - Year (if any)

    Filename: {file_info.path.name}
    Path: {file_info.path}
    Size: {file_info.size} bytes

    Respond with JSON format:
    {{"type": ..., "owner": ..., "year": ...}}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )

        content = response["choices"][0]["message"]["content"]
        result = eval(content)
        file_info.type = result.get("type")
        file_info.owner = result.get("owner")
        file_info.year = result.get("year")

    except Exception as e:
        file_info.type = "Unknown"
        file_info.owner = None
        file_info.year = None

    return file_info