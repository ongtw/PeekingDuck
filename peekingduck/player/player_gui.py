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
PeekingDuck Player GUI Creation Code
"""

#
# dotw technotes:
#   using __future__ and TYPE_CHECKING works with pylint 2.10.x but fails with 2.7.x
#
# from __future__ import annotations
# from typing import TYPE_CHECKING
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from peekingduck.player.player_utils import load_image
from peekingduck.player.single_column_view import SingleColumnPlayListView

# if TYPE_CHECKING:
#     from peekingduck.player.player import Player

# VIEW_TYPE = "Single"
IMAGE_BUTTONS = False
LOGO: str = "peekingduck/player/PeekingDuckLogo.png"
MIN_HEIGHT: int = 768
MIN_WIDTH: int = 1024
WIN_HEIGHT: int = 960
WIN_WIDTH: int = 1280
# Emojis
# IMG_PLAYLIST: str = "peekingduck/player/btn_playlist.png"
# IMG_PLAY: str = "peekingduck/player/btn_play.png"
# IMG_STOP: str = "peekingduck/player/btn_stop.png"
# IMG_ZOOM_IN: str = "peekingduck/player/btn_zoom_in.png"
# IMG_ZOOM_OUT: str = "peekingduck/player/btn_zoom_out.png"


#
# Tk GUI Main Window Creation Code
#
def gui_create_window(player) -> None:  # type: ignore
    """Create the PeekingDuck Player Tkinter window and frames"""
    root = tk.Tk()
    root.wm_protocol("WM_DELETE_WINDOW", player.on_exit)
    root.title("PeekingDuck Player")
    # bind event handlers
    root.bind("<Configure>", player.resize)
    root.bind("<Key>", player.on_keypress)
    root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
    root.update()  # force update without mainloop() to get correct size
    root.minsize(MIN_WIDTH, MIN_HEIGHT)
    player.root = root  # save main window
    #
    # dotw technote: need to create footer before body to ensure the footer
    #                controls do not get covered when image is zoomed in
    #
    gui_create_header(player)
    gui_create_footer(player)
    gui_create_body(player)


#
# Window Components
# - Header
# - Body
# - Footer
#
def gui_create_header(player) -> None:  # type: ignore
    """Create header with logo and pipeline info text"""
    header_frm = ttk.Frame(master=player.root, name="header")
    header_frm.pack(side=tk.TOP, fill=tk.X)
    # header top padding
    lbl = tk.Label(header_frm, text="")
    lbl.grid(row=0, column=0)
    # header contents
    logo_path = Path(LOGO)
    player.logger.debug(f"logo={logo_path}, exists={logo_path.exists()}")
    player.img_logo = load_image(LOGO, resize_pct=0.10)  # prevent python GC
    logo = tk.Label(header_frm, image=player.img_logo)
    logo.grid(row=1, column=0, sticky="nsew")
    player.tk_logo = logo
    for i in range(2):
        dummy = tk.Label(header_frm, text="")
        dummy.grid(row=1, column=i + 2, sticky="nsew")
    lbl = tk.Label(header_frm, text="PeekingDuck Player Header", font=("arial 20"))
    lbl.grid(row=1, column=1, columnspan=3, sticky="nsew")
    player.tk_lbl_header = lbl
    # spacer
    lbl_blank = tk.Label(header_frm, text="")
    lbl_blank.grid(row=1, column=4)
    # configure expansion and uniform column sizes
    num_col, _ = header_frm.grid_size()
    for i in range(num_col):
        header_frm.grid_columnconfigure(i, weight=1, uniform="tag")
    player.header_frm = header_frm  # save header frame


def gui_create_body(player) -> None:  # type: ignore
    """Create body with left video image and right playlist"""
    body_frm = ttk.Frame(master=player.root)
    body_frm.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=40)
    player.tk_body_frm = body_frm

    lbl = tk.Label(body_frm, text="")  # spacer above body
    lbl.pack(side=tk.TOP)
    lbl = tk.Label(body_frm, text="")  # spacer below body
    lbl.pack(side=tk.BOTTOM)

    # playlist frame (right)
    playlist_frm = ttk.Frame(
        master=body_frm, name="playlist", relief=tk.RIDGE, borderwidth=1
    )
    # playlist_frm = ttk.Frame(master=body_frm, name="playlist")
    playlist_frm.pack(side=tk.RIGHT, fill=tk.Y)
    player.tk_playlist_frm = playlist_frm

    # if VIEW_TYPE == "Single":
    player.tk_playlist_view = SingleColumnPlayListView(
        playlist=player.playlist, root=playlist_frm
    )
    player.tk_playlist_view.register_callback("add", player.on_add_pipeline)
    player.tk_playlist_view.register_callback("delete", player.on_delete_pipeline)
    player.tk_playlist_view.register_callback("play", player.on_play_pipeline)

    # if VIEW_TYPE == "Multi":
    #     player.tk_playlist_view = MultiColumnPlayListView()

    player.playlist_show = True
    # image (left)
    image_frm = ttk.Frame(master=body_frm, name="image")
    image_frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    output_image = tk.Label(image_frm)
    output_image.pack(fill=tk.BOTH, expand=True)
    player.tk_output_image = output_image
    player.image_frm = image_frm

    player.btn_hide_show_playlist_press()  # first toggle to hide playlist


def gui_create_footer(player) -> None:  # type: ignore
    """Create footer with progress bar/slider and control buttons"""
    # info and controls
    footer_frm = ttk.Frame(master=player.root, name="footer")
    footer_frm.pack(side=tk.BOTTOM, fill=tk.X)
    player.footer_frm = footer_frm  # save footer frame
    gui_create_progress_slider(player)
    gui_create_control_buttons(player)
    lbl = tk.Label(footer_frm, text="")  # spacer between controls from statusbar
    lbl.pack(side=tk.TOP)
    gui_create_statusbar(player)
    lbl = tk.Label(footer_frm, text="")  # spacer below footer
    lbl.pack(side=tk.TOP)


#
# Footer Components
# - Control buttons
# - Progress bar / Slider
# - Status bar
#
def gui_create_control_buttons(player) -> None:  # type: ignore
    """Create buttons"""
    controls_frm = ttk.Frame(master=player.footer_frm, name="controls")
    controls_frm.pack(side=tk.TOP, fill=tk.X)
    player.controls_frm = controls_frm  # save controls frame

    # player._img_playlist = load_image(IMG_PLAYLIST, resize_pct=0.1)
    # player._img_play = load_image(IMG_PLAY, resize_pct=0.1)
    # player._img_stop = load_image(IMG_STOP, resize_pct=0.1)
    # player._img_zoom_in = load_image(IMG_ZOOM_IN, resize_pct=0.1)
    # player._img_zoom_out = load_image(IMG_ZOOM_OUT, resize_pct=0.1)

    btn_play = ttk.Button(
        controls_frm,
        text="Play",
        command=player.btn_play_stop_press,
    )
    player.tk_btn_play = btn_play
    player.tk_btn_play.grid(row=0, column=1, sticky="ns")

    #
    # zoom: - / zoom_factor / +
    # zoom out button
    #
    btn_zoom_out = ttk.Button(
        controls_frm,
        text="-",
        command=player.btn_zoom_out_press,
    )
    player.tk_btn_zoom_out = btn_zoom_out
    player.tk_btn_zoom_out.grid(row=0, column=5, sticky="ns")
    # zoom factor number
    player.tk_lbl_zoom = tk.Label(controls_frm, text="1.0")
    player.tk_lbl_zoom.grid(row=0, column=6, sticky="ns")
    # zoom in button
    btn_zoom_in = ttk.Button(
        controls_frm,
        text="+",
        command=player.btn_zoom_in_press,
    )
    player.tk_btn_zoom_in = btn_zoom_in
    player.tk_btn_zoom_in.grid(row=0, column=7, sticky="ns")

    # hide/show playlist button
    btn_hide_show_playlist = ttk.Button(
        controls_frm, text="Playlist", command=player.btn_hide_show_playlist_press
    )
    player.btn_hide_show_playlist = btn_hide_show_playlist
    player.btn_hide_show_playlist.grid(row=0, column=8, sticky="ns")

    lbl = tk.Label(controls_frm, text="")  # spacer
    lbl.grid(row=0, column=9)

    # configure expansion and uniform column sizes
    num_col, _ = controls_frm.grid_size()
    for i in range(num_col):
        controls_frm.grid_columnconfigure(i, weight=1, uniform="tag")


def gui_create_progress_slider(player) -> None:  # type: ignore
    """Create progress bar and slider overlaid on each other"""
    info_frm = ttk.Frame(master=player.footer_frm, name="info")
    info_frm.pack(side=tk.TOP, fill=tk.X)
    # slider
    player.tk_scale = ttk.Scale(
        info_frm,
        orient=tk.HORIZONTAL,
        from_=1,
        to=100,
        command=player.sync_slider_to_frame,
    )
    player.tk_scale.grid(row=0, column=1, columnspan=7, sticky="nsew")
    player.tk_scale.grid_remove()  # hide it first
    # progress bar
    player.tk_progress = ttk.Progressbar(
        info_frm,
        orient=tk.HORIZONTAL,
        length=100,
        mode="determinate",
        value=0,
        maximum=100,
    )
    player.tk_progress.grid(row=0, column=1, columnspan=7, sticky="nsew")
    # frame number
    player.tk_lbl_frame_num = tk.Label(info_frm, text="0")
    player.tk_lbl_frame_num.grid(row=0, column=8)

    lbl = tk.Label(info_frm, text="")  # spacer
    lbl.grid(row=0, column=9)

    # configure expansion and uniform column sizes
    num_col, _ = info_frm.grid_size()
    for i in range(num_col):
        info_frm.grid_columnconfigure(i, weight=1, uniform="tag")
    player.info_frm = info_frm  # save info frame


def gui_create_statusbar(player) -> None:  # type: ignore
    """Create status bar at bottom of window"""
    status_frm = ttk.Frame(master=player.footer_frm, name="status")
    status_frm.pack(side=tk.TOP, fill=tk.X)
    lbl = tk.Label(status_frm, text="")  # spacer
    lbl.grid(row=0, column=0)
    player.status_bar = tk.Label(
        master=status_frm,
        anchor=tk.W,
        text="This is the PeekingDuck Player status bar",
    )
    player.status_bar.grid(row=0, column=1, columnspan=8, sticky="we")
    lbl = tk.Label(status_frm, text="")  # spacer
    lbl.grid(row=0, column=9)
    # configure expansion and uniform column sizes
    num_col, _ = status_frm.grid_size()
    for i in range(num_col):
        status_frm.grid_columnconfigure(i, weight=1, uniform="tag")
    player.status_frm = status_frm
