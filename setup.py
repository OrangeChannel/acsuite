import setuptools

with open('README.md') as fh:
    long_description = fh.read()

with open('requirements.txt') as fh:
    install_requires = fh.read()

setuptools.setup(
    name='acsuite-orangechannel',
    version='4.2.0',
    description='Frame-based cutting/trimming/splicing of audio with VapourSynth.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/OrangeChannel/acsuite',
    author='Dave',
    author_email='orangechannel@pm.me',
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
    keywords="audio vapoursynth encoding trim cut",
    project_urls={
        'Documentation': 'https://orangechannel.github.io/acsuite/html/index.html',
        'Source': 'https://github.com/OrangeChannel/acsuite/blob/master/acsuite/__init__.py',
        'Tracker': 'https://github.com/OrangeChannel/acsuite/issues',
    },
    packages=setuptools.find_packages(exclude=['tests']),
    package_data={
        'acsuite': ['py.typed']
    },
    python_requires='>=3.8',
)
