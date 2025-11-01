"""Setup script for AGI Assistant."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ''

# Read requirements
requirements_file = Path(__file__).parent / 'requirements.txt'
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='agi-assistant-mvp',
    version='0.1.0',
    author='AGI Assistant Team',
    author_email='your.email@example.com',
    description='Privacy-first desktop AI assistant that learns and automates workflows',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/agi-assistant-mvp',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Office/Business',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: Microsoft :: Windows',
    ],
    python_requires='>=3.10',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'agi-assistant=src.main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
