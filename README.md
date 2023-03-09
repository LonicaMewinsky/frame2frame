# frame2frame
Automatic1111 Stable Diffusion WebUI extension, generates img2img against frames in video files. Best-effort to retain audio.

Currently in-development but working. Mostly. Will succeed [gif2gif](https://github.com/LonicaMewinsky/gif2gif) in the near future.

- [ControlNet](https://github.com/Mikubill/sd-webui-controlnet) extensions handling improved.
   - Script will now only fill empty model image prompts with animation frames.
   - You can, for example, leave a static depth image in place while HED is animated.
- Builds video file in real-time. Generates SD images and and writes video frame in same pass.
- Accompanying .png file generated alongside video houses png information.
- Attempts to extracts and restores audio to file. To be made optional later.
- Does not require intermediary images saved to disk, but you can choose to.
- Currently defaults to H264 output, more codecs to be added.
- Accepts GIFs as well
