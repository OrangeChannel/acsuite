# acsuite

audiocutter(.py) replacement for VapourSynth.

Allows for easy frame-based cutting/trimming/splicing of audio files
from within a VapourSynth environment.


## Functions:

### eztrim(clip, trims, audio_file, outfile)

```py
import vapoursynth as vs
core = vs.core

from acsuite import eztrim

file  = r'/BDMV/STREAM/00003.m2ts'
afile = r'/BDMV/STREAM/00003.wav'  # pre-extracted with TSMuxer or similar

src = core.lsmas.LWLibavSource(file)
# for the example, we will assume the src clip is 100 frames long (0-99)

clip = src[3:22]+src[23:40]+src[48]+src[50:-20]+src[-10:-5]+src[97:]

eztrim(src, [(3,22),(23,40),(48,49),(50,-20),(-10,-5),(97,0)], afile, 'cut.wav')
# clip should be the uncut/untrimmed src that you are trimming from
```

<!--
## Ordered chapters information:
If `gui` is `True`,
MKVToolNix GUI will open into a new chapter editor environment
with the timestamps needed for ordered chapters.
The OGM or simple chapter format doesn't support using end timestamps,
but ordered-chapters require them for every chapter.
In order to determine the end timestamps,
under `Additional modifications` tick
`Derive end timestamps from start timestamps`.
The last chapter is simply a placeholder
to determine the end timestamp for the last chapter specified in `trims`.
After deriving the end timestamps,
delete this chapter.
-->

---

## Getting Started

### Dependencies
- [Python 3.8+](https://www.python.org/downloads/)
- [VapourSynth](https://github.com/vapoursynth/vapoursynth/releases)
- [MKVToolNix](https://mkvtoolnix.download/downloads.html)

### Installing

#### Windows

1. Navigate to your Python installation folder (i.e. `C:\Python\`).
1. Download the `acsuite.py` file to the site-packages folder (`C:\Python\Lib\site-packages\`).

#### Arch Linux

Install the [AUR package](https://aur.archlinux.org/packages/vapoursynth-plugin-acsuite-git/) `vapoursynth-plugin-acsuite-git` with your favorite AUR helper:

```sh
yay -S vapoursynth-plugin-acsuite-git
```

#### Gentoo Linux

Install via the [VapourSynth portage tree](https://github.com/4re/vapoursynth-portage).

## Help!

Use python's builtin `help`: 

```py
help('acsuite')
```

