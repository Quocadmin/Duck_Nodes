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
from aiohttp_session import setup, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
import folder_paths

node_dir = os.path.dirname(__file__)
comfy_dir = os.path.dirname(folder_paths.__file__)
user_data_dir = os.path.join(comfy_dir, "user")
password_path = os.path.join(user_data_dir, "PASSWORD")
config_path = os.path.join(user_data_dir, "login_config.json")
os.makedirs(user_data_dir, exist_ok=True)

TOKEN = ""
user_cache = {}
config_cache = None

translations = {
    "en": {
        "comfyui_login": "ComfyUI Login",
        "create_your_account": "Create Your Account",
        "welcome_back": "Welcome Back",
        "set_password_prompt": "Set a password to secure your ComfyUI instance.",
        "username": "Username",
        "enter_username": "Enter username",
        "password": "Password",
        "enter_password": "Enter password",
        "register_login": "Register & Login",
        "login": "Login",
        "skip_disable_login": "Skip (Disable Login)",
        "change_password_question": "Change Password?",
        "change_password": "Change Password",
        "old_password": "Old Password",
        "current_password": "Your current password",
        "new_password": "New Password",
        "choose_new_password": "Choose a new password",
        "confirm_new_password": "Confirm New Password",
        "confirm_the_new_password": "Confirm the new password",
        "update_password": "Update Password",
        "back_to_login": "Back to Login",
        "good_morning": "Good Morning",
        "good_afternoon": "Good Afternoon",
        "good_evening": "Good Evening",
        "feedback_user_pass_required": "Username and password are required for registration.",
        "feedback_wrong_password": "Wrong password.",
        "feedback_passwords_no_match": "New passwords do not match.",
        "feedback_new_password_empty": "New password cannot be empty.",
        "feedback_old_password_incorrect": "Old password is incorrect.",
        "feedback_password_changed_success": "Password changed successfully!",
    },
    "vi": {
        "comfyui_login": "Đăng nhập ComfyUI",
        "create_your_account": "Tạo tài khoản của bạn",
        "welcome_back": "Chào mừng trở lại",
        "set_password_prompt": "Đặt mật khẩu để bảo vệ ComfyUI của bạn.",
        "username": "Tên người dùng",
        "enter_username": "Nhập tên người dùng",
        "password": "Mật khẩu",
        "enter_password": "Nhập mật khẩu",
        "register_login": "Đăng ký & Đăng nhập",
        "login": "Đăng nhập",
        "skip_disable_login": "Bỏ qua (Tắt đăng nhập)",
        "change_password_question": "Đổi mật khẩu?",
        "change_password": "Đổi mật khẩu",
        "old_password": "Mật khẩu cũ",
        "current_password": "Mật khẩu hiện tại của bạn",
        "new_password": "Mật khẩu mới",
        "choose_new_password": "Chọn mật khẩu mới",
        "confirm_new_password": "Xác nhận mật khẩu mới",
        "confirm_the_new_password": "Xác nhận lại mật khẩu mới",
        "update_password": "Cập nhật mật khẩu",
        "back_to_login": "Quay lại Đăng nhập",
        "good_morning": "Chào buổi sáng",
        "good_afternoon": "Chào buổi chiều",
        "good_evening": "Chào buổi tối",
        "feedback_user_pass_required": "Yêu cầu tên người dùng và mật khẩu để đăng ký.",
        "feedback_wrong_password": "Sai mật khẩu.",
        "feedback_passwords_no_match": "Mật khẩu mới không khớp.",
        "feedback_new_password_empty": "Mật khẩu mới không được để trống.",
        "feedback_old_password_incorrect": "Mật khẩu cũ không chính xác.",
        "feedback_password_changed_success": "Đổi mật khẩu thành công!",
    }
}

def get_config():
    global config_cache
    if config_cache is not None:
        return config_cache

    if not os.path.exists(config_path):
        default_config = {"enabled": True, "language": "en"}
        with open(config_path, 'w') as f:
            json.dump(default_config, f)
        config_cache = default_config
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            config.setdefault("enabled", True)
            config.setdefault("language", "en")
            config_cache = config
            return config
    except Exception as e:
        print(f"❌ Error reading login config: {e}. Defaulting to basic config.")
        return {"enabled": True, "language": "en"}

