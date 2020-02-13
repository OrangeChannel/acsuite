"""Frame-based cutting/trimming/splicing of audio with VapourSynth."""
__all__ = ['AC']
__author__ = 'Dave <orangechannel@pm.me>'
__date__ = '3 February 2020'
__credits__ = """AzraelNewtype, for the original audiocutter.py.
Ricardo Constantino (wiiaboo), for vfr.py from which this was inspired.
"""

from fractions import Fraction
from re import compile, IGNORECASE
from shlex import split
from shutil import which
from string import ascii_uppercase
from subprocess import PIPE, Popen, run
from sys import getfilesystemencoding
from typing import List, Tuple, Union

import vapoursynth as vs

import_as = 'acs'


class AC:
    """Base class for trimming functions."""

    def __init__(self, clip=None, /, audio_file=None, outfile=None, chapter_file=None):
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

    def eztrim(self, clip: vs.VideoNode, /, trims: Union[List[Tuple[int, int]],
                                                         Tuple[int, int]],
               audio_file: str, outfile: str, *, debug: bool = False):
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

        :param outfile: either a filename `'out.wav'` or a full path `'/path/to/out.wav'`

        OUTPUTS: a cut/spliced audio file in either the script's directoy or the path specified with 'outfile'
        """
        self.__init__(clip, audio_file, outfile)
        single = False

        if not isinstance(trims, (list, tuple)): raise TypeError('eztrim: trims must be a list of 2-tuples (or just one 2-tuple)')

        for trim in trims:
            if type(trim) == int:  # if first element is an int, assume it's a single tuple
                single = True
                if len(trims) != 2: raise ValueError('eztrim: the trim must have 2 elements')
                break

            else:  # makes sure to error check only for multiple tuples
                if not isinstance(trim, tuple): raise TypeError('eztrim: the trim {} is not a tuple'.format(trim))
                if len(trim) != 2: raise ValueError('eztrim: the trim {} needs 2 elements'.format(trim))
                for i in trim:
                    if type(i) != int: raise ValueError('eztrim: the trim {} must have 2 ints'.format(trim))

        if single: self.s, self.e = trims

        else:
            for s, e in trims:
                self.s.append(s)
                self.e.append(e)

        self.s, self.e = self._negative_to_positive(self.s, self.e)

        if single:
            if self.e <= self.s: raise ValueError('the trim {} is not logical'.format(trims))
            self.cut_ts_s.append(self._f2ts(self.s))
            self.cut_ts_e.append(self._f2ts(self.e))

        else:
            if self._check_ordered():
                for i in self.s: self.cut_ts_s.append(self._f2ts(i))
                for i in self.e: self.cut_ts_e.append(self._f2ts(i))

            else: raise ValueError('the trims are not logical')

        if debug: return {'s': self.s, 'e': self.e, 'cut_ts_s': self.cut_ts_s, 'cut_ts_e': self.cut_ts_e}

        self._cut_audio()

    def octrim(self, clip: vs.VideoNode, /, trims: Union[List[Union[Tuple[int, int, str],
                                                                    Tuple[int, str]]],
                                                         List[Union[Tuple[int, int],
                                                                    Tuple[int]]]],
               audio_file: str, outfile: str, chapter_file: str, gui: bool = True, names: bool = True,
               *, debug: bool = False):
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

        :param gui: whether or not to auto-open MKVToolNix GUI with chapter_file (Default value = True)

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
            raise TypeError('octrim: trims must be a list [] of tuples')

        if names:
            for trim in trims:
                if type(trim) != tuple: raise TypeError('octrim: trims must all be tuples (if only using start frame, enter as (int,)')
                if len(trim) > 3: raise ValueError('octrim: trim {} must have at most 2 ints and 1 string'.format(trim))

                elif len(trim) == 3:
                    for i in range(2):
                        if not isinstance(trim[i], int): raise TypeError('octrim: trim {} must have 2 ints'.format(trim))
                    if not isinstance(trim[2], str): raise TypeError('octrim: expected str in pos 2 in trim {}'.format(trim))

                elif len(trim) == 2:
                    if not isinstance(trim[0], int): raise TypeError('octrim: expected int in pos 0 in trim {}'.format(trim))
                    if not isinstance(trim[1], str): raise TypeError('octrim: expected str in pos 1 in trim {}'.format(trim))

                else: raise ValueError('octrim: trim {} must be at least 2 elements long'.format(trim))

            if len(trims[-1]) != 3: raise ValueError('octrim: the last trim, {}, must have 3 elements'.format(trims[-1]))

        else:
            for trim in trims:
                if type(trim) != tuple: raise TypeError('octrim: trims must all be tuples (if only using start frame, enter as (int,))')
                if len(trim) > 2: raise ValueError('octrim: trim {} must have at most 2 ints'.format(trim))

                elif len(trim) == 2:
                    for i in range(2):
                        if not isinstance(trim[i], int): raise TypeError('octrim: trim {} must have 2 ints'.format(trim))

                elif len(trim) == 1:
                    if not isinstance(trim[0], int): raise TypeError('octrim: expected int in pos 0 in trim {}'.format(trim))

            if len(trims[-1]) != 2: raise ValueError('octrim: the last trim, {}, must have 2 ints'.format(trims[-1]))

        for i in trims: self.s.append(i[0])

        if names:
            for k, v in enumerate(trims):
                if type(v[1]) == str: self.e.append(self.s[k + 1] - 1)  # derive end time from next start
                else: self.e.append(v[1])

            for trim in trims:
                if len(trim) == 2: self.chapter_names.append(trim[1])  # 2nd value is chapter name
                else: self.chapter_names.append(trim[2])

        else:
            for k, v in enumerate(trims):
                if len(v) == 1: self.e.append(self.s[k + 1] - 1)  # derive end time from next start
                else: self.e.append(v[1])

        cut_s, cut_e = self._combine()

        if self._check_ordered():
            for i in cut_s: self.cut_ts_s.append(self._f2ts(i))
            for i in cut_e: self.cut_ts_e.append(self._f2ts(i))

        else: raise ValueError('the trims are not logical')

        chap_s, chap_e = self._chapter_timings()

        chap_s_ts = [self._f2ts(i, precision=3) for i in chap_s]
        chap_e_ts = [self._f2ts(i, precision=3) for i in chap_e]

        if debug: return {'cut_s': cut_s, 'cut_e': cut_e, 'chap_s_ts': chap_s_ts, 'chap_e_ts': chap_e_ts}

        self._cut_audio()
        self._write_chapters(chap_s_ts, chap_e_ts)

        if gui:
            cmd = '{} --edit-chapters "{}"'
            args = split(cmd.format(self.mkvtoolnixgui, self.chapter_file))
            Popen(args)

    def _chapter_timings(self, a: List[int] = None, b: List[int] = None) -> Tuple[List[int], List[int]]:
        """Shifts lists to remove space between consecutive pairs."""
        a, b = a if a else self.s, b if b else self.e
        index, diff = 1, 0

        if a[0] > 0:
            idiff = a[0]  # shift all values so that 'a' starts at 0
            a = [i - idiff for i in a]
            b = [i - idiff for i in b]

        while index < len(a):
            for i in range(index, len(a)):
                if a[i] != b[i - 1] + 1:  # shift all values starting at 'index' to remove space between a and previous b
                    diff = a[i] - b[i - 1] - 1
                    index = i
                    break

                diff = 0
                index += 1

            for i in range(index, len(a)):
                a[i] -= diff
                b[i] -= diff

        b[-1] += 1  # last b value incremented by 1 to include the last frame in the virtual ordered-chapters timeline

        return a, b

    def _check_ordered(self, a: List[int] = None, b: List[int] = None) -> bool:
        """Checks if lists follow logical python slicing."""
        a, b = a if a else self.s, b if b else self.e

        if not all(a[i] < a[i + 1] for i in range(len(a) - 1)):
            return False  # checks if list a is ordered L to G
        if not all(b[i] < a[i + 1] for i in range(len(a) - 1)):
            return False  # checks if all ends are less than next start
        if not all(a[i] < b[i] for i in range(len(a))):
            return False  # makes sure pair is at least one frame long

        return True

    def _combine(self, a: List[int] = None, b: List[int] = None, tclip: vs.VideoNode = None) -> Tuple[List[int], List[int]]:
        """If b is consecutive with next a, remove both."""
        a, b = a if a else self.s, b if b else self.e
        b = [i + 1 for i in b]  # because b is inclusive, we need next frame for the timestamp

        a, b = self._negative_to_positive(a, b, tclip)

        a_combined, b_combined = [], []

        for i in range(len(a)):
            if i == 0:
                a_combined.append(a[i])
                if b[i] != a[i + 1]: b_combined.append(b[i])
                continue
            elif i < len(a) - 1:
                if a[i] != b[i - 1]: a_combined.append(a[i])
                if b[i] != a[i + 1]: b_combined.append(b[i])
                continue
            elif i == len(a) - 1:
                if a[i] != b[i - 1]: a_combined.append(a[i])
                b_combined.append(b[i])

        return a_combined, b_combined

    def _cut_audio(self):
        """Uses mkvmerge to split and re-join the audio clips."""
        ts_cmd = self.mkvmerge + '{delay} --split parts:'

        for s, e in zip(self.cut_ts_s, self.cut_ts_e): ts_cmd += '{}-{},+'.format(s, e)

        cut_cmd = ts_cmd[:-2]

        ident = run([self.mkvmerge, '--identify', self.audio_file], check=True, stdout=PIPE).stdout
        identre = compile(r'Track ID (\d+): audio')
        ret = (identre.search(ident.decode(getfilesystemencoding())) if ident else None)
        tid = ret.group(1) if ret else '0'
        delre = compile(r'DELAY ([-]?\d+)', flags=IGNORECASE)
        ret = delre.search(self.audio_file)

        delay = '{0}:{1}'.format(tid, ret.group(1)) if ret else None
        delay_statement = ' --sync {}'.format(delay) if delay else ''

        cut_cmd += ' -o "{}" "{}"'.format(self.outfile, self.audio_file)
        args = split(cut_cmd.format(delay=delay_statement))
        cut_exec = Popen(args).returncode

        if cut_exec == 1:
            print('Mkvmerge exited with warnings: 1')
        elif cut_exec == 2:
            print(args)
            exit('Failed to execute mkvmerge: 2')

    def _f2ts(self, f: int, /, tclip: vs.VideoNode = None, *, precision: int = 9) -> str:
        """Converts frame number to HH:mm:ss.nnnnnnnnn or HH:mm:ss.mmm timestamp based on clip's framerate."""
        if not tclip and not self.clip: raise ValueError('_f2ts: clip needs to be specified')
        n, d = [tclip.fps_num, tclip.fps_den] if tclip else [self.clip.fps_num, self.clip.fps_den]

        t = round(10 ** precision * f * Fraction(d, n) + .5) if precision == 3 else round(10 ** precision * f * Fraction(d, n))

        s = t / 10 ** precision
        m = s // 60
        s %= 60
        h = m // 60
        m %= 60

        # OGM chapter files only support millisecond accuracy
        if precision == 3:
            return '{:02.0f}:{:02.0f}:{:06.3f}'.format(h, m, s)
        else:
            return '{:02.0f}:{:02.0f}:{:012.9f}'.format(h, m, s)

    def _negative_to_positive(self, a: Union[List[int], int], b: Union[List[int], int], tclip: vs.VideoNode = None) \
            -> Union[Tuple[List[int],
                           List[int]],
                     Tuple[int, int]]:
        """Changes neg index to pos based on clip.num_frames."""
        num_frames = tclip.num_frames if tclip else self.clip.num_frames

        if type(a) == int and type(b) == int:  # speed-up analysis of a single trim
            if abs(a) > num_frames or abs(b) > num_frames: raise ValueError('{} is out of bounds'.format(max(abs(a), abs(b))))

            return a if a >= 0 else num_frames + a, b if b > 0 else num_frames + b

        positive_a, positive_b = [], []

        if len(a) != len(b): raise ValueError('lists must be same length')

        for x, y in zip(a, b):
            if abs(x) > num_frames or abs(y) > num_frames: raise ValueError('{} is out of bounds'.format(max(abs(x), abs(y))))

        if all(i >= 0 for i in a) and all(i > 0 for i in b): return a, b

        for x, y in zip(a, b):
            positive_a.append(x if x >= 0 else num_frames + x)
            positive_b.append(y if y > 0 else num_frames + y)

        return positive_a, positive_b

    def _write_chapters(self, a: List[str], b: List[str], chapter_file: str = None):
        """Writes chapters in basic OGM format to a plaintext file."""
        chapter_file = chapter_file if chapter_file else self.chapter_file

        if '.txt' not in chapter_file: chapter_file += '.txt'

        chapter_names = self.chapter_names if self.chapter_names else list(ascii_uppercase)

        if not self.chapter_names: chapter_names = ['Part ' + i for i in chapter_names]

        lines = []

        for i in range(len(a)):
            lines.append('CHAPTER{:02d}={}'.format(i, a[i]))
            lines.append('CHAPTER{:02d}NAME={}'.format(i, chapter_names[i]))

        lines.append('CHAPTER{:02d}={}'.format(len(a), b[-1]))
        lines.append('CHAPTER{:02d}NAME=DELETE ME'.format(len(a)))

        text_file = open(chapter_file, 'w')
        for i in lines: text_file.write(i + '\n')
        text_file.close()


def audio_trim(path: str, trims: list, ez: bool = False, name: str = None):
    """Wrapper for audio extraction for ordered-chapters creation."""
    ffmpeg = which('ffmpeg')

    file, ext = path.split('.')

    clip = vs.core.lsmas.LWLibavSource(path)

    cmd = '{} -i "{}" -vn "{}.wav"'.format(ffmpeg, path, file)
    run(split(cmd))

    if ez:
        if name:
            AC().eztrim(clip, trims, audio_file='{}.wav'.format(file), outfile='{}_cut.wav'.format(name))
        else:
            AC().eztrim(clip, trims, audio_file='{}.wav'.format(file), outfile='{}_cut.wav'.format(file))
    else:
        if name:
            AC().octrim(clip, trims, audio_file='{}.wav'.format(file), outfile='{}_cut.wav'.format(name), chapter_file='{}_chapters.txt'.format(file), gui=False)
        else:
            AC().octrim(clip, trims, audio_file='{}.wav'.format(file), outfile='{}_cut.wav'.format(file), chapter_file='{}_chapters.txt'.format(file), gui=False)
