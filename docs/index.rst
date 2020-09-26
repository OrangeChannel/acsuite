acsuite documentation
---------------------

.. toctree::
   :maxdepth: 4
   :caption: Contents:

.. automodule:: acsuite

.. autofunction:: eztrim

.. autofunction:: concat

.. autofunction:: f2ts

.. code-block:: python
    :emphasize-lines: 8

    from functools import partial
    import vapoursynth as vs
    core = vs.core

    clip = core.std.BlankClip()
    ts = partial(f2ts, src_clip=clip)

    ts(5), ts(9), ts(clip.num_frames), ts(-1)
    # ('00:00:00.208', '00:00:00.375', '00:00:10.000', '00:00:09.958')

.. autofunction:: clip_to_timecodes
