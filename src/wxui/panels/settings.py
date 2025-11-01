from __future__ import annotations

import wx


class SettingsPanel(wx.Panel):
    """Settings panel for application configuration."""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        vbox = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Settings")
        font = title.GetFont()
        font.MakeBold()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        vbox.Add(title, flag=wx.ALL, border=12)

        # Capture settings
        capture_box = wx.StaticBox(self, label="Capture Settings")
        capture_sizer = wx.StaticBoxSizer(capture_box, wx.VERTICAL)
        
        form = wx.FlexGridSizer(0, 2, 8, 12)
        form.AddGrowableCol(1, 1)

        form.Add(wx.StaticText(self, label="Screenshot Interval (seconds):"))
        self.interval = wx.SpinCtrl(self, min=1, max=60, initial=3)
        form.Add(self.interval, flag=wx.EXPAND)

        form.Add(wx.StaticText(self, label="Enable Screen Capture:"))
        self.chk_screen = wx.CheckBox(self)
        self.chk_screen.SetValue(True)
        form.Add(self.chk_screen)

        capture_sizer.Add(form, flag=wx.EXPAND | wx.ALL, border=8)
        vbox.Add(capture_sizer, flag=wx.EXPAND | wx.ALL, border=12)

        # Audio settings
        audio_box = wx.StaticBox(self, label="Audio Settings")
        audio_sizer = wx.StaticBoxSizer(audio_box, wx.VERTICAL)
        
        audio_form = wx.FlexGridSizer(0, 2, 8, 12)
        audio_form.AddGrowableCol(1, 1)

        audio_form.Add(wx.StaticText(self, label="Sample Rate (Hz):"))
        self.sample_rate = wx.SpinCtrl(self, min=8000, max=48000, initial=16000)
        audio_form.Add(self.sample_rate, flag=wx.EXPAND)

        audio_form.Add(wx.StaticText(self, label="Enable Audio Transcription:"))
        self.chk_transcription = wx.CheckBox(self)
        self.chk_transcription.SetValue(True)
        audio_form.Add(self.chk_transcription)

        audio_sizer.Add(audio_form, flag=wx.EXPAND | wx.ALL, border=8)
        vbox.Add(audio_sizer, flag=wx.EXPAND | wx.ALL, border=12)

        # Storage settings
        storage_box = wx.StaticBox(self, label="Storage Settings")
        storage_sizer = wx.StaticBoxSizer(storage_box, wx.VERTICAL)
        
        storage_form = wx.FlexGridSizer(0, 2, 8, 12)
        storage_form.AddGrowableCol(1, 1)

        storage_form.Add(wx.StaticText(self, label="Storage Limit (GB):"))
        self.storage_limit = wx.SpinCtrl(self, min=1, max=1000, initial=10)
        storage_form.Add(self.storage_limit, flag=wx.EXPAND)

        storage_sizer.Add(storage_form, flag=wx.EXPAND | wx.ALL, border=8)
        vbox.Add(storage_sizer, flag=wx.EXPAND | wx.ALL, border=12)

        vbox.AddStretchSpacer()

        # Action buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_save = wx.Button(self, label="Save Settings")
        self.btn_reset = wx.Button(self, label="Reset to Defaults")
        btn_sizer.Add(self.btn_save)
        btn_sizer.Add(self.btn_reset, flag=wx.LEFT, border=6)
        vbox.Add(btn_sizer, flag=wx.ALL, border=12)

        self.SetSizer(vbox)
        
        # Bind events
        self.btn_save.Bind(wx.EVT_BUTTON, self._on_save)
        self.btn_reset.Bind(wx.EVT_BUTTON, self._on_reset)
    
    def _on_save(self, evt: wx.CommandEvent) -> None:
        """Handle save button click."""
        try:
            from src.config import get_config, set_config
            
            config = get_config()
            
            # Update config values
            config.screen_capture.screenshot_interval = self.interval.GetValue()
            config.audio.sample_rate = self.sample_rate.GetValue()
            config.audio.enabled = self.chk_transcription.GetValue()
            config.storage.max_storage_gb = self.storage_limit.GetValue()
            
            # Save config
            set_config(config)
            
            # Update storage manager if available
            parent = self.GetParent()
            while parent and not hasattr(parent, '_storage_manager'):
                parent = parent.GetParent()
            
            if parent and hasattr(parent, '_storage_manager') and parent._storage_manager:
                parent._storage_manager.set_storage_limit(self.storage_limit.GetValue())
            
            settings = {
                "interval": self.interval.GetValue(),
                "screen_capture": self.chk_screen.GetValue(),
                "sample_rate": self.sample_rate.GetValue(),
                "transcription": self.chk_transcription.GetValue(),
                "storage_limit": self.storage_limit.GetValue(),
            }
            
            msg = f"Settings saved:\n\n"
            msg += f"Screenshot Interval: {settings['interval']}s\n"
            msg += f"Screen Capture: {'Enabled' if settings['screen_capture'] else 'Disabled'}\n"
            msg += f"Sample Rate: {settings['sample_rate']} Hz\n"
            msg += f"Transcription: {'Enabled' if settings['transcription'] else 'Disabled'}\n"
            msg += f"Storage Limit: {settings['storage_limit']} GB"
            wx.MessageBox(msg, "Settings Saved", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Failed to save settings:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)
    
    def _on_reset(self, evt: wx.CommandEvent) -> None:
        """Handle reset button click."""
        dlg = wx.MessageDialog(
            self,
            "Reset all settings to defaults?",
            "Confirm Reset",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            try:
                from src.config import get_config
                config = get_config()
                
                # Reset to defaults
                self.interval.SetValue(config.screen_capture.screenshot_interval)
                self.chk_screen.SetValue(True)
                self.sample_rate.SetValue(config.audio.sample_rate)
                self.chk_transcription.SetValue(config.audio.enabled)
                self.storage_limit.SetValue(config.storage.max_storage_gb)
                
                wx.MessageBox("Settings reset to defaults.", "Reset", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                # Fallback defaults
                self.interval.SetValue(3)
                self.chk_screen.SetValue(True)
                self.sample_rate.SetValue(16000)
                self.chk_transcription.SetValue(True)
                self.storage_limit.SetValue(10)
                wx.MessageBox("Settings reset to defaults.", "Reset", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()


