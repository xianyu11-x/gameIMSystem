#!/usr/bin/env python3
import socket
import struct
import sys
import os
import threading
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
        
        # 定义命令补全器
        self.command_completer = WordCompleter([
            '/login', '/logout', '/chat', '/whisper', '/help', '/quit'
        ])

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"已连接到服务器: {self.host}:{self.port}")
            return True
        except ConnectionRefusedError:
            print(f"连接失败: 服务器 {self.host}:{self.port} 拒绝连接")
            return False
        except Exception as e:
            print(f"连接错误: {str(e)}")
            return False
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
        print("已断开连接")
    
    def send_message(self, message_bytes):
        try:
            # 直接发送序列化后的消息，不添加长度前缀
            self.socket.sendall(message_bytes)
            return True
        except Exception as e:
            print(f"发送消息失败: {str(e)}")
            return False
            
    def receive_message(self):
        try:
            # 设置接收超时，防止永久阻塞
            self.socket.settimeout(100.0)  # 设置1秒超时
            
            # 直接接收消息，不读取长度前缀
            buffer_size = 4096
            received_bytes = bytearray()
            
            # 读取可用数据
            try:
                chunk = self.socket.recv(buffer_size)
                # 添加调试信息
                print(f"接收到数据：{len(chunk)} 字节")
                
                if not chunk:
                    print("接收消息失败，服务器可能已断开连接")
                    return None
                    
                received_bytes.extend(chunk)
            except socket.timeout:
                # 超时但不中断连接
                print("接收超时，没有数据可读")
                return None
                
            # 尝试读取所有可用数据
            try:
                self.socket.settimeout(0.1)  # 短超时用于额外数据
                while True:
                    try:
                        more_data = self.socket.recv(buffer_size)
                        if more_data:
                            print(f"接收到额外数据：{len(more_data)} 字节")
                            received_bytes.extend(more_data)
                        else:
                            break
                    except socket.timeout:
                        # 没有更多数据
                        break
            except Exception as e:
                print(f"读取额外数据时出错: {str(e)}")
            finally:
                # 恢复默认超时设置
                self.socket.settimeout(None)
                
            # 添加调试信息：打印接收到的数据的前几个字节
            if received_bytes:
                max_preview = min(20, len(received_bytes))
                hex_data = ' '.join(f'{b:02x}' for b in received_bytes[:max_preview])
                print(f"接收到总共 {len(received_bytes)} 字节数据，前 {max_preview} 字节: {hex_data}")
                
            return received_bytes
            
        except ConnectionError as e:
            print(f"接收消息失败，连接错误: {str(e)}")
            self.connected = False
            return None
        except Exception as e:
            print(f"接收消息错误: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印详细的错误信息
            return None
    
    def send_and_wait_response(self, message_bytes, max_retries=3):
        """发送消息并等待服务器响应"""
        if not self.connected:
            print("未连接到服务器")
            return False
            
        # 发送消息
        if not self.send_message(message_bytes):
            return False
            
        # 等待并处理响应
        retry_count = 0
        while retry_count < max_retries:
            response = self.receive_message()
            if response:
                return self.handle_response(response)
            
            retry_count += 1
            print(f"尝试重新接收响应 ({retry_count}/{max_retries})...")
            
        print("等待响应超时")
        return False
    
    def create_base_message(self, msg_type, body):
        # 创建基础消息
        base_msg = BaseMsg_pb2.baseMsg()
        
        # 创建并设置MsgInfo结构体
        msg_info = BaseMsg_pb2.MsgInfo()
        msg_info.msgType = msg_type
        msg_info.msgSender = BaseMsg_pb2.MsgSender.EN_MSG_SENDER_CLIENT
        msg_info.msgBodyType = BaseMsg_pb2.MsgBodyType.EN_REQ
        
        # 设置baseMsg的msgInfo字段
        base_msg.msgInfo.CopyFrom(msg_info)
        base_msg.msgBody = body
        return base_msg

    def create_login_request(self, username):
        # 创建玩家信息
        player_info = player_pb2.PlayerInfo()
        player_info.playerId = 0  # 新用户ID为0
        player_info.playerName = username
        player_info.playerToken = ""  # 首次登录无token
        
        # 创建登录请求
        login_req = CSMsg_pb2.CSLoginMsgReq()
        login_req.msgType = CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGIN
        login_req.info.CopyFrom(player_info)
        
        # 创建CS消息请求
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_LOGIN  
        cs_msg_req.loginReq.CopyFrom(login_req)
        
        # 打包到base message中
        base_msg = self.create_base_message(BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS, 
                                           cs_msg_req.SerializeToString())
        return base_msg.SerializeToString()
    
    def create_logout_request(self):
        # 创建玩家信息
        player_info = player_pb2.PlayerInfo()
        player_info.playerId = self.player_id
        player_info.playerName = self.player_name
        player_info.playerToken = self.player_token
        
        # 创建登出请求
        logout_req = CSMsg_pb2.CSLoginMsgReq()
        logout_req.msgType = CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGOUT
        logout_req.info.CopyFrom(player_info)
        
        # 创建CS消息请求
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_LOGIN  # 修正字段名
        cs_msg_req.loginReq.CopyFrom(logout_req)
        
        # 打包到base message中
        base_msg = self.create_base_message(BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS, 
                                           cs_msg_req.SerializeToString())
        return base_msg.SerializeToString()
    def handle_response(self, response_bytes):
        if not response_bytes:
            return False
            
        try:
            # 解析基础消息
            base_msg = BaseMsg_pb2.baseMsg()
            base_msg.ParseFromString(response_bytes)
            
            if base_msg.msgInfo.msgType == BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS:
                # 解析CS消息
                cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
                cs_msg_rsp.ParseFromString(base_msg.msgBody)
                
                if cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_LOGIN:
                    # 处理登录响应
                    login_rsp = cs_msg_rsp.loginRsp
                    if login_rsp.isSuccess:
                        # 保存用户信息
                        self.player_id = login_rsp.info.playerId
                        self.player_name = login_rsp.info.playerName
                        self.player_token = login_rsp.info.playerToken
                        print(f"\n登录成功! 欢迎 {self.player_name}! (ID: {self.player_id})\n")
                    else:
                        err_msg = login_rsp.errMsg if login_rsp.HasField("errMsg") else "未知错误"
                        print(f"\n登录失败: {err_msg}\n")
                
                # 此处可以添加更多消息类型处理，如聊天等
                
            return True
        except Exception as e:
            print(f"处理响应失败: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印完整的堆栈跟踪，帮助调试
            return False
    
    def login(self, username):
        """处理用户登录"""
        if not self.connected and not self.connect():
            return False
            
        login_msg = self.create_login_request(username)
        if self.send_and_wait_response(login_msg):
            print(f"登录请求已发送，用户名: {username}")
            return True
        return False
    
    def logout(self):
        """处理用户登出"""
        if not self.connected or not self.player_name:
            print("未登录，无需登出")
            return False
            
        logout_msg = self.create_logout_request()
        if self.send_and_wait_response(logout_msg):
            print(f"登出请求已发送，用户名: {self.player_name}")
            self.player_name = None
            self.player_token = None
            self.player_id = None
            return True
        return False
    
    def print_help(self):
        """打印帮助信息"""
        print("\n可用命令:")
        print("  /login <用户名>    - 以指定用户名登录")
        print("  /logout           - 登出当前用户")
        print("  /help             - 显示此帮助信息")
        print("  /quit             - 退出客户端")
        print("  其他输入将被视为聊天消息 (功能待实现)")
    
    def run(self):
        """运行客户端主循环"""
        self.running = True
        print("欢迎使用游戏即时通讯客户端!")
        print("输入 /help 获取帮助")
        
        # 创建历史记录文件
        #history_file = os.path.expanduser('.game_client_history')
        #history = FileHistory(history_file)
        
        while self.running:
            try:
                # 使用prompt_toolkit提供交互式输入
                user_input = prompt(
                    '> ', 
                    auto_suggest=AutoSuggestFromHistory(),
                    completer=self.command_completer
                )
                
                if not user_input.strip():
                    continue
                
                # 处理命令
                if user_input.startswith('/'):
                    parts = user_input.split(maxsplit=1)
                    command = parts[0].lower()
                    
                    if command == '/login':
                        if len(parts) < 2:
                            print("错误: 请提供用户名，如 /login username")
                        else:
                            self.login(parts[1])
                    
                    elif command == '/logout':
                        self.logout()
                    
                    elif command == '/help':
                        self.print_help()
                    
                    elif command == '/quit':
                        if self.player_name:
                            self.logout()
                        self.running = False
                        print("再见!")
                        break
                    
                    else:
                        print(f"未知命令: {command}")
                        self.print_help()
                
                else:
                    # 将来这里可以实现聊天功能
                    print("聊天功能尚未实现")
                    
            except KeyboardInterrupt:
                print("\n收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"错误: {str(e)}")
        
        # 清理资源
        self.running = False
        if self.connected:
            self.disconnect()

if __name__ == "__main__":
    # 默认连接设置
    host = "localhost"
    port = 8888
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:  # 修复这里的语法错误
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"警告: 端口号 '{sys.argv[2]}' 无效，使用默认端口 8888")
            port = 8888
    
    client = GameClient(host, port)
    client.run()