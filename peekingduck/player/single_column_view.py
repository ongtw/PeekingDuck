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

import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk
from peekingduck.player.playlist import PlayList


class SingleColumnPlayListView(object):
    """Use tk.ListBox as single-column list view"""

    def __init__(self, playlist: PlayList, root: tk.Widget):
        self.playlist = playlist
        self.root = root
        self.view = None
        self._create_tk_widgets()
        self._make_view()

    def _create_tk_widgets(self):
        """Create Tk widgets for the GUI view"""
        lbl = tk.Label(self.root, text="List of Pipelines:")
        lbl.pack(side=tk.TOP)

        # playlist controls
        playlist_ctrl_frm = ttk.Frame(master=self.root, name="playlist_ctrl")
        playlist_ctrl_frm.pack(side=tk.BOTTOM)

        # if IMAGE_BUTTONS:
        #     btn_add = tk.Button(playlist_ctrl_frm, text="+")
        #     btn_delete = tk.Button(playlist_ctrl_frm, text="-")
        #     btn_edit = tk.Button(playlist_ctrl_frm, text="Edit")
        # else:
        btn_add = ttk.Button(playlist_ctrl_frm, text="+")
        btn_delete = ttk.Button(playlist_ctrl_frm, text="-")
        btn_edit = ttk.Button(playlist_ctrl_frm, text="Edit")

        btn_add.pack(side=tk.LEFT)
        btn_delete.pack(side=tk.LEFT)
        btn_edit.pack(side=tk.LEFT)

        # listbox
        playlist_listbox = tk.Listbox(
            master=self.root, relief=tk.RIDGE, borderwidth=1, height=20
        )
        playlist_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tk_playlist = playlist_listbox

    def _make_view(self):
        """Populate view with playlist contents"""
        for i, pipeline in enumerate(sorted(self.playlist)):
            stats = self.playlist.get_stats(pipeline)
            self.tk_playlist.insert(i, stats)

    def reset(self):
        self.tk_playlist.config(width=0)
