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

"""Implements the PlayList single-column list view class"""

from typing import Callable, Dict, Union
import logging
import tkinter as tk
from tkinter import ttk
from peekingduck.player.playlist import PipelineStats, PlayList

# Emoji's
DOWN_ARROW = "\u2B07"
UP_ARROW = "\u2B06"
SKULL = "\U0001F480"
THUMBS_UP = "\U0001F44D"

# Supported GUI operations
OP_LIST = ["add", "delete", "play"]


class SingleColumnPlayListView:  # pylint: disable=too-few-public-methods, too-many-instance-attributes
    """Use tk.ListBox as single-column list view"""

    def __init__(self, playlist: PlayList, root: tk.Widget):
        self.logger = logging.getLogger(__name__)
        self.playlist = playlist
        self.root = root
        self.view = None
        self._callback: Dict[str, Callable] = {}
        self._selected: Union[None, str] = None
        self._sort_desc = False
        self._create_tk_widgets()
        self._redraw_view()

    def _change_sort_order(
        self, event: tk.Event  # pylint: disable=unused-argument
    ) -> None:
        self._sort_desc = not self._sort_desc
        self._redraw_view()
        self._show_selected()

    def _create_tk_widgets(self) -> None:
        """Create Tk widgets for the GUI view"""
        lbl = tk.Label(self.root, text="Pipelines:")
        lbl.pack(side=tk.TOP)
        lbl.bind("<Button-1>", self._change_sort_order)
        self.header = lbl

        # playlist controls
        playlist_ctrl_frm = ttk.Frame(master=self.root, name="playlist_ctrl")
        playlist_ctrl_frm.pack(side=tk.BOTTOM)

        # if IMAGE_BUTTONS:
        #     btn_add = tk.Button(playlist_ctrl_frm, text="+")
        #     btn_delete = tk.Button(playlist_ctrl_frm, text="-")
        #     btn_edit = tk.Button(playlist_ctrl_frm, text="Edit")
        # else:
        self._btn_add = ttk.Button(playlist_ctrl_frm, text="+")
        self._btn_delete = ttk.Button(playlist_ctrl_frm, text="-")
        self._btn_play = ttk.Button(playlist_ctrl_frm, text="Play")
        # dotw technotes:
        # - if bind to Button (mouse down) event,
        #   the Play button will be "stuck" and show button down style (blue on macOS)
        #   when it is clicked on.
        # - binding to ButtonRelease (mouse up) event solves above issue
        self._btn_add.bind("<ButtonRelease-1>", self.btn_add_press)
        self._btn_delete.bind("<ButtonRelease-1>", self.btn_delete_press)
        self._btn_play.bind("<ButtonRelease-1>", self.btn_play_press)
        for child in playlist_ctrl_frm.winfo_children():
            child.pack(side=tk.LEFT)  # pack above buttons

        # info panel
        info_frm = ttk.Frame(master=self.root, name="playlist_info")
        info_frm.pack(side=tk.BOTTOM, fill=tk.X)
        lbl = tk.Label(info_frm, text="Pipeline Information:")
        lbl.pack(side=tk.TOP)

        info_labels = ttk.Frame(master=info_frm)
        info_labels.pack(side=tk.LEFT, anchor=tk.N)
        lbl = tk.Label(info_labels, text="Name")
        lbl = tk.Label(info_labels, text="Date Time")
        lbl = tk.Label(info_labels, text="Path")
        for child in info_labels.winfo_children():
            child.pack(side=tk.TOP, anchor=tk.E)  # pack above 4 labels

        info_details = ttk.Frame(master=info_frm)
        info_details.pack(side=tk.RIGHT, anchor=tk.N, fill=tk.X, expand=True)
        self._info_name = tk.Label(info_details, text="name")
        self._info_datetime = tk.Label(info_details, text="datetime")
        self._info_path = tk.Message(info_details, text="path", width=200)
        for child in info_details.winfo_children():
            child.pack(side=tk.TOP, anchor=tk.W)  # pack above 4 labels

        # listbox
        playlist_listbox = tk.Listbox(
            master=self.root, relief=tk.RIDGE, borderwidth=1, height=20
        )
        playlist_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        playlist_listbox.bind("<<ListboxSelect>>", self._selection_changed)
        self.tk_listbox = playlist_listbox

    def _redraw_view(self) -> None:
        """Populate playlist contents"""
        self.sorted_playlist = sorted(self.playlist, reverse=self._sort_desc)
        self._pipeline_to_index_map: Dict[str, int] = {}
        self._index_to_stats_map: Dict[int, PipelineStats] = {}
        self.tk_listbox.delete(0, tk.END)
        for i, stats in enumerate(self.sorted_playlist):
            self._pipeline_to_index_map[stats.pipeline] = i
            self._index_to_stats_map[i] = stats
            display_name = (
                f"{THUMBS_UP} {stats.name}"
                if stats.datetime
                else f"{SKULL} {stats.name}"
            )
            self.tk_listbox.insert(i, display_name)
        self.header[
            "text"
        ] = f"Pipelines: {DOWN_ARROW if self._sort_desc else UP_ARROW}"

    def _get_selected_index(self) -> int:
        """Return index of selected listbox entry

        Returns:
            int: Index of selected entry
        """
        selection_indices = self.tk_listbox.curselection()
        i = selection_indices[0]  # only want first selection
        return i

    def _selection_changed(
        self, event: tk.Event  # pylint: disable=unused-argument
    ) -> None:
        """Update pipeline info when user selects a pipeline in playlist

        Args:
            event (tk.Event): Tk event object
        """
        i = self._get_selected_index()
        self._show_pipeline_info(i)

    def _show_pipeline_info(self, i: int) -> None:
        """Update pipeline info panel details"""
        stats = self._index_to_stats_map[i]
        self.logger.info(f"show stats[{i}]: {stats.name}")
        self._info_name["text"] = stats.name
        if stats.datetime:
            display_datetime = f"{stats.datetime} {THUMBS_UP}"
        else:
            display_datetime = f"{SKULL}"
        self._info_datetime["text"] = display_datetime
        self._info_path["text"] = stats.pipeline

    def _show_selected(self) -> None:
        """Highlight select pipeline with stats"""
        if self._selected:
            i = self._pipeline_to_index_map[self._selected]
            self.tk_listbox.select_set(i)
            self._show_pipeline_info(i)

    def register_callback(self, operation: str, player_callback: Callable) -> None:
        """Register callback function in Player to be called when playlist events are generated

        Args:
            operation (str): One of [ "add", "delete", "play" ]
            player_callback (Callable): The hook to the Player
        """
        if operation in OP_LIST:
            self._callback[operation] = player_callback
        else:
            raise ValueError(f"Unsupported callback operation: {operation}")

    def reset(self) -> None:
        """Force widget to recalculate width based on contents"""
        self.tk_listbox.config(width=0)

    def select(self, pipeline: str) -> None:
        """Select given pipeline on the GUI

        Args:
            pipeline (str): Pipeline to select.
        """
        self._selected = pipeline
        self._show_selected()

    #
    # Button callbacks
    #
    def btn_add_press(self, event: tk.Event) -> None:  # pylint: disable=unused-argument
        """Callback to handle "+" button

        Args:
            event (tk.Event): Tk event object
        """
        self.logger.info("btn_add_press")
        if self._callback["add"]():
            self._redraw_view()

    def btn_delete_press(
        self, event: tk.Event  # pylint: disable=unused-argument
    ) -> None:
        """Callback to handle "-" button

        Args:
            event (tk.Event): Tk event object
        """
        i = self._get_selected_index()
        stats = self._index_to_stats_map[i]
        self.logger.info(f"btn_delete_press: {stats.pipeline}")
        if self._callback["delete"](pipeline=stats.pipeline):
            self._redraw_view()

    def btn_play_press(
        self, event: tk.Event  # pylint: disable=unused-argument
    ) -> None:
        """Callback to handle "Play" button

        Args:
            event (tk.Event): Tk event object
        """
        i = self._get_selected_index()
        stats = self._index_to_stats_map[i]
        self.logger.info(f"btn_play_press: {stats.pipeline}")
        self._callback["play"](pipeline=stats.pipeline)
