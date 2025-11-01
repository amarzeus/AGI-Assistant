from __future__ import annotations

import wx


class DashboardPanel(wx.Panel):
    """Overview dashboard panel with metrics and quick actions."""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Overview Dashboard")
        font = title.GetFont()
        font.MakeBold()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        vbox.Add(title, flag=wx.ALL, border=12)
        
        # Info text
        info = wx.StaticText(self, label="Welcome to AGI Assistant!")
        vbox.Add(info, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        
        # Metrics section
        metrics_label = wx.StaticText(self, label="Session Metrics:")
        metrics_font = metrics_label.GetFont()
        metrics_font.MakeBold()
        metrics_label.SetFont(metrics_font)
        vbox.Add(metrics_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=12)
        
        # Metrics info (updatable)
        self.metrics_info = wx.StaticText(
            self, 
            label="• Total Actions: 0\n• Patterns Detected: 0\n• Storage Used: 0 MB\n• Active Sessions: 0"
        )
        vbox.Add(self.metrics_info, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=24)
        
        vbox.AddStretchSpacer()
        
        # Quick actions
        actions_label = wx.StaticText(self, label="Quick Actions:")
        actions_font = actions_label.GetFont()
        actions_font.MakeBold()
        actions_label.SetFont(actions_font)
        vbox.Add(actions_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=12)
        
        actions_info = wx.StaticText(
            self,
            label="Use the toolbar buttons to start recording and manage your session."
        )
        vbox.Add(actions_info, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=24)
        
        self.SetSizer(vbox)


