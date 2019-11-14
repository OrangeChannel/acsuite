"""Frame-based cutting/trimming/splicing of audio files with VapourSynth.

VapourSynth-based replacement for @AzraelNewtype's audiocutter.py:

    https://github.com/AzraelNewtype/audiocutter

Run "acsuite.AC().eztrim(clip, <trims>, <audio_file>, <outfile>)" with trims that follow VS/python slicing syntax.

Run "acsuite.AC().octrim(clip, <trims>, <audio_file>, <outfile>, <chapter_file>)" for ordered-chapters creation.
"""
__author__ = 'Dave <orangechannel@pm.me>'
__date__ = '14 November 2019'

__credits__ = """AzraelNewtype, for the original audiocutter.py.
Ricardo Constantino (wiiaboo), for vfr.py from which this was inspired.
"""

from fractions import Fraction
from re import compile, IGNORECASE
from shlex import split
from string import ascii_uppercase
from subprocess import PIPE, Popen, run
from sys import getfilesystemencoding
from typing import List, Tuple, Union

import vapoursynth as vs


# noinspection PyMissingOrEmptyDocstring
class AC(object):

    def __init__(self):
        """if mkvmerge is not in your PATH, add an absolute path to the executable here"""
        self.mkvmerge = r'mkvmerge'
        self.mkvtoolnixgui = r'mkvtoolnix-gui'
        self.s = []
        self.e = []
        self.cut_ts_s = []
        self.cut_ts_e = []
        self.chapter_names = []
        self.clip = None
        self.audio_file = None
        self.outfile = None
        self.chapter_file = None

    def eztrim(self, clip: vs.VideoNode, trims: Iterable, audio_file: str, outfile: str, debug: bool = False):
        """
        Simpler trimming function that follows VS/python slicing syntax (end frame is NOT inclusive video-wise)

        A VapourSynth slice of a 100 frame clip ( clip[:100] ):

        * clip[3:22]+clip[23:40]+clip[48]+clip[50:-20]+clip[-10:-5]+clip[97:]

        can be (almost) directly entered as

        * trims=[(3,22),(23,40),(48,49),(50,-20),(-10,-5),(97,0)]

        *** clip[3:-13]

        can be directly entered as

        *** trims=(3,-13)

        :param clip: vs.VideoNode:  needed to determine framerate for audio timecodes, num_frames for negative indexing
        :param trims: Iterable: either a list of 2-tuples, or a single tuple of 2 ints
                empty slicing must represented with a '0'
                    * clip[:10]+clip[-5:]
                    * trims=[(0,10), (-5,0)]
                single frame slices must be represented as a normal slice
                    * clip[15]
                    * trims=(15,16)

        :param audio_file: str:  '/path/to/audio_file.wav'
        :param outfile: str:  can be either a filename 'out.wav' or a full path '/path/to/out.wav'
        :param debug: bool:  used for testing, leave blank

        OUTPUTS: a cut/spliced audio file in either the script's directoy or the path specified with 'outfile'
        """
        self.__init__()

        single = False

        if not isinstance(trims, (list, tuple)):
            raise TypeError('eztrim: trims must be a list of 2-tuples (or just one 2-tuple)')

        for trim in trims:
            if type(trim) == int:
                """if the first element in trims is an int, we will assume it's a single tuple"""
                single = True
                if len(trims) != 2:
                    raise ValueError('eztrim: the trim must have 2 elements')
                break

            else:
                """makes sure to error check only for multiple tuples"""
                if not isinstance(trim, (list, tuple)):
                    raise TypeError('eztrim: the trim {} is not a tuple'.format(trim))
                if len(trim) != 2:
                    raise ValueError('eztrim: the trim {} needs 2 elements'.format(trim))
                for i in trim:
                    if type(i) != int:
                        raise ValueError('eztrim: the trim {} must have 2 ints'.format(trim))

        self.clip = clip
        self.audio_file = audio_file
        self.outfile = outfile

        if single:
            self.s.append(trims[0])
            self.e.append(trims[1])

        else:
            for s, e in trims:
                self.s.append(s)
                self.e.append(e)

        self.s, self.e = self._negative_to_positive(self.s, self.e)

        if single:
            if self.e[0] <= self.s[0]:
                raise ValueError('the trim {} is not logical'.format(trims))
            self.cut_ts_s.append(self._f2ts(self.s[0]))
            self.cut_ts_e.append(self._f2ts(self.e[0]))

        else:
            if self._check_ordered():
                for i in self.s:
                    self.cut_ts_s.append(self._f2ts(i))
                for i in self.e:
                    self.cut_ts_e.append(self._f2ts(i))
            else:
                raise ValueError('the trims are not logical')

        if debug:
            return {'s': self.s, 'e': self.e, 'cut_ts_s': self.cut_ts_s, 'cut_ts_e': self.cut_ts_e}

        self._cut_audio()

    def octrim(self, clip: vs.VideoNode, trims: list, audio_file: str, outfile: str, chapter_file: str,
               gui: bool = True, names: bool = True, debug: bool = False):
        """
        Trimming function designed for ordered-chapters creation.
        ALWAYS uses frame numbers from un-cut/un-trimmed src video.

        A VapourSynth clip with the following information:
        chapter 'A' is frame 1 through 2 inclusive
        chapter 'B' is frame 4 through 7 inclusive
        chapter 'C': 8 - 9        chapter 'D': 11 - 13      chapter 'E': 14 - 17
        chapter 'F': 18 - 20      chapter 'G': 24 - 30      chapter 'H': 33 - 35
        chapter 'J': 36 - 41

        Can be entered as

        * trims=[(1,2,'A'),(4,7,'B'),(8,9,'C'),(11,13,'D'),(14,17,'E'),(18,20,'F'),(24,30,'G'),(33,35,'H'),(36,41,'J')]

        or can be simplified to:

        ** trims=[(1,2,'A'),(4,'B'),(8,9,'C'),(11,'D'),(14,'E'),(18,20,'F'),(24,30,'G'),(33,'H'),(36,41,'J')]

        by leaving out the ending frame if chapters are continuous (only need the start frame of the next chapter)

        This will cut audio (inclusive) from frames:

        [1,2]+[4,9]+[11,20]+[24,30]+[33,41]

        or using timecodes of the following frames:
        [1,3],  [4,10],  [11,21],  [24,31],  [33,42]

        resulting in a (2-1+1)+(9-4+1)+(20-11+1)+(30-24+1)+(41-33+1) = 34 frame long clip

        This will leave us with chapters starting at (trimmed) frame:
        'A': 0,     'B': 2,     'C': 6
        'D': 8,     'E': 11,    'F': 15
        'G': 18     'H': 25     'J': 28
        'DELETE THIS': 34 (explained on the README)

        :param clip: vs.VideoNode:  needed for framerate for audio/chapter timecodes
        :param trims: list:  must be a list of 2 or 3-tuples in the format
            [(start,end,'name'),...]
            or
            [(start,'name'),...,(start,end,'name')]

            Only need to specify start frame if chapter is continuous (see example above).
                Last tuple must specify end frame.
            If specifying end frame, it is ALWAYS inclusive.

        :param audio_file: str:  '/path/to/audio_file.wav'
        :param outfile: str:  can be either a filename 'out.wav' or a full path '/path/to/out.wav'
        :param chapter_file: str:  can be either a filename 'chap.txt' or a full path '/path/to/chap.txt'
        :param gui: bool:  whether or not to auto-open MKVToolNix GUI with chapter timings
        :param names: bool:  whether or not to use specified names or auto-generated
            if False, you do not need to specify chapter names:

            ? param trims:
                if False, must be a list of either 1 or 2-tuples in the format
                [(start,end),...]
                or
                [(start,),...,(start,end)]

                Only need to specify start frame if chapter is continuous (see example above).
                    Last tuple must specify end frame.
                If specifying end frame, it is ALWAYS inclusive.

        :param debug: bool:  used for testing, leave blank

        OUTPUTS: * a cut/spliced audio file in either the script's directoy or the path specified with 'outfile'
                 * a plaintext file with chapter timings
                 ? can open MKVToolNix GUI automatically if 'gui' is True
        """
        self.__init__()

        if not isinstance(trims, list):
            raise TypeError('octrim: trims must be a list [] of tuples')

        if names:
            for trim in trims:
                if type(trim) != tuple:
                    raise TypeError('octrim: trims must all be tuples (if only using start frame, enter as (int,)')
                if len(trim) > 3:
                    raise ValueError('octrim: trim {} must have at most 2 ints and 1 string'.format(trim))
                elif len(trim) == 3:
                    check_int = lambda a: isinstance(a, int)
                    for i in range(2):
                        if not check_int(trim[i]):
                            raise TypeError('octrim: trim {} must have 2 ints'.format(trim))
                    if not isinstance(trim[2], str):
                        raise TypeError('octrim: expected str in pos 2 in trim {}'.format(trim))
                elif len(trim) == 2:
                    if not isinstance(trim[0], int):
                        raise TypeError('octrim: expected int in pos 0 in trim {}'.format(trim))
                    if not isinstance(trim[1], str):
                        raise TypeError('octrim: expected str in pos 1 in trim {}'.format(trim))
                else:
                    raise ValueError('octrim: trim {} must be at least 2 elements long'.format(trim))

            if len(trims[-1]) != 3:
                raise ValueError('octrim: the last trim, {}, must have 3 elements'.format(trims[-1]))

        else:
            for trim in trims:
                if type(trim) != tuple:
                    raise TypeError('octrim: trims must all be tuples (if only using start frame, enter as (int,))')
                if len(trim) > 2:
                    raise ValueError('octrim: trim {} must have at most 2 ints'.format(trim))
                elif len(trim) == 2:
                    check_int = lambda a: isinstance(a, int)
                    for i in range(2):
                        if not check_int(trim[i]):
                            raise TypeError('octrim: trim {} must have 2 ints'.format(trim))
                elif len(trim) == 1:
                    if not isinstance(trim[0], int):
                        raise TypeError('octrim: expected int in pos 0 in trim {}')
            if len(trims[-1]) != 2:
                raise ValueError('octrim: the last trim, {}, must have 2 ints'.format(trims[-1]))

        self.clip = clip
        self.audio_file = audio_file
        self.outfile = outfile
        self.chapter_file = chapter_file

        [self.s.append(i[0]) for i in trims]

        if names:
            for k, v in enumerate(trims):
                if type(v[1]) == str:
                    self.e.append(self.s[k + 1] - 1)
                else:
                    self.e.append(v[1])
        else:
            for k, v in enumerate(trims):
                if len(v) == 1:
                    self.e.append(self.s[k + 1] - 1)
                else:
                    self.e.append(v[1])
        if names:
            for trim in trims:
                if len(trim) == 2:
                    self.chapter_names.append(trim[1])
                else:
                    self.chapter_names.append(trim[2])

        cut_s, cut_e = self._combine()

        if self._check_ordered():
            for i in cut_s:
                self.cut_ts_s.append(self._f2ts(i))
            for i in cut_e:
                self.cut_ts_e.append(self._f2ts(i))
        else:
            raise ValueError('the trims are not logical')

        chap_s, chap_e = self._chapter_timings()

        chap_s_ts = [self._f2ts(i, precision=3) for i in chap_s]
        chap_e_ts = [self._f2ts(i, precision=3) for i in chap_e]

        if debug:
            return {'cut_s': cut_s, 'cut_e': cut_e, 'chap_s_ts': chap_s_ts, 'chap_e_ts': chap_e_ts}

        self._cut_audio()
        self._write_chapters(chap_s_ts, chap_e_ts)

        if gui:
            cmd = '{} --edit-chapters "{}"'
            args = split(cmd.format(self.mkvtoolnixgui, self.chapter_file))
            Popen(args)

    def _chapter_timings(self, a: list = None, b: list = None):
        s = a if a else self.s
        e = b if b else self.e

        index = 1
        diff = 0

        if s[0] > 0:
            idiff = s[0]
            s = [i - idiff for i in s]
            e = [i - idiff for i in e]

        while index < len(s):
            for i in range(index, len(s)):
                if s[i] != e[i - 1] + 1:
                    diff = s[i] - e[i - 1] - 1
                    index = i
                    break

                diff = 0
                index += 1

            for i in range(index, len(s)):
                s[i] -= diff
                e[i] -= diff

        e[-1] += 1

        return s, e

    def _check_ordered(self, a: list = None, b: list = None):
        """checks if lists follow logical python slicing 4,-10 on a 0-99 (100 fr) >> [4:90]"""
        a = a if a else self.s
        b = b if b else self.e

        if not all(a[i] < a[i + 1] for i in range(len(a) - 1)):
            """makes sure list a is ordered L to G, without overlaps"""
            return False

        if not all(b[i] < a[i + 1] for i in range(len(a) - 1)):
            """makes sure all ends are less than next start"""
            return False

        if not all(a[i] < b[i] for i in range(len(a))):
            """makes sure each pair is at least one frame long"""
            return False

        return True

    def _combine(self, a: list = None, b: list = None, tclip: vs.VideoNode = None):
        s = a if a else self.s
        e = b if b else self.e

        e = [i + 1 for i in e]

        s, e = self._negative_to_positive(s, e, tclip)

        c_s = []
        c_e = []

        for i in range(len(s)):
            if i == 0:
                c_s.append(s[i])
                if e[i] != s[i + 1]:
                    c_e.append(e[i])
                    continue
                else:
                    continue
            elif i < len(s) - 1:
                if s[i] != e[i - 1]:
                    c_s.append(s[i])
                if e[i] != s[i + 1]:
                    c_e.append(e[i])
                    continue
                else:
                    continue
            elif i == len(s) - 1:
                if s[i] != e[i - 1]:
                    c_s.append(s[i])
                c_e.append(e[i])

        return c_s, c_e

    def _cut_audio(self):
        ts_cmd = self.mkvmerge + '{delay} --split parts:'

        for s, e in zip(self.cut_ts_s, self.cut_ts_e):
            ts_cmd += '{}-{},+'.format(s, e)

        cut_cmd = ts_cmd[:-2]

        ident = run([self.mkvmerge, '--identify', self.audio_file], check=True, stdout=PIPE).stdout
        identre = compile(r'Track ID (\d+): audio')
        ret = (identre.search(ident.decode(getfilesystemencoding())) if ident else None)
        tid = ret.group(1) if ret else '0'
        delre = compile(r'DELAY ([-]?\d+)', flags=IGNORECASE)
        ret = delre.search(self.audio_file)

        delay = '{0}:{1}'.format(tid, ret.group(1)) if ret else None
        if delay:
            delay_statement = ' --sync {}'.format(delay)
        else:
            delay_statement = ''

        cut_cmd += ' -o "{}" "{}"'.format(self.outfile, self.audio_file)

        args = split(cut_cmd.format(delay=delay_statement))
        cut_exec = Popen(args).returncode

        if cut_exec == 1:
            print('Mkvmerge exited with warnings: 1')
        elif cut_exec == 2:
            print(args)
            exit('Failed to execute mkvmerge: 2')

    def _f2ts(self, f: int, tclip: vs.VideoNode = None, precision: int = 9):
        if self.clip:
            n = self.clip.fps_num
            d = self.clip.fps_den
        elif tclip:
            n = tclip.fps_num
            d = tclip.fps_den
        else:
            raise ValueError('_f2ts: clip needs to be specified')

        t = round(10 ** precision * f * Fraction(d, n)) if precision > 3 else round(
            10 ** precision * f * Fraction(d, n) + .5)
        s = t / 10 ** precision
        m = s // 60
        s = s % 60
        h = m // 60
        m = m % 60

        if precision == 3:
            return '{:02.0f}:{:02.0f}:{:06.3f}'.format(h, m, s)
        else:
            return '{:02.0f}:{:02.0f}:{:012.9f}'.format(h, m, s)

    def _negative_to_positive(self, a: list, b: list, tclip: vs.VideoNode = None):
        num_frames = tclip.num_frames if tclip else self.clip.num_frames
        positive_a = []
        positive_b = []

        if len(a) != len(b):
            """checks whether lists are same length (redundant with other funcs)"""
            raise ValueError('lists must be same length')

        for x, y in zip(a, b):
            if abs(x) > num_frames or abs(y) > num_frames:
                raise ValueError('{} is out of bounds'.format(max(abs(x), abs(y))))

        if all(i >= 0 for i in a) and all(i > 0 for i in b):
            return a, b

        for x, y in zip(a, b):
            positive_a.append(x if x >= 0 else num_frames + x)
            positive_b.append(y if y > 0 else num_frames + y)

        return positive_a, positive_b

    def _write_chapters(self, a: list, b: list, chapter_file: str = None):
        chapter_file = chapter_file if chapter_file else self.chapter_file

        if '.txt' not in chapter_file:
            chapter_file += '.txt'

        chapter_names = self.chapter_names if self.chapter_names else list(ascii_uppercase)
        if not self.chapter_names:
            chapter_names = ['Part ' + i for i in chapter_names]

        lines = []

        for i in range(len(a)):
            lines.append('CHAPTER{:02d}={}'.format(i, a[i]))
            lines.append('CHAPTER{:02d}NAME={}'.format(i, chapter_names[i]))

        lines.append('CHAPTER{:02d}={}'.format(len(a), b[-1]))
        lines.append('CHAPTER{:02d}NAME=DELETE ME'.format(len(a)))

        text_file = open(chapter_file, 'w')
        for i in lines:
            text_file.write(i + '\n')
        text_file.close()
