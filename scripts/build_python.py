#!/usr/bin/env python3
"""Build wheel and complete source archive using installed setuptools/wheel."""
from pathlib import Path
import os
from setuptools.build_meta import build_wheel,build_sdist
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
(ROOT/'dist').mkdir(exist_ok=True)
print(build_sdist(str(ROOT/'dist')))
print(build_wheel(str(ROOT/'dist')))
