import unittest
from fractions import Fraction

import vapoursynth as vs

import acsuite


class ACsuiteTests(unittest.TestCase):
    BLANK_CLIP = vs.core.std.BlankClip(format=vs.YUV420P8, length=100, fpsnum=5, fpsden=1)

    def test_default_clip(self):
        self.assertEqual(self.BLANK_CLIP.num_frames, 100)
        self.assertEqual(self.BLANK_CLIP.fps, Fraction(5, 1))
        self.assertEqual(acsuite._f2ts(self.BLANK_CLIP.fps, self.BLANK_CLIP.num_frames), '00:00:20.000')

    def test_eztrim(self):
        with self.assertRaisesRegex(TypeError, 'trims must be a list of 2-tuples'):
            acsuite.eztrim(self.BLANK_CLIP, trims='str', audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(ValueError, 'must have 2 elements'):
            acsuite.eztrim(self.BLANK_CLIP, trims=(1, 2, 3), audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(TypeError, 'is not a tuple'):
            acsuite.eztrim(self.BLANK_CLIP, trims=[(1, 2), 'str'], audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(ValueError, 'needs 2 elements'):
            acsuite.eztrim(self.BLANK_CLIP, trims=[(1, 2), (3, 4, 5)], audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(ValueError, '2 ints'):
            acsuite.eztrim(self.BLANK_CLIP, trims=[(1, 2), (3, 'str')], audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(ValueError, 'is not logical'):
            acsuite.eztrim(self.BLANK_CLIP, trims=(-95, -99), audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(ValueError, 'is not logical'):
            acsuite.eztrim(self.BLANK_CLIP, trims=(1, 1), audio_file='', outfile='', debug=True)

        with self.assertRaisesRegex(ValueError, 'are not logical'):
            acsuite.eztrim(self.BLANK_CLIP, trims=[(1, 10), (2, -95)], audio_file='', outfile='', debug=True)

        with self.assertWarns(SyntaxWarning):
            acsuite.eztrim(self.BLANK_CLIP, trims=[(5, 10)], audio_file='', outfile='', debug=True)

        self.assertEqual(
            acsuite.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                           outfile='', debug=True)['s'], [3, 23, 48, 50, 90, 97])

        self.assertEqual(
            acsuite.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                           outfile='', debug=True)['e'], [22, 40, 49, 80, 95, 100])

        self.assertEqual(
            acsuite.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                           outfile='', debug=True)['cut_ts_s'],
            ['00:00:00.600', '00:00:04.600', '00:00:09.600', '00:00:10.000',
             '00:00:18.000', '00:00:19.400'])

        self.assertEqual(
            acsuite.eztrim(self.BLANK_CLIP, [(3, 22), (23, 40), (48, 49), (50, -20), (-10, -5), (97, 0)], audio_file='',
                           outfile='', debug=True)['cut_ts_e'],
            ['00:00:04.400', '00:00:08.000', '00:00:09.800', '00:00:16.000',
             '00:00:19.000', '00:00:20.000'])

        self.assertEqual(acsuite.eztrim(self.BLANK_CLIP, (3, -13), audio_file='', outfile='', debug=True),
                         {'s': 3, 'e': 87, 'cut_ts_s': ['00:00:00.600'], 'cut_ts_e': ['00:00:17.400']})

    def test_check_ordered(self):
        self.assertFalse(acsuite._check_ordered([0, 5, 8], [1, 9, 10]))
        self.assertFalse(acsuite._check_ordered([0, 2, 4], [0, 3, 5]))

        self.assertTrue(acsuite._check_ordered([0, 2, 4], [1, 3, 5]))

    def test_f2ts(self):
        self.assertEqual(acsuite._f2ts(self.BLANK_CLIP.fps, 0), '00:00:00.000')
        self.assertEqual(acsuite._f2ts(self.BLANK_CLIP.fps, 69), '00:00:13.800')

    def test_negative_to_positive(self):
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [0, 3, 101], [0, 1, 2])
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [0, 3, 98], [0, 1, -102])

        with self.assertRaisesRegex(ValueError, 'same length'):
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [1, 2], [3, 4, 5])

        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [1, 4, 5], [10, 75, 85]), ([1, 4, 5], [10, 75, 85]))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [4, 0, 5], [10, 20, 1]), ([4, 0, 5], [10, 20, 1]))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [4, 0, 5], [10, 0, 1]), ([4, 0, 5], [10, 100, 1]))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [-10, 0, -5], [-10, 0, 5]),
                         ([90, 0, 95], [90, 100, 5]))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [0], [-12]), ([0], [88]))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [-12], [0]), ([88], [100]))


if __name__ == '__main__':
    unittest.main()
