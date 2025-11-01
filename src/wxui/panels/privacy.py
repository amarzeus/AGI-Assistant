from __future__ import annotations

import wx
from datetime import datetime


class PrivacyPanel(wx.Panel):
    """Privacy and session management panel."""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        vbox = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Privacy & Sessions")
        font = title.GetFont()
        font.MakeBold()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        vbox.Add(title, flag=wx.ALL, border=12)

        # Privacy info
        info_box = wx.StaticBox(self, label="Privacy Information")
        info_sizer = wx.StaticBoxSizer(info_box, wx.VERTICAL)
        
        privacy_text = wx.StaticText(
            self,
            label="All data is stored locally on your machine. No data is sent to external servers.\n"
                  "You can delete individual sessions or all data at any time."
        )
        info_sizer.Add(privacy_text, flag=wx.EXPAND | wx.ALL, border=8)
        vbox.Add(info_sizer, flag=wx.EXPAND | wx.ALL, border=12)

        # Sessions list
        sessions_box = wx.StaticBox(self, label="Recording Sessions")
        sessions_sizer = wx.StaticBoxSizer(sessions_box, wx.VERTICAL)
        
        self.table = wx.ListCtrl(
            self, 
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_THEME
        )
        self.table.InsertColumn(0, "Session ID", width=200)
        self.table.InsertColumn(1, "Started", width=140)
        self.table.InsertColumn(2, "Duration", width=100)
        self.table.InsertColumn(3, "Actions", width=80)
        self.table.InsertColumn(4, "Status", width=100)
        sessions_sizer.Add(self.table, 1, wx.EXPAND | wx.ALL, 8)
        
        # Buttons
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_view = wx.Button(self, label="View Details")
        self.btn_delete = wx.Button(self, label="Delete Session")
        self.btn_refresh = wx.Button(self, label="Refresh")
        self.btn_delete_all = wx.Button(self, label="Delete All Data")
        btns.Add(self.btn_view)
        btns.Add(self.btn_delete, flag=wx.LEFT, border=6)
        btns.Add(self.btn_refresh, flag=wx.LEFT, border=6)
        btns.AddStretchSpacer()
        btns.Add(self.btn_delete_all, flag=wx.LEFT, border=6)
        sessions_sizer.Add(btns, flag=wx.EXPAND | wx.ALL, border=8)
        
        vbox.Add(sessions_sizer, 1, wx.EXPAND | wx.ALL, border=12)

        self.SetSizer(vbox)
        
        # Add sample session
        self._add_sample_session()
        
        # Bind events
        self.btn_view.Bind(wx.EVT_BUTTON, self._on_view)
        self.btn_delete.Bind(wx.EVT_BUTTON, self._on_delete)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self._on_refresh)
        self.btn_delete_all.Bind(wx.EVT_BUTTON, self._on_delete_all)
    
    def _add_sample_session(self):
        """Add sample session for demonstration."""
        idx = self.table.InsertItem(0, "abc123...")
        self.table.SetItem(0, 1, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.table.SetItem(0, 2, "00:05:23")
        self.table.SetItem(0, 3, "42")
        self.table.SetItem(0, 4, "Active")
    
    def _on_view(self, evt: wx.CommandEvent) -> None:
        """Handle view button click."""
        if self.table.GetSelectedItemCount() == 0:
            wx.MessageBox("Please select a session first.", "No Selection", wx.OK | wx.ICON_WARNING)
            return
        
        idx = self.table.GetFirstSelected()
        session_id = self.table.GetItemText(idx, 0)
        wx.MessageBox(
            f"Session Details:\n\n"
            f"ID: {session_id}\n"
            f"Started: {self.table.GetItemText(idx, 1)}\n"
            f"Duration: {self.table.GetItemText(idx, 2)}\n"
            f"Actions: {self.table.GetItemText(idx, 3)}\n"
            f"Status: {self.table.GetItemText(idx, 4)}",
            "Session Details",
            wx.OK | wx.ICON_INFORMATION
        )
    
    def _on_delete(self, evt: wx.CommandEvent) -> None:
        """Handle delete button click."""
        if self.table.GetSelectedItemCount() == 0:
            wx.MessageBox("Please select a session to delete.", "No Selection", wx.OK | wx.ICON_WARNING)
            return
        
        dlg = wx.MessageDialog(
            self,
            "Delete selected session? This cannot be undone.",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_WARNING
        )
        if dlg.ShowModal() == wx.ID_YES:
            idx = self.table.GetFirstSelected()
            self.table.DeleteItem(idx)
            wx.MessageBox("Session deleted.", "Delete", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()
    
    def _on_refresh(self, evt: wx.CommandEvent) -> None:
        """Handle refresh button click."""
        # Get parent frame and refresh sessions
        parent = self.GetParent()
        while parent and not hasattr(parent, 'refresh_sessions'):
            parent = parent.GetParent()
        
        if parent and hasattr(parent, 'refresh_sessions'):
            parent.refresh_sessions()
            wx.MessageBox("Sessions refreshed.", "Refresh", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("Sessions refreshed.", "Refresh", wx.OK | wx.ICON_INFORMATION)
    
    def _on_delete_all(self, evt: wx.CommandEvent) -> None:
        """Handle delete all button click."""
        dlg = wx.MessageDialog(
            self,
            "Delete ALL data? This will permanently remove all sessions and cannot be undone!",
            "Confirm Delete All",
            wx.YES_NO | wx.ICON_ERROR
        )
        if dlg.ShowModal() == wx.ID_YES:
            self.table.DeleteAllItems()
            wx.MessageBox("All data deleted.", "Delete All", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()


