#!/usr/bin/env python3
"""
FIT Module Package Initialization

This module provides functionality for converting workout data to Garmin FIT format
and uploading FIT files to Garmin Connect.
"""

from .fit_converter import FITConverter

__all__ = ['FITConverter']
