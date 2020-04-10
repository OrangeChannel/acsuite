"""Frame-based cutting/trimming/splicing of audio with VapourSynth."""
__all__ = ['eztrim']
__author__ = 'Dave <orangechannel@pm.me>'
__date__ = '9 April 2020'
__credits__ = """AzraelNewtype, for the original audiocutter.py.
Ricardo Constantino (wiiaboo), for vfr.py from which this was inspired.
"""

from inspect import stack as n
from re import compile, IGNORECASE
from subprocess import PIPE, run
from typing import List, Tuple, Union
from warnings import simplefilter, warn

import vapoursynth as vs

simplefilter("always")  # display warnings


class AC:
    """Base class for trimming functions."""

    def __init__(self, clip=None, audio_file=None, outfile=None):
        """Add executable paths here if not already in PATH."""
        self.mkvmerge = r'mkvmerge'
        self.s = []
        self.e = []
        self.cut_ts_s = []
        self.cut_ts_e = []
        self.chapter_names = []
        self.clip = clip
        self.audio_file = audio_file
        self.outfile = outfile

    def eztrim(self, clip: vs.VideoNode,
               /,
               trims: Union[List[Tuple[int, int]],
                            Tuple[int, int]],
               audio_file: str,
               outfile: str,
               *,
               debug: bool = False):
        """
        Simple trimming function that follows VS slicing syntax.

        End frame is NOT inclusive.

        For a 100 frame long VapourSynth clip (src[:100]):

        > src[3:22]+src[23:40]+src[48]+src[50:-20]+src[-10:-5]+src[97:]
        can be (almost) directly entered as
        > trims=[(3,22),(23,40),(48,49),(50,-20),(-10,-5),(97,0)]

        >> src[3:-13]
        can be directly entered as
        >> trims=(3,-13)

        :param clip: needed to determine framerate for audio timecodes and `num_frames` for negative indexing
            :bit depth: ANY
            :color family: ANY
            :float precision: ANY
            :sample type: ANY
            :subsampling: ANY

        :param trims: either a list of 2-tuples, or one tuple of 2 ints
            empty slicing must represented with a `0`
                > src[:10]+src[-5:]
                > trims=[(0,10), (-5,0)]
            single frame slices must be represented as a normal slice
                >> src[15]
                >> trims=(15,16)

        :param audio_file: `'/path/to/audio_file.wav'`
            can also be a container file that uses a slice-able audio codec
            i.e. a remuxed BDMV source into a .mkv file with FLAC / PCM audio: `'/path/to/remuxed_bdmv.mkv'`

        :param outfile: either a filename `'out.mka'` or a full path `'/path/to/out.mka'`

        OUTPUTS: a cut/spliced audio file in either the script's directoy or the path specified with `outfile`
        """
        self.__init__(clip, audio_file, outfile)
        single = False

        # error checking
        if not isinstance(trims, (list, tuple)):
            raise TypeError(f'{g(n())}: trims must be a list of 2-tuples (or just one 2-tuple)')
        if len(trims) == 1 and type(trims) == list:
            warn(f'{g(n())}: using a list of one 2-tuple is not recommended; for a single trim, directly use a tuple: `trims=(5,-2)` instead of `trims=[(5,-2)]`', SyntaxWarning)
        for trim in trims:
            if type(trim) == int:  # if first element is an int, assume it's a single tuple
                single = True
                if len(trims) != 2:
                    raise ValueError(f'{g(n())}: the trim must have 2 elements')
                break
            else:  # makes sure to error check only for multiple tuples
                if not isinstance(trim, tuple):
                    raise TypeError(f'{g(n())}: the trim {trim} is not a tuple')
                if len(trim) != 2:
                    raise ValueError(f'{g(n())}: the trim {trim} needs 2 elements')
                for i in trim:
                    if type(i) != int:
                        raise ValueError(f'{g(n())}: the trim {trim} must have 2 ints')

        if single:
            self.s, self.e = trims  # directly un-pack values from the single trim
        else:
            for s, e in trims:
                self.s.append(s)
                self.e.append(e)

        self.s, self.e = self._negative_to_positive(self.s, self.e)

        if single:
            if self.e <= self.s:
                raise ValueError(f'{g(n())}: the trim {trims} is not logical')
            self.cut_ts_s.append(self._f2ts(self.s))
            self.cut_ts_e.append(self._f2ts(self.e))
        else:
            if _check_ordered(self.s, self.e):
                self.cut_ts_s = [self._f2ts(f) for f in self.s]
                self.cut_ts_e = [self._f2ts(f) for f in self.e]
            else:
                raise ValueError(f'{g(n())}: the trims are not logical')

        if debug: return {'s': self.s, 'e': self.e, 'cut_ts_s': self.cut_ts_s, 'cut_ts_e': self.cut_ts_e}

        self.__cut_audio()

    def __cut_audio(self):
        """Uses mkvmerge to split and re-join the audio clips."""
        delay_statement = []

        split_parts = 'parts:'
        for s, e in zip(self.cut_ts_s, self.cut_ts_e):
            split_parts += f'{s}-{e},+'

        split_parts = split_parts[:-2]

        identify_proc = run([self.mkvmerge, '--output-charset', 'utf-8', '--identify', self.audio_file], text=True, check=True, stdout=PIPE, encoding='utf-8')
        identify_pattern = compile(r'Track ID (\d+): audio')
        if re_return_proc := identify_pattern.search(identify_proc.stdout) if identify_proc.stdout else None:
            tid = re_return_proc.group(1) if re_return_proc else '0'

            filename_delay_pattern = compile(r'DELAY ([-]?\d+)', flags=IGNORECASE)
            re_return_filename = filename_delay_pattern.search(self.audio_file)

            delay_statement = ['--sync', f'{tid}:{re_return_filename.group(1)}'] if (tid and re_return_filename) else []

        cut_args = [self.mkvmerge, '-o', self.outfile] +  delay_statement + ['--split', split_parts, '-D', '-S', '-B', '-M', '-T', '--no-global-tags', '--no-chapters', self.audio_file]
        run(cut_args)

    def _f2ts(self, f: int) -> str:
        """Converts frame number to HH:mm:ss.nnnnnnnnn timestamp based on clip's framerate."""
        if self.clip is None:
            raise ValueError(f'{g(n())}: clip needs to be specified')

        t = round(10 ** 9 * f * self.clip.fps ** -1)

        s = t / 10 ** 9
        m = s // 60
        s %= 60
        h = m // 60
        m %= 60

        return f'{h:02.0f}:{m:02.0f}:{s:012.9f}'

    def _negative_to_positive(self, a: Union[List[int], int], b: Union[List[int], int]) \
            -> Union[Tuple[List[int], List[int]], Tuple[int, int]]:
        """Changes negative/zero index to positive based on clip.num_frames."""
        if self.clip is None:
            raise ValueError(f'{g(n())}: clip needs to be specified')
        num_frames = self.clip.num_frames

        # speed-up analysis of a single trim
        if type(a) == int and type(b) == int:
            if abs(a) > num_frames or abs(b) > num_frames:
                raise ValueError(f'{g(n())}: {max(abs(a), abs(b))} is out of bounds')
            return a if a >= 0 else num_frames + a, b if b > 0 else num_frames + b

        positive_a, positive_b = [], []

        if len(a) != len(b):
            raise ValueError(f'{g(n())}: lists must be same length')

        for x, y in zip(a, b):
            if abs(x) > num_frames or abs(y) > num_frames:
                raise ValueError(f'{g(n())}: {max(abs(x), abs(y))} is out of bounds')

        if all(i >= 0 for i in a) and all(i > 0 for i in b): return a, b

        for x, y in zip(a, b):
            positive_a.append(x if x >= 0 else num_frames + x)
            positive_b.append(y if y > 0 else num_frames + y)

        return positive_a, positive_b


# Static helper functions
def _check_ordered(a: List[int], b: List[int]) -> bool:
    """Checks if lists follow logical python slicing."""
    if len(a) != len(b):
        raise ValueError(f'{g(n())}: lists must be same length')
    if len(a) == 1 and len(b) == 1:
        if a[0] >= b[0]:
            return False

    if not all(a[i] < a[i + 1] for i in range(len(a) - 1)):
        return False  # checks if list a is ordered L to G
    if not all(b[i] < a[i + 1] for i in range(len(a) - 1)):
        return False  # checks if all ends are less than next start
    if not all(a[i] < b[i] for i in range(len(a))):
        return False  # makes sure pair is at least one frame long

    return True


# Decorator functions
g = lambda x: x[0][3]  # g(inspect.stack()) inside a function will print its name

# Wrapper functions
eztrim = AC().eztrim
