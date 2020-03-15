"""Frame-based cutting/trimming/splicing of audio with VapourSynth."""
__all__ = ['eztrim']
__author__ = 'Dave <orangechannel@pm.me>'
__date__ = '15 March 2020'
__credits__ = """AzraelNewtype, for the original audiocutter.py.
Ricardo Constantino (wiiaboo), for vfr.py from which this was inspired.
"""

from inspect import stack as n
from re import compile, IGNORECASE
from string import ascii_uppercase
from subprocess import PIPE, run
from typing import List, Tuple, Union
from warnings import simplefilter, warn

import vapoursynth as vs

simplefilter("always")  # display warnings


class AC:
    """Base class for trimming functions."""

    def __init__(self, clip=None, audio_file=None, outfile=None, chapter_file=None):
        """Add executable paths here if not already in PATH."""
        self.mkvmerge = r'mkvmerge'
        self.mkvtoolnixgui = r'mkvtoolnix-gui'
        self.s = []
        self.e = []
        self.cut_ts_s = []
        self.cut_ts_e = []
        self.chapter_names = []
        self.clip = clip
        self.audio_file = audio_file
        self.outfile = outfile
        self.chapter_file = chapter_file

    def eztrim(self, clip: vs.VideoNode,
               /,
               trims: Union[List[Tuple[int, int]],
                            Tuple[int, int]],
               audio_file: str,
               outfile: str,
               *,
               debug: bool = False):
        """
        Simpler trimming function that follows VS slicing syntax.

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

        :param outfile: either a filename `'out.wav'` or a full path `'/path/to/out.wav'`

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

    def octrim(self, clip: vs.VideoNode,
               /,
               trims: Union[List[Union[Tuple[int, int, str],
                                       Tuple[int, str]]],
                            List[Union[Tuple[int, int],
                                       Tuple[int]]]],
               audio_file: str,
               outfile: str,
               chapter_file: str = None,
               names: bool = True,
               gui: bool = False,
               *,
               debug: bool = False):
        """
        Trimming function designed for ordered-chapters creation.

        ALWAYS uses frame numbers from un-cut/un-trimmed src video.

        A VapourSynth clip with the following information:
        chapter 'A' is frame 1 through 2 inclusive
        chapter 'B':  4 -  7      chapter 'C':  8 -  9
        chapter 'D': 11 - 13      chapter 'E': 14 - 17
        chapter 'F': 18 - 20      chapter 'G': 24 - 30
        chapter 'H': 33 - 35      chapter 'J': 36 - 41

        Can be entered as
        > trims=[(1,2,'A'),(4,7,'B'),(8,9,'C'),(11,13,'D'),(14,17,'E'),
                 (18,20,'F'),(24,30,'G'),(33,35,'H'),(36,41,'J')]

        or can be simplified to:
        >> trims=[(1,2,'A'),(4,'B'),(8,9,'C'),(11,'D'),(14,'E'),(18,20,'F'),
                  (24,30,'G'),(33,'H'),(36,41,'J')]
        by leaving out the ending frame if chapters are continuous
        (only need the start frame of the next chapter).

        This will cut audio (inclusive) from frames:
        [1,2]+[4,9]+[11,20]+[24,30]+[33,41]
        or using timecodes of the following frames:
        [1,3],  [4,10],  [11,21],  [24,31],  [33,42]

        resulting in a (3-1)+(10-4)+(21-11)+(31-24)+(42-33) = 34
        frame long audio clip.

        This will leave us with chapters starting at (trimmed) frame:
        'A': 0,     'B': 2,     'C': 6
        'D': 8,     'E': 11,    'F': 15
        'G': 18     'H': 25     'J': 28
        'DELETE THIS': 34 (explained on the README)

        :param clip: needed to determine framerate for timecodes
            :bit depth: ANY
            :color family: ANY
            :float precision: ANY
            :sample type: ANY
            :subsampling: ANY

        :param trims: a list of 2 or 3-tuples:
            [(start,end,'name'),...]
            or
            [(start,'name'),...,(start,end,'name')]

            Only need to specify start frame if chapter is continuous.
            Last tuple MUST specify end frame.
            If specifying end frame, it is ALWAYS inclusive.
            Refer to `names`.

        :param audio_file: `'/path/to/audio_file.wav'`

        :param outfile: can be either a filename `'out.wav'` or a full path `'/path/to/out.wav'`

        :param chapter_file: can be either a filename 'chap.txt' or a full path `'/path/to/chap.txt'`

        :param gui: whether or not to auto-open MKVToolNix GUI with chapter_file (Default value = False)

        :param names: whether or not to use specified chapter names (Default value = True)
            if False, you do not need to specify chapter names:
                `trims` must be a list of 1 or 2-tuples in the format
                    [(start,end),...]
                    or
                    [(start,),...,(start,end)]

        OUTPUTS:
            * a cut/spliced audio file in either the script's directoy
              or the path specified with 'outfile'
            * a plaintext file with chapter timings
        """
        self.__init__(clip, audio_file, outfile, chapter_file)

        if not isinstance(trims, list):
            raise TypeError(f'{g(n())}: trims must be a list [] of tuples')

        # error checking
        if names:
            for trim in trims:
                if type(trim) != tuple:
                    raise TypeError(f'{g(n())}: trims must all be tuples (if only using start frame, enter as (int,)')
                if len(trim) > 3:
                    raise ValueError(f'{g(n())}: trim {trim} must have at most 2 ints and 1 string')
                elif len(trim) == 3:
                    for i in range(2):
                        if not isinstance(trim[i], int):
                            raise TypeError(f'{g(n())}: trim {trim} must have 2 ints')
                    if not isinstance(trim[2], str):
                        raise TypeError(f'{g(n())}: expected str in pos 2 in trim {trim}')
                elif len(trim) == 2:
                    if not isinstance(trim[0], int):
                        raise TypeError(f'{g(n())}: expected int in pos 0 in trim {trim}')
                    if not isinstance(trim[1], str):
                        raise TypeError(f'{g(n())}: expected str in pos 1 in trim {trim}')
                else:
                    raise ValueError(f'{g(n())}: trim {trim} must be at least 2 elements long')
            if len(trims[-1]) != 3:
                raise ValueError(f'{g(n())}: the last trim, {trims[-1]}, must have 3 elements')
        else:
            for trim in trims:
                if type(trim) != tuple:
                    raise TypeError(f'{g(n())}: trims must all be tuples (if only using start frame, enter as (int,))')
                if len(trim) > 2:
                    raise ValueError(f'{g(n())}: trim {trim} must have at most 2 ints')
                elif len(trim) == 2:
                    for i in range(2):
                        if not isinstance(trim[i], int):
                            raise TypeError(f'{g(n())}: trim {trim} must have 2 ints')
                elif len(trim) == 1:
                    if not isinstance(trim[0], int):
                        raise TypeError(f'{g(n())}: expected int in pos 0 in trim {trim}')
            if len(trims[-1]) != 2:
                raise ValueError(f'{g(n())}: the last trim, {trims[-1]}, must have 2 ints')

        for i in trims:
            self.s.append(i[0])

        if names:
            for k, v in enumerate(trims):
                if type(v[1]) == str:
                    self.e.append(self.s[k + 1] - 1)  # derive end time from next start
                else:
                    self.e.append(v[1])
            for trim in trims:
                if len(trim) == 2:
                    self.chapter_names.append(trim[1])  # 2nd value is chapter name
                else:
                    self.chapter_names.append(trim[2])
        else:
            for k, v in enumerate(trims):
                if len(v) == 1:
                    self.e.append(self.s[k + 1] - 1)  # derive end time from next start
                else:
                    self.e.append(v[1])

        cut_s, cut_e = _combine(self.s, self.e)
        cut_e = [i + 1 for i in cut_e]

        if _check_ordered(cut_s, cut_e):
            self.cut_ts_s = [self._f2ts(f) for f in cut_s]
            self.cut_ts_e = [self._f2ts(f) for f in cut_e]
        else:
            raise ValueError(f'{g(n())}: the trims are not logical')

        chap_s, chap_e = _compress(self.s, self.e)
        chap_e[-1] += 1  # needed to include last frame in virtual timeline

        chap_s_ts = [self._f2ts(i) for i in chap_s]
        chap_e_ts = [self._f2ts(i) for i in chap_e]

        if debug: return {'cut_s': cut_s, 'cut_e': cut_e, 'chap_s_ts': chap_s_ts, 'chap_e_ts': chap_e_ts}

        self.__cut_audio()
        if self.chapter_file:
            self.__write_chapters(chap_s_ts, chap_e_ts)
            if gui:
                run([self.mkvtoolnixgui, '--edit-chapters', self.chapter_file])

    def __cut_audio(self):
        """Uses mkvmerge to split and re-join the audio clips."""
        delay_statement = []

        split_parts = 'parts:'
        for s, e in zip(self.cut_ts_s, self.cut_ts_e):
            split_parts += f'{s}-{e},+'

        split_parts = split_parts[:-2]

        identify_proc = run([self.mkvmerge, '--identify', self.audio_file], text=True, check=True, stdout=PIPE)
        identify_pattern = compile(r'Track ID (\d+): audio')
        if re_return_proc := identify_pattern.search(identify_proc.stdout) if identify_proc.stdout else None:
            tid = re_return_proc.group(1) if re_return_proc else '0'

            filename_delay_pattern = compile(r'DELAY ([-]?\d+)', flags=IGNORECASE)
            re_return_filename = filename_delay_pattern.search(self.audio_file)

            delay_statement = ['--sync', f'{tid}:{re_return_filename.group(1)}'] if (tid and re_return_filename) else []

        cut_args = [self.mkvmerge, '-o', self.outfile] +  delay_statement + ['--split', split_parts, '-D', '-S', '-B', '-M', '-T', '--no-global-tags', '--no-chapters', self.audio_file]
        run(cut_args)

    def _f2ts(self, f: int) -> str:
        """Converts frame number to HH:mm:ss.nnnnnnnnn or HH:mm:ss.mmm timestamp based on clip's framerate."""
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

    def __write_chapters(self, a: List[str], b: List[str], debug: bool = False):
        """Writes chapters in basic OGM format to a plaintext file."""
        chapter_file = self.chapter_file

        if '.txt' not in chapter_file: chapter_file += '.txt'

        chapter_names = self.chapter_names if self.chapter_names else list(ascii_uppercase)

        if not self.chapter_names: chapter_names = ['Part ' + i for i in chapter_names]

        lines = []

        for i in range(len(a)):
            lines.append('CHAPTER{:02d}={}'.format(i, a[i]))
            lines.append('CHAPTER{:02d}NAME={}'.format(i, chapter_names[i]))

        lines.append('CHAPTER{:02d}={}'.format(len(a), b[-1]))
        lines.append('CHAPTER{:02d}NAME=DELETE ME'.format(len(a)))

        if debug: return lines

        text_file = open(chapter_file, 'w')
        for i in lines: text_file.write(i + '\n')
        text_file.close()

