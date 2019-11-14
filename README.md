# acsuite

audiocutter(.py) replacement for VapourSynth.

Allows for easy frame-based cutting/trimming/splicing of audio files
from within a VapourSynth environment.

### eztrim(self, clip, trims, audio_file, outfile, debug=False)
```py
import vapoursynth as vs
core = vs.core

import acsuite
ac = acsuite.AC()

file  = r'/BDMV/STREAM/00003.m2ts'
afile = r'/BDMV/STREAM/00003.wav'  # pre-extracted with TSMuxer or similar

src = core.lsmas.LWLibavSource(file)  # for the example, we will assume the src clip is 100 frames long (0-99)

clip = src[3:22]+src[23:40]+src[48]+src[50:-20]+src[-10:-5]+src[97:]

ac.eztrim(src, [(3,22),(23,40),(48,49),(50,-20),(-10,-5),(97,0)], afile, 'cut.wav')
# clip should be the uncut/untrimmed src that you are trimming from
 ```

### octrim(self, clip, trims, audio_file, outfile, chapter_file, gui=True, names=True, debug=False)

```py
import vapoursynth as vs
core = vs.core

import acsuite
ac = acsuite.AC()

file  = r'/BDMV/STREAM/00003.m2ts'
afile = r'/BDMV/STREAM/00003.wav'  # pre-extracted with TSMuxer or similar

src = core.lsmas.LWLibavSource(file)

clip = src[1:3]+src[4:10]+src[11:21]+src[24:31]+src[33:42]

ac.octrim(src, [(1, 2, 'A'), (4, 'B'), (8, 9, 'C'), (11, 'D'), (14, 'E'), (18, 20, 'F'), (24, 30, 'G'), (33, 'H'), (36, 41, 'J')], afile, 'cut.wav', 'chapters.txt')
# clip should be the uncut/untrimmed src that you are trimming from
 ```

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
