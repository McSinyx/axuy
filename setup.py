#!/usr/bin/env python3
from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='axuy',
    version='0.0.1',
    description='Minimalist first-person shooter',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/McSinyx/axuy',
    author='Nguyễn Gia Phong',
    author_email='vn.mcsinyx@gmail.com',
    license='AGPLv3+',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Games/Entertainment :: First Person Shooters'],
    keywords='fps opengl glfw',
    packages=['axuy'],
    install_requires=['numpy', 'pyrr', 'moderngl', 'glfw'],
    package_data={'axuy': ['map.npy', 'shaders']},
    entry_points={'console_scripts': ['axuy = axuy.peer:main']})
