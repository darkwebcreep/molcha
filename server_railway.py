#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import json
import os
import time
import hashlib
import secrets
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# ============================================
# НАСТРОЙКИ
# ============================================
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'

users = {}
chats = {}
invites = {}
messages = {}  # {chat_id: [сообщения]}
active_connections = {}  # {user: connection}
message_queue = {}  # {user: [сообщения]}

print(f"""
============================================
🚀 МОЛЧА - Сервер (HTTP mode)
👤 Создатель: Stardamnplugg (2026)
============================================
📡 Порт: {PORT}
🌍 Railway: {os.environ.get('RAILWAY_STATIC_URL', 'localhost')}
============================================
""")

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def hash_password(password):
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000, 32)
    return key.hex(), salt

def verify_password(password, stored_hash, salt):
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000, 32)
    return key.hex() == stored_hash

# ============================================
# HTTP HANDLER (все запросы через HTTP)
# ============================================
class MolchaHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET запросы - статус"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        online = len([u for u in users.values() if u.get('online')])
        html = f"""
        <html>
        <head>
            <title>МОЛЧА</title>
            <style>
                body {{ font-family: monospace; padding: 20px; background: #000; color: #0f0; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .header {{ border-bottom: 2px solid #0f0; padding: 10px; }}
                .stats {{ margin: 20px 0; }}
                .online {{ color: #0f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 МОЛЧА</h1>
                    <p>Создатель: Stardamnplugg (2026)</p>
                </div>
                <div class="stats">
                    <h3>Статус: <span class="online">ОНЛАЙН</span></h3>
                    <p>Пользователей онлайн: {online}</p>
                    <p>Всего пользователей: {len(users)}</p>
                    <p>Активных чатов: {len(chats)}</p>
                    <p>Время: {get_time()}</p>
                </div>
                <div class="online">
                    <h3>Сейчас онлайн:</h3>
                    <ul>
                    {''.join([f'<li>{u}</li>' for u in users.keys() if users[u].get('online')])}
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def do_POST(self):
        """POST запросы - все команды чата"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            response = self.handle_chat_command(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def handle_chat_command(self, data):
        """Обработка команд чата"""
        cmd = data.get('command')
        user = data.get('user')
        password = data.get('password')
        
        # Логин/регистрация
        if cmd == 'login':
            if user in users:
                if verify_password(password, users[user]['password_hash'], users[user]['salt']):
                    users[user]['online'] = True
                    users[user]['last_seen'] = time.time()
                    return {
                        "status": "ok",
                        "users": [u for u in users.keys() if users[u].get('online') and u != user]
                    }
            else:
                password_hash, salt = hash_password(password)
                users[user] = {
                    'online': True,
                    'password_hash': password_hash,
                    'salt': salt,
                    'last_seen': time.time()
                }
                return {
                    "status": "ok",
                    "users": [u for u in users.keys() if users[u].get('online') and u != user]
                }
            return {"status": "error", "message": "Неверный пароль"}
        
        # Получить список пользователей
        elif cmd == 'get_users':
            if user in users and users[user].get('online'):
                return {
                    "status": "ok",
                    "users": [u for u in users.keys() if users[u].get('online') and u != user]
                }
        
        # Отправить приглашение
        elif cmd == 'invite':
            to = data.get('to')
            if to in users and users[to].get('online'):
                if to not in message_queue:
                    message_queue[to] = []
                message_queue[to].append({
                    "type": "invite",
                    "from": user
                })
                return {"status": "ok", "message": "Приглашение отправлено"}
        
        # Принять приглашение
        elif cmd == 'accept':
            from_user = data.get('from')
            chat_id = f"{min(user, from_user)}_{max(user, from_user)}"
            
            if chat_id not in chats:
                chats[chat_id] = [user, from_user]
                messages[chat_id] = []
            
            return {"status": "ok", "chat_id": chat_id}
        
        # Отправить сообщение
        elif cmd == 'send_message':
            chat_id = data.get('chat_id')
            text = data.get('text')
            
            if chat_id in chats:
                if chat_id not in messages:
                    messages[chat_id] = []
                
                msg = {
                    "from": user,
                    "text": text,
                    "time": get_time()
                }
                messages[chat_id].append(msg)
                
                # Добавляем в очередь для другого пользователя
                for u in chats[chat_id]:
                    if u != user and u in users and users[u].get('online'):
                        if u not in message_queue:
                            message_queue[u] = []
                        message_queue[u].append({
                            "type": "message",
                            "chat_id": chat_id,
                            "from": user,
                            "text": text,
                            "time": get_time()
                        })
                
                return {"status": "ok"}
        
        # Получить новые сообщения
        elif cmd == 'poll':
            if user in message_queue and message_queue[user]:
                queue = message_queue[user]
                message_queue[user] = []
                return {"status": "ok", "messages": queue}
            return {"status": "ok", "messages": []}
        
        # Получить историю чата
        elif cmd == 'get_history':
            chat_id = data.get('chat_id')
            if chat_id in messages:
                return {"status": "ok", "messages": messages[chat_id]}
        
        return {"status": "error", "message": "Неизвестная команда"}
    
    def log_message(self, format, *args):
        pass

# ============================================
# ЗАПУСК
# ============================================
def main():
    # Запускаем HTTP сервер
    server = HTTPServer((HOST, PORT), MolchaHTTPHandler)
    print(f"[{get_time()}] ✅ Сервер запущен, жду подключения...")
    print(f"[{get_time()}] 🌍 http://{os.environ.get('RAILWAY_STATIC_URL', 'localhost')}:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{get_time()}] 👋 Сервер остановлен")

if __name__ == "__main__":
    main()
