import copy
import os
import modules.scripts as scripts
import modules.images
import gradio as gr
import numpy as np
import tempfile
import random
import cv2
from PIL import Image, ImageSequence
from modules.processing import Processed, process_images
from modules.shared import state, sd_upscalers

with open(os.path.join(scripts.basedir(), "instructions.txt"), 'r') as file:
    mkd_inst = file.read()

types_vid = ['.mp4', '.mkv', '.avi', '.ogv', '.ogg', '.webm']
types_gif = ['.gif', '.webp']
types_all = types_vid+types_gif

#Get num closest to 8
def cl8(num):
    rem = num % 8
    if rem <= 4:
        return round(num - rem)
    else:
        return round(num + (8 - rem))
    
class Script(scripts.Script):
    def __init__(self):
        self.frame2frame_dir = tempfile.TemporaryDirectory()
        self.active_file = None
        self.audio_codec = None
        self.video_codec = None
        self.fourcc = None
        self.orig_fps = 0
        self.desired_fps = 0
        self.orig_runtime = 0
        self.desired_runtime = 0
        self.orig_num_frames = 0
        self.orig_width = 0
        self.orig_height = 0
        self.orig_gif_dur = 0
        self.desired_gif_dur = 0
        self.img2img_component = gr.Image()
        self.img2img_inpaint_component = gr.Image()
        self.img2img_w_slider = gr.Slider()
        self.img2img_h_slider = gr.Slider()
        return None

    def title(self):
        return "frame2frame"

    def show(self, is_img2img):
        return is_img2img

    def ui(self, is_img2img):
        #Controls
        with gr.Row():
                with gr.Box():
                    with gr.Column():
                        upload_anim = gr.File(label="Upload Animation", file_types = types_all, live=True, file_count = "single")
                        preview_gif = gr.Image(inputs = upload_anim, visible=False, Source="Upload", interactive=True, label = "Preview", type= "filepath")
                        preview_vid = gr.Video(inputs = upload_anim, visible=False, Source="Upload", interactive=True, label = "Preview", type= "filepath")
                with gr.Column():
                    with gr.Box():
                        with gr.Tabs():
                            with gr.Tab("Output"):
                                with gr.Box():
                                    send_blend = gr.Button("Send blended image to img2img Inpainting tab")
                            with gr.Tab("Settings"):
                                with gr.Box():
                                    anim_resize = gr.Checkbox(value = True, label="Resize result back to original dimensions")
                                    anim_clear_frames = gr.Checkbox(value = True, label="Delete intermediate frames after generation")
                                    anim_common_seed = gr.Checkbox(value = True, label="For -1 seed, all frames in an animation have fixed seed")
                            with gr.Tab("Info"):
                                with gr.Box():
                                    anim_fps = gr.Textbox(value="", interactive = False, label = "FPS")
                                    anim_runtime = gr.Textbox(value="", interactive = False, label = "Runtime")
                                    anim_frames = gr.Textbox(value="", interactive = False, label = "Total frames")
                            with gr.Tab("Loopback"):
                                with gr.Box():
                                    loop_backs = gr.Slider(0, 50, step = 1, label = "Generation loopbacks", value = 0)
                                    loop_denoise = gr.Slider(0.01, 1, step = 0.01, value=0.10, interactive = True, label = "Loopback denoise strength")
                                    loop_decay = gr.Slider(0, 2, step = 0.05, value=1.0, interactive = True, label = "Loopback decay")
                            with gr.Tab("Upscaling"):
                                    with gr.Column():
                                        with gr.Row():
                                            ups_upscaler = gr.Dropdown(value = "None", interactive = True, choices = [x.name for x in sd_upscalers], label = "Upscaler")
                                            ups_only_upscale = gr.Checkbox(value = False, label = "No generation, only upscale")
                                        with gr.Tabs():
                                            with gr.Tab("Scale by") as tab_scale_by:
                                                with gr.Box():
                                                    ups_scale_by = gr.Slider(1, 8, step = 0.1, value=2, interactive = True, label = "Factor")
                                            with gr.Tab("Scale to") as tab_scale_to:
                                                with gr.Box():
                                                    ups_scale_to_w = gr.Slider(0, 8000, step = 8, value=512, interactive = True, label = "Target width")
                                                    ups_scale_to_h = gr.Slider(0, 8000, step = 8, value=512, interactive = True, label = "Target height")
        #Control funcs
        def process_upload(file):
            if file == None:
                return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0
            
            #Handle gif upload
            elif any(substring in file.name for substring in types_gif):
                try:
                    self.active_file = file.name
                    #Collect and set info
                    pimg = Image.open(file.name)
                    self.orig_width = pimg.width
                    self.orig_gif_dur = pimg.info["duration"]
                    self.orig_num_frames = pimg.n_frames
                    self.orig_fps = round((1000 / self.orig_gif_dur), 2)
                    return file.name, file.name, cl8(pimg.width), cl8(pimg.height), gr.File.update(visible=False), gr.Image.update(value=file.name, visible=True), gr.Video.update(visible=False), self.orig_fps, self.orig_runtime, self.orig_num_frames
                except:
                    print(f"Trouble loading GIF/WEBP file {file.name}")
                    self.active_file = None
                    return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0 ,0
            
            #Handle video upload
            elif any(substring in file.name for substring in types_vid):
                try:
                    self.active_file = file.name
                    #Collect and set info
                    vstream = cv2.VideoCapture(file.name)
                    fourcc = int(vstream.get(cv2.CAP_PROP_FOURCC))
                    self.fourcc = fourcc
                    self.orig_fps = int(vstream.get(cv2.CAP_PROP_FPS))
                    self.orig_num_frames = int(vstream.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.orig_runtime = self.orig_num_frames / self.orig_fps
                    self.orig_width = int(vstream.get(cv2.CAP_PROP_FRAME_WIDTH))
                    self.orig_height = int(vstream.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    self.video_codec = chr(fourcc & 0xFF) + chr((fourcc >> 8) & 0xFF) + chr((fourcc >> 16) & 0xFF) + chr((fourcc >> 24) & 0xFF)
                    self.audio_codec = int(vstream.get(cv2.CAP_PROP_FOURCC)) >> 16
                    success, frame = vstream.read()
                    if success:
                        cimg = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pimg = Image.fromarray(cimg).convert("RGB")
                        vstream.release()
                        return pimg, pimg, cl8(pimg.width), cl8(pimg.height), gr.File.update(visible=False), gr.Image.update(visible=False), gr.Video.update(value=file.name, visible=True), self.orig_fps, self.orig_runtime, self.orig_num_frames
                    else: vstream.release()
                except:
                    print(f"Trouble loading video file {file.name}")
                    self.active_file = None
                    return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0
            
            #Handle other filetypes?
            else:
                print(f"Unrecognized filetype. Accepted filetypes: {types_all}")
                return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0
        
        #Listeners
        def clear_anim(anim):
            if anim == None:
                return None, None, gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0
            else: #do nothing
                return gr.Image.update(), gr.Image.update(), gr.File.update(), gr.Image.update(), gr.Video.update(), gr.Textbox.update(), gr.Textbox.update(), gr.Textbox.update()
 
        upload_anim.upload(fn=process_upload, inputs=[upload_anim], outputs=[self.img2img_component, self.img2img_inpaint_component, self.img2img_w_slider, self.img2img_h_slider,  upload_anim, preview_gif, preview_vid, anim_fps, anim_runtime, anim_frames])
        preview_gif.change(fn=clear_anim, inputs=preview_gif, outputs=[self.img2img_component, self.img2img_inpaint_component, upload_anim, preview_gif, preview_vid, anim_fps, anim_runtime, anim_frames])
        preview_vid.change(fn=clear_anim, inputs=preview_vid, outputs=[self.img2img_component, self.img2img_inpaint_component, upload_anim, preview_gif, preview_vid, anim_fps, anim_runtime, anim_frames])
        return [upload_anim]

    #Grab the img2img image components for update later
    #Maybe there's a better way to do this?
    def after_component(self, component, **kwargs):
        if component.elem_id == "img2img_image":
            self.img2img_component = component
            return self.img2img_component
        if component.elem_id == "img2maskimg":
            self.img2img_inpaint_component = component
            return self.img2img_inpaint_component
        if component.elem_id == "img2img_width":
            self.img2img_w_slider = component
            return self.img2img_w_slider
        if component.elem_id == "img2img_height":
            self.img2img_h_slider = component
            return self.img2img_h_slider