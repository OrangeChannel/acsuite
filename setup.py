import setuptools
from distutils.util import convert_path


__author__, __version__ = str(), str()
exec(open(convert_path('acsuite/_metadata.py')).read())
if not __author__ and not __version__:
    raise ValueError('setup: package missing metadata')

with open('README.md') as fh:
    long_description = fh.read()

with open('requirements.txt') as fh:
    # this is so it gets recognized by GitHub's packages thing
    install_requires = fh.read()

setuptools.setup(
    name='acsuite-orangechannel',
    version=__version__,
    description='Frame-based cutting/trimming/splicing of audio with VapourSynth and FFmpeg.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/OrangeChannel/acsuite',
    author=__author__.split()[0],
    author_email=__author__.split()[1][1:-1],
    license='UNLICENSE',
    install_requires=install_requires,
    extras_require={
        "VFR Progress Bar": ['rich>=6.1.2']
    },
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
