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
messages = {}
message_queue = {}
start_time = time.time()
connections_count = 0
commands_count = 0

print(f"""
╔════════════════════════════════════════════════════════════╗
║                    🚀 МОЛЧА СЕРВЕР                        ║
║                    Создатель: Stardamnplugg (2026)        ║
╠════════════════════════════════════════════════════════════╣
║  📡 Порт: {PORT}                                              ║
║  🌍 URL: https://{os.environ.get('RAILWAY_STATIC_URL', 'localhost')}   ║
║  🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}        ║
╚════════════════════════════════════════════════════════════╝
""")

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def get_uptime():
    uptime = int(time.time() - start_time)
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    seconds = uptime % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def print_stats():
    """Вывод статистики"""
    online_users = [u for u in users.keys() if users[u].get('online')]
    print(f"\n[{get_time()}] ⏰ Uptime: {get_uptime()}")
    print(f"[{get_time()}] 📊 СТАТИСТИКА:")
    print(f"   • Всего пользователей: {len(users)}")
    print(f"   • Онлайн: {len(online_users)}")
    print(f"   • Активных чатов: {len(chats)}")
    print(f"   • Сообщений: {sum(len(m) for m in messages.values())}")
    print(f"   • Подключений: {connections_count}")
    print(f"   • Команд: {commands_count}")
    
    if online_users:
        print(f"\n[{get_time()}] 👥 Онлайн пользователи:")
        for user in online_users:
            connected = int(time.time() - users[user].get('connected_at', time.time()))
            print(f"   • {user} - {connected}с - {users[user].get('ip', 'unknown')}")
    
    if chats:
        print(f"\n[{get_time()}] 💬 Активные чаты:")
        for chat_id, participants in list(chats.items())[-5:]:
            msg_count = len(messages.get(chat_id, []))
            print(f"   • {chat_id}: {' и '.join(participants)} ({msg_count} сообщений)")

def hash_password(password):
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000, 32)
    return key.hex(), salt

def verify_password(password, stored_hash, salt):
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000, 32)
    return key.hex() == stored_hash