def save_config(new_config):
    global config_cache
    with open(config_path, 'w') as f:
        json.dump(new_config, f)
    config_cache = new_config
    print(f"✅ Duck Nodes config updated: {new_config}")

def get_user_data():
    if 'username' in user_cache and 'password' in user_cache:
        return user_cache['username'], user_cache['password']
    
    if os.path.exists(password_path):
        try:
            with open(password_path, "rb") as f:
                stored_data = f.read().split(b'\n')
                password = stored_data[0]
                user_cache['password'] = password
                username = stored_data[1].decode('utf-8').strip() if len(stored_data) > 1 and stored_data[1].strip() else None
                user_cache['username'] = username
                return username, password
        except Exception as e:
            print(f"Error reading password file: {e}")
    return None, None

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')

prompt_server = server.PromptServer.instance
app = prompt_server.app
routes = prompt_server.routes

secret_key = generate_key()
setup(app, EncryptedCookieStorage(secret_key))

@routes.get("/login")
async def get_login_page(request):
    config = get_config()
    lang = config.get("language", "en")
    t = translations.get(lang, translations["en"])

    if not config.get("enabled", True):
        return web.HTTPFound('/')
    
    session = await get_session(request)
    if 'logged_in' in session and session['logged_in']:
        return web.HTTPFound('/')

    feedback_key = request.query.get('feedback_key', '')
    feedback_msg = t.get(feedback_key, '')
    
    env = Environment(loader=FileSystemLoader(node_dir), autoescape=select_autoescape(['html', 'xml']))
    template = env.get_template('login.html')
    first_time = not os.path.exists(password_path)
    
    return web.Response(
        text=template.render(first_time=first_time, feedback_msg=feedback_msg, T=t, lang=lang),
        content_type='text/html'
    )

@routes.post("/login/language")
async def set_language_handler(request):
    """Xử lý việc thay đổi ngôn ngữ từ giao diện đăng nhập."""
    data = await request.post()
    lang = data.get('lang')
    if lang in ['en', 'vi']:
        config = get_config()
        config['language'] = lang
        save_config(config)
    return web.HTTPFound('/login')


@routes.post("/login")
async def login_handler(request):
    if not get_config().get("enabled", True): return web.HTTPFound('/')
    
    data = await request.post()
    password_input = data.get('password', '').encode('utf-8')

    first_time_setup = not os.path.exists(password_path)
    if first_time_setup:
        username_input = data.get('username')
        if not username_input or not password_input:
            return web.HTTPFound('/login?feedback_key=feedback_user_pass_required')

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_input, salt)
        with open(password_path, "wb") as file:
            file.write(hashed_password + b'\n' + username_input.encode('utf-8'))
        
        user_cache.clear()
        get_user_data()
        config = get_config()
        config["enabled"] = True
        save_config(config)

        session = await get_session(request)
        session['logged_in'] = True
        session['username'] = username_input
        return web.HTTPFound('/')
    else:
        username_cached, password_cached = get_user_data()
        if password_cached and bcrypt.checkpw(password_input, password_cached):
            session = await get_session(request)
            session['logged_in'] = True
            session['username'] = username_cached
            return web.HTTPFound('/')
        else:
            return web.HTTPFound('/login?feedback_key=feedback_wrong_password')

@routes.post("/login/skip")
async def skip_login_setup(request):
    if not os.path.exists(password_path):
        config = get_config()
        config["enabled"] = False
        save_config(config)
    return web.HTTPFound('/')

@routes.post("/login/change")
async def change_password_handler(request):
    if not get_config().get("enabled", True): return web.HTTPFound('/')
    
    data = await request.post()
    old_password = data.get('old_password', '').encode('utf-8')
    new_password = data.get('new_password', '').encode('utf-8')
    confirm_password = data.get('confirm_password', '').encode('utf-8')

    if new_password != confirm_password:
        return web.HTTPFound('/login?feedback_key=feedback_passwords_no_match')
    if not new_password:
        return web.HTTPFound('/login?feedback_key=feedback_new_password_empty')

    username_cached, password_cached = get_user_data()
    if not password_cached or not bcrypt.checkpw(old_password, password_cached):
        return web.HTTPFound('/login?feedback_key=feedback_old_password_incorrect')

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(new_password, salt)
    with open(password_path, "wb") as file:
        file.write(hashed_password + b'\n' + (username_cached or '').encode('utf-8'))
    
    user_cache.clear()
    return web.HTTPFound('/login?feedback_key=feedback_password_changed_success')

