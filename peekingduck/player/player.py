# Copyright 2022 AI Singapore
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Implement PeekingDuck Player
"""

from typing import List, Union
from pathlib import Path
import logging
import platform
import tkinter as tk
from tkinter import filedialog
from tkinter.messagebox import askyesno
import threading
import copy
import cv2
import numpy as np
from PIL import ImageTk, Image
from peekingduck.declarative_loader import DeclarativeLoader
from peekingduck.pipeline.pipeline import Pipeline
from peekingduck.player.playlist import PlayList
from peekingduck.player.player_gui import gui_create_window
from peekingduck.player.player_utils import get_keyboard_char, get_keyboard_modifier

####################
# Globals
####################
BUTTON_DELAY: int = 250  # milliseconds (0.25 of a second)
BUTTON_REPEAT: int = int(1000 / 60)  # milliseconds (60 fps)
CHANGE_PIPELINE_DELAY: float = 1.0
FPS_60: int = int(1000 / 60)  # milliseconds per iteration
ZOOMS: List[float] = [0.5, 0.75, 1.0, 1.25, 1.50, 2.00, 2.50, 3.00]  # > 3x is slow!
ZOOM_DEFAULT_IDX: int = 2
ZOOM_TEXT: List[str] = ["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x", "2.5x", "3x"]
# Emojis
EMOJI_PLAY = "\u25B6"
EMOJI_STOP = "\u23F9"
EMOJI_MAGNIFYING_GLASS_LEFT = "\U0001F50D"
EMOJI_MAGNIFYING_GLASS_RIGHT = "\U0001F50E"
BTN_PAD = 0


class Player:  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """Implement PeekingDuck Player class"""

    def __init__(
        self,
        pipeline_path: Path,
        config_updates_cli: str,
        custom_nodes_parent_subdir: str,
        num_iter: int = 0,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.config_updates_cli = config_updates_cli
        self.custom_nodes_parent_path = custom_nodes_parent_subdir
        self.num_iter = num_iter
        # init PlayList object
        self.home_path = Path.home()
        self.playlist = PlayList(self.home_path)
        self.playlist.load_playlist_file()
        self.playlist_show: bool = False
        # init internal working variables
        self.frames: List[np.ndarray] = []
        self.frame_idx: int = -1
        self.zoom_idx: int = ZOOM_DEFAULT_IDX
        self.bkgd_job: Union[None, str] = None
        # init pipeline to run
        self.init_pipeline(pipeline_path)
        self.playlist.add_pipeline(self.pipeline_full_path)
        # configure keyboard shortcuts -> function map
        self.keyboard_shortcuts = {
            "z": self._zoom_reset,
            "+": self._zoom_in,
            "-": self._zoom_out,
        }

    def run(self) -> None:
        """Main method to setup Player and run Tk event loop"""
        self.logger.info(f"cwd={Path.cwd()}")
        self.logger.info(f"pipeline={self.pipeline_path}")
        gui_create_window(self)
        # trap macOS cmd-Q so Player will quit correctly as expected
        if platform.system() == "Darwin":
            self.logger.info("binding macOS cmd-Q")
            self.root.createcommand("::tk::mac::Quit", self.on_exit)
        # activate internal timer function and start Tkinter event loop
        self.timer_function()
        self.root.mainloop()

    def resize(self, event: tk.Event) -> None:
        """Callback to handle widget resize event.

        Args:
            event (tk.Event): The resize event.
        """
        if str(event.widget) == ".":
            # "." is the root widget, i.e. main window resize
            self.logger.debug(
                f"resize: widget={event.widget}, h={event.height}, w={event.width}"
            )

    #######################
    #
    # Background Event Loop
    #
    #######################
    def timer_function(self) -> None:
        """Function to do background processing in Tkinter's way"""
        if self.state == "play":
            # Only two states: 1) playing back video or 2) executing pipeline
            if self.is_output_playback:
                self.do_playback()
            else:
                # Executing pipeline: check which execution state we are in
                if not self.is_pipeline_running:
                    self.run_pipeline_start()
                elif self._pipeline.terminate:
                    self.run_pipeline_end()
                else:
                    self.run_pipeline_one_iteration()

        self.root.update()  # wake up GUI
        self.bkgd_job = self.tk_logo.after(FPS_60, self.timer_function)

    def cancel_timer_function(self) -> None:
        """Cancel the background timer function"""
        if self.bkgd_job:
            self.logger.info("cancel background timer")
            self.tk_logo.after_cancel(self.bkgd_job)
            self.bkgd_job = None

    ####################
    #
    # Tk Event Handlers
    #
    ####################
    def btn_hide_show_playlist_press(self) -> None:
        """Handle Hide/Show Playlist button

        dotw technotes:
            - Behavior:
                Playlist on right is fixed width.  When image is expanded, it should not
                cover playlist.  But when playlist is hidden and revealed, the expanding
                image will cover playlist
            - To fix above, need to
              a) also pack_forget() the image frame, along with the playlist frame
              b) when revealing playlist, pack() playlist first, then pack() image
              c) now the expanding image will not cover the playlist
        """
        if self.playlist_show:
            self.tk_playlist_frm.pack_forget()
        else:
            self.image_frm.pack_forget()
            self.tk_playlist_frm.pack(side=tk.RIGHT, fill=tk.Y)
            self.tk_playlist_view.reset()
            self.tk_playlist_view.select(str(self.pipeline_full_path))
            self.image_frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.playlist_show = not self.playlist_show

    def btn_play_stop_press(self) -> None:
        """Handle Play/Stop button"""
        self.logger.debug(f"btn_play_stop_press start: self._state={self.state}")
        if self.is_pipeline_running:
            self.stop_pipeline_run()
        elif self.is_output_playback:
            self.stop_playback()
        else:
            self.start_playback()
        self.logger.debug(f"btn_play_stop_press end: self._state={self.state}")

    def btn_first_frame_press(self) -> None:
        """Goto first frame"""
        if self.is_pipeline_running or self.is_output_playback or self.frames is None:
            return
        self.logger.debug("btn_first_frame_press")
        self.frame_idx = 0
        self._update_slider_and_show_frame()

    def btn_last_frame_press(self) -> None:
        """Goto last frame"""
        if self.is_pipeline_running or self.is_output_playback or self.frames is None:
            return
        self.logger.debug("btn_last_frame_press")
        self.frame_idx = len(self.frames) - 1
        self._update_slider_and_show_frame()

    def btn_forward_press(self) -> None:
        """Forward one frame"""
        if self.is_pipeline_running or self.is_output_playback or self.frames is None:
            return
        self._forward_one_frame()

    def btn_backward_press(self) -> None:
        """Back one frame"""
        if self.is_pipeline_running or self.is_output_playback or self.frames is None:
            return
        self._backward_one_frame()

    def btn_zoom_in_press(self) -> None:
        """Zoom in: make image larger"""
        self.logger.info("btn_zoom_in_press")
        self._zoom_in()

    def btn_zoom_out_press(self) -> None:
        """Zoom out: make image smaller"""
        self.logger.info("btn_zoom_out_press")
        self._zoom_out()

    def on_keypress(self, event: tk.Event) -> None:
        """Handle all keydown events.
        Default system shortcuts are automatically handled, e.g. CMD-Q quits on macOS

        Args:
            event (tk.Event): the key down event
        """
        self.logger.info(
            f"keypressed: char={event.char}, keysym={event.keysym}, state={event.state}"
        )
        key_state: int = int(event.state)
        mod = get_keyboard_modifier(key_state)
        key = get_keyboard_char(event.char, event.keysym)
        self.logger.info(f"mod={mod}, key={key}")
        # handle supported keyboard shortcuts here
        if mod.startswith("ctrl"):
            if key in self.keyboard_shortcuts:
                self.keyboard_shortcuts[key]()

    def on_exit(self) -> None:
        """Handle quit player event"""
        self.logger.info("saving playlist")
        self.playlist.save_playlist_file()
        self.logger.info("quitting player")
        self.cancel_timer_function()
        self.root.destroy()

    def on_add_pipeline(self) -> bool:
        """Add pipeline to playlist

        Returns:
            bool: True if pipeline added, False otherwise
        """
        self.logger.info("on add pipeline")
        filetypes = (("Pipeline files", "*.yml"), ("All files", "*.*"))
        pipeline_filepath = filedialog.askopenfilename(
            title="Open a pipeline file (*.yml)",
            initialdir=self.home_path,
            filetypes=filetypes,
        )
        self.logger.info(f"filepath={pipeline_filepath}")
        if pipeline_filepath:
            self.logger.info("to add to playlist")
            self.playlist.add_pipeline(pipeline_filepath)
            return True
        return False

    def on_delete_pipeline(self, pipeline: str) -> bool:
        """Delete pipeline from playlist

        Args:
            pipeline (str): Pipeline to delete
        """
        self.logger.info(f"on delete pipeline {pipeline}")
        answer = askyesno(
            title="Confirm delete pipeline file",
            message=f"Are you sure you want to delete {pipeline}?",
        )
        if answer:
            self.playlist.delete_pipeline(pipeline)
            return True
        return False

    def on_play_pipeline(self, pipeline: str) -> None:
        """Callback function for Play pipeline

        Args:
            pipeline (str): Pipeline to execute
        """
        self.logger.info(f"on play pipeline {pipeline}")
        if pipeline == str(self.pipeline_full_path):
            self.logger.info("already running, do nothing")
            return

        # run new pipeline
        self.logger.info("switch to new pipeline")
        if self.is_pipeline_running:
            self.logger.info("stop current run")
            self.run_pipeline_end()
        elif self.is_output_playback:
            self.logger.info("stop current playback")
            self.stop_playback()

        # add non-blocking wait to let background task clean up properly
        self.logger.info(f"wait {CHANGE_PIPELINE_DELAY} sec")
        wait_event = threading.Event()
        wait_event.wait(CHANGE_PIPELINE_DELAY)

        # double check status variables
        self.logger.debug(f"self.state={self.state}")
        self.logger.debug(f"self.is_output_playback={self.is_output_playback}")
        self.logger.debug(f"self.is_pipeline_running={self.is_pipeline_running}")
        assert self.state != "play"
        assert not self.is_output_playback
        assert not self.is_pipeline_running

        # start new pipeline here
        self.cancel_timer_function()
        self.init_pipeline(Path(pipeline))
        self.timer_function()

    ####################
    #
    # Methods for Display Management
    #
    ####################
    def _backward_one_frame(self) -> bool:
        """Move back one frame, can be called repeatedly"""
        if self.frame_idx > 0:
            self.frame_idx -= 1
            self._update_slider_and_show_frame()
            return True
        return False

    def _forward_one_frame(self) -> bool:
        """Move forward one frame, can be called repeatedly"""
        if self.frame_idx + 1 < len(self.frames):
            self.frame_idx += 1
            self._update_slider_and_show_frame()
            return True
        return False

    def _show_frame(self) -> None:
        """Display image frame pointed to by frame_idx"""
        if self.frames:
            frame = self.frames[self.frame_idx]
            frame = self._apply_zoom(frame)
            img_arr = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(img_arr)
            self._img_tk = img_tk  # save to avoid python GC
            self.tk_output_image.config(image=img_tk)

    def _apply_zoom(self, frame: np.ndarray) -> np.ndarray:
        """Zoom output image according to current zoom setting

        Args:
            frame (np.ndarray): image frame data to be zoomed

        Returns:
            np.ndarray: the zoomed image
        """
        if self.zoom_idx != ZOOM_DEFAULT_IDX:
            # zoom image
            zoom = ZOOMS[self.zoom_idx]
            new_size = (
                int(frame.shape[0] * zoom),
                int(frame.shape[1] * zoom),
                frame.shape[2],
            )
            # note: opencv is faster than scikit-image!
            frame = cv2.resize(frame, (new_size[1], new_size[0]))
        return frame

    def _zoom_in(self) -> None:
        """Zoom in on image"""
        if self.zoom_idx + 1 < len(ZOOMS):
            self.zoom_idx += 1
            self._update_zoom_and_show_frame()

    def _zoom_out(self) -> None:
        """Zoom out on image"""
        if self.zoom_idx > 0:
            self.zoom_idx -= 1
            self._update_zoom_and_show_frame()

    def _zoom_reset(self) -> None:
        """Reset zoom to default 1x"""
        self.zoom_idx = ZOOM_DEFAULT_IDX
        self._update_zoom_and_show_frame()

    def _update_zoom_and_show_frame(self) -> None:
        """Update zoom widget and refresh current frame"""
        glyph = ZOOM_TEXT[self.zoom_idx]
        self.logger.info(f"Zoom: {glyph}")
        self.tk_lbl_zoom["text"] = f"{glyph}"
        self._show_frame()

    def _set_header_playing(self) -> None:
        """Change header text to playing..."""
        self.tk_lbl_header["text"] = f"Playing {self.pipeline_path.name}"

    def _set_header_running(self) -> None:
        """Change header text to running..."""
        self.tk_lbl_header["text"] = f"Running {self.pipeline_path.name}"

    def _set_header_stop(self) -> None:
        """Change header text to pipeline pathname"""
        self.tk_lbl_header["text"] = f"{self.pipeline_path.name}"

    def _update_slider_and_show_frame(self) -> None:
        """Update slider based on frame index and show new frame"""
        frame_num = self.frame_idx + 1
        self.tk_scale.set(frame_num)
        self.tk_lbl_frame_num["text"] = frame_num
        self._show_frame()

    def _enable_progress(self) -> None:
        """Show progress bar and hide slider"""
        self.logger.debug("enable progress")
        self.tk_scale.grid_remove()  # hide slider
        self.tk_progress.grid()  # show progress bar

    def _enable_slider(self) -> None:
        """Show slider and hide progress bar"""
        self.logger.debug("enable slider")
        self.tk_progress.grid_remove()  # hide progress bar
        self.tk_scale.grid()  # show slider
        self.tk_scale.configure(to=len(self.frames))
        self.sync_slider_to_frame(self.tk_scale.get())

    def _set_status_text(self, text: str) -> None:
        """Set the status bar text to given text string

        Args:
            text (str): the status bar text string
        """
        self.status_bar["text"] = text

    def sync_slider_to_frame(self, val: str) -> None:
        """Update frame index based on slider value change

        Args:
            val (str): slider value
        """
        self.logger.debug(f"sync slider to frame: {val} {type(val)}")
        self.frame_idx = round(float(val)) - 1
        self.tk_lbl_frame_num["text"] = self.frame_idx + 1
        self._show_frame()

    ####################
    #
    # Pipeline Execution Methods
    #
    ####################
    def init_pipeline(self, pipeline_path: Path) -> None:
        """Initialise pipeline to be run

        Args:
            pipeline_path (Path): The pipeline to run
        """
        self.pipeline_path = pipeline_path
        is_abs = pipeline_path.is_absolute()
        self.logger.info(
            f"init pipeline: pipeline_path={pipeline_path}, is_abs={is_abs}"
        )
        # expand pipeline path if required
        if not is_abs:
            full_path = pipeline_path.resolve()
            self.logger.info(f"full path: {full_path}")
            self.pipeline_full_path = full_path
        else:
            self.pipeline_full_path = pipeline_path
        # set custom nodes path accordingly
        self.custom_nodes_parent_path = str(self.pipeline_full_path.parent / "src")
        self.logger.info(f"custom nodes parent: {type(self.custom_nodes_parent_path)}")
        # init internal working vars
        self.frames = []
        self.frame_idx = -1
        self.zoom_idx = ZOOM_DEFAULT_IDX
        self.is_output_playback: bool = False
        self.is_pipeline_running: bool = False
        self.state: str = "play"  # activate auto play (cf. self.timer_function)
        self.bkgd_job = None

    def run_pipeline_end(self) -> None:
        """Called when pipeline execution is completed.
        To perform clean-up/housekeeping tasks to ensure system consistency"""
        self.logger.debug("run pipeline end")
        for node in self._pipeline.nodes:
            if node.name.endswith("input.visual"):
                node.release_resources()  # clean up nodes with threads
        self.is_pipeline_running = False
        self._enable_slider()
        self.set_player_state_to_stop()
        self._set_header_stop()

    def run_pipeline_one_iteration(self) -> None:  # pylint: disable=too-many-branches
        """Run one iteration of the pipeline"""
        self.is_pipeline_running = True
        for node in self._pipeline.nodes:
            if self._pipeline.data.get("pipeline_end", False):
                self._pipeline.terminate = True
                if "pipeline_end" not in node.inputs:
                    continue
            if "all" in node.inputs:
                inputs = copy.deepcopy(self._pipeline.data)
            else:
                inputs = {
                    key: self._pipeline.data[key]
                    for key in node.inputs
                    if key in self._pipeline.data
                }
            if hasattr(node, "optional_inputs"):
                # Nodes won't receive inputs with optional key if not found upstream
                for key in node.optional_inputs:
                    if key in self._pipeline.data:
                        inputs[key] = self._pipeline.data[key]
            if node.name.endswith("output.screen"):
                # intercept screen output to Tkinter
                img = self._pipeline.data["img"]
                frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # BGR -> RGB for Tkinter
                self.frames.append(frame)  # save frame for playback
                self.frame_idx += 1
                self._show_frame()
            else:
                outputs = node.run(inputs)
                self._pipeline.data.update(outputs)
            # check for FPS on first iteration
            if self.frame_idx == 0 and node.name.endswith("input.visual"):
                num_frames = node.total_frame_count
                if num_frames > 0:
                    self.tk_progress["maximum"] = num_frames
                else:
                    self.tk_progress["mode"] = "indeterminate"
            # check if need to stop after fixed number of iterations
            if self.num_iter and self.frame_idx + 1 >= self.num_iter:
                self.logger.info(f"Stopping pipeline after {self.num_iter} iterations")
                self.stop_pipeline_run()
        # update progress bar after each iteration
        self.tk_progress["value"] = self.frame_idx
        self.tk_lbl_frame_num["text"] = self.frame_idx + 1

    def run_pipeline_start(self) -> None:
        """Run PeekingDuck's pipeline"""
        self.logger.info("run pipeline start")
        self.logger.info(f"pipeline path: {self.pipeline_path}")
        self.logger.info(f"custom_nodes: {self.custom_nodes_parent_path}")

        self._node_loader = DeclarativeLoader(
            self.pipeline_path,
            self.config_updates_cli,
            self.custom_nodes_parent_path,
        )
        self._pipeline: Pipeline = self._node_loader.get_pipeline()
        self._set_header_running()
        self.set_player_state_to_play()
        self._set_status_text(str(self.pipeline_full_path))
        self.is_pipeline_running = True
        self._enable_progress()

    def stop_pipeline_run(self) -> None:
        """Signal pipeline execution to be stopped"""
        self._pipeline.terminate = True

    ####################
    #
    # Output Playback Methods
    #
    ####################
    def start_playback(self) -> None:
        """Start output playback process"""
        self.is_output_playback = True
        # auto-rewind if at last frame
        if self.frame_idx + 1 >= len(self.frames):
            self.frame_idx = 0
            self._update_slider_and_show_frame()
        self.set_player_state_to_play()
        self._set_header_playing()
        self.do_playback()

    def do_playback(self) -> None:
        """Playback saved video frames: to be called continuously"""
        if self._forward_one_frame():
            self.tk_scale.set(self.frame_idx + 1)
        else:
            self.stop_playback()

    def stop_playback(self) -> None:
        """Stop output playback"""
        self.is_output_playback = False
        self.set_player_state_to_stop()
        self._set_header_stop()

    def set_player_state_to_play(self) -> None:
        """Set self state to play for either 1) pipeline execution or 2) playback"""
        self.state = "play"
        # if IMAGE_BUTTONS:
        #     self.tk_btn_play["image"] = self._img_stop
        # else:
        self.tk_btn_play["text"] = "Stop"

    def set_player_state_to_stop(self) -> None:
        """Set self state to stop"""
        self.state = "stop"
        # if IMAGE_BUTTONS:
        #     self.tk_btn_play["image"] = self._img_play
        # else:
        self.tk_btn_play["text"] = "Play"
