"""
Replacement for @AzraelNewtype's audiocutter.py:  https://github.com/AzraelNewtype/audiocutter
- eztrim() works directly with VapourSynth slicing syntax
- trim() is currently WIP, but should allow for easy ordered chapters creation
"""

import re
import shlex
import sys
from fractions import Fraction
from subprocess import call, check_output
from typing import Iterable

import vapoursynth as vs


# noinspection PyMissingOrEmptyDocstring
class AC(object):

    def __init__(self):
        """if mkvmerge is not in your PATH, add an absolute path to the executable here"""
        self.mkvmerge = r'mkvmerge'
        self.s = []
        self.e = []
        self.cut_ts_s = []
        self.cut_ts_e = []
        self.chapter_names = []
        self.clip = None
        self.audio_file = None
        self.outfile = None

    # def trim(self, clip: vs.VideoNode = None, trims: list = None, audio_file: str = None, outfile: str = None,
    #          debug: str = None):
    #     """
    #     Main trimming function for creating an ordered-chapters release.
    #     Trims should be the start frame of each chapter, followed by the ending frame number of that chapter,
    #     followed by a name.
    #
    #     These frame numbers should all be from the un-cut clip!!
    #
    #     * The syntax is different from VS/python slicing, end IS inclusive *
    #
    #     :param clip: vs.VideoNode:  clip that is being sliced
    #     :param trims: list:  a list of 3-tuples
    #
    #         [(start_frame, end_frame, 'chapter_name'), ...]
    #         the start frame is ALWAYS inclusive
    #         the end frame is also inclusive, but will auto-fix overlaps with the next trim's start frame
    #             the end frame can also be '-1' if the chapters are continuous
    #
    #         VapourSynth slicing clip[1:20]+clip[45:77] can be represented as
    #
    #         [(1, 19, 'intro'), (45, 76, 'outro')]
    #
    #         or as
    #
    #         [(1, -1, 'A'), (15, 19, 'B'), (45, 55, 'C'), (55, 76, 'D')]
    #         with chapter 'A' being frames [ 1,14] inclusive
    #              chapter 'B' being frames [15,19] inclusive
    #              chapter 'C' being frames [45,54] inclusive
    #              chapter 'D' being frames [55,76] inclusive
    #
    #
    #     :param audio_file: string:  path to pre-extracted audio file -- '/BDMV/STREAM/00004.wav'
    #
    #         [(1, 19, 'intro'), (45, 76, 'outro')] will result in audio cut at the following timecodes:
    #
    #         [1, 20) ++ [45, 77)
    #
    #     :param outfile: string:  cut audio filename with extension -- 'Cut.wav'
    #     :param debug: int:  0 disables, 1 runs full process, 2 stops before __write_chapters, 3 prints info
    #
    #     OUTPUT:  outputs the cut audio file, and a plaintext file 'Cut.txt' for chapter timings in the script directory
    #
    #     """
    #
    #     if None in (clip, trims, audio_file, outfile):
    #         raise TypeError('trim: function requires a clip, a list of trims, an audio_file path, and an outfile')
    #     if (not isinstance(trims, (list, tuple))):
    #         raise TypeError('trim: trims must be a list of 3-tuples')
    #     if len(trims) < 2:
    #         raise ValueError('trim: there must be at least two trims')
    #     for trim in trims:
    #         if (not isinstance(trim, (list, tuple))):
    #             raise TypeError('trim: the trim "{}" is not a 3-tuple'.format(trim))
    #         if len(trim) < 3:
    #             raise ValueError('trim: the trim "{}" must have 3 elements'.format(trim))
    #         if type(trim[2]) != str:
    #             raise TypeError('trim: the third element in the trim "{}" is not a string'.format(trim))
    #
    #     self.clip = clip
    #     num_frames = 100 if debug == 3 else clip.num_frames
    #     self.audio_file = audio_file
    #     self.outfile = outfile
    #     mod_s = []
    #     mod_e = []
    #     for s, e, n in trims:
    #         self.s.append(int(s))
    #         self.e.append(int(e))
    #         self.chapter_names.append(n)
    #
    #     if not self.__check_ordered(self.s, self.e):
    #         raise ValueError('trim: the tuples are not ordered correctly')
    #
    #     if self.e[-1] == 0 or self.e[-1] >= num_frames:
    #         if debug == 3:
    #             print('last element of e is {}, so being set to {}'.format(self.e[-1], num_frames - 1))
    #         self.e[-1] = num_frames - 1
    #
    #     if debug == 3:
    #         print('s: {}'.format(self.s))
    #         print('e: {}'.format(self.e))
    #         print('names: {}'.format(self.chapter_names))
    #
    #     mod_s.append(self.s[0])
    #
    #     for i in range(1, len(self.e)):
    #         if self.e[i - 1] not in (-1, self.s[i], self.s[i] - 1):
    #             """if the ending frame is neither -1, the next start frame, or one less, append (+=1) to modified end list"""
    #             mod_e.append(self.e[i - 1] + 1)
    #             if debug == 3:
    #                 print('{} added to mod_e'.format(self.e[i - 1] + 1))
    #                 print(mod_e)
    #         else:
    #             self.e[i - 1] = self.s[i] - 1
    #             if debug == 3:
    #                 print('self.e[{}] is now {}'.format(i - 1, self.s[i] - 1))
    #                 print('self.e: {}'.format(self.e))
    #         if self.s[i] not in (self.e[i - 1], self.e[i - 1] + 1):
    #             if self.e[i - 1] != -1:
    #                 mod_s.append(self.s[i])
    #                 if debug == 3:
    #                     print('{} added to mod_s'.format(self.s[i]))
    #                     print(mod_s)
    #
    #     mod_e.append(self.e[-1] + 1)
    #     if debug == 3:
    #         print('{} added to mod_e'.format(self.e[-1] + 1))
    #         print(mod_e)
    #
    #     for i in mod_s:
    #         self.cut_ts_s.append(self.__f2ts(i))
    #     for i in mod_e:
    #         self.cut_ts_e.append(self.__f2ts(i))
    #
    #     if debug == 2:
    #         return {'s':        self.s, 'e': self.e, 'names': self.chapter_names, 'mod_s': mod_s, 'mod_e': mod_e,
    #                 'cut_ts_s': self.cut_ts_s, 'cut_ts_e': self.cut_ts_e}
    #
    #     self.__write_chapters(outfile)
    #     self.__cut_audio()

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
        :param debug:  bool: used for testing, leave blank

        OUTPUTS: a cut/spliced audio file in either the script's directoy or the path specified with 'outfile'
        """

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

    def _check_ordered(self, a: list = None, b: list = None):
        """checks if lists follow logical python slicing 4,-10 on a 0-99 (100 fr) >> [4:90]"""
        a = self.s if self.s else a
        b = self.e if self.e else b

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

    def _cut_audio(self):
        ts_cmd = self.mkvmerge + '{2} --split parts:'

        for s, e in zip(self.cut_ts_s, self.cut_ts_e):
            ts_cmd += '{}-{},+'.format(s, e)

        cut_cmd = ts_cmd[:-2]

        ident = check_output([self.mkvmerge, '--identify', self.audio_file])
        identre = re.compile(r'Track ID (\d+): audio')
        ret = (identre.search(ident.decode(sys.getfilesystemencoding())) if ident else None)
        tid = ret.group(1) if ret else '0'
        delre = re.compile(r'DELAY ([-]?\d+)', flags=re.IGNORECASE)
        ret = delre.search(self.audio_file)

        delay = '{0}:{1}'.format(tid, ret.group(1)) if ret else None
        if delay:
            delay_statement = ' --sync {}'.format(delay)
        else:
            delay_statement = ''

        cut_cmd += ' -o "{1}" "{0}"'

        args = shlex.split(cut_cmd.format(self.audio_file, self.outfile, delay_statement))
        cut_exec = call(args)

        if cut_exec == 1:
            print("Mkvmerge exited with warnings: {0:d}".format(cut_exec))
        elif cut_exec == 2:
            print(args)
            exit("Failed to execute mkvmerge: {0:d}".format(cut_exec))

    def _f2ts(self, f: int, tclip: vs.VideoNode = None):
        if self.clip:
            n = self.clip.fps_num
            d = self.clip.fps_den
        elif tclip:
            n = tclip.fps_num
            d = tclip.fps_den
        else:
            raise ValueError('_f2ts: clip needs to be specified')

        t = round(10 ** 9 * f * Fraction(d, n))
        s = t / 10 ** 9
        m = s // 60
        s = s % 60
        h = m // 60
        m = m % 60

        return '{:02.0f}:{:02.0f}:{:012.9f}'.format(h, m, s)

    def _negative_to_positive(self, a: list, b: list, tclip: vs.VideoNode = None):
        num_frames = self.clip.num_frames if self.clip else tclip.num_frames
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

    # def __write_chapters(self, outfile: str = None, debug: str = None):
    #     if not debug:
    #         fn, e = outfile.split('.')
    #         fn += '.txt'
    #
    #     index = 1
    #     diff = 0
    #
    #     if self.s[0] > 0:
    #         idiff = self.s[0]
    #         if debug == 3:
    #             print('fist frame is not 0, shifting all frames backwards by {}'.format(idiff))
    #         for k, v in enumerate(self.s):
    #             self.s[k] -= idiff
    #         for k, v in enumerate(self.e):
    #             self.e[k] -= idiff
    #
    #         if debug == 3:
    #             print('s: {}'.format(self.s))
    #             print('e: {}'.format(self.e))
    #
    #     while index < len(self.e):
    #         if debug == 3:
    #             print('starting index: {}'.format(index))
    #         for i in range(index, len(self.e)):
    #             if self.s[i] != self.e[i - 1] + 1:
    #                 if debug == 3:
    #                     print('s[{}] was different than e[{}] + 1'.format(i, i - 1))
    #                 diff = self.s[i] - self.e[i - 1] - 1
    #                 index = i
    #                 if debug == 3:
    #                     print('diff is now {}, index is now {}'.format(diff, index))
    #                 break
    #             if debug == 3:
    #                 print('s[{}] was same as e[{}] + 1'.format(i, i - 1))
    #
    #             diff = 0
    #             index += 1
    #             if debug == 3:
    #                 print('diff is now {}, index is now {}'.format(diff, index))
    #
    #         for i in range(index, len(self.e)):
    #             if debug == 3:
    #                 print('shifting all frames starting with [{}] to account for diff ({})'.format(index, diff))
    #                 print('s: {}'.format(self.s))
    #                 print('e: {}'.format(self.e))
    #             self.s[i] -= diff
    #             self.e[i] -= diff
    #             if debug == 3:
    #                 print('new s: {}'.format(self.s))
    #                 print('new e: {}'.format(self.e))
    #     chap_ts_s = []
    #     chap_ts_e = []
    #
    #     for i in self.s:
    #         chap_ts_s.append(self.__f2ts(i))
    #         chap_ts_e.append('')
    #
    #     if debug == 3:
    #         print('chap_ts_s: {}'.format(chap_ts_s))
    #         print('chap_ts_e: {}'.format(chap_ts_e))
    #
    #     chap_ts_e[-1] = self.__f2ts(self.e[-1] + 1)
    #
    #     if debug == 3:
    #         print('chap_ts_e[-1] is now {}'.format(chap_ts_e[-1]))
    #
    #     lines = []
    #     for i in range(len(chap_ts_e)):
    #         lines.append('{:<12}    {}    {}'.format(self.chapter_names[i], chap_ts_s[i], chap_ts_e[i]))
    #
    #     if not debug:
    #         text_file = open(fn, 'w')
    #         for i in lines:
    #             text_file.write(i + '\n')
    #         text_file.close()
    #     elif debug == 3:
    #         for line in lines:
    #             print(line)
    #     elif debug == 1:
    #         return
