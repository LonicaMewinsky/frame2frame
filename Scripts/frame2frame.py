import copy
import os
import modules.scripts as scripts
import modules.images
import gradio as gr
import numpy as np
import cv2
from PIL import Image, ImageSequence
from modules.processing import Processed, process_images
from modules.shared import state, sd_upscalers
from moviepy.editor import VideoFileClip
''' To be re-implemented
with open(os.path.join(scripts.basedir(), "instructions.txt"), 'r') as file:
    mkd_inst = file.read()'''

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
    
def blend_images(images):
    sizes = [img.size for img in images]
    min_width, min_height = min(sizes, key=lambda s: s[0]*s[1])
    blended_img = Image.new('RGB', (min_width, min_height))
    
    for x in range(min_width):
        for y in range(min_height):
            colors = [img.getpixel((x, y)) for img in images]
            avg_color = tuple(int(sum(c[i] for c in colors) / len(colors)) for i in range(3))
            blended_img.putpixel((x, y), avg_color)
    
    return blended_img    

class Script(scripts.Script):
    def __init__(self):
        #self.frame2frame_dir = tempfile.TemporaryDirectory()
        self.gif_mode = False
        self.active_file = None
        self.audio_codec = None
        self.video_codec = None
        self.fourcc = None
        self.orig_fps = 0
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
                            with gr.Tab("Configuration"):
                                with gr.Box():
                                    desired_fps_slider = gr.Slider(0.01, 1.00, step = 0.01, value=1.00, interactive = True, label = "Processing FPS reduction")
                                    desired_fps = gr.Number(value=0, interactive = False, label = "Resultant FPS")
                                    desired_frames = gr.Number(value=0, interactive = False, label = "Resultant frames (generations)")
                            with gr.Tab("Options"):
                                with gr.Box():
                                    anim_resize = gr.Checkbox(value = True, label="Resize result back to original dimensions")
                                    anim_clear_frames = gr.Checkbox(value = True, label="Delete intermediate frames after generation")
                                    anim_common_seed = gr.Checkbox(value = True, label="For -1 seed, all frames in an animation have fixed seed")
                            with gr.Tab("Info"):
                                with gr.Box():
                                    anim_fps = gr.Number(value=0, interactive = False, label = "Original FPS")
                                    anim_runtime = gr.Number(value=0, interactive = False, label = "Original runtime")
                                    anim_frames = gr.Number(value=0, interactive = False, label = "Original total frames")
                            ''' To be re-implemented
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
                                                    ups_scale_to_h = gr.Slider(0, 8000, step = 8, value=512, interactive = True, label = "Target height")'''
        #Control funcs
        def process_upload(file, fps_factor):
            if file == None:
                return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0, 0, 0
            
            #Handle gif upload
            elif any(substring in file.name for substring in types_gif):
                try:
                    self.active_file = file.name
                    #Collect and set info
                    pimg = Image.open(file.name)
                    self.orig_width = pimg.width
                    self.orig_height = pimg.height
                    self.orig_gif_dur = pimg.info["duration"]
                    self.orig_num_frames = pimg.n_frames
                    self.orig_fps = round((1000 / self.orig_gif_dur), 2)
                    self.gif_mode = True
                    return file.name, file.name, cl8(pimg.width), cl8(pimg.height), gr.File.update(visible=False), gr.Image.update(value=file.name, visible=True), gr.Video.update(visible=False), self.orig_fps, self.orig_runtime, self.orig_num_frames, round(self.orig_fps*fps_factor, 2), round(self.orig_num_frames*fps_factor)
                except:
                    print(f"Trouble loading GIF/WEBP file {file.name}")
                    self.active_file = None
                    return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0 ,0, 0, 0
            
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
                        self.gif_mode = False
                        vstream.release()
                        return pimg, pimg, cl8(pimg.width), cl8(pimg.height), gr.File.update(visible=False), gr.Image.update(visible=False), gr.Video.update(value=file.name, visible=True), self.orig_fps, self.orig_runtime, self.orig_num_frames, round(self.orig_fps*fps_factor, 2), round(self.orig_num_frames*fps_factor)
                    else: vstream.release()
                except:
                    print(f"Trouble loading video file {file.name}")
                    self.active_file = None
                    return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0, 0, 0
            
            #Handle other filetypes?
            else:
                print(f"Unrecognized filetype. Accepted filetypes: {types_all}")
                return None, None, gr.Slider.update(), gr.Slider.update(), gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0, 0, 0
        
        #Listeners
        def clear_anim(anim):
            if anim == None:
                self.orig_fps = 0
                self.orig_num_frames = 0
                return None, None, gr.File.update(value=None, visible=True), gr.Image.update(visible=False), gr.Video.update(visible=False), 0, 0, 0, 0, 0
            else: #do nothing
                return gr.Image.update(), gr.Image.update(), gr.File.update(), gr.Image.update(), gr.Video.update(), gr.Textbox.update(), gr.Textbox.update(), gr.Textbox.update(), gr.Textbox.update(), gr.Textbox.update()

        def updatefps(fps_factor):
            if self.orig_fps == 0:
                return None, None
            else:
                return round(self.orig_fps*fps_factor, 2), round(self.orig_num_frames*fps_factor)

        upload_anim.upload(fn=process_upload, inputs=[upload_anim, desired_fps_slider], outputs=[self.img2img_component, self.img2img_inpaint_component, self.img2img_w_slider, self.img2img_h_slider,  upload_anim, preview_gif, preview_vid, anim_fps, anim_runtime, anim_frames, desired_fps, desired_frames])
        preview_gif.change(fn=clear_anim, inputs=preview_gif, outputs=[self.img2img_component, self.img2img_inpaint_component, upload_anim, preview_gif, preview_vid, anim_fps, anim_runtime, anim_frames, desired_fps, desired_frames])
        preview_vid.change(fn=clear_anim, inputs=preview_vid, outputs=[self.img2img_component, self.img2img_inpaint_component, upload_anim, preview_gif, preview_vid, anim_fps, anim_runtime, anim_frames, desired_fps, desired_frames])
        desired_fps_slider.change(fn=updatefps, inputs=[desired_fps_slider], outputs=[desired_fps, desired_frames])
        return [upload_anim, anim_clear_frames, anim_common_seed, anim_resize, desired_fps, desired_frames, desired_fps_slider]

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

    def run(self, p, upload_anim, anim_clear_frames, anim_common_seed, anim_resize, desired_fps, desired_frames, desired_fps_slider):
        try:
            if self.gif_mode:
                inc_gif = Image.open(upload_anim.name)
            else:
                inc_clip_raw = VideoFileClip(upload_anim.name)
                inc_clip = inc_clip_raw.set_fps(desired_fps)
        except:
            print("Something went wrong with animation. Processing still from img2img.")
            proc = process_images(p)
            return proc
        outpath = os.path.join(p.outpath_samples, "frame2frame")
        self.return_images, self.all_prompts, self.infotexts, self.inter_images = [], [], [], []
        
        #Actual generation function
        def generate_frame(image, p):
            if state.skipped: state.skipped = False
            if state.interrupted: return
            state.job = f"{state.job_no + 1} out of {state.job_count}"
            copy_p.init_images = [image] * p.batch_size
            copy_p.control_net_input_image = image.convert("RGB")
            proc = process_images(copy_p) #process
            #Handle batches
            proc_batch = []
            for pi in proc.images:
                if type(pi) is Image.Image: #just in case
                    proc_batch.append(pi)
            if len(proc_batch) > 1 and p.batch_size > 1:
                return_img = blend_images(proc_batch)
            else:
                return_img = proc_batch[0]
            if(anim_resize):
                    return_img = return_img.resize((self.orig_width, self.orig_height))
            self.all_prompts = proc.all_prompts
            self.infotexts = proc.infotexts

            return return_img 
        
        #Wrapper for moviepy function
        def generate_mpframe(image, p):
            nimg = Image.fromarray(image)
            return np.array(generate_frame(nimg, p))
        
        #Fix/setup vars
        state.job_count = int(desired_frames * p.n_iter)
        p.do_not_save_grid = True
        p.do_not_save_samples = anim_clear_frames
        anim_n_iter = p.n_iter
        p.n_iter = 1

        #Iterate batch count
        print(f"Will process {anim_n_iter} animation(s) with {state.job_count} total generations.")
        for x in range(anim_n_iter):
            if state.skipped: state.skipped = False
            if state.interrupted: break
            copy_p = copy.copy(p)
            if(anim_common_seed and (p.seed == -1)):
                modules.processing.fix_seed(copy_p)
            if self.gif_mode:
                prv_frame = ImageSequence.Iterator(inc_gif)[0]
            else:
                prv_frame = Image.fromarray(inc_clip.get_frame(1))
            out_filename_png = (modules.images.save_image(prv_frame, p.outpath_samples, "frame2frame", extension = 'png')[0])
            out_filename_noext = os.path.basename(out_filename_png).split(".")[0]
            if not anim_clear_frames:
                copy_p.outpath_samples = os.path.join(p.outpath_samples, out_filename_noext)
                print(f"Saving intermediary files to {copy_p.outpath_samples}..")
            #color_correction = [modules.processing.setup_color_correction(copy_p.init_images[0])]
            #Generate frames
            if self.gif_mode:
                generated_frames = []
                out_filename = out_filename_png.replace(".png",".gif")
                for frame in ImageSequence.Iterator(inc_gif):
                    generated_frames.append(generate_frame(frame, p=copy_p))
                    print(len(generated_frames))
                generated_frames[0].save(out_filename,
                    save_all = True, append_images = generated_frames[1:], loop = 0,
                    optimize = False, duration = self.orig_gif_dur)
            else:
                out_filename = out_filename_png.replace(".png",".mp4")
                out_clip = inc_clip.fl_image(lambda image: generate_mpframe(image, p=copy_p))
                out_clip.write_videofile(out_filename)
            #Save a PNG potentially with PNGINFO
            current_info = self.infotexts[len(self.infotexts)-1]
            modules.images.save_image(prv_frame, p.outpath_samples, "frame2frame", info=current_info, forced_filename = out_filename_noext, extension = 'png')
            self.return_images.append(out_filename_png)

        return Processed(copy_p, self.return_images, copy_p.seed, "", all_prompts=self.all_prompts, infotexts=self.infotexts)