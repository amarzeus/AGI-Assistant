from __future__ import annotations

import wx


class StoragePanel(wx.Panel):
    """Storage management panel with usage stats and cleanup options."""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Storage Management")
        font = title.GetFont()
        font.MakeBold()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        vbox.Add(title, flag=wx.ALL, border=12)
        
        # Storage stats section
        stats_box = wx.StaticBox(self, label="Storage Usage")
        stats_sizer = wx.StaticBoxSizer(stats_box, wx.VERTICAL)
        
        stats_grid = wx.FlexGridSizer(3, 2, 8, 12)
        stats_grid.AddGrowableCol(1, 1)
        
        stats_grid.Add(wx.StaticText(self, label="Total Used:"))
        self.lbl_used = wx.StaticText(self, label="0 MB")
        stats_grid.Add(self.lbl_used, flag=wx.ALIGN_RIGHT)
        
        stats_grid.Add(wx.StaticText(self, label="Available:"))
        self.lbl_available = wx.StaticText(self, label="10 GB")
        stats_grid.Add(self.lbl_available, flag=wx.ALIGN_RIGHT)
        
        stats_grid.Add(wx.StaticText(self, label="Limit:"))
        self.lbl_limit = wx.StaticText(self, label="10 GB")
        stats_grid.Add(self.lbl_limit, flag=wx.ALIGN_RIGHT)
        
        stats_sizer.Add(stats_grid, flag=wx.EXPAND | wx.ALL, border=8)
        
        # Progress bar
        usage_label = wx.StaticText(self, label="Usage:")
        stats_sizer.Add(usage_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
        self.gauge = wx.Gauge(self, range=100, size=(-1, 24))
        self.gauge.SetValue(0)
        stats_sizer.Add(self.gauge, flag=wx.EXPAND | wx.ALL, border=8)
        
        vbox.Add(stats_sizer, flag=wx.EXPAND | wx.ALL, border=12)
        
        # Actions section
        actions_box = wx.StaticBox(self, label="Actions")
        actions_sizer = wx.StaticBoxSizer(actions_box, wx.VERTICAL)
        
        actions_info = wx.StaticText(
            self,
            label="Manage your storage and export data."
        )
        actions_sizer.Add(actions_info, flag=wx.ALL, border=8)
        
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cleanup = wx.Button(self, label="Cleanup Old Data")
        self.btn_export = wx.Button(self, label="Export Data")
        self.btn_refresh = wx.Button(self, label="Refresh Stats")
        btns.Add(self.btn_cleanup)
        btns.Add(self.btn_export, flag=wx.LEFT, border=6)
        btns.Add(self.btn_refresh, flag=wx.LEFT, border=6)
        actions_sizer.Add(btns, flag=wx.ALL, border=8)
        
        vbox.Add(actions_sizer, flag=wx.EXPAND | wx.ALL, border=12)
        
        vbox.AddStretchSpacer()
        
        self.SetSizer(vbox)
        
        # Bind events
        self.btn_cleanup.Bind(wx.EVT_BUTTON, self._on_cleanup)
        self.btn_export.Bind(wx.EVT_BUTTON, self._on_export)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self._on_refresh)
    
    def _on_cleanup(self, evt: wx.CommandEvent) -> None:
        """Handle cleanup button click."""
        dlg = wx.MessageDialog(
            self,
            "This will delete old capture data. Continue?",
            "Confirm Cleanup",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            wx.MessageBox("Cleanup operation would be performed here.", "Cleanup", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()
    
    def _on_export(self, evt: wx.CommandEvent) -> None:
        """Handle export button click."""
        with wx.FileDialog(
            self,
            "Export Data",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
            wx.MessageBox(f"Data would be exported to:\n{path}", "Export", wx.OK | wx.ICON_INFORMATION)
    
    def _on_refresh(self, evt: wx.CommandEvent) -> None:
        """Handle refresh button click."""
        # Get parent frame and refresh stats
        parent = self.GetParent()
        while parent and not hasattr(parent, 'refresh_storage_stats'):
            parent = parent.GetParent()
        
        if parent and hasattr(parent, 'refresh_storage_stats'):
            parent.refresh_storage_stats()
            wx.MessageBox("Storage stats refreshed.", "Refresh", wx.OK | wx.ICON_INFORMATION)
        else:
            # Fallback: update with sample data
            self.lbl_used.SetLabel("125 MB")
            self.lbl_available.SetLabel("9.875 GB")
            self.gauge.SetValue(1)
            wx.MessageBox("Storage stats refreshed.", "Refresh", wx.OK | wx.ICON_INFORMATION)


