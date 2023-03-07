# frame2frame
Automatic1111 Stable Diffusion WebUI extension, generates img2img against frames in video files, retains audio when possible.

Currently in-delopment but working. Probably. Possible dependency issue right now.
Lacks GIF support at the moment, but will succeed [gif2gif](https://github.com/LonicaMewinsky/gif2gif) in the near future.

- Builds video file in real-time. Generates SD images and and writes video frame in same pass.
- Accompanying .png file generated alongside video houses png information.
- Attempts to extracts and restores audio to file. To be made optional later.
- Does not require intermediary images saved to disk, but you can choose to.
- Currently defaults to H264 output, more codecs to be added.
