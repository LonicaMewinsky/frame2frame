# frame2frame
Automatic1111 Stable Diffusion WebUI extension, generates img2img against frames in video files.

Still in-development but functional. Will succeed [gif2gif](https://github.com/LonicaMewinsky/gif2gif) in the near future.

- Builds video file in real-time. Generates SD images and and writes video frame in same pass.
- Accompanying .png file generated alongside video houses png information.
- Attempts to extract and restore audio to file. To be made optional later.
- Does not require intermediary images saved to disk, but you can choose to.
- Currently defaults to H264 output, more codecs to be added.
- Accepts GIFs as well
- [ControlNet](https://github.com/Mikubill/sd-webui-controlnet) extension handling improved:
   - Script will no longer overwrite existing ControlNet input images.
   - Script will only target ControlNet models with no input image specified.
   - Allows, for example, a static depth background while animation feeds openpose.

![ControlNetInst](https://user-images.githubusercontent.com/93007558/224233623-88abcf87-3e01-4bf3-8209-6ee691b1f749.jpg)

