# acsuite

audiocutter(.py) replacement for VapourSynth.

Allows for easy frame-based cutting/trimming/splicing of audio files
from within a VapourSynth editor environment.

### eztrim(self, clip: vs.VideoNode, trims: Iterable, audio_file: str, outfile: str)
```py
import vapoursynth as vs
core = vs.core

import acsuite
ac = acsuite.AC()

file  = r'/BDMV/STREAM/00003.m2ts'
afile = r'/BDMV/STREAM/00003.wav' # pre-extracted with TSMuxer or similar

src = core.lsmas.LWLibavSource(file) # for the example, we will assume the src clip is 100 frames long (0-99)

clip = src[3:22]+src[23:40]+src[48]+src[50:-20]+src[-10:-5]+src[97:]

ac.eztrim(src, [(3,22),(23,40),(48,49),(50,-20),(-10,-5),(97,0)], afile, 'cut.wav')
# clip should be the uncut/untrimmed src that you are trimming from
 ```
