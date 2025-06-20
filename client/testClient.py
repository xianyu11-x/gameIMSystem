#!/usr/bin/env python3
import socket
import struct
import sys
import os
import threading
import time
import random
import uuid
from typing import Optional, Callable

# 添加协议目录到Python路径中
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build/protocol"))

# 尝试导入protobuf生成的模块
try:
    from common import BaseMsg_pb2
    from common import player_pb2
    from common import chatMessage_pb2
    from common import channel_pb2
    from gatesvr import CSMsg_pb2
except ImportError:
    print("错误: 无法导入Protocol Buffers模块")
    print("请确保已经编译proto文件并且生成了Python绑定")
    sys.exit(1)

class TestClient:
    """用于压力测试的简化客户端类"""
    
    def __init__(self, client_id: int, host: str = "localhost", port: int = 8888):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.socket = None
        self.player_name = None
        self.player_token = None
        self.player_id = None
        self.running = False
        self.connected = False
        self.receiver_thread = None
        self.assigned_username = None  # 预分配的用户名
        
        # 统计信息
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'login_attempts': 0,
            'login_success': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 详细记录信息
        self.detailed_logs = {
            'sent_commands': [],      # 发送的命令记录
            'received_private_chats': [],  # 接收到的私人聊天消息
            'received_channel_chats': [],  # 接收到的群聊消息
            'login_events': [],       # 登录相关事件
            'channel_events': []      # 频道相关事件
        }
        
        # 消息ID管理
        self._pending_requests = {}  # 存储等待响应的请求 {msgId: request_info}
        self._msg_id_lock = threading.Lock()
        
        # 回调函数
        self.on_message_received: Optional[Callable] = None
        self.on_login_success: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def connect(self) -> bool:
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.stats['start_time'] = time.time()
            
            # 启动接收线程
            self.running = True
            self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
            self.receiver_thread.start()
            return True
        except Exception as e:
            self.stats['errors'] += 1
            if self.on_error:
                self.on_error(f"Client {self.client_id} connect failed: {str(e)}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.stats['end_time'] = time.time()
        
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
            self.socket = None
        
        self.connected = False
        
        if self.receiver_thread and self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=2.0)
    
    def send_message(self, message_bytes: bytes) -> bool:
        """发送消息"""
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.sendall(message_bytes)
            self.stats['messages_sent'] += 1
            
            # 记录发送的命令
            self._log_sent_command(message_bytes)
            
            return True
        except Exception as e:
            self.stats['errors'] += 1
            if self.on_error:
                self.on_error(f"Client {self.client_id} send failed: {str(e)}")
            self.connected = False
            return False
    
    def receive_message(self, timeout: float = 1.0) -> Optional[bytearray]:
        """接收消息"""
        if not self.connected or not self.socket:
            return None
        
        try:
            self.socket.settimeout(timeout)
            buffer_size = 4096
            received_bytes = bytearray()
            
            # 接收第一块数据
            chunk = self.socket.recv(buffer_size)
            if not chunk:
                self.connected = False
                return None
            received_bytes.extend(chunk)
            
            # 尝试接收更多数据（非阻塞）
            try:
                self.socket.settimeout(0.01)
                while True:
                    try:
                        more_data = self.socket.recv(buffer_size)
                        if not more_data:
                            break
                        received_bytes.extend(more_data)
                    except socket.timeout:
                        break
            except Exception:
                pass
            finally:
                self.socket.settimeout(None)
                
            return received_bytes
            
        except socket.timeout:
            return None
        except Exception as e:
            if self.running:
                self.stats['errors'] += 1
                if self.on_error:
                    self.on_error(f"Client {self.client_id} receive failed: {str(e)}")
            self.connected = False
            return None
    
    def _receiver_loop(self):
        """消息接收循环"""
        last_cleanup_time = time.time()
        cleanup_interval = 30.0  # 每30秒清理一次超时请求
        
        while self.running and self.connected:
            response_bytes = self.receive_message(timeout=1.0)
            if response_bytes:
                self.stats['messages_received'] += 1
                self.handle_incoming_message(response_bytes)
            elif not self.connected and self.running:
                break
            
            # 定期清理超时的请求
            current_time = time.time()
            if current_time - last_cleanup_time > cleanup_interval:
                self._cleanup_old_requests()
                last_cleanup_time = current_time
    
    def create_base_message(self, msg_type, body, body_type=BaseMsg_pb2.MsgBodyType.EN_REQ, msg_id: str = None):
        """创建基础消息"""
        base_msg = BaseMsg_pb2.baseMsg()
        msg_info = BaseMsg_pb2.MsgInfo()
        msg_info.msgType = msg_type
        msg_info.msgSender = BaseMsg_pb2.MsgSender.EN_MSG_SENDER_CLIENT
        msg_info.msgBodyType = body_type
        
        # 如果没有提供msgId且是请求消息，则生成一个
        if msg_id is None and body_type == BaseMsg_pb2.MsgBodyType.EN_REQ:
            msg_id = self._generate_msg_id()
        
        # 设置msgId
        if msg_id:
            msg_info.msgId = msg_id
            
        base_msg.msgInfo.CopyFrom(msg_info)
        base_msg.msgBody = body
        return base_msg, msg_id

    def create_login_request(self, username: str) -> tuple[bytes, str]:
        """创建登录请求"""
        player_info = player_pb2.PlayerInfo()
        player_info.playerId = 0
        player_info.playerName = username
        player_info.playerToken = ""
        
        login_req_payload = CSMsg_pb2.CSLoginMsgReq()
        login_req_payload.msgType = CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGIN
        login_req_payload.info.CopyFrom(player_info)
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_LOGIN
        cs_msg_req.loginReq.CopyFrom(login_req_payload)
        
        base_msg, msg_id = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ
        )
        
        # 注册请求
        self._register_request(msg_id, 'login', username=username)
        
        return base_msg.SerializeToString(), msg_id
    
    def create_logout_request(self) -> tuple[bytes, str]:
        """创建登出请求"""
        player_info = player_pb2.PlayerInfo()
        if self.player_id is not None:
            player_info.playerId = self.player_id
        if self.player_name is not None:
            player_info.playerName = self.player_name
        if self.player_token is not None:
            player_info.playerToken = self.player_token
        
        logout_req_payload = CSMsg_pb2.CSLoginMsgReq()
        logout_req_payload.msgType = CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGOUT
        logout_req_payload.info.CopyFrom(player_info)
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_LOGIN
        cs_msg_req.loginReq.CopyFrom(logout_req_payload)
        
        base_msg, msg_id = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ
        )
        
        # 注册请求
        self._register_request(msg_id, 'logout', player_name=self.player_name)
        
        return base_msg.SerializeToString(), msg_id

    def create_chat_request(self, message_text: str, recipient_name: str) -> tuple[bytes, str]:
        """创建聊天请求 - 必须指定接收者"""
        if not recipient_name:
            raise ValueError("Chat message must have a recipient_name specified")
        
        cs_chat_req_payload = CSMsg_pb2.CSChatMsgReq()
        cs_chat_req_payload.msgType = CSMsg_pb2.CSChatMsgType.EN_SEND

        # 填充发送者信息
        cs_chat_req_payload.sendPlayer.playerId = self.player_id or 0
        cs_chat_req_payload.sendPlayer.playerName = self.player_name or self.assigned_username or f"TestUser{self.client_id}"
        if self.player_token:
            cs_chat_req_payload.sendPlayer.playerToken = self.player_token

        # 填充接收者信息 - 必须指定
        cs_chat_req_payload.receivePlayer.playerName = recipient_name
        cs_chat_req_payload.receivePlayer.playerId = 0  # 服务器会根据名称查找ID

        # 创建聊天消息
        chat_msg_content = cs_chat_req_payload.chatMessage.add()
        chat_msg_content.msg = message_text
        chat_msg_content.sendPlayer.CopyFrom(cs_chat_req_payload.sendPlayer)
        chat_msg_content.time = int(time.time())

        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_req.chatReq.CopyFrom(cs_chat_req_payload)

        return self._create_request_with_msg_id(
            cs_msg_req, 'chat_send', 
            message=message_text, recipient=recipient_name
        )

    def create_channel_request(self, msg_type, channel_name: Optional[str] = None, 
                             channel_id: Optional[int] = None, message_text: Optional[str] = None) -> tuple[bytes, str]:
        """创建频道请求"""
        cs_channel_req_payload = CSMsg_pb2.CSChannelMsgReq()
        cs_channel_req_payload.msgType = msg_type

        # 填充发送者信息
        cs_channel_req_payload.sendPlayer.playerId = self.player_id or 0
        cs_channel_req_payload.sendPlayer.playerName = self.player_name or self.assigned_username or f"TestUser{self.client_id}"
        if self.player_token:
            cs_channel_req_payload.sendPlayer.playerToken = self.player_token

        # 填充频道信息
        if channel_name or channel_id:
            cs_channel_req_payload.channelInfo.channelName = channel_name or ""
            if channel_id is not None:
                cs_channel_req_payload.channelInfo.channelId = channel_id

        # 如果是发送消息，添加消息内容
        if message_text and msg_type == CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_SEND:
            chat_msg_content = cs_channel_req_payload.chatMessage.add()
            chat_msg_content.msg = message_text
            chat_msg_content.sendPlayer.CopyFrom(cs_channel_req_payload.sendPlayer)
            chat_msg_content.time = int(time.time())

        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_req.channelReq.CopyFrom(cs_channel_req_payload)

        # 使用通用方法创建带msgId的请求
        return self._create_request_with_msg_id(
            cs_msg_req, 
            f"channel_{msg_type}",
            channel_name=channel_name,
            channel_id=channel_id,
            message_text=message_text
        )

    def create_chat_history_request(self) -> tuple[bytes, str]:
        """创建拉取聊天历史消息请求"""
        cs_chat_req_payload = CSMsg_pb2.CSChatMsgReq()
        cs_chat_req_payload.msgType = CSMsg_pb2.CSChatMsgType.EN_HISTORY

        # 填充发送者信息
        cs_chat_req_payload.sendPlayer.playerId = self.player_id or 0
        cs_chat_req_payload.sendPlayer.playerName = self.player_name or self.assigned_username or f"TestUser{self.client_id}"
        if self.player_token:
            cs_chat_req_payload.sendPlayer.playerToken = self.player_token

        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_req.chatReq.CopyFrom(cs_chat_req_payload)

        # 使用通用方法创建带msgId的请求
        return self._create_request_with_msg_id(cs_msg_req, "chat_history")

    def fetch_chat_history(self) -> bool:
        """拉取聊天历史消息"""
        if not self.connected or not self.player_name:
            return False

        history_msg_bytes, msg_id = self.create_chat_history_request()
        success = self.send_message(history_msg_bytes)
        if success:
            print(f"Client {self.client_id} 发送聊天历史请求，msgId: {msg_id}")
        return success

    def create_chat_receive_acknowledgment(self, received_msg_req, original_msg_id: str = None) -> bytes:
        """创建聊天消息接收确认"""
        cs_chat_rsp_payload = CSMsg_pb2.CSChatMsgRsp()
        cs_chat_rsp_payload.msgType = CSMsg_pb2.CSChatMsgType.EN_RECEIVE
        
        # 复制发送者信息
        cs_chat_rsp_payload.sendPlayer.CopyFrom(received_msg_req.chatReq.sendPlayer)
        cs_chat_rsp_payload.isSuccess = True
        
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_rsp.chatRsp.CopyFrom(cs_chat_rsp_payload)
        
        base_msg, _ = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_rsp.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_RSP,
            msg_id=original_msg_id
        )
        
        return base_msg.SerializeToString()

    def create_channel_receive_acknowledgment(self, received_msg_req, original_msg_id: str = None) -> bytes:
        """创建频道消息接收确认"""
        cs_channel_rsp_payload = CSMsg_pb2.CSChannelMsgRsp()
        cs_channel_rsp_payload.msgType = CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_RECEIVE
        
        # 复制发送者信息
        cs_channel_rsp_payload.sendPlayer.CopyFrom(received_msg_req.channelReq.sendPlayer)
        cs_channel_rsp_payload.isSuccess = True
        
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_rsp.channelRsp.CopyFrom(cs_channel_rsp_payload)
        
        base_msg, _ = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_rsp.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_RSP,
            msg_id=original_msg_id
        )
        
        return base_msg.SerializeToString()

    def login(self, username: str) -> bool:
        """登录"""
        if not self.connected:
            return False
        
        self.stats['login_attempts'] += 1
        
        # 记录登录尝试
        self.detailed_logs['login_events'].append({
            'timestamp': time.time(),
            'event': 'login_attempt',
            'username': username,
            'client_id': self.client_id
        })
        
        login_msg_bytes, msg_id = self.create_login_request(username)
        return self.send_message(login_msg_bytes)
    
    def logout(self) -> bool:
        """登出"""
        if not self.connected or not self.player_name:
            return False
        
        # 记录登出事件
        self.detailed_logs['login_events'].append({
            'timestamp': time.time(),
            'event': 'logout_attempt',
            'username': self.player_name,
            'client_id': self.client_id
        })
        
        logout_msg_bytes, msg_id = self.create_logout_request()
        success = self.send_message(logout_msg_bytes)
        if success:
            self.player_name = None
            self.player_token = None
            self.player_id = None
        return success
    
    def send_chat_message(self, message_text: str, recipient_name: str) -> bool:
        """发送聊天消息 - 必须指定接收者"""
        if not self.connected or not self.player_name:
            return False
        
        if not recipient_name:
            if self.on_error:
                self.on_error(f"Client {self.client_id} attempted to send chat without recipient")
            return False
        
        try:
            chat_msg_bytes, msg_id = self.create_chat_request(message_text, recipient_name)
            return self.send_message(chat_msg_bytes)
        except ValueError as e:
            if self.on_error:
                self.on_error(f"Client {self.client_id} chat error: {str(e)}")
            return False
    
    def join_channel(self, channel_name: str) -> bool:
        """加入频道"""
        if not self.connected or not self.player_name:
            return False
        
        # 记录频道事件
        self.detailed_logs['channel_events'].append({
            'timestamp': time.time(),
            'event': 'join_channel',
            'channel_name': channel_name,
            'client_id': self.client_id,
            'player_name': self.player_name
        })
        
        channel_msg_bytes, msg_id = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_JOIN,
            channel_name=channel_name
        )
        success = self.send_message(channel_msg_bytes)
        if success:
            print(f"Client {self.client_id} 发送加入频道请求，频道: {channel_name}，msgId: {msg_id}")
        return success
    
    def send_channel_message(self, channel_name: str, message_text: str) -> bool:
        """发送频道消息"""
        if not self.connected or not self.player_name:
            return False
        
        channel_msg_bytes, msg_id = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_SEND,
            channel_name=channel_name,
            message_text=message_text
        )
        success = self.send_message(channel_msg_bytes)
        if success:
            print(f"Client {self.client_id} 发送频道消息，频道: {channel_name}，内容: {message_text}，msgId: {msg_id}")
        return success
    
    def create_channel(self, channel_name: str) -> bool:
        """创建频道"""
        if not self.connected or not self.player_name:
            return False
        
        # 记录频道事件
        self.detailed_logs['channel_events'].append({
            'timestamp': time.time(),
            'event': 'create_channel',
            'channel_name': channel_name,
            'client_id': self.client_id,
            'player_name': self.player_name
        })
        
        channel_msg_bytes, msg_id = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_CREATE,
            channel_name=channel_name
        )
        success = self.send_message(channel_msg_bytes)
        if success:
            print(f"Client {self.client_id} 发送创建频道请求，频道: {channel_name}，msgId: {msg_id}")
        return success
    
    def destroy_channel(self, channel_name: str) -> bool:
        """销毁频道"""
        if not self.connected or not self.player_name:
            return False
        
        # 记录频道事件
        self.detailed_logs['channel_events'].append({
            'timestamp': time.time(),
            'event': 'destroy_channel',
            'channel_name': channel_name,
            'client_id': self.client_id,
            'player_name': self.player_name
        })
        
        channel_msg_bytes, msg_id = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_DESTROY,
            channel_name=channel_name
        )
        success = self.send_message(channel_msg_bytes)
        if success:
            print(f"Client {self.client_id} 发送销毁频道请求，频道: {channel_name}，msgId: {msg_id}")
        return success
    
    def handle_incoming_message(self, response_bytes: bytearray):
        """处理接收到的消息"""
        try:
            base_msg = BaseMsg_pb2.baseMsg()
            base_msg.ParseFromString(response_bytes)
            
            msg_info = base_msg.msgInfo
            msg_id = msg_info.msgId if msg_info.msgId else None
            
            if msg_info.msgType == BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS:
                if msg_info.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_RSP:
                    # 处理响应消息
                    cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
                    cs_msg_rsp.ParseFromString(base_msg.msgBody)
                    
                    # 如果有msgId，获取对应的请求信息
                    original_request = None
                    if msg_id:
                        original_request = self._get_and_remove_request(msg_id)
                        if original_request:
                            print(f"Client {self.client_id}: 收到响应 msgId={msg_id}, 原请求类型: {original_request['request_type']}")
                    
                    if cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_LOGIN:
                        login_rsp = cs_msg_rsp.loginRsp
                        if login_rsp.isSuccess and login_rsp.info.playerName:
                            # 登录成功
                            self.player_id = login_rsp.info.playerId
                            self.player_name = login_rsp.info.playerName
                            self.player_token = login_rsp.info.playerToken
                            self.stats['login_success'] += 1
                            
                            # 记录登录成功事件
                            self.detailed_logs['login_events'].append({
                                'timestamp': time.time(),
                                'event': 'login_success',
                                'username': self.player_name,
                                'player_id': self.player_id,
                                'client_id': self.client_id,
                                'msg_id': msg_id,
                                'original_request': original_request
                            })
                            
                            if self.on_login_success:
                                self.on_login_success(self.client_id, self.player_name)
                            
                            # 登录成功后自动拉取历史消息
                            def delayed_fetch_history():
                                time.sleep(0.5)  # 等待一下再拉取历史消息
                                self.fetch_chat_history()
                            
                            threading.Thread(target=delayed_fetch_history, daemon=True).start()
                    
                    elif cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_CHAT:
                        # 处理聊天响应（包括历史消息响应）
                        if cs_msg_rsp.HasField('chatRsp'):
                            chat_rsp = cs_msg_rsp.chatRsp
                            if chat_rsp.msgType == CSMsg_pb2.CSChatMsgType.EN_HISTORY:
                                # 历史消息响应，通常不需要特殊处理
                                pass
                
                elif msg_info.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_REQ:
                    # 处理请求消息（来自其他客户端的消息）
                    cs_msg_req = CSMsg_pb2.CSMsgReq()
                    cs_msg_req.ParseFromString(base_msg.msgBody)
                    
                    # 处理聊天消息接收
                    if cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHAT and cs_msg_req.HasField('chatReq'):
                        chat_req = cs_msg_req.chatReq
                        if chat_req.msgType == CSMsg_pb2.CSChatMsgType.EN_RECEIVE:
                            # 记录接收到的私聊消息
                            self._log_received_private_chat(chat_req)
                            
                            # 发送接收确认
                            ack_msg_bytes = self.create_chat_receive_acknowledgment(cs_msg_req, original_msg_id=msg_id)
                            self.send_message(ack_msg_bytes)
                    
                    # 处理频道消息接收
                    elif cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHANNEL and cs_msg_req.HasField('channelReq'):
                        channel_req = cs_msg_req.channelReq
                        if channel_req.msgType == CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_RECEIVE:
                            # 记录接收到的群聊消息
                            self._log_received_channel_chat(channel_req)
                            
                            # 发送接收确认
                            ack_msg_bytes = self.create_channel_receive_acknowledgment(cs_msg_req, original_msg_id=msg_id)
                            self.send_message(ack_msg_bytes)
                    
                    if self.on_message_received:
                        self.on_message_received(self.client_id, cs_msg_req)
            
        except Exception as e:
            self.stats['errors'] += 1
            if self.on_error:
                self.on_error(f"Client {self.client_id} handle message failed: {str(e)}")
            try:
                print(f"DEBUG - Error parsing message. BytesLen={len(response_bytes)}, "
                  f"Bytes={response_bytes.hex()}")
            except:
                pass
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats_copy = self.stats.copy()
        if stats_copy['start_time'] and stats_copy['end_time']:
            stats_copy['duration'] = stats_copy['end_time'] - stats_copy['start_time']
        elif stats_copy['start_time']:
            stats_copy['duration'] = time.time() - stats_copy['start_time']
        else:
            stats_copy['duration'] = 0
        
        # 添加详细日志统计
        stats_copy['detailed_counts'] = {
            'sent_commands': len(self.detailed_logs['sent_commands']),
            'received_private_chats': len(self.detailed_logs['received_private_chats']),
            'received_channel_chats': len(self.detailed_logs['received_channel_chats']),
            'login_events': len(self.detailed_logs['login_events']),
            'channel_events': len(self.detailed_logs['channel_events'])
        }
        
        return stats_copy

    def _log_sent_command(self, message_bytes: bytes, command_type: str = "unknown"):
        """记录发送的命令"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'command_type': command_type,
                'size_bytes': len(message_bytes),
                'client_id': self.client_id,
                'player_name': self.player_name or "not_logged_in"
            }
            
            # 尝试解析消息类型以获取更详细信息
            try:
                base_msg = BaseMsg_pb2.baseMsg()
                base_msg.ParseFromString(message_bytes)
                
                if base_msg.msgInfo.msgType == BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS:
                    cs_msg_req = CSMsg_pb2.CSMsgReq()
                    cs_msg_req.ParseFromString(base_msg.msgBody)
                    
                    if cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_LOGIN:
                        log_entry['command_type'] = 'login'
                        if cs_msg_req.HasField('loginReq'):
                            if cs_msg_req.loginReq.msgType == CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGIN:
                                log_entry['action'] = 'player_login'
                                log_entry['username'] = cs_msg_req.loginReq.info.playerName
                            elif cs_msg_req.loginReq.msgType == CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGOUT:
                                log_entry['action'] = 'player_logout'
                    
                    elif cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHAT:
                        log_entry['command_type'] = 'chat'
                        if cs_msg_req.HasField('chatReq'):
                            if cs_msg_req.chatReq.msgType == CSMsg_pb2.CSChatMsgType.EN_SEND:
                                log_entry['action'] = 'send_private_message'
                                log_entry['recipient'] = cs_msg_req.chatReq.receivePlayer.playerName if cs_msg_req.chatReq.HasField('receivePlayer') else 'unknown'
                                # 获取消息内容（可能在chatMessage字段中）
                                if len(cs_msg_req.chatReq.chatMessage) > 0:
                                    msg_content = cs_msg_req.chatReq.chatMessage[0].msg
                                    log_entry['message'] = msg_content[:50] + "..." if len(msg_content) > 50 else msg_content
                            elif cs_msg_req.chatReq.msgType == CSMsg_pb2.CSChatMsgType.EN_HISTORY:
                                log_entry['action'] = 'fetch_history'
                            elif cs_msg_req.chatReq.msgType == CSMsg_pb2.CSChatMsgType.EN_RECEIVE:
                                log_entry['action'] = 'ack_message'
                    
                    elif cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHANNEL:
                        log_entry['command_type'] = 'channel'
                        if cs_msg_req.HasField('channelReq'):
                            if cs_msg_req.channelReq.msgType == CSMsg_pb2.CSChannelMsgType.EN_CREATE:
                                log_entry['action'] = 'create_channel'
                                log_entry['channel_name'] = cs_msg_req.channelReq.channelInfo.channelName if cs_msg_req.channelReq.HasField('channelInfo') else 'unknown'
                            elif cs_msg_req.channelReq.msgType == CSMsg_pb2.CSChannelMsgType.EN_DESTROY:
                                log_entry['action'] = 'destroy_channel'
                                log_entry['channel_name'] = cs_msg_req.channelReq.channelInfo.channelName if cs_msg_req.channelReq.HasField('channelInfo') else 'unknown'
                            elif cs_msg_req.channelReq.msgType == CSMsg_pb2.CSChannelMsgType.EN_JOIN:
                                log_entry['action'] = 'join_channel'
                                log_entry['channel_name'] = cs_msg_req.channelReq.channelInfo.channelName if cs_msg_req.channelReq.HasField('channelInfo') else 'unknown'
                            elif cs_msg_req.channelReq.msgType == CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_SEND:
                                log_entry['action'] = 'send_channel_message'
                                log_entry['channel_name'] = cs_msg_req.channelReq.channelInfo.channelName if cs_msg_req.channelReq.HasField('channelInfo') else 'unknown'
                                # 获取消息内容（可能在chatMessage字段中）
                                if len(cs_msg_req.channelReq.chatMessage) > 0:
                                    msg_content = cs_msg_req.channelReq.chatMessage[0].msg
                                    log_entry['message'] = msg_content[:50] + "..." if len(msg_content) > 50 else msg_content
                            elif cs_msg_req.channelReq.msgType == CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_RECEIVE:
                                log_entry['action'] = 'ack_channel_message'
                                log_entry['channel_name'] = cs_msg_req.channelReq.channelInfo.channelName if cs_msg_req.channelReq.HasField('channelInfo') else 'unknown'
            except Exception:
                # 如果解析失败，保持基本信息
                pass
            
            self.detailed_logs['sent_commands'].append(log_entry)
            
        except Exception as e:
            # 记录错误但不影响正常发送
            if self.on_error:
                self.on_error(f"Client {self.client_id} command logging error: {str(e)}")
    
    def _log_received_private_chat(self, chat_req):
        """记录接收到的私聊消息"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'sender': 'unknown',
                'message': '',
                'message_id': 0,
                'send_time': 0,
                'client_id': self.client_id,
                'receiver': self.player_name or "unknown"
            }
            
            # 从聊天消息列表中获取信息
            if len(chat_req.chatMessage) > 0:
                chat_msg = chat_req.chatMessage[0]
                log_entry['sender'] = chat_msg.sendPlayer.playerName if chat_msg.HasField('sendPlayer') else 'unknown'
                log_entry['message'] = chat_msg.msg
                log_entry['send_time'] = chat_msg.time
            
            self.detailed_logs['received_private_chats'].append(log_entry)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Client {self.client_id} private chat logging error: {str(e)}")
    
    def _log_received_channel_chat(self, channel_req):
        """记录接收到的群聊消息"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'channel_name': channel_req.channelInfo.channelName if channel_req.HasField('channelInfo') else 'unknown',
                'sender': 'unknown',
                'message': '',
                'message_id': 0,
                'send_time': 0,
                'client_id': self.client_id,
                'receiver': self.player_name or "unknown"
            }
            
            # 从聊天消息列表中获取信息
            if len(channel_req.chatMessage) > 0:
                chat_msg = channel_req.chatMessage[0]
                log_entry['sender'] = chat_msg.sendPlayer.playerName if chat_msg.HasField('sendPlayer') else 'unknown'
                log_entry['message'] = chat_msg.msg
                log_entry['send_time'] = chat_msg.time
            
            self.detailed_logs['received_channel_chats'].append(log_entry)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Client {self.client_id} channel chat logging error: {str(e)}")
    
    def get_detailed_logs(self) -> dict:
        """获取详细的日志记录"""
        return {
            'client_id': self.client_id,
            'assigned_username': getattr(self, 'assigned_username', None),
            'actual_username': self.player_name,
            'logs': self.detailed_logs.copy()
        }
    
    def get_logs_summary(self) -> dict:
        """获取日志统计摘要"""
        return {
            'client_id': self.client_id,
            'assigned_username': getattr(self, 'assigned_username', None),
            'actual_username': self.player_name,
            'sent_commands_count': len(self.detailed_logs['sent_commands']),
            'received_private_chats_count': len(self.detailed_logs['received_private_chats']),
            'received_channel_chats_count': len(self.detailed_logs['received_channel_chats']),
            'login_events_count': len(self.detailed_logs['login_events']),
            'channel_events_count': len(self.detailed_logs['channel_events'])
        }
    
    def _generate_msg_id(self) -> str:
        """生成唯一的消息ID"""
        return str(uuid.uuid4())
    
    def _register_request(self, msg_id: str, request_type: str, **kwargs):
        """注册待响应的请求"""
        with self._msg_id_lock:
            self._pending_requests[msg_id] = {
                'request_type': request_type,
                'timestamp': time.time(),
                'client_id': self.client_id,
                **kwargs
            }
    
    def _get_and_remove_request(self, msg_id: str) -> Optional[dict]:
        """获取并移除待响应的请求"""
        with self._msg_id_lock:
            return self._pending_requests.pop(msg_id, None)
    
    def _cleanup_old_requests(self, timeout: float = 60.0):
        """清理超时的请求"""
        current_time = time.time()
        with self._msg_id_lock:
            expired_keys = [
                msg_id for msg_id, req_info in self._pending_requests.items()
                if current_time - req_info['timestamp'] > timeout
            ]
            for msg_id in expired_keys:
                del self._pending_requests[msg_id]
    
    def _create_request_with_msg_id(self, cs_msg_req, request_type: str, **kwargs) -> tuple[bytes, str]:
        """创建带有msgId的请求消息的通用方法"""
        base_msg, msg_id = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ
        )
        
        # 注册请求
        self._register_request(msg_id, request_type, **kwargs)
        
        return base_msg.SerializeToString(), msg_id
    
# 生成随机测试数据的工具函数
def generate_random_username(client_id: int) -> str:
    """生成随机用户名"""
    return f"TestUser_{client_id}_{random.randint(1000, 9999)}"

def generate_random_message() -> str:
    """生成随机消息"""
    messages = [
        "Hello, this is a test message!",
        "Testing the chat system",
        "Random message for stress test",
        "How are you doing?",
        "This is message number",
        "Testing 123",
        "Stress test in progress",
        "Hello world from client",
        "Chat message test",
        "Performance testing message"
    ]
    return f"{random.choice(messages)} {random.randint(1, 1000)}"

def generate_random_channel_name() -> str:
    """生成随机频道名"""
    prefixes = ["test", "game", "chat", "group", "channel"]
    suffixes = ["room", "hall", "zone", "area", "space"]
    return f"{random.choice(prefixes)}_{random.choice(suffixes)}_{random.randint(1, 100)}"