# ============================================
# HTTP HANDLER
# ============================================
class MolchaHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET запросы - статус"""
        global connections_count
        connections_count += 1
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        online = [u for u in users.keys() if users[u].get('online')]
        online_list = ''.join([f'<li>{u}</li>' for u in online])
        
        chats_list = ''
        for chat_id, parts in list(chats.items())[-10:]:
            msg_count = len(messages.get(chat_id, []))
            chats_list += f'<li>{chat_id}: {" и ".join(parts)} ({msg_count} сообщ.)</li>'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>МОЛЧА Сервер</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff00; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ border: 2px solid #00ff00; padding: 20px; margin-bottom: 20px; }}
                .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .box {{ border: 1px solid #00ff00; padding: 15px; }}
                .online {{ color: #00ff00; }}
                .offline {{ color: #ff0000; }}
                h1, h2 {{ color: #00ff00; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; }}
                .blink {{ animation: blink 1s infinite; }}
                @keyframes blink {{ 50% {{ opacity: 0; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 МОЛЧА СЕРВЕР</h1>
                    <p>Создатель: Stardamnplugg (2026)</p>
                    <p>Статус: <span class="online blink">🟢 ONLINE</span></p>
                </div>
                
                <div class="stats">
                    <div class="box">
                        <h2>📊 ОБЩАЯ СТАТИСТИКА</h2>
                        <p>⏰ Uptime: {get_uptime()}</p>
                        <p>👥 Всего пользователей: {len(users)}</p>
                        <p>🟢 Сейчас онлайн: {len(online)}</p>
                        <p>💬 Всего чатов: {len(chats)}</p>
                        <p>📨 Всего сообщений: {sum(len(m) for m in messages.values())}</p>
                        <p>🔌 Всего подключений: {connections_count}</p>
                        <p>⚡ Всего команд: {commands_count}</p>
                    </div>
                    
                    <div class="box">
                        <h2>🕐 ВРЕМЯ</h2>
                        <p>📅 Дата: {datetime.now().strftime('%Y-%m-%d')}</p>
                        <p>⏰ Время: {datetime.now().strftime('%H:%M:%S')}</p>
                        <p>⚡ Uptime: {get_uptime()}</p>
                    </div>
                </div>
                
                <div class="box">
                    <h2>👥 ОНЛАЙН ПОЛЬЗОВАТЕЛИ ({len(online)})</h2>
                    <ul>
                        {online_list if online_list else '<li>Нет пользователей</li>'}
                    </ul>
                </div>
                
                <div class="box">
                    <h2>💬 АКТИВНЫЕ ЧАТЫ ({len(chats)})</h2>
                    <ul>
                        {chats_list if chats_list else '<li>Нет активных чатов</li>'}
                    </ul>
                </div>
                
                <div class="footer">
                    <p>МОЛЧА v1.0 - Stardamnplugg (2026)</p>
                </div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def do_POST(self):
        """POST запросы - все команды чата"""
        global commands_count
        commands_count += 1
        
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
            print(f"[{get_time()}] ❌ Ошибка обработки запроса: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def handle_chat_command(self, data):
        """Обработка команд чата"""
        global connections_count
        
        cmd = data.get('command')
        user = data.get('user')
        password = data.get('password')
        
        print(f"[{get_time()}] 📨 Команда: {cmd} от {user}")
        
        # Логин/регистрация
        if cmd == 'login':
            if user in users:
                if verify_password(password, users[user]['password_hash'], users[user]['salt']):
                    users[user]['online'] = True
                    users[user]['last_seen'] = time.time()
                    users[user]['connected_at'] = time.time()
                    print(f"[{get_time()}] ✅ {user} вошел в систему")
                    return {
                        "status": "ok",
                        "users": [u for u in users.keys() if users[u].get('online') and u != user]
                    }
                else:
                    print(f"[{get_time()}] ❌ Неудачная попытка входа для {user}")
                    return {"status": "error", "message": "Неверный пароль"}
            else:
                password_hash, salt = hash_password(password)
                users[user] = {
                    'online': True,
                    'password_hash': password_hash,
                    'salt': salt,
                    'last_seen': time.time(),
                    'connected_at': time.time(),
                    'ip': self.client_address[0]
                }
                print(f"[{get_time()}] ✨ Новый пользователь: {user} (IP: {self.client_address[0]})")
                return {
                    "status": "ok",
                    "users": [u for u in users.keys() if users[u].get('online') and u != user]
                }
        
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
                print(f"[{get_time()}] 📨 {user} пригласил {to}")
                return {"status": "ok", "message": "Приглашение отправлено"}
            else:
                print(f"[{get_time()}] ⚠️ {user} пытался пригласить {to}, но {to} не в сети")
                return {"status": "error", "message": f"{to} не в сети"}
        
        # Принять приглашение
        elif cmd == 'accept':
            from_user = data.get('from')
            chat_id = f"{min(user, from_user)}_{max(user, from_user)}"
            
            if chat_id not in chats:
                chats[chat_id] = [user, from_user]
                messages[chat_id] = []
                print(f"[{get_time()}] 💬 НОВЫЙ ЧАТ! {user} принял приглашение от {from_user}")
                print(f"[{get_time()}] 💬 Чат {chat_id} создан между {user} и {from_user}")
                
                # Уведомляем обоих
                if from_user in message_queue:
                    message_queue[from_user].append({
                        "type": "info",
                        "text": f"✅ {user} принял ваше приглашение! Чат начат."
                    })
                if user in message_queue:
                    message_queue[user].append({
                        "type": "info",
                        "text": f"✅ Вы приняли приглашение от {from_user}! Чат начат."
                    })
            else:
                print(f"[{get_time()}] 💬 Чат {chat_id} уже существует")
            
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
                print(f"[{get_time()}] 💬 {user} -> {chat_id}: {text[:50]}{'...' if len(text)>50 else ''}")
                
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
                print(f"[{get_time()}] 📬 Отправлено {len(queue)} сообщений для {user}")
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
# СТАТИСТИКА В КОНСОЛЬ
# ============================================
def stats_printer():
    """Выводит статистику каждые 60 секунд"""
    while True:
        time.sleep(60)
        print_stats()

# ============================================
# ЗАПУСК
# ============================================
def main():
    # Запускаем поток статистики
    stats_thread = threading.Thread(target=stats_printer, daemon=True)
    stats_thread.start()
    
    # Запускаем HTTP сервер
    server = HTTPServer((HOST, PORT), MolchaHTTPHandler)
    print(f"[{get_time()}] ✅ HTTP сервер запущен на порту {PORT}")
    print(f"[{get_time()}] 🌍 http://{os.environ.get('RAILWAY_STATIC_URL', 'localhost')}:{PORT}")
    print(f"[{get_time()}] 📊 Статистика будет обновляться каждые 60 секунд")
    print("-" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{get_time()}] 👋 Остановка сервера...")
        print_stats()
        print(f"[{get_time()}] 👋 Сервер остановлен")

if __name__ == "__main__":
    main()
