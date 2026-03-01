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

# ============================================
# НАСТРОЙКИ
# ============================================
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'

users = {}
chats = {}
invites = {}
messages_count = 0
chat_counter = 0

print(f"""
============================================
🚀 МОЛЧА - Сервер
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
# ОСНОВНОЙ СЕРВЕР
# ============================================
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(20)
print(f"[{get_time()}] ✅ Сервер запущен, жду подключения...")

def handle_client(conn, addr):
    global chat_counter, messages_count
    name = None
    
    try:
        data = conn.recv(4096).decode()
        if not data:
            return
            
        msg = json.loads(data)
        
        if msg['type'] == 'login':
            name = msg['name']
            password = msg['password']
            
            if name in users:
                if verify_password(password, users[name]['password_hash'], users[name]['salt']):
                    users[name]['conn'] = conn
                    users[name]['online'] = True
                    users[name]['ip'] = addr[0]
                    print(f"[{get_time()}] ✅ {name} вошел")
                else:
                    conn.send(json.dumps({"type": "error", "text": "❌ Неверный пароль"}).encode())
                    return
            else:
                password_hash, salt = hash_password(password)
                users[name] = {
                    'conn': conn,
                    'online': True,
                    'ip': addr[0],
                    'password_hash': password_hash,
                    'salt': salt
                }
                print(f"[{get_time()}] ✨ Новый пользователь: {name}")
            
            # Отправляем список пользователей
            user_list = [u for u in users.keys() if u != name and users[u].get('online')]
            conn.send(json.dumps({"type": "user_list", "users": user_list}).encode())
            
            # Основной цикл
            while True:
                data = conn.recv(4096).decode()
                if not data:
                    break
                    
                msg = json.loads(data)
                
                if msg['type'] == 'get_users':
                    user_list = [u for u in users.keys() if u != name and users[u].get('online')]
                    conn.send(json.dumps({"type": "user_list", "users": user_list}).encode())
                
                elif msg['type'] == 'invite':
                    to = msg['to']
                    if to in users and users[to].get('online'):
                        if to not in invites:
                            invites[to] = []
                        if name not in invites[to]:
                            invites[to].append(name)
                        users[to]['conn'].send(json.dumps({"type": "invite", "from": name}).encode())
                        conn.send(json.dumps({"type": "info", "text": f"✅ Приглашение отправлено"}).encode())
                    else:
                        conn.send(json.dumps({"type": "error", "text": f"❌ {to} не в сети"}).encode())
                
                elif msg['type'] == 'accept':
                    from_user = msg['from']
                    chat_counter += 1
                    chat_id = f"chat_{chat_counter}"
                    chats[chat_id] = [name, from_user]
                    
                    if name in invites and from_user in invites[name]:
                        invites[name].remove(from_user)
                    
                    conn.send(json.dumps({"type": "chat_created", "chat_id": chat_id, "with": from_user}).encode())
                    if from_user in users:
                        users[from_user]['conn'].send(json.dumps({"type": "chat_created", "chat_id": chat_id, "with": name}).encode())
                    print(f"[{get_time()}] 💬 Новый чат: {name} и {from_user}")
                
                elif msg['type'] == 'message':
                    chat_id = msg['chat_id']
                    text = msg['text']
                    messages_count += 1
                    
                    if chat_id in chats:
                        for user in chats[chat_id]:
                            if user != name and user in users:
                                try:
                                    users[user]['conn'].send(json.dumps({
                                        "type": "chat_message",
                                        "chat_id": chat_id,
                                        "from": name,
                                        "text": text
                                    }).encode())
                                except:
                                    pass
                    
    except Exception as e:
        print(f"[{get_time()}] Ошибка: {e}")
    finally:
        if name and name in users:
            users[name]['online'] = False
            print(f"[{get_time()}] ❌ {name} отключился")
        conn.close()

# Главный цикл
while True:
    try:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except Exception as e:
        print(f"[{get_time()}] Ошибка: {e}")