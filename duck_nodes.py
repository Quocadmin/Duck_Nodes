import os
import re
import io
import json
import urllib.parse
import base64
import logging
from datetime import datetime

import torch
import numpy as np
import pandas as pd
import requests
import docx
from PIL import Image, ImageOps
import bcrypt

import server
from comfy.cli_args import args
import aiohttp
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
import folder_paths

node_dir = os.path.dirname(__file__)
comfy_dir = os.path.dirname(folder_paths.__file__)
password_path = os.path.join(comfy_dir, "login", "PASSWORD")
TOKEN = ""
user_cache = {}

def get_user_data():
    if 'username' in user_cache:
        return user_cache['username'], user_cache['password']
    else:
        if os.path.exists(password_path):
            with open(password_path, "rb") as f:
                stored_data = f.read().split(b'\n')
                password = stored_data[0]
                user_cache['password'] = password
                if len(stored_data) > 1 and stored_data[1].strip():
                    username = stored_data[1].decode('utf-8').strip()
                else:
                    username = None
                user_cache['username'] = username
                return username, password
        return None, None

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')

def load_token():
    global TOKEN
    try:
        with open(password_path, "r", encoding="utf-8") as f:
            TOKEN = f.readline().strip()
            logging.info(f"For direct API calls, use token={TOKEN}")
    except FileNotFoundError as e:
        logging.error("Please set up your password before use.")
        TOKEN = ""

async def process_request(request, handler):
    response = await handler(request)
    if request.path == '/':
        response.headers.setdefault('Cache-Control', 'no-cache')
    return response

prompt_server = server.PromptServer.instance
app = prompt_server.app
routes = prompt_server.routes

secret_key = generate_key()
setup(app, EncryptedCookieStorage(secret_key))

@routes.get("/login")
async def get_root(request):
    session = await get_session(request)
    wrong_password = request.query.get('wrong_password', '')
    if 'logged_in' in session and session['logged_in']:
        raise web.HTTPFound('/')
    else:
        env = Environment(loader=FileSystemLoader(node_dir), autoescape=select_autoescape(['html', 'xml']))
        template = env.get_template('login.html')
        first_time = not os.path.exists(password_path)
        username, _ = get_user_data() if not first_time else (None, None)
        prompt_for_username = (username is None and not first_time)
        return web.Response(text=template.render(first_time=first_time, username=username, wrong_password=wrong_password, prompt_for_username=prompt_for_username), content_type='text/html')

@routes.post("/login")
async def login_handler(request):
    data = await request.post()
    username_input = data.get('username')
    password_input = data.get('password').encode('utf-8')

    if os.path.exists(password_path):
        username_cached, password_cached = get_user_data()
        if password_cached and bcrypt.checkpw(password_input, password_cached):
            session = await get_session(request)
            session['logged_in'] = True
            if username_cached:
                session['username'] = username_cached
            else:
                with open(password_path, "wb") as file:
                    file.write(password_cached + b'\n' + username_input.encode('utf-8'))
                user_cache['username'] = username_input
                session['username'] = username_input
            return web.HTTPFound('/')
        else:
            return web.HTTPFound('/login?wrong_password=1')
    else:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_input, salt)
        with open(password_path, "wb") as file:
            file.write(hashed_password + b'\n' + username_input.encode('utf-8'))
        user_cache['username'] = username_input
        user_cache['password'] = hashed_password
        session = await get_session(request)
        session['logged_in'] = True
        session['username'] = username_input
        return web.HTTPFound('/')
    return web.HTTPFound('/login')

@routes.get("/logout")
async def logout_handler(request):
    session = await get_session(request)
    session['logged_in'] = False
    session.pop('username', None)
    return web.HTTPFound('/login')

@web.middleware
async def check_login_status(request: web.Request, handler):
    if request.path in ['/login', '/logout'] or request.path.endswith(('.css', '.js')):
        return await handler(request)
    if TOKEN == "": load_token()
    session = await get_session(request)
    if 'logged_in' in session and session['logged_in']:
        return await process_request(request, handler)
    if args.enable_cors_header:
        authorization_header = request.headers.get("Authorization")
        if authorization_header and authorization_header.split()[1] == TOKEN:
            return await process_request(request, handler)
    if request.query.get("token") == TOKEN:
        return await process_request(request, handler)
    raise web.HTTPFound('/login')

if not os.path.exists(os.path.dirname(password_path)):
    os.makedirs(os.path.dirname(password_path))
old_password_path = os.path.join(comfy_dir, "PASSWORD")
if os.path.exists(old_password_path):
    os.rename(old_password_path, password_path)
load_token()
app.middlewares.append(check_login_status)

def col_to_index(col_str):
    col_str = col_str.upper()
    result = 0
    for char in col_str:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1

