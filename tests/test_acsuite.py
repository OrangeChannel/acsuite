import os
import shutil
import unittest
from fractions import Fraction

import vapoursynth as vs

core = vs.core

import acsuite


class ACsuiteTests(unittest.TestCase):
    BLANK_CLIP = core.std.BlankClip(format=vs.YUV420P8, length=100, fpsnum=5, fpsden=1)
    VFR_CLIP = core.std.BlankClip(fpsnum=24000, fpsden=1001, length=24000) + core.std.BlankClip(
        fpsnum=30000, fpsden=1001, length=30000
    )

    def test_default_clip(self):
        self.assertEqual(self.BLANK_CLIP.num_frames, 100)
        self.assertEqual(self.BLANK_CLIP.fps, Fraction(5, 1))
        self.assertEqual(acsuite.f2ts(self.BLANK_CLIP.num_frames, src_clip=self.BLANK_CLIP), "00:00:20.000")

    def test_vfr_clip(self):
        self.assertEqual(self.VFR_CLIP.num_frames, 54000)
        self.assertEqual(self.VFR_CLIP.fps, Fraction())
        self.assertEqual(acsuite.f2ts(self.VFR_CLIP.num_frames, src_clip=self.VFR_CLIP), "00:33:22.000")

    def test_check_ordered(self):
        with self.assertWarnsRegex(Warning, "overlapping"):
            acsuite._check_ordered([0, 5, 8], [1, 9, 10])
        self.assertFalse(acsuite._check_ordered([0, 2, 4], [0, 3, 5]))
        self.assertTrue(acsuite._check_ordered([0, 2, 4], [1, 3, 5]))

    def test_negative_to_positive(self):
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, None, None), (0, 100))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, -90, -20), (10, 80))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, 20, 30), (20, 30))
        self.assertEqual(acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, 0, -10), (0, 90))

        with self.assertRaisesRegex(ValueError, "bounds"):
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, None, 101)

        with self.assertRaisesRegex(ValueError, "length"):
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [None, 10, 20], [None, -30])

        with self.assertRaisesRegex(ValueError, "bounds"):
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [None, 10, 20], [None, -30, 101])

        self.assertEqual(
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [0, 20, 30], [10, 30, 40]),
            ([0, 20, 30], [10, 30, 40]),
        )
        self.assertEqual(
            acsuite._negative_to_positive(self.BLANK_CLIP.num_frames, [0, 20, 30], [10, None, -30]),
            ([0, 20, 30], [10, 100, 70]),
        )

    def test_f2ts_and_clip_to_timecodes(self):
        with self.assertRaisesRegex(ValueError, "multiple of 3"):
            acsuite.f2ts(0, src_clip=self.BLANK_CLIP, precision=1)

        self.assertEqual(acsuite.f2ts(0, src_clip=self.BLANK_CLIP), "00:00:00.000")
        self.assertEqual(acsuite.f2ts(0, src_clip=self.VFR_CLIP), "00:00:00.000")

        self.assertEqual(acsuite.f2ts(69, src_clip=self.BLANK_CLIP, precision=0), "00:00:14")
        self.assertEqual(acsuite.f2ts(69, src_clip=self.BLANK_CLIP), "00:00:13.800")
        self.assertEqual(acsuite.f2ts(69, src_clip=self.BLANK_CLIP, precision=6), "00:00:13.800000")
        self.assertEqual(acsuite.f2ts(69, src_clip=self.BLANK_CLIP, precision=9), "00:00:13.800000000")

        self.assertEqual(acsuite.f2ts(10000, src_clip=self.VFR_CLIP), "00:06:57.083")
        self.assertEqual(acsuite.f2ts(25000, src_clip=self.VFR_CLIP), "00:17:14.367")

    def test_eztrim(self):
        with self.assertRaisesRegex(FileNotFoundError, "not found"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "non_existent_file.wav")
        with self.assertWarnsRegex(Warning, "supported"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_unknown_audio.zzz")

        with self.assertWarnsRegex(Warning, "correct"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_wav_audio.wav", "outfile.xyz")
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_wav_audio1.wav")

        with self.assertRaisesRegex(FileNotFoundError, "ffmpeg"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_wav_audio.wav", ffmpeg_path="empty_path.exe")

        with self.assertRaisesRegex(FileNotFoundError, "not found"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_wav_audio.wav", timecodes_file="empty_path.txt")

        with self.assertRaisesRegex(TypeError, "trims must be"):
            acsuite.eztrim(self.BLANK_CLIP, "str", "test_wav_audio.wav", "outfile.wav")
        with self.assertWarnsRegex(SyntaxWarning, "directly"):
            acsuite.eztrim(self.BLANK_CLIP, [(5, -2)], "test_wav_audio.wav", "outfile.wav")
        with self.assertRaisesRegex(TypeError, "inner trim"):
            acsuite.eztrim(self.BLANK_CLIP, ["str"], "test_wav_audio.wav", "outfile.wav")

        with self.assertRaisesRegex(ValueError, "2 elements"):
            acsuite.eztrim(self.BLANK_CLIP, (1, 2, 3), "test_wav_audio.wav", "outfile.wav")
        with self.assertRaisesRegex(TypeError, "contain only"):
            acsuite.eztrim(self.BLANK_CLIP, (1, "str"), "test_wav_audio.wav", "outfile.wav")
        with self.assertRaisesRegex(ValueError, "end with 0"):
            acsuite.eztrim(self.BLANK_CLIP, (1, 0), "test_wav_audio.wav", "outfile.wav")
        with self.assertWarnsRegex(Warning, "quitting"):
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_wav_audio.wav", "outfile.wav")

        with self.assertRaisesRegex(TypeError, "not a tuple"):
            acsuite.eztrim(self.BLANK_CLIP, [(1, 2), "str"], "test_wav_audio.wav", "output.wav")
        with self.assertRaisesRegex(ValueError, "2 elements"):
            acsuite.eztrim(self.BLANK_CLIP, [(1, 2), (1, 2, 3)], "test_wav_audio.wav", "output.wav")
        with self.assertRaisesRegex(TypeError, "2 ints"):
            acsuite.eztrim(self.BLANK_CLIP, [(1, 2), (1, "str")], "test_wav_audio.wav", "output.wav")
        with self.assertRaisesRegex(ValueError, "end with 0"):
            acsuite.eztrim(self.BLANK_CLIP, [(1, 2), (1, 0)], "test_wav_audio.wav", "output.wav")

        with self.assertRaisesRegex(ValueError, "not logical"):
            acsuite.eztrim(self.BLANK_CLIP, (10, 10), "test_wav_audio.wav", "output.wav")

        with self.assertRaisesRegex(ValueError, "not logical"):
            acsuite.eztrim(self.BLANK_CLIP, [(None, 2), (10, 8)], "test_wav_audio.wav", "output.wav")

        # --------------------------------------------------------------------------------------------------------------

        temp_file = open("_acsuite_temp_concat.txt", "w")
        temp_file.write("t")
        temp_file.close()

        with self.assertRaisesRegex(FileExistsError, "exists"):
            acsuite.eztrim(self.BLANK_CLIP, [(None, -1), (None, -1)], "test_wav_audio.wav", "outfile.wav")

        os.remove("_acsuite_temp_concat.txt")

        # --------------------------------------------------------------------------------------------------------------

        self.assertEqual(
            acsuite.eztrim(self.BLANK_CLIP, (None, None), "test_wav_audio.wav", "outfile.wav"), "outfile.wav"
        )

        # --------------------------------------------------------------------------------------------------------------

        none_none_test_locals = acsuite.eztrim(
            self.BLANK_CLIP, (None, None), "test_wav_audio.wav", "outfile.xxx", debug=True
        )

        self.assertEqual(none_none_test_locals["trims"], (None, None))
        self.assertEqual(none_none_test_locals["ffmpeg_path"], shutil.which("ffmpeg"))
        self.assertEqual(none_none_test_locals["audio_file_name"], "test_wav_audio")
        self.assertEqual(none_none_test_locals["audio_file_ext"], ".wav")
        self.assertEqual(none_none_test_locals["codec_args"], ["-c:a", "copy", "-rf64", "auto"])

        single_test_locals = acsuite.eztrim(
            self.VFR_CLIP, (10000, -29000), "test_wav_audio.wav", "outfile.xxx", debug=True, quiet=True
        )

        self.assertEqual(single_test_locals["trims"], (10000, -29000))
        self.assertEqual(single_test_locals["num_frames"], self.VFR_CLIP.num_frames)
        self.assertEqual((single_test_locals["start"], single_test_locals["end"]), (10000, 25000))
        single_test_args = (
            [shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "16"]
            + ["-i", "test_wav_audio.wav", "-vn", "-ss", "00:06:57.083", "-to", "00:17:14.367"]
            + ["-c:a", "copy", "-rf64", "auto"]
            + ["outfile.wav"]
        )

        self.assertEqual(single_test_locals["args"], single_test_args)

        double_test_locals = acsuite.eztrim(
            self.VFR_CLIP, [(None, 10000), (10000, -29000)], "test_wav_audio.wav", "outfile.xxx", debug=True
        )

        self.assertEqual(double_test_locals["starts"], [0, 10000])
        self.assertEqual(double_test_locals["ends"], [10000, 25000])
        self.assertEqual(
            double_test_locals["temp_filelist"], ["_acsuite_temp_output_0.wav", "_acsuite_temp_output_1.wav"]
        )

        double_test_args = [shutil.which("ffmpeg"), "-hide_banner"] + [
            "-f",
            "concat",
            "-i",
            "_acsuite_temp_concat.txt",
            "-c",
            "copy",
            "outfile.wav",
        ]
        self.assertEqual(double_test_locals["args"], double_test_args)

    def test_concat(self):
        with self.assertRaisesRegex(ValueError, "2 or more"):
            acsuite.concat(["test_wav_audio.wav"], "outfile.wav")
        with self.assertRaisesRegex(ValueError, "same extension"):
            acsuite.concat(["test_wav_audio.wav", "test_wav_audio.wav1"], "outfile.zzz")
            acsuite.concat(["test_wav_audio.wav", "test_unknown_audio1.zzz"], "outfile.wav")
        with self.assertRaisesRegex(ValueError, "valid extension"):
            acsuite.concat(["test_unknown_audio.zzz", "test_unknown_audio1.zzz"], "outfile.zzz")
        with self.assertRaises(FileNotFoundError):
            acsuite.concat(["test_wav_audio.wav", "nonexistent_file.wav"], "outfile.wav")
        with self.assertRaises(FileExistsError):
            acsuite.concat(["test_wav_audio.wav", "test_wav_audio1.wav"], "test_wav_audio1_cut.wav")

        # --------------------------------------------------------------------------------------------------------------

        temp_file = open("_acsuite_temp_concat.txt", "w")
        temp_file.write("t")
        temp_file.close()

        with self.assertRaisesRegex(FileExistsError, "concat"):
            acsuite.concat(["test_wav_audio.wav", "test_wav_audio1.wav"], "outfile.wav")

        os.remove("_acsuite_temp_concat.txt")

        # --------------------------------------------------------------------------------------------------------------

        args = [shutil.which("ffmpeg"), "-hide_banner"] + [
            "-f",
            "concat",
            "-i",
            "_acsuite_temp_concat.txt",
            "-c",
            "copy",
            "outfile.wav",
        ]

        self.assertEqual(
            acsuite.concat(["test_wav_audio.wav", "test_wav_audio1.wav"], "outfile.wav", debug=True)["args"],
            args,
        )


if __name__ == "__main__":
    unittest.main()
