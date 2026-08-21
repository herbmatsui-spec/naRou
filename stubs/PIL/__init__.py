"""Stub for Pillow (PIL) used in tests.
Only provides minimal Image and ImageFont classes required by the test suite.
"""
from __future__ import annotations


class Image:
    @staticmethod
    def open(path):
        return Image()

    def save(self, path):
        pass


class ImageDraw:
    def __init__(self, image=None):
        pass

    @staticmethod
    def Draw(image):
        return ImageDraw()


class ImageFont:
    @staticmethod
    def load_default():
        return ImageFont()

    @staticmethod
    def truetype(path, size):
        return ImageFont()

    def getsize(self, text):
        return (0, 0)
