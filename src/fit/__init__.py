#!/usr/bin/env python3
"""
FIT Module Package Initialization

This module provides functionality for converting workout data to Garmin FIT format
and uploading FIT files to Garmin Connect.
"""

from .fit_converter import FITConverter
from .garmin_uploader import GarminUploader

__all__ = ['FITConverter', 'GarminUploader']
