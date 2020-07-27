# acsuite

audiocutter(.py) replacement for VapourSynth.

Allows for easy frame-based cutting/trimming/splicing of audio files
using VapourSynth clip information.


## Functions:

### eztrim(clip, trims, audio_file[, outfile, ffmpeg_path=, quiet=])

```py
import vapoursynth as vs
core = vs.core
from acsuite import eztrim

file  = r'/BDMV/STREAM/00003.m2ts'
afile = r'/BDMV/STREAM/00003.wav'  # pre-extracted with TSMuxer or similar

src = core.lsmas.LWLibavSource(file)

# for the example, we will assume the src clip is 100 frames long (0-99)
trimmed_clip = src[3:22]+src[23:40]+src[48]+src[50:-20]+src[-10:-5]+src[97:]

# `clip` arg should be the uncut/untrimmed source that you are trimming from
eztrim(src, [(3,22),(23,40),(48,49),(50,-20),(-10,-5),(97,None)], afile)
```

##### Output:

Uses the file extension of the input _audio_file_ to output a cut/trimmed audio file with the same extension. If no _outfile_ is given, defaults to `audio_file_cut.ext`.

## Getting Started

### Dependencies
- [FFmpeg](https://ffmpeg.org/)
- [VapourSynth R49+](https://github.com/vapoursynth/vapoursynth/releases)

### Installing

#### Arch Linux

Install the [AUR package](https://aur.archlinux.org/packages/vapoursynth-tools-acsuite-git/) `vapoursynth-tools-acsuite-git` with your favorite AUR helper:

```sh
$ yay -S vapoursynth-tools-acsuite-git
```

#### Gentoo Linux

Install via the [VapourSynth portage tree](https://github.com/4re/vapoursynth-portage).

#### Windows / Other

Use the [Python Package Index (PyPI / pip)](https://pypi.org/project/acsuite-orangechannel/#description):

```sh
python3 -m pip install --user --upgrade acsuite-orangechannel
```

or simply

```sh
pip install acsuite-orangechannel
```

if you are able to use a `pip` executable directly.

## Help!

Check out the [documentation](https://orangechannel.github.io/acsuite/html/index.html) or use Python's builtin `help()`: 

```py
help('acsuite')
```

