import unittest
from fractions import Fraction

import acsuite

ac = acsuite.AC()

import vapoursynth as vs

core = vs.core


class ACsuiteTests(unittest.TestCase):
    BLANK_CLIP = core.std.BlankClip(_format=vs.YUV420P8, length=100, fpsnum=5, fpsden=1)

    def setUp(self) -> None:
        ac.__init__()

    def test_default_clip(self):
        self.assertEqual(self.BLANK_CLIP.num_frames, 100, '100 frames were expected')
        self.assertEqual(self.BLANK_CLIP.fps, Fraction(5, 1), '5 fps was expected')
        self.assertEqual(ac._f2ts(self.BLANK_CLIP.num_frames, tclip=self.BLANK_CLIP), '00:00:20.000000000',
                         '20 sec was expected')

    def test_eztrim(self):
        with self.assertRaisesRegex(TypeError, 'or just one'):
            ac.eztrim(self.BLANK_CLIP, trims='str', audio_file='', outfile='')

        with self.assertRaisesRegex(ValueError, 'must have 2 elements'):
            ac.eztrim(self.BLANK_CLIP, trims=(1, 2, 3), audio_file='', outfile='')

        with self.assertRaisesRegex(TypeError, 'is not a tuple'):
            ac.eztrim(self.BLANK_CLIP, trims=[(1, 2), 'str'], audio_file='', outfile='')

        with self.assertRaisesRegex(ValueError, 'needs 2 elements'):
            ac.eztrim(self.BLANK_CLIP, trims=[(1, 2), (3, 4, 5)], audio_file='', outfile='')

        with self.assertRaisesRegex(ValueError, '2 ints'):
            ac.eztrim(self.BLANK_CLIP, trims=[(1, 2), (3, 'str')], audio_file='', outfile='')

        with self.assertRaisesRegex(ValueError, 'is not logical'):
            ac.eztrim(self.BLANK_CLIP, trims=(-95, -99), audio_file='', outfile='')

        with self.assertRaisesRegex(ValueError, 'is not logical'):
            ac.eztrim(self.BLANK_CLIP, trims=(1, 1), audio_file='', outfile='')

        with self.assertRaisesRegex(ValueError, 'are not logical'):
            ac.eztrim(self.BLANK_CLIP, trims=[(1, 10), (2, -95)], audio_file='', outfile='')

        self.assertEqual(
            ac.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                      outfile='', debug=True)['s'], [3, 23, 48, 50, 90, 97])

        self.assertEqual(
            ac.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                      outfile='', debug=True)['e'], [22, 40, 49, 80, 95, 100])

        self.assertEqual(
            ac.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                      outfile='', debug=True)['cut_ts_s'],
            ['00:00:00.600000000', '00:00:04.600000000', '00:00:09.600000000', '00:00:10.000000000',
             '00:00:18.000000000', '00:00:19.400000000'])

        self.assertEqual(
            ac.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                      outfile='', debug=True)['cut_ts_e'],
            ['00:00:04.400000000', '00:00:08.000000000', '00:00:09.800000000', '00:00:16.000000000',
             '00:00:19.000000000', '00:00:20.000000000'])

        self.assertEqual(ac.eztrim(self.BLANK_CLIP, (3, -13), audio_file='', outfile='', debug=True)['s'], [3])

        self.assertEqual(ac.eztrim(self.BLANK_CLIP, (3, -13), audio_file='', outfile='', debug=True)['e'], [87])

    def test_check_ordered(self):
        self.assertFalse(ac._check_ordered([0, 1, 1]))
        self.assertFalse(ac._check_ordered([0, 2, 1]))
        self.assertFalse(ac._check_ordered([0, 5, 8], [1, 9, 10]))
        self.assertFalse(ac._check_ordered([0, 2, 4], [0, 3, 5]))

        self.assertTrue(ac._check_ordered([0, 2, 4], [1, 3, 5]))

    def test_f2ts(self):
        self.assertEqual(ac._f2ts(0, tclip=self.BLANK_CLIP), '00:00:00.000000000')
        self.assertEqual(ac._f2ts(69, tclip=self.BLANK_CLIP), '00:00:13.800000000')

        with self.assertRaisesRegex(ValueError, 'clip needs to be specified'):
            ac._f2ts(0)

    def test_negative_to_positive(self):
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            ac._negative_to_positive([0, 3, 101], [0, 1, 2], self.BLANK_CLIP)
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            ac._negative_to_positive([0, 3, 98], [0, 1, -102], self.BLANK_CLIP)

        with self.assertRaises(AttributeError):
            ac._negative_to_positive([1, 2, 3], [4, 5, 6])

        with self.assertRaisesRegex(ValueError, 'same length'):
            ac._negative_to_positive([1, 2], [3, 4, 5], self.BLANK_CLIP)

        self.assertEqual(ac._negative_to_positive([1, 4, 5], [10, 75, 85], self.BLANK_CLIP), ([1, 4, 5], [10, 75, 85]),
                         'expected same list')
        self.assertEqual(ac._negative_to_positive([4, 0, 5], [10, 20, 1], self.BLANK_CLIP), ([4, 0, 5], [10, 20, 1]),
                         'expected same list')
        self.assertEqual(ac._negative_to_positive([4, 0, 5], [10, 0, 1], self.BLANK_CLIP), ([4, 0, 5], [10, 100, 1]),
                         'expected different list')
        self.assertEqual(ac._negative_to_positive([-10, 0, -5], [-10, 0, 5], self.BLANK_CLIP),
                         ([90, 0, 95], [90, 100, 5]), 'expected positives')
        self.assertEqual(ac._negative_to_positive([0], [-12], self.BLANK_CLIP), ([0], [88]), '')
        self.assertEqual(ac._negative_to_positive([-12], [0], self.BLANK_CLIP), ([88], [100]), '')

    def test_octrim(self):
        with self.assertRaisesRegex(TypeError, 'must be a list'):
            ac.octrim(self.BLANK_CLIP, 'test', '', '', '')
        with self.assertRaisesRegex(TypeError, 'all be tuples'):
            ac.octrim(self.BLANK_CLIP, [(1), (1, 2, '')], '', '', '')
        with self.assertRaisesRegex(ValueError, 'at most'):
            ac.octrim(self.BLANK_CLIP, [(1, 2, '', ''), (1, 2, '')], '', '', '')
        with self.assertRaisesRegex(TypeError, 'have 2 ints'):
            ac.octrim(self.BLANK_CLIP, [(7, '', ''), (8, 9, '')], '', '', '')
        with self.assertRaisesRegex(TypeError, 'expected str'):
            ac.octrim(self.BLANK_CLIP, [(7, 8, 9)], '', '', '')
        with self.assertRaisesRegex(TypeError, 'expected int in pos 0'):
            ac.octrim(self.BLANK_CLIP, [('', '')], '', '', '')
        with self.assertRaisesRegex(TypeError, 'str in pos 1'):
            ac.octrim(self.BLANK_CLIP, [(7, 8)], '', '', '')
        with self.assertRaisesRegex(ValueError, 'at least 2 elements'):
            ac.octrim(self.BLANK_CLIP, [(9,)], '', '', '')

        with self.assertRaisesRegex(TypeError, 'all be tuples'):
            ac.octrim(self.BLANK_CLIP, ['', ('',)], '', '', '', names=False)
        with self.assertRaisesRegex(ValueError, 'at most 2 ints'):
            ac.octrim(self.BLANK_CLIP, [(3, 4, 5)], '', '', '', names=False)
        with self.assertRaisesRegex(TypeError, 'have 2 ints'):
            ac.octrim(self.BLANK_CLIP, [('', '')], '', '', '', names=False)
        with self.assertRaisesRegex(TypeError, 'expected int in pos 0'):
            ac.octrim(self.BLANK_CLIP, [('',)], '', '', '', names=False)
        with self.assertRaisesRegex(ValueError, 'last trim'):
            ac.octrim(self.BLANK_CLIP, [(9, 10), (8,)], '', '', '', names=False)

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 7, 'B'), (8, 9, 'C'), (11, 13, 'D'), (14, 17, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 35, 'H'), (36, 41, 'J')], '', '', '', debug=True)['cut_s'],
                         [1, 4, 11, 24, 33])

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 'B'), (8, 9, 'C'), (11, 'D'), (14, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 'H'), (36, 41, 'J')], '', '', '', debug=True)['cut_s'],
                         [1, 4, 11, 24, 33])

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 7, 'B'), (8, 9, 'C'), (11, 13, 'D'), (14, 17, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 35, 'H'), (36, 41, 'J')], '', '', '', debug=True)['cut_e'],
                         [3, 10, 21, 31, 42])

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 'B'), (8, 9, 'C'), (11, 'D'), (14, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 'H'), (36, 41, 'J')], '', '', '', debug=True)['cut_e'],
                         [3, 10, 21, 31, 42])

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 7, 'B'), (8, 9, 'C'), (11, 13, 'D'), (14, 17, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 35, 'H'), (36, 41, 'J')], '', '', '', debug=True)['chap_s_ts'],
                         ['00:00:00.000', '00:00:00.400', '00:00:01.200', '00:00:01.600',
                          '00:00:02.200', '00:00:03.000', '00:00:03.600', '00:00:05.000',
                          '00:00:05.600'])

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 'B'), (8, 9, 'C'), (11, 'D'), (14, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 'H'), (36, 41, 'J')], '', '', '', debug=True)['chap_s_ts'],
                         ['00:00:00.000', '00:00:00.400', '00:00:01.200', '00:00:01.600',
                          '00:00:02.200', '00:00:03.000', '00:00:03.600', '00:00:05.000',
                          '00:00:05.600'])

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 7, 'B'), (8, 9, 'C'), (11, 13, 'D'), (14, 17, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 35, 'H'), (36, 41, 'J')], '', '', '', debug=True)['chap_e_ts'][
                             -1], '00:00:06.800')

        self.assertEqual(ac.octrim(self.BLANK_CLIP,
                                   [(1, 2, 'A'), (4, 'B'), (8, 9, 'C'), (11, 'D'), (14, 'E'), (18, 20, 'F'),
                                    (24, 30, 'G'), (33, 'H'), (36, 41, 'J')], '', '', '', debug=True)['chap_e_ts'][-1],
                         '00:00:06.800')

    def test_chapter_timings(self):
        self.assertEqual(ac._chapter_timings([1, 5, 11, 13], [3, 8, 12, 15]), ([0, 3, 7, 9], [2, 6, 8, 12]))

    def test_combine(self):
        self.assertEqual(ac._combine([0, 5, 9, 12, 17, 19, 25], [2, 8, 11, 14, 18, 20, 27], self.BLANK_CLIP),
                         ([0, 5, 17, 25], [3, 15, 21, 28]))


if __name__ == '__main__':
    unittest.main()
