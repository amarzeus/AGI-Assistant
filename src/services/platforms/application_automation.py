"""
Application Automation Platform for Windows applications.

This module provides automation capabilities for Windows applications
including Excel, File Explorer, and window management.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

# Try to import win32com for Windows automation
try:
    import win32com.client
    import win32gui
    import win32con
    import win32api
    import win32process
    import pywintypes
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    win32com = None
    win32gui = None
    win32con = None
    win32api = None
    win32process = None
    pywintypes = None


class ApplicationAutomationPlatform:
    """
    Application automation platform for Windows applications.
    
    Features:
    - Excel automation (open, edit, save)
    - File Explorer operations (copy, move, rename)
    - Window management (focus, minimize, maximize)
    - Application launching
    """
    
    def __init__(self):
        """Initialize application automation platform."""
        self.logger = logging.getLogger(__name__)
        self.enabled = WIN32_AVAILABLE
        
        # Excel instance
        self._excel = None
        self._workbook = None
        
        # State
        self._initialized = False
        
        if not self.enabled:
            self.logger.warning("Win32COM not available - application automation disabled")
        else:
            self.logger.info("Application automation platform initialized")
    
    # Excel Automation
    
    async def open_excel(self, file_path: str, visible: bool = True) -> None:
        """
        Open Excel file.
        
        Args:
            file_path: Path to Excel file
            visible: Make Excel visible
        """
        if not self.enabled:
            raise RuntimeError("Win32COM not available")
        
        try:
            self.logger.info(f"Opening Excel file: {file_path}")
            
            # Create Excel application
            self._excel = win32com.client.Dispatch("Excel.Application")
            self._excel.Visible = visible
            self._excel.DisplayAlerts = False
            
            # Open workbook
            abs_path = str(Path(file_path).resolve())
            self._workbook = self._excel.Workbooks.Open(abs_path)
            
            self._initialized = True
            self.logger.info("Excel file opened successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to open Excel file: {e}")
            raise
    
    async def create_excel(self, visible: bool = True) -> None:
        """
        Create new Excel workbook.
        
        Args:
            visible: Make Excel visible
        """
        if not self.enabled:
            raise RuntimeError("Win32COM not available")
        
        try:
            self.logger.info("Creating new Excel workbook")
            
            # Create Excel application
            self._excel = win32com.client.Dispatch("Excel.Application")
            self._excel.Visible = visible
            self._excel.DisplayAlerts = False
            
            # Create new workbook
            self._workbook = self._excel.Workbooks.Add()
            
            self._initialized = True
            self.logger.info("Excel workbook created")
            
        except Exception as e:
            self.logger.error(f"Failed to create Excel workbook: {e}")
            raise
    
    async def close_excel(self, save: bool = False) -> None:
        """
        Close Excel workbook and application.
        
        Args:
            save: Save workbook before closing
        """
        if not self._initialized:
            return
        
        try:
            if self._workbook:
                self._workbook.Close(SaveChanges=save)
                self._workbook = None
            
            if self._excel:
                self._excel.Quit()
                self._excel = None
            
            self._initialized = False
            self.logger.info("Excel closed")
            
        except Exception as e:
            self.logger.error(f"Error closing Excel: {e}")
    
    async def save_excel(self, file_path: Optional[str] = None) -> None:
        """
        Save Excel workbook.
        
        Args:
            file_path: Path to save file (None to save in place)
        """
        self._ensure_excel()
        
        try:
            if file_path:
                abs_path = str(Path(file_path).resolve())
                self._workbook.SaveAs(abs_path)
                self.logger.info(f"Excel saved as: {abs_path}")
            else:
                self._workbook.Save()
                self.logger.info("Excel saved")
                
        except Exception as e:
            self.logger.error(f"Failed to save Excel: {e}")
            raise
    
    async def read_cell(self, sheet: str, cell: str) -> Any:
        """
        Read value from Excel cell.
        
        Args:
            sheet: Sheet name or index
            cell: Cell reference (e.g., 'A1')
            
        Returns:
            Cell value
        """
        self._ensure_excel()
        
        try:
            worksheet = self._get_worksheet(sheet)
            value = worksheet.Range(cell).Value
            self.logger.debug(f"Read cell {sheet}!{cell}: {value}")
            return value
            
        except Exception as e:
            self.logger.error(f"Failed to read cell {sheet}!{cell}: {e}")
            raise
    
    async def write_cell(self, sheet: str, cell: str, value: Any) -> None:
        """
        Write value to Excel cell.
        
        Args:
            sheet: Sheet name or index
            cell: Cell reference (e.g., 'A1')
            value: Value to write
        """
        self._ensure_excel()
        
        try:
            worksheet = self._get_worksheet(sheet)
            worksheet.Range(cell).Value = value
            self.logger.debug(f"Wrote cell {sheet}!{cell}: {value}")
            
        except Exception as e:
            self.logger.error(f"Failed to write cell {sheet}!{cell}: {e}")
            raise
    
    async def read_range(self, sheet: str, range_ref: str) -> List[List[Any]]:
        """
        Read range of cells from Excel.
        
        Args:
            sheet: Sheet name or index
            range_ref: Range reference (e.g., 'A1:C10')
            
        Returns:
            2D list of cell values
        """
        self._ensure_excel()
        
        try:
            worksheet = self._get_worksheet(sheet)
            range_obj = worksheet.Range(range_ref)
            values = range_obj.Value
            
            # Convert to list of lists
            if values is None:
                return [[]]
            elif isinstance(values, tuple):
                return [list(row) if isinstance(row, tuple) else [row] for row in values]
            else:
                return [[values]]
                
        except Exception as e:
            self.logger.error(f"Failed to read range {sheet}!{range_ref}: {e}")
            raise
    
    async def write_range(self, sheet: str, start_cell: str, data: List[List[Any]]) -> None:
        """
        Write range of data to Excel.
        
        Args:
            sheet: Sheet name or index
            start_cell: Starting cell (e.g., 'A1')
            data: 2D list of values
        """
        self._ensure_excel()
        
        try:
            worksheet = self._get_worksheet(sheet)
            
            # Calculate end cell
            rows = len(data)
            cols = len(data[0]) if data else 0
            
            if rows == 0 or cols == 0:
                return
            
            # Convert start cell to row/col
            start_row, start_col = self._cell_to_rowcol(start_cell)
            end_row = start_row + rows - 1
            end_col = start_col + cols - 1
            
            # Get range
            end_cell = self._rowcol_to_cell(end_row, end_col)
            range_ref = f"{start_cell}:{end_cell}"
            range_obj = worksheet.Range(range_ref)
            
            # Write data
            range_obj.Value = data
            self.logger.debug(f"Wrote range {sheet}!{range_ref}")
            
        except Exception as e:
            self.logger.error(f"Failed to write range: {e}")
            raise
    
    async def insert_formula(self, sheet: str, cell: str, formula: str) -> None:
        """
        Insert formula into Excel cell.
        
        Args:
            sheet: Sheet name or index
            cell: Cell reference
            formula: Formula (e.g., '=SUM(A1:A10)')
        """
        self._ensure_excel()
        
        try:
            worksheet = self._get_worksheet(sheet)
            worksheet.Range(cell).Formula = formula
            self.logger.debug(f"Inserted formula in {sheet}!{cell}: {formula}")
            
        except Exception as e:
            self.logger.error(f"Failed to insert formula: {e}")
            raise
    
    async def get_sheet_names(self) -> List[str]:
        """Get list of sheet names in workbook."""
        self._ensure_excel()
        
        try:
            sheets = []
            for sheet in self._workbook.Worksheets:
                sheets.append(sheet.Name)
            return sheets
            
        except Exception as e:
            self.logger.error(f"Failed to get sheet names: {e}")
            raise
    
    async def add_sheet(self, name: str) -> None:
        """Add new worksheet."""
        self._ensure_excel()
        
        try:
            self._workbook.Worksheets.Add()
            self._workbook.ActiveSheet.Name = name
            self.logger.info(f"Added sheet: {name}")
            
        except Exception as e:
            self.logger.error(f"Failed to add sheet: {e}")
            raise
    
    def _ensure_excel(self) -> None:
        """Ensure Excel is initialized."""
        if not self._initialized or not self._excel or not self._workbook:
            raise RuntimeError("Excel not initialized - call open_excel() or create_excel() first")
    
    def _get_worksheet(self, sheet: str):
        """Get worksheet by name or index."""
        try:
            # Try as name first
            return self._workbook.Worksheets(sheet)
        except:
            # Try as index
            try:
                return self._workbook.Worksheets(int(sheet))
            except:
                raise ValueError(f"Invalid sheet reference: {sheet}")
    
    def _cell_to_rowcol(self, cell: str) -> Tuple[int, int]:
        """Convert cell reference to row/col (1-indexed)."""
        import re
        match = re.match(r'([A-Z]+)(\d+)', cell.upper())
        if not match:
            raise ValueError(f"Invalid cell reference: {cell}")
        
        col_str, row_str = match.groups()
        
        # Convert column letters to number
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord('A') + 1)
        
        row = int(row_str)
        return row, col
    
    def _rowcol_to_cell(self, row: int, col: int) -> str:
        """Convert row/col (1-indexed) to cell reference."""
        col_str = ''
        while col > 0:
            col -= 1
            col_str = chr(col % 26 + ord('A')) + col_str
            col //= 26
        return f"{col_str}{row}"
    
    # File System Operations
    
    async def copy_file(self, source: str, destination: str) -> None:
        """
        Copy file.
        
        Args:
            source: Source file path
            destination: Destination file path
        """
        try:
            import shutil
            shutil.copy2(source, destination)
            self.logger.info(f"Copied file: {source} -> {destination}")
            
        except Exception as e:
            self.logger.error(f"Failed to copy file: {e}")
            raise
    
    async def move_file(self, source: str, destination: str) -> None:
        """
        Move file.
        
        Args:
            source: Source file path
            destination: Destination file path
        """
        try:
            import shutil
            shutil.move(source, destination)
            self.logger.info(f"Moved file: {source} -> {destination}")
            
        except Exception as e:
            self.logger.error(f"Failed to move file: {e}")
            raise
    
    async def rename_file(self, old_path: str, new_path: str) -> None:
        """
        Rename file.
        
        Args:
            old_path: Current file path
            new_path: New file path
        """
        try:
            Path(old_path).rename(new_path)
            self.logger.info(f"Renamed file: {old_path} -> {new_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to rename file: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> None:
        """
        Delete file.
        
        Args:
            file_path: File path to delete
        """
        try:
            Path(file_path).unlink()
            self.logger.info(f"Deleted file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete file: {e}")
            raise
    
    async def create_folder(self, folder_path: str) -> None:
        """
        Create folder.
        
        Args:
            folder_path: Folder path to create
        """
        try:
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created folder: {folder_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to create folder: {e}")
            raise
    
    async def delete_folder(self, folder_path: str) -> None:
        """
        Delete folder.
        
        Args:
            folder_path: Folder path to delete
        """
        try:
            import shutil
            shutil.rmtree(folder_path)
            self.logger.info(f"Deleted folder: {folder_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete folder: {e}")
            raise
    
    async def list_files(self, folder_path: str, pattern: str = "*") -> List[str]:
        """
        List files in folder.
        
        Args:
            folder_path: Folder path
            pattern: File pattern (e.g., '*.txt')
            
        Returns:
            List of file paths
        """
        try:
            folder = Path(folder_path)
            files = [str(f) for f in folder.glob(pattern) if f.is_file()]
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise
    
    # Window Management
    
    async def find_window(self, title: str) -> Optional[int]:
        """
        Find window by title.
        
        Args:
            title: Window title (partial match)
            
        Returns:
            Window handle or None
        """
        if not self.enabled:
            raise RuntimeError("Win32 not available")
        
        try:
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if title.lower() in window_title.lower():
                        windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                return windows[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find window: {e}")
            return None
    
    async def focus_window(self, hwnd: int) -> None:
        """
        Focus window.
        
        Args:
            hwnd: Window handle
        """
        if not self.enabled:
            raise RuntimeError("Win32 not available")
        
        try:
            win32gui.SetForegroundWindow(hwnd)
            self.logger.info(f"Focused window: {hwnd}")
            
        except Exception as e:
            self.logger.error(f"Failed to focus window: {e}")
            raise
    
    async def minimize_window(self, hwnd: int) -> None:
        """Minimize window."""
        if not self.enabled:
            raise RuntimeError("Win32 not available")
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            self.logger.info(f"Minimized window: {hwnd}")
            
        except Exception as e:
            self.logger.error(f"Failed to minimize window: {e}")
            raise
    
    async def maximize_window(self, hwnd: int) -> None:
        """Maximize window."""
        if not self.enabled:
            raise RuntimeError("Win32 not available")
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            self.logger.info(f"Maximized window: {hwnd}")
            
        except Exception as e:
            self.logger.error(f"Failed to maximize window: {e}")
            raise
    
    async def close_window(self, hwnd: int) -> None:
        """Close window."""
        if not self.enabled:
            raise RuntimeError("Win32 not available")
        
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            self.logger.info(f"Closed window: {hwnd}")
            
        except Exception as e:
            self.logger.error(f"Failed to close window: {e}")
            raise
    
    async def get_window_title(self, hwnd: int) -> str:
        """Get window title."""
        if not self.enabled:
            raise RuntimeError("Win32 not available")
        
        try:
            return win32gui.GetWindowText(hwnd)
        except Exception as e:
            self.logger.error(f"Failed to get window title: {e}")
            return ""
