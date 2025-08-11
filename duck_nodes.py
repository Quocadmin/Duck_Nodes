# =================================================================================
# Import các thư viện cần thiết cho tất cả các node
# =================================================================================
import os
import re
import io
import json
import urllib.parse

import torch
import numpy as np
import pandas as pd
import requests
import docx  # Thư viện cho file Word
from PIL import Image, ImageOps

# =================================================================================
# Định nghĩa Lớp (Class) cho từng Node
# =================================================================================

# --- Hàm trợ giúp để chuyển đổi tên cột Excel (A, B, AA) thành chỉ số ---
def col_to_index(col_str):
    """Converts an Excel-style column name (e.g., 'A', 'B', 'AA') to a zero-based index."""
    col_str = col_str.upper()
    result = 0
    for char in col_str:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1

# === Node: Tải dòng từ Google Sheet ===
class Duck_LoadGoogleSheetOneRow:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Url": ("STRING", {"default": "URL của Google Sheet"}),
                "Column": ("STRING", {"default": "A2:A"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("row",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "load_one_row"
    CATEGORY = "Duck Nodes/GoogleSheet"

    def load_one_row(self, Url, Column, seed):
        if "https://docs.google.com/spreadsheets/d/" not in Url:
            print("❌ URL của Google Sheet không hợp lệ")
            return ([""],)
        
        try:
            sheet_id = Url.split("/")[5]
            gid_match = re.search(r"gid=(\d+)", Url)
            gid = gid_match.group(1) if gid_match else "0"
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            response = requests.get(csv_url, timeout=10)
            response.raise_for_status()
            content = response.content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content), header=None)
            df.dropna(how='all', inplace=True)

        except requests.exceptions.RequestException as e:
            print(f"❌ Không thể tải Google Sheet. Vui lòng kiểm tra lại URL và đảm bảo nó được chia sẻ công khai. Lỗi: {e}")
            return ([""],)
        except Exception as e:
            print(f"❌ Đã xảy ra lỗi khi xử lý dữ liệu từ Google Sheet: {e}")
            return ([""],)
        
        if df.empty:
            print("⚠️ Google Sheet trống.")
            return ([""],)

        try:
            if Column.strip():
                start_column, end_column_maybe = Column.split(":")
                start_col_str, start_row_str = re.match(r"([A-Z]+)(\d+)", start_column).groups()
                end_col_match = re.match(r"([A-Z]+)(\d*)", end_column_maybe)
                end_col_str, end_row_str = end_col_match.group(1), end_col_match.group(2)
                start_col, end_col = col_to_index(start_col_str), col_to_index(end_col_str)
                start_row, end_row = int(start_row_str) - 1, int(end_row_str) if end_row_str else len(df)
                rows = df.iloc[start_row:end_row, start_col:end_col+1].values.tolist()
            else:
                rows = df.values.tolist()
        except Exception as e:
            print(f"❌ Lỗi khi phân tích dải ô '{Column}': {e}")
            return ([""],)

        if not rows: return ([""],)
        idx = seed % len(rows)
        selected_row = rows[idx]
        result = [str(column) if pd.notna(column) else "" for column in selected_row]
        return (result,)

# === Node: Tải dòng từ Google Doc ===
class Duck_LoadGoogleDocLine:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Url": ("STRING", {"default": "URL của Google Docs"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("line",)
    FUNCTION = "load_line"
    CATEGORY = "Duck Nodes/GoogleDocs"

    def load_line(self, Url, seed):
        if "https://docs.google.com/document/d/" not in Url:
            print("❌ URL của Google Docs không hợp lệ.")
            return ("",)
        try:
            doc_id_match = re.search(r"/document/d/([^/]+)", Url)
            if not doc_id_match:
                print("❌ Không thể phân tích ID của Google Docs từ URL.")
                return ("",)
            doc_id = doc_id_match.group(1)
            txt_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            response = requests.get(txt_url, timeout=10)
            response.raise_for_status()
            content = response.content.decode('utf-8')
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if not lines:
                print("⚠️ Google Doc trống.")
                return ("",)
            idx = seed % len(lines)
            return (lines[idx],)
        except Exception as e:
            print(f"❌ Lỗi khi tải hoặc xử lý Google Doc: {e}")
            return ("",)

# === Node: Tải dòng từ file Excel offline ===
class Duck_LoadExcelRow:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "C:\\path\\to\\your\\file.xlsx"}),
                "sheet_name": ("STRING", {"default": "Sheet1"}),
                "Column": ("STRING", {"default": "A1:A"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("row",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "load_row"
    CATEGORY = "Duck Nodes/LocalFiles"

    def load_row(self, file_path, sheet_name, Column, seed):
        clean_path = file_path.strip().strip('"')
        if not os.path.exists(clean_path) or not clean_path.lower().endswith('.xlsx'):
            print(f"❌ Đường dẫn file Excel không hợp lệ: {clean_path}")
            return ([[]],)
        try:
            df = pd.read_excel(clean_path, sheet_name=sheet_name, header=None)
            df.dropna(how='all', inplace=True)
            if df.empty:
                print(f"⚠️ Sheet '{sheet_name}' trong file Excel trống.")
                return ([[]],)
            if Column.strip():
                start_column, end_column_maybe = Column.split(":")
                start_col_str, start_row_str_match = re.match(r"([A-Z]+)(\d*)", start_column).groups()
                start_row_str = start_row_str_match if start_row_str_match else "1"
                end_col_match = re.match(r"([A-Z]+)(\d*)", end_column_maybe)
                end_col_str, end_row_str = end_col_match.group(1), end_col_match.group(2)
                start_col, end_col = col_to_index(start_col_str), col_to_index(end_col_str)
                start_row = int(start_row_str) - 1
                end_row = int(end_row_str) if end_row_str else len(df)
                rows = df.iloc[start_row:end_row, start_col:end_col+1].values.tolist()
            else:
                rows = df.values.tolist()
            if not rows: return ([[]],)
            idx = seed % len(rows)
            selected_row = rows[idx]
            result = [str(column) if pd.notna(column) else "" for column in selected_row]
            return (result,)
        except Exception as e:
            print(f"❌ Lỗi khi đọc file Excel hoặc dải ô: {e}")
            return ([[]],)

# === Node: Tải dòng từ file Word offline ===
class Duck_LoadWordLine:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "C:\\path\\to\\your\\file.docx"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("line",)
    FUNCTION = "load_line"
    CATEGORY = "Duck Nodes/LocalFiles"

    def load_line(self, file_path, seed):
        clean_path = file_path.strip().strip('"')
        if not os.path.exists(clean_path) or not clean_path.lower().endswith('.docx'):
            print(f"❌ Đường dẫn file Word không hợp lệ: {clean_path}")
            return ("",)
        try:
            document = docx.Document(clean_path)
            paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            if not paragraphs:
                print("⚠️ File Word trống.")
                return ("",)
            idx = seed % len(paragraphs)
            return (paragraphs[idx],)
        except Exception as e:
            print(f"❌ Lỗi khi đọc file Word: {e}")
            return ("",)

# === Node: Tải prompt từ file text offline ===
class Duck_PromptLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "C:\\path\\to\\your\\prompts.txt"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("prompt", "line_count")
    FUNCTION = "load_prompt"
    CATEGORY = "Duck Nodes/LocalFiles"

    def load_prompt(self, file_path, seed):
        clean_path = file_path.strip().strip('"')
        if not os.path.exists(clean_path):
            print(f"❌ File không tồn tại: {clean_path}")
            return ("", 0)
        try:
            with open(clean_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f if line.strip()]
            if not lines:
                print(f"⚠️ File trống: {clean_path}")
                return ("", 0)
            line_count = len(lines)
            selected_index = seed % line_count
            return (lines[selected_index], line_count)
        except Exception as e:
            print(f"❌ Lỗi khi đọc file: {e}")
            return ("", 0)

# =================================================================================
# Đăng ký tất cả các Node với ComfyUI
# =================================================================================

NODE_CLASS_MAPPINGS = {
    "Duck_LoadGoogleSheetOneRow": Duck_LoadGoogleSheetOneRow,
    "Duck_LoadGoogleDocLine": Duck_LoadGoogleDocLine,
    "Duck_LoadExcelRow": Duck_LoadExcelRow,
    "Duck_LoadWordLine": Duck_LoadWordLine,
    "Duck_PromptLoader": Duck_PromptLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Duck_LoadGoogleSheetOneRow": "Duck - Load Google Sheet Row",
    "Duck_LoadGoogleDocLine": "Duck - Load Google Doc Line",
    "Duck_LoadExcelRow": "Duck - Load Excel Row",
    "Duck_LoadWordLine": "Duck - Load Word Line",
    "Duck_PromptLoader": "Duck - Load Prompt From File"
}
