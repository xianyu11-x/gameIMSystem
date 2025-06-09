#!/usr/bin/env python3
import socket
import struct
import sys
import os
import threading
import time
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

# 添加协议目录到Python路径中
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build/protocol"))

# 尝试导入protobuf生成的模块
try:
    from common import BaseMsg_pb2
    from common import player_pb2
    from common import chatMessage_pb2 # Added for chat messages
    from common import channel_pb2 # Added for channel info
    from gatesvr import CSMsg_pb2
except ImportError:
    print("错误: 无法导入Protocol Buffers模块")
    print("请确保已经编译proto文件并且生成了Python绑定")
    print("尝试运行: protoc --python_out=build/protocol protocol/**/*.proto")
    sys.exit(1)

class GameClient:
    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.player_name = None
        self.player_token = None
        self.player_id = None
        self.running = False
        self.connected = False
        self.receiver_thread = None
        
        # 定义命令补全器
        self.command_completer = WordCompleter([
            '/login', '/logout', '/chat', '/channel', '/help', '/quit'
        ])

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"已连接到服务器: {self.host}:{self.port}")
            
            self.running = True
            self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
            self.receiver_thread.start()
            return True
        except ConnectionRefusedError:
            print(f"连接失败: 服务器 {self.host}:{self.port} 拒绝连接")
            return False
        except Exception as e:
            print(f"连接错误: {str(e)}")
            return False
    
    def disconnect(self):
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
            self.socket = None
        self.connected = False
        if self.receiver_thread and self.receiver_thread.is_alive() and threading.current_thread() != self.receiver_thread:
            self.receiver_thread.join(timeout=2.0)
        print("已断开连接")
    
    def send_message(self, message_bytes):
        if not self.connected or not self.socket:
            print("发送消息失败: 未连接")
            return False
        try:
            self.socket.sendall(message_bytes)
            return True
        except Exception as e:
            print(f"发送消息失败: {str(e)}")
            self.connected = False
            return False
            
    def receive_message(self, timeout=1.0):
        if not self.connected or not self.socket:
            return None
        try:
            self.socket.settimeout(timeout) 
            buffer_size = 4096
            received_bytes = bytearray()
            try:
                chunk = self.socket.recv(buffer_size)
                if not chunk:
                    print("接收消息失败，服务器可能已断开连接")
                    self.connected = False
                    return None
                received_bytes.extend(chunk)
            except socket.timeout:
                return None
            except ConnectionResetError:
                print("连接被对方重置。")
                self.connected = False
                return None
            except OSError as e:
                if self.running:
                     print(f"Socket error during receive: {e}")
                self.connected = False
                return None

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
            
        except ConnectionError as e:
            if self.running:
                print(f"接收消息失败，连接错误: {str(e)}")
            self.connected = False
            return None
        except Exception as e:
            if self.running:
                print(f"接收消息错误: {str(e)}")
            return None
    
    def _receiver_loop(self):
        print("消息接收线程已启动。")
        while self.running and self.connected:
            response_bytes = self.receive_message(timeout=1.0)
            if response_bytes:
                self.handle_incoming_message(response_bytes)
            elif not self.connected and self.running:
                print("连接已断开，停止接收消息。")
                break
        print("消息接收线程已停止。")

    def create_base_message(self, msg_type, body, body_type=BaseMsg_pb2.MsgBodyType.EN_REQ): # Added body_type
        base_msg = BaseMsg_pb2.baseMsg()
        msg_info = BaseMsg_pb2.MsgInfo()
        msg_info.msgType = msg_type
        msg_info.msgSender = BaseMsg_pb2.MsgSender.EN_MSG_SENDER_CLIENT
        msg_info.msgBodyType = body_type # Use passed body_type
        base_msg.msgInfo.CopyFrom(msg_info)
        base_msg.msgBody = body
        return base_msg

    def create_login_request(self, username):
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
        
        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS, 
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ # Explicitly REQ
        )
        return base_msg.SerializeToString()
    
    def create_logout_request(self):
        player_info = player_pb2.PlayerInfo()
        if self.player_id is not None: player_info.playerId = self.player_id
        if self.player_name is not None: player_info.playerName = self.player_name
        if self.player_token is not None: player_info.playerToken = self.player_token
        
        logout_req_payload = CSMsg_pb2.CSLoginMsgReq()
        logout_req_payload.msgType = CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGOUT
        logout_req_payload.info.CopyFrom(player_info)
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_LOGIN
        cs_msg_req.loginReq.CopyFrom(logout_req_payload)
        
        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS, 
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ # Explicitly REQ
        )
        return base_msg.SerializeToString()

    def create_chat_request(self, message_text, recipient_name=None):
        """创建聊天请求消息 - Client sending a message"""
        cs_chat_req_payload = CSMsg_pb2.CSChatMsgReq()
        cs_chat_req_payload.msgType = CSMsg_pb2.CSChatMsgType.EN_SEND

        # Populate sender info
        cs_chat_req_payload.sendPlayer.playerId = self.player_id or 0
        cs_chat_req_payload.sendPlayer.playerName = self.player_name or "UnknownUser" # Should have player_name if logged in
        if self.player_token:
             cs_chat_req_payload.sendPlayer.playerToken = self.player_token

        if recipient_name:
            cs_chat_req_payload.receivePlayer.playerName = recipient_name
            # Other fields of receivePlayer are not strictly necessary for the server to identify by name

        # Create and add the chatMessage
        chat_msg_content = cs_chat_req_payload.chatMessage.add()
        chat_msg_content.msg = message_text
        chat_msg_content.sendPlayer.CopyFrom(cs_chat_req_payload.sendPlayer) # Message's own sender field
        chat_msg_content.time = int(time.time())
        # chat_msg_content.id and seq can be set by server or client if needed by design

        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHAT # Corrected: Use EN_CHAT
        cs_msg_req.chatReq.CopyFrom(cs_chat_req_payload)

        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ # Explicitly REQ
        )
        return base_msg.SerializeToString()

    def create_chat_history_request(self):
        """创建拉取聊天历史消息请求"""
        cs_chat_req_payload = CSMsg_pb2.CSChatMsgReq()
        cs_chat_req_payload.msgType = CSMsg_pb2.CSChatMsgType.EN_HISTORY

        # Populate sender info
        cs_chat_req_payload.sendPlayer.playerId = self.player_id or 0
        cs_chat_req_payload.sendPlayer.playerName = self.player_name or ""
        if self.player_token:
            cs_chat_req_payload.sendPlayer.playerToken = self.player_token

        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_req.chatReq.CopyFrom(cs_chat_req_payload)

        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ
        )
        return base_msg.SerializeToString()

    def send_chat_message(self, message_text, recipient_name=None):
        if not self.connected:
            print("未连接到服务器，无法发送聊天消息。")
            return False
        if not self.player_name: # Ensure logged in
            print("请先登录再发送聊天消息。")
            return False

        chat_msg_bytes = self.create_chat_request(message_text, recipient_name)
        if chat_msg_bytes:
            if self.send_message(chat_msg_bytes):
                # Confirmation will come as an async response (ACK)
                # print(f"聊天消息已发送给 {recipient_name if recipient_name else '公共频道'}: {message_text}") # Avoid immediate print
                return True
            else:
                print("发送聊天消息失败。")
                return False
        return False

    def fetch_chat_history(self):
        """拉取聊天历史消息 - 仅在登录时自动调用"""
        if not self.connected:
            return False
        if not self.player_name:
            return False

        history_msg_bytes = self.create_chat_history_request()
        if history_msg_bytes:
            if self.send_message(history_msg_bytes):
                return True
            else:
                print("拉取历史消息失败。")
                return False
        return False

    def create_chat_receive_acknowledgment(self, received_msg_req):
        """创建聊天消息接收确认 - Client acknowledging receipt of a message"""
        # 创建聊天回复
        cs_chat_rsp_payload = CSMsg_pb2.CSChatMsgRsp()
        cs_chat_rsp_payload.msgType = CSMsg_pb2.CSChatMsgType.EN_RECEIVE  # 确认接收到消息
        
        # 复制发送者信息，这个是我们正在确认其消息的发送者
        cs_chat_rsp_payload.sendPlayer.CopyFrom(received_msg_req.chatReq.sendPlayer)
        cs_chat_rsp_payload.isSuccess = True  # 标记成功接收
        
        # 创建CS消息响应
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_CHAT  # 聊天消息类型
        cs_msg_rsp.chatRsp.CopyFrom(cs_chat_rsp_payload)
        
        # 创建基础消息
        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,  # CS消息类型
            cs_msg_rsp.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_RSP  # 响应类型
        )
        
        return base_msg.SerializeToString()

    def create_channel_receive_acknowledgment(self, received_msg_req):
        """创建频道消息接收确认 - Client acknowledging receipt of a channel message"""
        # 创建频道回复
        cs_channel_rsp_payload = CSMsg_pb2.CSChannelMsgRsp()
        cs_channel_rsp_payload.msgType = CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_RECEIVE  # 确认接收到频道消息
        
        # 复制发送者信息，这个是我们正在确认其消息的发送者
        cs_channel_rsp_payload.sendPlayer.CopyFrom(received_msg_req.channelReq.sendPlayer)
        cs_channel_rsp_payload.isSuccess = True  # 标记成功接收
        
        # 创建CS消息响应
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_CHANNEL  # 频道消息类型
        cs_msg_rsp.channelRsp.CopyFrom(cs_channel_rsp_payload)
        
        # 创建基础消息
        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,  # CS消息类型
            cs_msg_rsp.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_RSP  # 响应类型
        )
        
        return base_msg.SerializeToString()

    # ========== 频道相关方法 ==========
    def create_channel_request(self, msg_type, channel_name=None, channel_id=None, message_text=None):
        """创建频道相关请求"""
        cs_channel_req_payload = CSMsg_pb2.CSChannelMsgReq()
        cs_channel_req_payload.msgType = msg_type

        # 填充发送者信息
        cs_channel_req_payload.sendPlayer.playerId = self.player_id or 0
        cs_channel_req_payload.sendPlayer.playerName = self.player_name or ""
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

        base_msg = self.create_base_message(
            BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS,
            cs_msg_req.SerializeToString(),
            BaseMsg_pb2.MsgBodyType.EN_REQ
        )
        return base_msg.SerializeToString()

    def create_channel(self, channel_name):
        """创建频道"""
        if not self.connected:
            print("未连接到服务器，无法创建频道。")
            return False
        if not self.player_name:
            print("请先登录再创建频道。")
            return False

        channel_msg_bytes = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_CREATE, 
            channel_name=channel_name
        )
        if channel_msg_bytes:
            if self.send_message(channel_msg_bytes):
                return True
            else:
                print("发送创建频道请求失败。")
                return False
        return False

    def destroy_channel(self, channel_name):
        """销毁频道"""
        if not self.connected:
            print("未连接到服务器，无法销毁频道。")
            return False
        if not self.player_name:
            print("请先登录再销毁频道。")
            return False

        channel_msg_bytes = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_DESTROY, 
            channel_name=channel_name
        )
        if channel_msg_bytes:
            if self.send_message(channel_msg_bytes):
                return True
            else:
                print("发送销毁频道请求失败。")
                return False
        return False

    def join_channel(self, channel_name):
        """加入频道"""
        if not self.connected:
            print("未连接到服务器，无法加入频道。")
            return False
        if not self.player_name:
            print("请先登录再加入频道。")
            return False

        channel_msg_bytes = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_JOIN, 
            channel_name=channel_name
        )
        if channel_msg_bytes:
            if self.send_message(channel_msg_bytes):
                return True
            else:
                print("发送加入频道请求失败。")
                return False
        return False

    def leave_channel(self, channel_name):
        """离开频道"""
        if not self.connected:
            print("未连接到服务器，无法离开频道。")
            return False
        if not self.player_name:
            print("请先登录再离开频道。")
            return False

        channel_msg_bytes = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_LEAVE, 
            channel_name=channel_name
        )
        if channel_msg_bytes:
            if self.send_message(channel_msg_bytes):
                return True
            else:
                print("发送离开频道请求失败。")
                return False
        return False

    def send_channel_message(self, channel_name, message_text):
        """发送频道消息"""
        if not self.connected:
            print("未连接到服务器，无法发送频道消息。")
            return False
        if not self.player_name:
            print("请先登录再发送频道消息。")
            return False

        channel_msg_bytes = self.create_channel_request(
            CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_SEND, 
            channel_name=channel_name,
            message_text=message_text
        )
        if channel_msg_bytes:
            if self.send_message(channel_msg_bytes):
                return True
            else:
                print("发送频道消息失败。")
                return False
        return False

    def pull_channels(self):
        """拉取频道列表"""
        if not self.connected:
            print("未连接到服务器，无法拉取频道列表。")
            return False
        if not self.player_name:
            print("请先登录再拉取频道列表。")
            return False

        channel_msg_bytes = self.create_channel_request(CSMsg_pb2.CSChannelMsgType.EN_PULL)
        if channel_msg_bytes:
            if self.send_message(channel_msg_bytes):
                return True
            else:
                print("发送拉取频道列表请求失败。")
                return False
        return False

    def handle_incoming_message(self, response_bytes):
        if not response_bytes:
            return False
            
        try:
            base_msg = BaseMsg_pb2.baseMsg()
            base_msg.ParseFromString(response_bytes)
            
            msg_info = base_msg.msgInfo

            if msg_info.msgType == BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS:
                # --- Handling Server Responses (ACKs) ---
                if msg_info.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_RSP:
                    cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
                    cs_msg_rsp.ParseFromString(base_msg.msgBody)
                    
                    if cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_LOGIN:
                        login_rsp = cs_msg_rsp.loginRsp
                        if login_rsp.isSuccess:
                            if login_rsp.info.playerName: 
                                self.player_id = login_rsp.info.playerId
                                self.player_name = login_rsp.info.playerName
                                self.player_token = login_rsp.info.playerToken
                                print(f"\n登录成功! 欢迎 {self.player_name}! (ID: {self.player_id})")
                                print("正在为您拉取历史消息...")
                                # 登录成功后自动拉取历史消息
                                threading.Timer(0.5, self.fetch_chat_history).start()
                                print("> ", end='', flush=True)
                            else: # Successful logout confirmation
                                print(f"\n操作成功 (如登出)。\n> ", end='', flush=True)
                        else:
                            # errMsg 是可选字段，所以可以用 HasField
                            err_msg = login_rsp.errMsg if login_rsp.HasField("errMsg") else "未知错误"
                            print(f"\n操作失败: {err_msg}\n> ", end='', flush=True)
                    
                    elif cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_CHAT:
                        # chatRsp 是消息类型字段，可以用 HasField
                        if cs_msg_rsp.HasField('chatRsp'):
                            chat_ack_rsp = cs_msg_rsp.chatRsp
                            
                            # 处理历史消息响应
                            if chat_ack_rsp.msgType == CSMsg_pb2.CSChatMsgType.EN_HISTORY:
                                if chat_ack_rsp.isSuccess:
                                    if chat_ack_rsp.chatMessage:
                                        print(f"\n========== 历史消息 ==========")
                                        for chat_msg_item in chat_ack_rsp.chatMessage:
                                            sender_name = chat_msg_item.sendPlayer.playerName if chat_msg_item.sendPlayer.playerName else "未知用户"
                                            message_text = chat_msg_item.msg
                                            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(chat_msg_item.time)) if chat_msg_item.time else ""
                                            if timestamp:
                                                print(f"[{timestamp}] {sender_name}: {message_text}")
                                            else:
                                                print(f"[{sender_name}]: {message_text}")
                                        print(f"========== 历史消息结束 ==========")
                                    else:
                                        print("\n暂无历史消息")
                                else:
                                    err_detail = f": {chat_ack_rsp.errMsg}" if chat_ack_rsp.HasField("errMsg") and chat_ack_rsp.errMsg else ""
                                    print(f"\n拉取历史消息失败{err_detail}")
                                print("> ", end='', flush=True)
                            else:
                                # 处理普通聊天消息发送确认
                                status_msg = "成功" if chat_ack_rsp.isSuccess else "失败"
                                err_detail = f": {chat_ack_rsp.errMsg}" if chat_ack_rsp.HasField("errMsg") and chat_ack_rsp.errMsg else ""
                                print(f"\n消息发送确认: {status_msg}{err_detail}\n> ", end='', flush=True)
                        else:
                            print(f"\n收到聊天响应但无chatRsp内容。\n> ", end='', flush=True)
                    
                    elif cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_CHANNEL:
                        # 处理频道响应
                        if cs_msg_rsp.HasField('channelRsp'):
                            channel_rsp = cs_msg_rsp.channelRsp
                            
                            if channel_rsp.msgType == CSMsg_pb2.CSChannelMsgType.EN_CREATE:
                                status_msg = "成功" if channel_rsp.isSuccess else "失败"
                                err_detail = f": {channel_rsp.errMsg}" if channel_rsp.HasField("errMsg") and channel_rsp.errMsg else ""
                                print(f"\n频道创建{status_msg}{err_detail}\n> ", end='', flush=True)
                                
                            elif channel_rsp.msgType == CSMsg_pb2.CSChannelMsgType.EN_DESTROY:
                                status_msg = "成功" if channel_rsp.isSuccess else "失败"
                                err_detail = f": {channel_rsp.errMsg}" if channel_rsp.HasField("errMsg") and channel_rsp.errMsg else ""
                                print(f"\n频道销毁{status_msg}{err_detail}\n> ", end='', flush=True)
                                
                            elif channel_rsp.msgType == CSMsg_pb2.CSChannelMsgType.EN_JOIN:
                                status_msg = "成功" if channel_rsp.isSuccess else "失败"
                                err_detail = f": {channel_rsp.errMsg}" if channel_rsp.HasField("errMsg") and channel_rsp.errMsg else ""
                                print(f"\n加入频道{status_msg}{err_detail}\n> ", end='', flush=True)
                                
                            elif channel_rsp.msgType == CSMsg_pb2.CSChannelMsgType.EN_LEAVE:
                                status_msg = "成功" if channel_rsp.isSuccess else "失败"
                                err_detail = f": {channel_rsp.errMsg}" if channel_rsp.HasField("errMsg") and channel_rsp.errMsg else ""
                                print(f"\n离开频道{status_msg}{err_detail}\n> ", end='', flush=True)
                                
                            elif channel_rsp.msgType == CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_SEND:
                                status_msg = "成功" if channel_rsp.isSuccess else "失败"
                                err_detail = f": {channel_rsp.errMsg}" if channel_rsp.HasField("errMsg") and channel_rsp.errMsg else ""
                                print(f"\n频道消息发送{status_msg}{err_detail}\n> ", end='', flush=True)
                                
                            elif channel_rsp.msgType == CSMsg_pb2.CSChannelMsgType.EN_PULL:
                                if channel_rsp.isSuccess:
                                    if channel_rsp.channelInfo:
                                        print(f"\n========== 频道列表 ==========")
                                        for channel_info in channel_rsp.channelInfo:
                                            channel_name = channel_info.channelName
                                            channel_id = channel_info.channelId
                                            print(f"频道: {channel_name} (ID: {channel_id})")
                                        print(f"========== 频道列表结束 ==========")
                                    else:
                                        print("\n暂无频道")
                                else:
                                    err_detail = f": {channel_rsp.errMsg}" if channel_rsp.HasField("errMsg") and channel_rsp.errMsg else ""
                                    print(f"\n拉取频道列表失败{err_detail}")
                                print("> ", end='', flush=True)
                        else:
                            print(f"\n收到频道响应但无channelRsp内容。\n> ", end='', flush=True)
                    # Add other EN_RSP handlers here if needed

                # --- Handling Server REQ messages (including notifications like chat messages from other users) ---
                elif msg_info.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_REQ:
                    # 解析为CSMsgReq
                    cs_msg_req = CSMsg_pb2.CSMsgReq()
                    cs_msg_req.ParseFromString(base_msg.msgBody)
                    
                    # chatReq 是消息类型字段，可以用 HasField
                    if cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHAT and cs_msg_req.HasField('chatReq'):
                        chat_req_payload = cs_msg_req.chatReq
                        
                        # 如果msgType是EN_RECEIVE，则认为是服务器推送的其他用户发来的消息
                        if chat_req_payload.msgType == CSMsg_pb2.CSChatMsgType.EN_RECEIVE:
                            sender_player_info = chat_req_payload.sendPlayer
                            # playerName 不是可选字段，不能用 HasField，应该直接检查是否为空字符串
                            sender_name = sender_player_info.playerName if sender_player_info.playerName else "未知用户"
                            
                            for chat_msg_item in chat_req_payload.chatMessage:
                                message_text = chat_msg_item.msg
                                timestamp = time.strftime('%H:%M:%S', time.localtime(chat_msg_item.time)) if chat_msg_item.time else ""
                                
                                # 改进消息显示格式
                                if timestamp:
                                    print(f"\n[{timestamp}] {sender_name}: {message_text}")
                                else:
                                    print(f"\n[{sender_name}]: {message_text}")
                                print("> ", end='', flush=True)
                            
                            # 发送接收确认响应回服务器
                            ack_msg_bytes = self.create_chat_receive_acknowledgment(cs_msg_req)
                            if self.send_message(ack_msg_bytes):
                                # 调试信息 - 可以取消注释如果需要看到确认信息
                                # print(f"\\n已发送消息接收确认到服务器\\n> ", end='', flush=True)
                                pass
                            else:
                                print(f"\n发送消息接收确认失败\n> ", end='', flush=True)
                    
                    # 处理频道REQ消息
                    elif cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHANNEL and cs_msg_req.HasField('channelReq'):
                        channel_req_payload = cs_msg_req.channelReq
                        
                        # 处理频道消息接收
                        if channel_req_payload.msgType == CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_RECEIVE:
                            sender_player_info = channel_req_payload.sendPlayer
                            sender_name = sender_player_info.playerName if sender_player_info.playerName else "未知用户"
                            channel_name = channel_req_payload.channelInfo.channelName if channel_req_payload.channelInfo.channelName else "未知频道"
                            
                            for chat_msg_item in channel_req_payload.chatMessage:
                                message_text = chat_msg_item.msg
                                timestamp = time.strftime('%H:%M:%S', time.localtime(chat_msg_item.time)) if chat_msg_item.time else ""
                                
                                # 显示频道消息格式
                                if timestamp:
                                    print(f"\n[{timestamp}] #{channel_name} {sender_name}: {message_text}")
                                else:
                                    print(f"\n#{channel_name} {sender_name}: {message_text}")
                                print("> ", end='', flush=True)
                            
                            # 发送频道消息接收确认响应回服务器
                            ack_msg_bytes = self.create_channel_receive_acknowledgment(cs_msg_req)
                            if self.send_message(ack_msg_bytes):
                                # 调试信息 - 可以取消注释如果需要看到确认信息
                                # print(f"\n已发送频道消息接收确认到服务器\n> ", end='', flush=True)
                                pass
                            else:
                                print(f"\n发送频道消息接收确认失败\n> ", end='', flush=True)
                    # 其他REQ类型的处理可以在这里添加（如果需要）
                                
                # 保留旧的NTF处理逻辑，以防协议变更或有其他类型的通知
                elif msg_info.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_NTF:
                    print(f"\n收到EN_NTF类型消息，但协议中未定义此类通知处理。\n> ", end='', flush=True)
                
                else:
                    print(f"\n收到未处理的CS消息体类型: {BaseMsg_pb2.MsgBodyType.Name(msg_info.msgBodyType)}\n> ", end='', flush=True)

            # Add more handlers for other base_msg.msgInfo.msgType if needed
            else:
                print(f"\n收到未处理的基础消息类型: {BaseMsg_pb2.MsgType.Name(msg_info.msgType)}\n> ", end='', flush=True)

            return True
            
        except Exception as e:
            print(f"处理接收到的消息失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def login(self, username):
        if self.player_name:
            print(f"您已作为 {self.player_name} 登录。请先登出。")
            return False
        if not self.connected:
            if not self.connect():
                return False
        
        login_msg_bytes = self.create_login_request(username)
        if self.send_message(login_msg_bytes):
            print(f"登录请求已发送，用户名: {username}")
            return True
        else:
            print(f"发送登录请求失败。")
            return False
    
    def logout(self):
        if not self.player_name:
            print("未登录，无需登出。")
            return False
        if not self.connected:
            print("未连接到服务器。")
            return False
            
        logout_msg_bytes = self.create_logout_request()
        if self.send_message(logout_msg_bytes):
            print(f"登出请求已发送，用户: {self.player_name}")
            # Optimistically clear some local state, server response will confirm
            # and handle_incoming_message might print success/failure.
            # Full clear upon successful logout confirmation in handle_incoming_message
            # if login_rsp.info.playerName is empty.
            self.player_name = None # Tentatively clear
            self.player_token = None
            self.player_id = None
            return True
        else:
            print(f"发送登出请求失败。")
            return False
    
    def print_help(self):
        print("\n可用命令:")
        print("  /login <用户名>          - 以指定用户名登录")
        print("  /logout                 - 登出当前用户")
        print("  /chat <消息>            - 发送公共聊天消息")
        print("  /chat @<用户名> <消息>  - 发送私聊消息")
        print("  /channel create <频道名> - 创建频道")
        print("  /channel destroy <频道名>- 销毁频道")
        print("  /channel join <频道名>   - 加入频道")
        print("  /channel leave <频道名>  - 离开频道")
        print("  /channel send <频道名> <消息> - 发送频道消息")
        print("  /channel list           - 查看频道列表")
        print("  /help                   - 显示此帮助信息")
        print("  /quit                   - 退出客户端")
        print("  直接输入内容             - 发送公共聊天消息")
    
    def run(self):
        if not self.connected:
            if not self.connect():
                print("无法启动客户端：连接服务器失败。")
                return

        print("欢迎使用游戏即时通讯客户端!")
        print("输入 /help 获取帮助")
        
        try:
            while self.running:
                try:
                    user_input = prompt(
                        '> ', 
                        # history=FileHistory('.game_client_history'),
                        auto_suggest=AutoSuggestFromHistory(),
                        completer=self.command_completer
                    ).strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.startswith('/'):
                        parts = user_input.split(maxsplit=1)
                        command = parts[0].lower()
                        args = parts[1] if len(parts) > 1 else ""
                        
                        if command == '/login':
                            if not args:
                                print("错误: 请提供用户名，如 /login username")
                            else:
                                self.login(args)
                        
                        elif command == '/logout':
                            self.logout()
                        
                        elif command == '/help':
                            self.print_help()
                        
                        elif command == '/quit':
                            if self.player_name:
                                print("正在尝试登出...")
                                self.logout()
                                time.sleep(0.5) 
                            self.running = False
                            print("正在退出客户端...")
                            break 
                        
                        elif command == '/chat':
                            if not args:
                                print("用法: /chat [@用户名] <消息内容> 或 /chat <消息内容>")
                                continue
                            
                            recipient_name = None
                            message_text = args
                            if args.startswith('@'):
                                try:
                                    recipient_part, message_text_remainder = args.split(maxsplit=1)
                                    # Check if recipient_part is just "@" or "@ "
                                    if len(recipient_part) > 1 and not recipient_part[1:].isspace():
                                        recipient_name = recipient_part[1:]
                                        message_text = message_text_remainder
                                    else: # Case like "/chat @ message" or "/chat @user" (no space after user)
                                        # Fallback to public message if only "@" or if no message after @user
                                        # Or treat as error. For now, let's be strict for private.
                                        if len(recipient_part) == 1: # just "@"
                                            message_text = args # Treat whole thing as public message
                                        else: # @user without space and message
                                            print("用法: /chat @用户名 <消息内容> (私聊请在@用户名后加空格)")
                                            continue
                                except ValueError: # No space after @username, e.g. "/chat @userMessage"
                                    # This means args was like "@usernameMessage"
                                    # Defaulting to public chat for this ambiguous case, or could be error
                                    # print("提示: 私聊请使用 /chat @用户名 <消息内容>")
                                    # message_text = args # Treat as public
                                    # For now, let's require space for private.
                                    print("用法: /chat @用户名 <消息内容> (私聊请在@用户名后加空格)")
                                    continue
                            
                            if not message_text.strip():
                                print("不能发送空消息。")
                                continue
                            self.send_chat_message(message_text, recipient_name)
                        
                        elif command == '/channel':
                            if not args:
                                print("用法: /channel <子命令> [参数...]")
                                print("可用子命令: create, destroy, join, leave, send, list")
                                continue
                            
                            # Parse channel subcommand and arguments
                            channel_parts = args.split(maxsplit=1)
                            subcommand = channel_parts[0].lower()
                            sub_args = channel_parts[1] if len(channel_parts) > 1 else ""
                            
                            if subcommand == 'create':
                                if not sub_args.strip():
                                    print("用法: /channel create <频道名>")
                                    continue
                                self.create_channel(sub_args.strip())
                            
                            elif subcommand == 'destroy':
                                if not sub_args.strip():
                                    print("用法: /channel destroy <频道名>")
                                    continue
                                self.destroy_channel(sub_args.strip())
                            
                            elif subcommand == 'join':
                                if not sub_args.strip():
                                    print("用法: /channel join <频道名>")
                                    continue
                                self.join_channel(sub_args.strip())
                            
                            elif subcommand == 'leave':
                                if not sub_args.strip():
                                    print("用法: /channel leave <频道名>")
                                    continue
                                self.leave_channel(sub_args.strip())
                            
                            elif subcommand == 'send':
                                send_parts = sub_args.split(maxsplit=1)
                                if len(send_parts) < 2:
                                    print("用法: /channel send <频道名> <消息内容>")
                                    continue
                                channel_name = send_parts[0]
                                message_content = send_parts[1]
                                if not message_content.strip():
                                    print("不能发送空消息。")
                                    continue
                                self.send_channel_message(channel_name, message_content.strip())
                            
                            elif subcommand == 'list':
                                self.pull_channels()
                            
                            else:
                                print(f"未知的频道子命令: {subcommand}")
                                print("可用子命令: create, destroy, join, leave, send, list")

                        else:
                            print(f"未知命令: {command}")
                            self.print_help()
                    
                    else: 
                        self.send_chat_message(user_input, None) # None for public chat
                        
                except KeyboardInterrupt:
                    print("\n收到中断信号，正在退出...")
                    if self.player_name:
                        self.logout()
                        time.sleep(0.5)
                    self.running = False
                    break
                except EOFError:
                    print("\n收到EOF，正在退出...")
                    if self.player_name:
                        self.logout()
                        time.sleep(0.5)
                    self.running = False
                    break
                except Exception as e:
                    print(f"主循环发生错误: {str(e)}")

        finally:
            print("清理资源...")
            self.disconnect()

if __name__ == "__main__":
    host = "localhost"
    port = 8888
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"警告: 端口号 '{sys.argv[2]}' 无效，使用默认端口 8888")
    
    client = GameClient(host, port)
    client.run()