@routes.get("/logout")
async def logout_handler(request):
    session = await get_session(request)
    session['logged_in'] = False
    session.pop('username', None)
    return web.HTTPFound('/login')

@routes.get("/duck_nodes/settings")
async def get_duck_nodes_settings(request):
    return web.json_response(get_config())

@routes.post("/duck_nodes/settings")
async def post_duck_nodes_settings(request):
    data = await request.json()
    current_config = get_config()

    if 'enabled' in data and isinstance(data['enabled'], bool):
        current_config['enabled'] = data['enabled']

    save_config(current_config)

    if current_config['enabled'] and not os.path.exists(password_path):
            return web.json_response({"status": "requires_setup"})
    return web.json_response({"status": "ok"})


@web.middleware
async def check_login_status(request: web.Request, handler):
    if not get_config().get("enabled", True):
        return await handler(request)

    if request.path.startswith('/login') or \
       request.path.startswith('/duck_nodes/') or \
       request.path.endswith(('.css', '.js', '.png', '.svg')):
        return await handler(request)
    
    if not os.path.exists(password_path):
        return web.HTTPFound('/login')

    session = await get_session(request)
    if 'logged_in' in session and session['logged_in']:
        return await handler(request)

    global TOKEN
    if not TOKEN:
        _, pw_hash = get_user_data()
        if pw_hash:
             TOKEN = base64.b64encode(pw_hash).decode('utf-8')

    if args.enable_cors_header:
        authorization_header = request.headers.get("Authorization")
        if authorization_header and authorization_header.split()[-1] == TOKEN:
            return await handler(request)
    if request.query.get("token") == TOKEN:
        return await handler(request)
    
    return web.HTTPFound('/login')

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
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "load_one_row"
    CATEGORY = "Duck Nodes/GoogleSheet"
    
    def load_one_row(self, Url, Column, seed):
        if "https://docs.google.com/spreadsheets/d/" not in Url: return ([""],)
        try:
            sheet_id = Url.split("/")[5]; gid_match = re.search(r"gid=(\d+)", Url); gid = gid_match.group(1) if gid_match else "0"
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"; response = requests.get(csv_url, timeout=10); response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), header=None); df.dropna(how='all', inplace=True)
            if df.empty: return ([""],)
            if Column.strip():
                start_column, end_column_maybe = Column.split(":"); 
                start_col_str, start_row_str_match = re.match(r"([A-Z]+)(\d*)", start_column).groups();
                start_row_str = start_row_str_match if start_row_str_match else "1";
                end_col_match = re.match(r"([A-Z]+)(\d*)", end_column_maybe);
                end_col_str, end_row_str = end_col_match.group(1), end_col_match.group(2)
                start_col, end_col = col_to_index(start_col_str), col_to_index(end_col_str);
                start_row = int(start_row_str) - 1; 
                end_row = int(end_row_str) if end_row_str else len(df)
                rows = df.iloc[start_row:end_row, start_col:end_col+1].values.tolist()
            else: 
                rows = df.values.tolist()
            if not rows: return ([""],)
            idx = seed % len(rows); selected_row = rows[idx]; result = [str(column) if pd.notna(column) else "" for column in selected_row]; return (result,)
        except Exception as e: print(f"❌ Lỗi khi tải hoặc xử lý Google Sheet: {e}"); return ([""],)

class Duck_LoadGoogleDocLine:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"Url": ("STRING", {"default": "Google Docs URL"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "load_line"
    CATEGORY = "Duck Nodes/GoogleDocs"
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
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "load_row"
    CATEGORY = "Duck Nodes/LocalFiles"

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
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "load_line"
    CATEGORY = "Duck Nodes/LocalFiles"
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
        return {"required": {"file_path": ("STRING", {"default": "C:\\path\\to\\your\\file.txt"}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),}}
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("prompt", "line_count")
    FUNCTION = "load_prompt"
    CATEGORY = "Duck Nodes/LocalFiles"
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
    "Duck_PromptLoader": "Duck - Load Prompt From File",
}
