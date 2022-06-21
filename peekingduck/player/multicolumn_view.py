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

"""Implements the PlayList multi-column list view class"""

from typing import List
import tkinter.font as tkFont
import tkinter.ttk as ttk


def sort_playlist(tree: ttk.Treeview, col: str, descending: bool) -> None:
    # get values to sort
    data = [(tree.set(child, col), child) for child in tree.get_children("")]
    data.sort(reverse=descending)
    for i, item in enumerate(data):
        tree.move(item[1], "", i)
    # switch heading to sort in opposite direction
    tree.heading(col, command=lambda col=col: sort_playlist(tree, col, not descending))


class MultiColumnPlayListView(object):
    """Use ttk.TreeView as a multi-column listbox"""

    def __init__(self, data: List, header: List):
        self.tree = None
        self.data = data
        self.header = header
        self._create_tk_widgets()
        self._make_view()

    def _create_tk_widgets(self):
        container = ttk.Frame()
        container.pack(fill="both", expand=True)
        # create treeview with dual scrollbars
        self.tree = ttk.Treeview(columns=self.header, show="headings")
        vsb = ttk.Scrollbar(orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky="nsew", in_=container)
        vsb.grid(column=1, row=0, sticky="ns", in_=container)
        hsb.grid(column=0, row=1, sticky="ew", in_=container)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _make_view(self):
        font_measure = tkFont.Font().measure
        for col in self.header:
            self.tree.heading(
                col,
                text=col.title(),
                command=lambda c=col: sort_playlist(self.tree, c, False),
            )
            # fit column width
            self.tree.column(col, width=font_measure(col.title()))

        for item in self.data:
            self.tree.insert("", "end", values=item)
            # fit column width
            for i, val in enumerate(item):
                col_width = font_measure(val)
                if self.tree.column(self.header[i], width=None) < col_width:
                    self.tree.column(self.header[i], width=col_width)
