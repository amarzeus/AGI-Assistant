from __future__ import annotations

from typing import Any, List
from datetime import datetime

import wx


class ActivityPanel(wx.Panel):
    """Activity feed panel showing captured actions and events with filtering."""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        
        # Action storage (max 1000)
        self._actions: List[Any] = []
        self._max_actions = 1000
        
        # Filter state
        self._filter_type = "All"
        self._filter_app = ""
        self._filter_search = ""
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Header with title and controls
        header = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(self, label="Activity Feed")
        font = title.GetFont()
        font.MakeBold()
        font.SetPointSize(font.GetPointSize() + 2)
        title.SetFont(font)
        header.Add(title, 1, wx.ALIGN_CENTER_VERTICAL)
        
        self.btn_clear = wx.Button(self, label="Clear")
        self.btn_refresh = wx.Button(self, label="Refresh")
        header.Add(self.btn_refresh, flag=wx.LEFT, border=6)
        header.Add(self.btn_clear, flag=wx.LEFT, border=6)
        
        vbox.Add(header, flag=wx.EXPAND | wx.ALL, border=12)
        
        # Filter controls
        filter_box = wx.BoxSizer(wx.HORIZONTAL)
        
        # Type filter
        filter_box.Add(wx.StaticText(self, label="Type:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        self.type_choice = wx.Choice(self, choices=["All", "Click", "Type", "Navigate", "Scroll", "Other"])
        self.type_choice.SetSelection(0)
        filter_box.Add(self.type_choice, flag=wx.RIGHT, border=12)
        
        # Application filter
        filter_box.Add(wx.StaticText(self, label="App:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        self.app_text = wx.TextCtrl(self, size=(150, -1))
        self.app_text.SetHint("Filter by app...")
        filter_box.Add(self.app_text, flag=wx.RIGHT, border=12)
        
        # Search box
        filter_box.Add(wx.StaticText(self, label="Search:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=4)
        self.search_text = wx.TextCtrl(self, size=(200, -1))
        self.search_text.SetHint("Search description...")
        filter_box.Add(self.search_text, flag=wx.RIGHT, border=12)
        
        # Apply filter button
        self.btn_filter = wx.Button(self, label="Apply Filter")
        filter_box.Add(self.btn_filter)
        
        vbox.Add(filter_box, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        
        # Activity list
        self.list = wx.ListCtrl(
            self, 
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self.list.InsertColumn(0, "Time", width=120)
        self.list.InsertColumn(1, "Type", width=120)
        self.list.InsertColumn(2, "Application", width=150)
        self.list.InsertColumn(3, "Description", width=400)
        self.list.InsertColumn(4, "Confidence", width=100)
        vbox.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        
        # Status/info
        self.info_text = wx.StaticText(
            self,
            label="Recent captured actions and events will appear here. (0 actions)"
        )
        vbox.Add(self.info_text, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        
        self.SetSizer(vbox)
        
        # Bind events
        self.btn_clear.Bind(wx.EVT_BUTTON, self._on_clear)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self._on_refresh)
        self.btn_filter.Bind(wx.EVT_BUTTON, self._on_apply_filter)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
    
    def add_action(self, action: Any) -> None:
        """
        Add action to feed with color-coded confidence.
        
        Args:
            action: Action object with timestamp, type, application, description, confidence
        """
        # Add to storage
        self._actions.insert(0, action)
        
        # Enforce max limit
        if len(self._actions) > self._max_actions:
            self._actions = self._actions[:self._max_actions]
        
        # Update display if passes filter
        if self._passes_filter(action):
            self._add_action_to_list(action)
        
        # Update count
        self._update_info_text()
    
    def _add_action_to_list(self, action: Any) -> None:
        """Add action to list control."""
        try:
            time_str = action.timestamp.strftime("%H:%M:%S") if hasattr(action, 'timestamp') else datetime.now().strftime("%H:%M:%S")
            action_type = action.type.value if hasattr(action, 'type') else str(getattr(action, 'action_type', 'Unknown'))
            app_name = getattr(action, 'application', 'Unknown')
            desc = getattr(action, 'description', getattr(action, 'target_element', 'Action'))
            confidence = getattr(action, 'confidence', 0.0)
            conf_str = f"{int(confidence * 100)}%"
            
            idx = self.list.InsertItem(0, time_str)
            self.list.SetItem(idx, 1, action_type)
            self.list.SetItem(idx, 2, app_name)
            self.list.SetItem(idx, 3, desc)
            self.list.SetItem(idx, 4, conf_str)
            
            # Color-code by confidence
            if confidence > 0.8:
                self.list.SetItemTextColour(idx, wx.Colour(0, 128, 0))  # Green
            elif confidence > 0.5:
                self.list.SetItemTextColour(idx, wx.Colour(255, 140, 0))  # Orange
            else:
                self.list.SetItemTextColour(idx, wx.Colour(255, 0, 0))  # Red
        except Exception as e:
            print(f"Error adding action to list: {e}")
    
    def _passes_filter(self, action: Any) -> bool:
        """Check if action passes current filters."""
        # Type filter
        if self._filter_type != "All":
            action_type = action.type.value if hasattr(action, 'type') else str(getattr(action, 'action_type', 'Unknown'))
            if action_type.lower() != self._filter_type.lower():
                return False
        
        # App filter
        if self._filter_app:
            app_name = getattr(action, 'application', 'Unknown')
            if self._filter_app.lower() not in app_name.lower():
                return False
        
        # Search filter
        if self._filter_search:
            desc = getattr(action, 'description', getattr(action, 'target_element', ''))
            if self._filter_search.lower() not in desc.lower():
                return False
        
        return True
    
    def _update_info_text(self) -> None:
        """Update info text with action count."""
        count = len(self._actions)
        displayed = self.list.GetItemCount()
        if displayed < count:
            self.info_text.SetLabel(f"Showing {displayed} of {count} actions (filtered)")
        else:
            self.info_text.SetLabel(f"{count} actions captured")
    
    def _on_clear(self, evt: wx.CommandEvent) -> None:
        """Handle clear button click."""
        dlg = wx.MessageDialog(
            self,
            "Clear all activity entries?",
            "Confirm Clear",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            self.list.DeleteAllItems()
            self._actions.clear()
            self._update_info_text()
        dlg.Destroy()
    
    def _on_refresh(self, evt: wx.CommandEvent) -> None:
        """Handle refresh button click."""
        # Reapply filters to display
        self._apply_filters()
    
    def _on_apply_filter(self, evt: wx.CommandEvent) -> None:
        """Handle apply filter button click."""
        self._filter_type = self.type_choice.GetStringSelection()
        self._filter_app = self.app_text.GetValue()
        self._filter_search = self.search_text.GetValue()
        self._apply_filters()
    
    def _apply_filters(self) -> None:
        """Apply current filters to action list."""
        self.list.DeleteAllItems()
        for action in self._actions:
            if self._passes_filter(action):
                self._add_action_to_list(action)
        self._update_info_text()
    
    def _on_item_selected(self, evt: wx.ListEvent) -> None:
        """Handle item selection - show details."""
        idx = evt.GetIndex()
        if idx >= 0 and idx < len(self._actions):
            action = self._actions[idx]
            
            # Build details string
            details = []
            details.append(f"Time: {action.timestamp if hasattr(action, 'timestamp') else 'Unknown'}")
            details.append(f"Type: {action.type.value if hasattr(action, 'type') else 'Unknown'}")
            details.append(f"Application: {getattr(action, 'application', 'Unknown')}")
            details.append(f"Description: {getattr(action, 'description', 'N/A')}")
            details.append(f"Confidence: {int(getattr(action, 'confidence', 0.0) * 100)}%")
            
            if hasattr(action, 'id'):
                details.append(f"ID: {action.id}")
            
            wx.MessageBox("\n".join(details), "Action Details", wx.OK | wx.ICON_INFORMATION)
    
    def get_actions(self) -> List[Any]:
        """Get all stored actions."""
        return self._actions.copy()


