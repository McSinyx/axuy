#!/usr/bin/env python3
from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='axuy',
    version='0.0.9',
    description='Minimalist first-person shooter',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/McSinyx/axuy',
    author='Nguyễn Gia Phong',
    author_email='vn.mcsinyx@gmail.com',
    license='AGPLv3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Games/Entertainment :: First Person Shooters'],
    keywords='fps p2p opengl glfw',
    packages=['axuy'],
    install_requires=['appdirs', 'numpy', 'pyrr',
                      'moderngl', 'glfw>=1.8', 'Pillow'],
    package_data={'axuy': ['map.npy', 'shaders/*',
                           'icon.png', 'settings.ini']},
    entry_points={'console_scripts': ['axuy = axuy.__main__:main']})