# Static helper functions
def _check_ordered(a: List[int], b: List[int]) -> bool:
    """Checks if lists follow logical python slicing."""

    if not all(a[i] < a[i + 1] for i in range(len(a) - 1)):
        return False  # checks if list a is ordered L to G
    if not all(b[i] < a[i + 1] for i in range(len(a) - 1)):
        return False  # checks if all ends are less than next start
    if not all(a[i] < b[i] for i in range(len(a))):
        return False  # makes sure pair is at least one frame long

    return True


def _combine(a: List[int], b: List[int]) -> Tuple[List[int], List[int]]:
    """Eliminates continuous pairs: (a1,b1)(a2,b2) -> (a1,b2) if b1 == a2"""
    if len(a) != len(b):
        raise ValueError(f'{g(n())}: lists must be same length')
    if len(a) == 1 and len(b) == 1:
        return a, b

    ca, cb = [], []
    for i in range(len(a)):
        if i == 0:
            ca.append(a[i])
            if b[i] + 1 != a[i + 1]:
                cb.append(b[i])
            continue
        elif i < len(a) - 1:
            if a[i] - 1 != b[i - 1]:  # should we skip the start?
                ca.append(a[i])
            if b[i] + 1 != a[i + 1]:  # should we skip the end?
                cb.append(b[i])
            continue
        elif i == len(a) - 1:
            if a[i] - 1 != b[i - 1]:
                ca.append(a[i])
            cb.append(b[i])

    return ca, cb


def _compress(a: List[int], b: List[int]) -> Tuple[List[int], List[int]]:
    """Compresses lists to become continuous. (5,9)(12,14) -> (0,4)(7,9) -> (0,4)(5,7)"""
    if len(a) != len(b):
        raise ValueError(f'{g(n())}: lists must be same length')

    if a[0] > 0:  # shift all values so that 'a' starts at 0
        init = a[0]
        a = [i - init for i in a]
        b = [i - init for i in b]

    if len(a) == 1 and len(b) == 1:  # (5,9) -> (0,4)
        return a, b

    index, diff = 1, 0  # initialize this loop

    while index < len(a):
        for i in range(index, len(a)):
            if a[i] != b[i - 1] + 1:
                diff = a[i] - b[i - 1] - 1
                index = i
                break

            diff = 0
            index += 1

        # we want to shift by one less than the difference so the pairs become continuous
        for i in range(index, len(a)):
            a[i] -= diff
            b[i] -= diff

    return a, b


# Decorator functions
g = lambda x: x[0][3]  # g(inspect.stack()) inside a function will print its name

# Wrapper functions
eztrim = AC().eztrim