class Duck_LoadGoogleSheetOneRow:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"Url": ("STRING", {"default": "Google Sheet URL"}), "Column": ("STRING", {"default": "A2:A"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("prompt",); OUTPUT_IS_LIST = (True,); FUNCTION = "load_one_row"; CATEGORY = "Duck Nodes/GoogleSheet"
    def load_one_row(self, Url, Column, seed):
        if "https://docs.google.com/spreadsheets/d/" not in Url: return ([""],)
        try:
            sheet_id = Url.split("/")[5]; gid_match = re.search(r"gid=(\d+)", Url); gid = gid_match.group(1) if gid_match else "0"
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"; response = requests.get(csv_url, timeout=10); response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), header=None); df.dropna(how='all', inplace=True)
            if df.empty: return ([""],)
            if Column.strip():
                start_column, end_column_maybe = Column.split(":"); start_col_str, start_row_str = re.match(r"([A-Z]+)(\d+)", start_column).groups(); end_col_match = re.match(r"([A-Z]+)(\d*)", end_column_maybe); end_col_str, end_row_str = end_col_match.group(1), end_col_match.group(2)
                start_col, end_col = col_to_index(start_col_str), col_to_index(end_col_str); start_row, end_row = int(start_row_str) - 1, int(end_row_str) if end_row_str else len(df)
                rows = df.iloc[start_row:end_row, start_col:end_col+1].values.tolist()
            else: rows = df.values.tolist()
            if not rows: return ([""],)
            idx = seed % len(rows); selected_row = rows[idx]; result = [str(column) if pd.notna(column) else "" for column in selected_row]; return (result,)
        except Exception as e: print(f"❌ Lỗi khi tải hoặc xử lý Google Sheet: {e}"); return ([""],)

class Duck_LoadGoogleDocLine:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"Url": ("STRING", {"default": "Google Docs URL"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("prompt",); FUNCTION = "load_line"; CATEGORY = "Duck Nodes/GoogleDocs"
    def load_line(self, Url, seed):
        if "https://docs.google.com/document/d/" not in Url: return ("",)
        try:
            doc_id_match = re.search(r"/document/d/([^/]+)", Url); doc_id = doc_id_match.group(1)
            txt_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"; response = requests.get(txt_url, timeout=10); response.raise_for_status()
            lines = [line.strip() for line in response.content.decode('utf-8').splitlines() if line.strip()];
            if not lines: return ("",)
            return (lines[seed % len(lines)],)
        except Exception as e: print(f"❌ Lỗi khi tải hoặc xử lý Google Doc: {e}"); return ("",)

class Duck_LoadExcelRow:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"file_path": ("STRING", {"default": "C:\\path\\to\\your\\file.xlsx"}), "sheet_name": ("STRING", {"default": "Sheet1"}), "Column": ("STRING", {"default": "A1:A"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("prompt",); OUTPUT_IS_LIST = (True,); FUNCTION = "load_row"; CATEGORY = "Duck Nodes/LocalFiles"
    def load_row(self, file_path, sheet_name, Column, seed):
        clean_path = file_path.strip().strip('"')
        if not os.path.exists(clean_path) or not clean_path.lower().endswith('.xlsx'): return ([[]],)
        try:
            df = pd.read_excel(clean_path, sheet_name=sheet_name, header=None); df.dropna(how='all', inplace=True)
            if df.empty: return ([[]],)
            if Column.strip():
                start_column, end_column_maybe = Column.split(":"); start_col_str, start_row_str_match = re.match(r"([A-Z]+)(\d*)", start_column).groups(); start_row_str = start_row_str_match if start_row_str_match else "1"; end_col_match = re.match(r"([A-Z]+)(\d*)", end_column_maybe); end_col_str, end_row_str = end_col_match.group(1), end_col_match.group(2)
                start_col, end_col = col_to_index(start_col_str), col_to_index(end_col_str); start_row = int(start_row_str) - 1; end_row = int(end_row_str) if end_row_str else len(df)
                rows = df.iloc[start_row:end_row, start_col:end_col+1].values.tolist()
            else: rows = df.values.tolist()
            if not rows: return ([[]],)
            idx = seed % len(rows); selected_row = rows[idx]; result = [str(column) if pd.notna(column) else "" for column in selected_row]; return (result,)
        except Exception as e: print(f"❌ Lỗi khi đọc file Excel: {e}"); return ([[]],)

class Duck_LoadWordLine:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"file_path": ("STRING", {"default": "C:\\path\\to\\your\\file.docx"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("prompt",); FUNCTION = "load_line"; CATEGORY = "Duck Nodes/LocalFiles"
    def load_line(self, file_path, seed):
        clean_path = file_path.strip().strip('"')
        if not os.path.exists(clean_path) or not clean_path.lower().endswith('.docx'): return ("",)
        try:
            document = docx.Document(clean_path); paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            if not paragraphs: return ("",)
            return (paragraphs[seed % len(paragraphs)],)
        except Exception as e: print(f"❌ Lỗi khi đọc file Word: {e}"); return ("",)

class Duck_PromptLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"file_path": ("STRING", {"default": "C:\path\to\your\file.txt"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING", "INT"); RETURN_NAMES = ("prompt", "line_count"); FUNCTION = "load_prompt"; CATEGORY = "Duck Nodes/LocalFiles"
    def load_prompt(self, file_path, seed):
        clean_path = file_path.strip().strip('"')
        if not os.path.exists(clean_path): return ("", 0)
        try:
            with open(clean_path, 'r', encoding='utf-8', errors='ignore') as f: lines = [line.strip() for line in f if line.strip()]
            if not lines: return ("", 0)
            return (lines[seed % len(lines)], len(lines))
        except Exception as e: print(f"❌ Lỗi khi đọc file: {e}"); return ("", 0)

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