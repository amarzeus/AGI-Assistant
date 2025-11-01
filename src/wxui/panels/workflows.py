from __future__ import annotations

import wx

from src.logger import get_app_logger


class WorkflowsPanel(wx.Panel):
    """Workflow patterns panel with detection and automation controls."""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.logger = get_app_logger()
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # Left: pattern list
        left_box = wx.StaticBox(self, label="Detected Patterns")
        left_sizer = wx.StaticBoxSizer(left_box, wx.VERTICAL)
        
        # Search/filter
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filter_sizer.Add(wx.StaticText(self, label="Filter:"), flag=wx.ALIGN_CENTER_VERTICAL)
        self.filter_text = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        filter_sizer.Add(self.filter_text, 1, wx.EXPAND | wx.LEFT, 6)
        left_sizer.Add(filter_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        
        self.list = wx.ListCtrl(
            self, 
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_THEME
        )
        self.list.InsertColumn(0, "Pattern Name", width=200)
        self.list.InsertColumn(1, "Frequency", width=80)
        self.list.InsertColumn(2, "Confidence", width=100)
        self.list.InsertColumn(3, "Last Seen", width=120)
        left_sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        
        hbox.Add(left_sizer, 1, wx.EXPAND | wx.ALL, 6)

        # Right: details panel
        right_box = wx.StaticBox(self, label="Pattern Details")
        right_sizer = wx.StaticBoxSizer(right_box, wx.VERTICAL)
        
        self.details_title = wx.StaticText(self, label="Select a pattern to view details")
        font = self.details_title.GetFont()
        font.MakeBold()
        self.details_title.SetFont(font)
        right_sizer.Add(self.details_title, flag=wx.ALL, border=8)
        
        self.details_text = wx.TextCtrl(
            self, 
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.BORDER_SUNKEN
        )
        self.details_text.SetValue("Select a pattern from the list to see detailed information, steps, and automation suggestions.")
        right_sizer.Add(self.details_text, 1, wx.EXPAND | wx.ALL, 8)
        
        # Metrics
        metrics = wx.StaticText(self, label="Time Saved: 0 min\nComplexity: Low")
        right_sizer.Add(metrics, flag=wx.ALL, border=8)
        
        # Parameters section
        params_box = wx.StaticBox(self, label="Workflow Parameters")
        params_sizer = wx.StaticBoxSizer(params_box, wx.VERTICAL)
        
        self.params_panel = wx.Panel(self)
        self.params_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.params_panel.SetSizer(self.params_panel_sizer)
        
        self.param_controls = {}  # Store parameter input controls
        
        params_sizer.Add(self.params_panel, 1, wx.EXPAND | wx.ALL, 8)
        right_sizer.Add(params_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        
        # Improvement suggestions section
        suggestions_box = wx.StaticBox(self, label="Improvement Suggestions")
        suggestions_sizer = wx.StaticBoxSizer(suggestions_box, wx.VERTICAL)
        
        self.suggestions_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.BORDER_SUNKEN,
            size=(-1, 80)
        )
        self.suggestions_text.SetValue("Execute a workflow to see improvement suggestions.")
        suggestions_sizer.Add(self.suggestions_text, 1, wx.EXPAND | wx.ALL, 8)
        
        right_sizer.Add(suggestions_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        
        # Parameters section
        params_box = wx.StaticBox(self, label="Workflow Parameters")
        params_sizer = wx.StaticBoxSizer(params_box, wx.VERTICAL)
        
        self.params_panel = wx.Panel(self)
        self.params_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.params_panel.SetSizer(self.params_panel_sizer)
        
        params_sizer.Add(self.params_panel, 1, wx.EXPAND | wx.ALL, 8)
        right_sizer.Add(params_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        
        self.parameter_controls = {}  # Store parameter input controls
        
        # Action buttons
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_execute = wx.Button(self, label="Execute Automation")
        self.btn_export = wx.Button(self, label="Export")
        self.btn_stop = wx.Button(self, label="Stop")
        self.btn_stop.Enable(False)
        
        # Emergency stop button (red, prominent)
        self.btn_emergency_stop = wx.Button(self, label="⚠ EMERGENCY STOP")
        self.btn_emergency_stop.SetBackgroundColour(wx.Colour(220, 53, 69))  # Red
        self.btn_emergency_stop.SetForegroundColour(wx.WHITE)
        self.btn_emergency_stop.SetToolTip("Immediately halt all automations (Ctrl+Shift+Esc)")
        
        btns.Add(self.btn_execute)
        btns.Add(self.btn_export, flag=wx.LEFT, border=6)
        btns.Add(self.btn_stop, flag=wx.LEFT, border=6)
        btns.AddStretchSpacer()
        btns.Add(self.btn_emergency_stop, flag=wx.LEFT, border=12)
        right_sizer.Add(btns, flag=wx.ALL | wx.EXPAND, border=8)
        
        # Emergency stop status indicator
        self.emergency_status = wx.StaticText(self, label="")
        right_sizer.Add(self.emergency_status, flag=wx.ALL, border=8)
        
        hbox.Add(right_sizer, 1, wx.EXPAND | wx.ALL, 6)

        self.SetSizer(hbox)
        
        # Bind events
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_pattern_selected)
        self.btn_execute.Bind(wx.EVT_BUTTON, self._on_execute)
        self.btn_export.Bind(wx.EVT_BUTTON, self._on_export)
        self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop)
        self.btn_emergency_stop.Bind(wx.EVT_BUTTON, self._on_emergency_stop)
        self.filter_text.Bind(wx.EVT_TEXT_ENTER, self._on_filter)
        
        # Store reference to coordinator (will be set by main frame)
        self.coordinator = None
        
        # Add sample patterns
        self._add_sample_patterns()
    
    def _add_sample_patterns(self):
        """Add sample patterns for demonstration."""
        patterns = [
            ("Excel Data Entry", "5x", "50%", "Today"),  # Base confidence
            ("Email Composition", "3x", "50%", "Today"),  # Base confidence
            ("Browser Navigation", "8x", "50%", "Yesterday"),  # Base confidence
        ]
        for pattern, freq, conf, last_seen in patterns:
            idx = self.list.InsertItem(self.list.GetItemCount(), pattern)
            self.list.SetItem(idx, 1, freq)
            self.list.SetItem(idx, 2, conf)
            self.list.SetItem(idx, 3, last_seen)
    
    def update_pattern_confidence(self, pattern_id: str, confidence: float) -> None:
        """
        Update confidence display for a pattern.
        
        Args:
            pattern_id: Pattern/workflow identifier
            confidence: Confidence score (0.0 to 1.0)
        """
        # Find pattern in list by ID (stored in item data)
        for i in range(self.list.GetItemCount()):
            item_data = self.list.GetItemData(i)
            if item_data and str(item_data) == pattern_id:
                # Update confidence column
                confidence_pct = f"{int(confidence * 100)}%"
                self.list.SetItem(i, 2, confidence_pct)
                
                # Color code based on confidence
                if confidence >= 0.8:
                    # High confidence - green
                    self.list.SetItemTextColour(i, wx.Colour(40, 167, 69))
                elif confidence >= 0.5:
                    # Medium confidence - default
                    self.list.SetItemTextColour(i, wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
                else:
                    # Low confidence - red
                    self.list.SetItemTextColour(i, wx.Colour(220, 53, 69))
                
                self.logger.debug(f"Updated confidence for pattern {pattern_id}: {confidence_pct}")
                break
    
    def _on_pattern_selected(self, evt: wx.ListEvent) -> None:
        """Handle pattern selection."""
        idx = evt.GetIndex()
        pattern_name = self.list.GetItemText(idx, 0)
        confidence = self.list.GetItemText(idx, 2)
        frequency = self.list.GetItemText(idx, 1)
        last_seen = self.list.GetItemText(idx, 3)
        
        # Parse confidence percentage
        try:
            conf_value = int(confidence.rstrip('%'))
            conf_desc = self._get_confidence_description(conf_value)
        except:
            conf_desc = "Unknown"
        
        self.details_title.SetLabel(f"Pattern: {pattern_name}")
        self.details_text.SetValue(
            f"Pattern Details: {pattern_name}\n\n"
            f"Confidence: {confidence} ({conf_desc})\n"
            f"Frequency: {frequency}\n"
            f"Last Seen: {last_seen}\n\n"
            f"Confidence Score:\n"
            f"The confidence score reflects how reliably this workflow executes.\n"
            f"• Starts at 50% (base confidence)\n"
            f"• Increases by 10% with each successful execution (max 100%)\n"
            f"• Decreases by 20% with each failure (min 0%)\n\n"
            f"Automation Steps:\n"
            f"1. Open application\n"
            f"2. Navigate to target\n"
            f"3. Perform actions\n"
            f"4. Save results\n\n"
            f"This pattern has been detected multiple times and is ready for automation."
        )
        self.btn_execute.Enable(True)
    
    def _get_confidence_description(self, confidence_pct: int) -> str:
        """Get human-readable confidence description."""
        if confidence_pct >= 80:
            return "High - Reliable execution"
        elif confidence_pct >= 60:
            return "Good - Generally reliable"
        elif confidence_pct >= 40:
            return "Medium - Some issues"
        elif confidence_pct >= 20:
            return "Low - Frequent failures"
        else:
            return "Very Low - Needs review"
    
    def update_improvement_suggestions(self, workflow_id: str, suggestions: list) -> None:
        """
        Update improvement suggestions display.
        
        Args:
            workflow_id: Workflow identifier
            suggestions: List of suggestion strings
        """
        if not suggestions:
            self.suggestions_text.SetValue("No suggestions at this time. Workflow is performing well.")
            return
        
        # Format suggestions as numbered list
        suggestions_text = "Improvement Suggestions:\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            suggestions_text += f"{i}. {suggestion}\n\n"
        
        self.suggestions_text.SetValue(suggestions_text.strip())
        self.logger.info(f"Updated suggestions for workflow {workflow_id}: {len(suggestions)} suggestions")
    
    def display_parameters(self, parameters: list) -> None:
        """
        Display parameter input controls.
        
        Args:
            parameters: List of parameter dictionaries
        """
        # Clear existing controls
        self.params_panel_sizer.Clear(True)
        self.param_controls.clear()
        
        if not parameters:
            no_params = wx.StaticText(self.params_panel, label="No parameters for this workflow")
            self.params_panel_sizer.Add(no_params, flag=wx.ALL, border=8)
        else:
            for param in parameters:
                param_name = param.get('name', 'unknown')
                param_type = param.get('type', 'text')
                param_desc = param.get('description', '')
                default_value = param.get('default_value', '')
                required = param.get('required', True)
                
                # Create label
                label_text = f"{param_name}{'*' if required else ''}: {param_desc}"
                label = wx.StaticText(self.params_panel, label=label_text)
                self.params_panel_sizer.Add(label, flag=wx.ALL, border=4)
                
                # Create input control based on type
                if param_type == 'text':
                    ctrl = wx.TextCtrl(self.params_panel, value=str(default_value))
                elif param_type == 'number':
                    ctrl = wx.SpinCtrlDouble(self.params_panel, value=str(default_value), min=0, max=999999)
                elif param_type == 'date':
                    ctrl = wx.TextCtrl(self.params_panel, value=str(default_value))
                elif param_type == 'file':
                    ctrl = wx.FilePickerCtrl(self.params_panel)
                    if default_value:
                        ctrl.SetPath(str(default_value))
                elif param_type == 'choice':
                    choices = param.get('validation_rules', {}).get('choices', [])
                    ctrl = wx.Choice(self.params_panel, choices=[str(c) for c in choices])
                    if default_value in choices:
                        ctrl.SetSelection(choices.index(default_value))
                else:
                    ctrl = wx.TextCtrl(self.params_panel, value=str(default_value))
                
                self.params_panel_sizer.Add(ctrl, flag=wx.EXPAND | wx.ALL, border=4)
                self.param_controls[param_name] = ctrl
        
        self.params_panel.Layout()
        self.Layout()
    
    def get_parameter_values(self) -> dict:
        """
        Get current parameter values from input controls.
        
        Returns:
            Dictionary of parameter name -> value
        """
        values = {}
        for param_name, ctrl in self.param_controls.items():
            if isinstance(ctrl, wx.TextCtrl):
                values[param_name] = ctrl.GetValue()
            elif isinstance(ctrl, wx.SpinCtrlDouble):
                values[param_name] = ctrl.GetValue()
            elif isinstance(ctrl, wx.FilePickerCtrl):
                values[param_name] = ctrl.GetPath()
            elif isinstance(ctrl, wx.Choice):
                values[param_name] = ctrl.GetStringSelection()
        return values
    
    def _on_execute(self, evt: wx.CommandEvent) -> None:
        """Handle execute button click."""
        if self.list.GetSelectedItemCount() == 0:
            wx.MessageBox("Please select a pattern first.", "No Selection", wx.OK | wx.ICON_WARNING)
            return
        
        dlg = wx.MessageDialog(
            self,
            "Execute automation for selected pattern?",
            "Confirm Execution",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            self.btn_execute.Enable(False)
            self.btn_stop.Enable(True)
            wx.MessageBox("Automation started. Check status in debug console.", "Execution Started", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()
    
    def _on_export(self, evt: wx.CommandEvent) -> None:
        """Handle export button click."""
        with wx.FileDialog(
            self,
            "Export Pattern",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
            wx.MessageBox(f"Pattern would be exported to:\n{path}", "Export", wx.OK | wx.ICON_INFORMATION)
    
    def _on_stop(self, evt: wx.CommandEvent) -> None:
        """Handle stop button click."""
        self.btn_execute.Enable(True)
        self.btn_stop.Enable(False)
        wx.MessageBox("Automation stopped.", "Stop", wx.OK | wx.ICON_INFORMATION)
    
    def _on_emergency_stop(self, evt: wx.CommandEvent) -> None:
        """Handle emergency stop button click."""
        # Check if we're resetting or triggering
        if self.btn_emergency_stop.GetLabel() == "Reset Emergency Stop":
            # Reset emergency stop
            if self.coordinator:
                import asyncio
                try:
                    executor = self.coordinator.automation_executor
                    if executor:
                        asyncio.create_task(executor.reset_emergency_stop())
                        self._set_emergency_stop_state(False)
                        wx.MessageBox(
                            "Emergency stop reset.\n\nAutomations can now run.",
                            "Reset Complete",
                            wx.OK | wx.ICON_INFORMATION
                        )
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to reset emergency stop: {e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR
                    )
            else:
                self._set_emergency_stop_state(False)
            return
        
        # Trigger emergency stop
        dlg = wx.MessageDialog(
            self,
            "EMERGENCY STOP will immediately halt ALL running automations.\n\n"
            "This action cannot be undone. Continue?",
            "Confirm Emergency Stop",
            wx.YES_NO | wx.ICON_WARNING
        )
        
        if dlg.ShowModal() == wx.ID_YES:
            # Trigger emergency stop via coordinator
            if self.coordinator:
                import asyncio
                try:
                    # Get the automation executor
                    executor = self.coordinator.automation_executor
                    if executor:
                        # Create task to trigger emergency stop
                        asyncio.create_task(executor.trigger_emergency_stop())
                        
                        # Update UI
                        self._set_emergency_stop_state(True)
                        
                        wx.MessageBox(
                            "Emergency stop triggered!\n\n"
                            "All automations have been halted.\n"
                            "Click 'Reset Emergency Stop' to resume.",
                            "Emergency Stop Active",
                            wx.OK | wx.ICON_ERROR
                        )
                    else:
                        wx.MessageBox(
                            "Automation executor not available.",
                            "Error",
                            wx.OK | wx.ICON_ERROR
                        )
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to trigger emergency stop: {e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR
                    )
            else:
                wx.MessageBox(
                    "Emergency stop triggered (demo mode).",
                    "Emergency Stop",
                    wx.OK | wx.ICON_WARNING
                )
        
        dlg.Destroy()
    
    def _set_emergency_stop_state(self, active: bool) -> None:
        """Update UI to reflect emergency stop state."""
        if active:
            self.emergency_status.SetLabel("⚠ EMERGENCY STOP ACTIVE")
            self.emergency_status.SetForegroundColour(wx.RED)
            self.btn_emergency_stop.SetLabel("Reset Emergency Stop")
            self.btn_emergency_stop.SetBackgroundColour(wx.Colour(40, 167, 69))  # Green
            self.btn_execute.Enable(False)
            self.btn_stop.Enable(False)
        else:
            self.emergency_status.SetLabel("")
            self.btn_emergency_stop.SetLabel("⚠ EMERGENCY STOP")
            self.btn_emergency_stop.SetBackgroundColour(wx.Colour(220, 53, 69))  # Red
            self.btn_execute.Enable(True)
        
        self.Layout()
    
    def set_coordinator(self, coordinator) -> None:
        """Set reference to application coordinator."""
        self.coordinator = coordinator
    
    def _on_filter(self, evt: wx.CommandEvent) -> None:
        """Handle filter text enter."""
        filter_text = self.filter_text.GetValue().lower()
        if not filter_text:
            # Show all items
            for i in range(self.list.GetItemCount()):
                self.list.SetItemState(i, 0, wx.LIST_STATE_HIDDEN)
                self.list.SetItemState(i, wx.LIST_STATE_DONTCARE, wx.LIST_STATE_HIDDEN)
        else:
            # Filter items
            for i in range(self.list.GetItemCount()):
                pattern_name = self.list.GetItemText(i, 0).lower()
                if filter_text in pattern_name:
                    self.list.SetItemState(i, 0, wx.LIST_STATE_HIDDEN)
                else:
                    self.list.SetItemState(i, wx.LIST_STATE_HIDDEN, wx.LIST_STATE_HIDDEN)



    
    def display_parameters(self, workflow_id: str, parameters: list) -> None:
        """Display parameter input controls for workflow."""
        # Clear existing controls
        self.params_panel_sizer.Clear(True)
        self.parameter_controls.clear()
        
        if not parameters:
            no_params = wx.StaticText(self.params_panel, label="No parameters required")
            self.params_panel_sizer.Add(no_params, flag=wx.ALL, border=8)
            self.params_panel.Layout()
            return
        
        # Create controls for each parameter
        for param in parameters:
            param_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            # Label
            label = wx.StaticText(self.params_panel, label=f"{param['name']}:")
            param_sizer.Add(label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=8)
            
            # Input control based on type
            if param['type'] == 'text':
                ctrl = wx.TextCtrl(self.params_panel, value=str(param.get('default_value', '')))
            elif param['type'] == 'number':
                ctrl = wx.SpinCtrlDouble(self.params_panel, value=str(param.get('default_value', 0)))
            elif param['type'] == 'file':
                ctrl = wx.FilePickerCtrl(self.params_panel)
                if param.get('default_value'):
                    ctrl.SetPath(param['default_value'])
            elif param['type'] == 'choice':
                choices = param.get('validation_rules', {}).get('choices', [])
                ctrl = wx.Choice(self.params_panel, choices=[str(c) for c in choices])
                if param.get('default_value'):
                    ctrl.SetStringSelection(str(param['default_value']))
            else:
                ctrl = wx.TextCtrl(self.params_panel, value=str(param.get('default_value', '')))
            
            param_sizer.Add(ctrl, 1, wx.EXPAND)
            self.params_panel_sizer.Add(param_sizer, flag=wx.EXPAND | wx.ALL, border=4)
            
            self.parameter_controls[param['name']] = ctrl
        
        self.params_panel.Layout()
        self.Layout()
    
    def get_parameter_values(self) -> dict:
        """Get current parameter values from controls."""
        values = {}
        for name, ctrl in self.parameter_controls.items():
            if isinstance(ctrl, wx.TextCtrl):
                values[name] = ctrl.GetValue()
            elif isinstance(ctrl, wx.SpinCtrlDouble):
                values[name] = ctrl.GetValue()
            elif isinstance(ctrl, wx.FilePickerCtrl):
                values[name] = ctrl.GetPath()
            elif isinstance(ctrl, wx.Choice):
                values[name] = ctrl.GetStringSelection()
        return values
