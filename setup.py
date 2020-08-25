from distutils.util import convert_path

import setuptools

meta = {}
exec(open(convert_path('acsuite/_metadata.py')).read(), meta)

with open('README.md') as fh:
    long_description = fh.read()

with open('requirements.txt') as fh:
    install_requires = fh.read()

setuptools.setup(
    name='acsuite-orangechannel',
    version=meta['__version__'],
    description='Frame-based cutting/trimming/splicing of audio with VapourSynth and FFmpeg.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/OrangeChannel/acsuite',
    author=meta['__author__'].split()[0],
    author_email=meta['__author__'].split()[1][1:-1],
    license='UNLICENSE',
    install_requires=install_requires,
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "License :: Public Domain",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Topic :: Multimedia :: Sound/Audio",
        "Typing :: Typed",
    ],
    keywords="audio vapoursynth encoding trim cut ffmpeg",
    project_urls={
        'Documentation': 'https://acsuite.readthedocs.io/en/latest/',
        'Source': 'https://github.com/OrangeChannel/acsuite/blob/master/acsuite/__init__.py',
        'Tracker': 'https://github.com/OrangeChannel/acsuite/issues',
    },
    packages=setuptools.find_packages(exclude=['tests']),
    package_data={
        'acsuite': ['py.typed']
    },
    python_requires='>=3.8',
)
