#!/usr/bin/env python3
"""
Protocol Buffer 消息构造器
支持构造各种CSMsgReq和CSMsgRsp消息，并以16进制格式输出序列化结果
"""

import sys
import os
import time
import argparse
from typing import Optional, Dict, Any

# 添加协议目录到Python路径中
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build/protocol"))

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

class MessageBuilder:
    """消息构造器类"""
    
    def __init__(self):
        self.player_id = 1001
        self.player_name = "TestUser"
        self.player_token = "test_token_123"
    
    def set_player_info(self, player_id: int, player_name: str, player_token: str = ""):
        """设置玩家信息"""
        self.player_id = player_id
        self.player_name = player_name
        self.player_token = player_token
    
    def create_base_message(self, msg_body: bytes, body_type=BaseMsg_pb2.MsgBodyType.EN_REQ) -> bytes:
        """创建基础消息"""
        base_msg = BaseMsg_pb2.baseMsg()
        msg_info = BaseMsg_pb2.MsgInfo()
        msg_info.msgType = BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS
        msg_info.msgSender = BaseMsg_pb2.MsgSender.EN_MSG_SENDER_GATESVR
        msg_info.msgBodyType = body_type
        base_msg.msgInfo.CopyFrom(msg_info)
        base_msg.msgBody = msg_body
        return base_msg.SerializeToString()
    
    def create_player_info(self, player_id: int = None, player_name: str = None, player_token: str = None):
        """创建玩家信息"""
        player_info = player_pb2.PlayerInfo()
        player_info.playerId = player_id if player_id is not None else self.player_id
        player_info.playerName = player_name if player_name is not None else self.player_name
        player_info.playerToken = player_token if player_token is not None else self.player_token
        return player_info
    
    # =============== CSMsgReq 构造方法 ===============
    
    def build_login_req(self, username: str = None, login_type=CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGIN) -> bytes:
        """构造登录请求"""
        player_info = self.create_player_info(
            player_id=0,  # 登录时通常为0
            player_name=username or self.player_name,
            player_token=""
        )
        
        login_req = CSMsg_pb2.CSLoginMsgReq()
        login_req.msgType = login_type
        login_req.info.CopyFrom(player_info)
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_LOGIN
        cs_msg_req.loginReq.CopyFrom(login_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    def build_logout_req(self) -> bytes:
        """构造登出请求"""
        return self.build_login_req(login_type=CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGOUT)
    
    def build_chat_send_req(self, message: str, recipient_name: str) -> bytes:
        """构造发送聊天消息请求"""
        chat_req = CSMsg_pb2.CSChatMsgReq()
        chat_req.msgType = CSMsg_pb2.CSChatMsgType.EN_SEND
        
        # 发送者信息
        chat_req.sendPlayer.CopyFrom(self.create_player_info())
        
        # 接收者信息
        chat_req.receivePlayer.playerName = recipient_name
        chat_req.receivePlayer.playerId = 0
        
        # 聊天消息内容
        chat_msg = chat_req.chatMessage.add()
        chat_msg.msg = message
        chat_msg.sendPlayer.CopyFrom(chat_req.sendPlayer)
        chat_msg.time = int(time.time())
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_req.chatReq.CopyFrom(chat_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    def build_chat_history_req(self) -> bytes:
        """构造聊天历史请求"""
        chat_req = CSMsg_pb2.CSChatMsgReq()
        chat_req.msgType = CSMsg_pb2.CSChatMsgType.EN_HISTORY
        chat_req.sendPlayer.CopyFrom(self.create_player_info())
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_req.chatReq.CopyFrom(chat_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    def build_channel_create_req(self, channel_name: str) -> bytes:
        """构造创建频道请求"""
        channel_req = CSMsg_pb2.CSChannelMsgReq()
        channel_req.msgType = CSMsg_pb2.CSChannelMsgType.EN_CREATE
        channel_req.sendPlayer.CopyFrom(self.create_player_info())
        channel_req.channelInfo.channelName = channel_name
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_req.channelReq.CopyFrom(channel_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    def build_channel_destroy_req(self, channel_name: str) -> bytes:
        """构造销毁频道请求"""
        channel_req = CSMsg_pb2.CSChannelMsgReq()
        channel_req.msgType = CSMsg_pb2.CSChannelMsgType.EN_DESTROY
        channel_req.sendPlayer.CopyFrom(self.create_player_info())
        channel_req.channelInfo.channelName = channel_name
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_req.channelReq.CopyFrom(channel_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    def build_channel_join_req(self, channel_name: str) -> bytes:
        """构造加入频道请求"""
        channel_req = CSMsg_pb2.CSChannelMsgReq()
        channel_req.msgType = CSMsg_pb2.CSChannelMsgType.EN_JOIN
        channel_req.sendPlayer.CopyFrom(self.create_player_info())
        channel_req.channelInfo.channelName = channel_name
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_req.channelReq.CopyFrom(channel_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    def build_channel_send_msg_req(self, channel_name: str, message: str) -> bytes:
        """构造发送频道消息请求"""
        channel_req = CSMsg_pb2.CSChannelMsgReq()
        channel_req.msgType = CSMsg_pb2.CSChannelMsgType.EN_CHANNELMSG_SEND
        channel_req.sendPlayer.CopyFrom(self.create_player_info())
        channel_req.channelInfo.channelName = channel_name
        
        # 添加消息内容
        chat_msg = channel_req.chatMessage.add()
        chat_msg.msg = message
        chat_msg.sendPlayer.CopyFrom(channel_req.sendPlayer)
        chat_msg.time = int(time.time())
        
        cs_msg_req = CSMsg_pb2.CSMsgReq()
        cs_msg_req.CSMsgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_req.channelReq.CopyFrom(channel_req)
        
        return self.create_base_message(cs_msg_req.SerializeToString())
    
    # =============== CSMsgRsp 构造方法 ===============
    
    def build_login_rsp(self, is_success: bool = True, player_id: int = None, player_name: str = None) -> bytes:
        """构造登录响应"""
        login_rsp = CSMsg_pb2.CSLoginMsgRsp()
        login_rsp.msgType = CSMsg_pb2.CSLoginMsgType.EN_PLAYER_LOGIN
        login_rsp.isSuccess = is_success
        
        if is_success:
            login_rsp.info.CopyFrom(self.create_player_info(
                player_id=player_id or self.player_id,
                player_name=player_name or self.player_name
            ))
        
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_LOGIN
        cs_msg_rsp.loginRsp.CopyFrom(login_rsp)
        
        return self.create_base_message(cs_msg_rsp.SerializeToString(), BaseMsg_pb2.MsgBodyType.EN_RSP)
    
    def build_chat_send_rsp(self, is_success: bool = True) -> bytes:
        """构造聊天发送响应"""
        chat_rsp = CSMsg_pb2.CSChatMsgRsp()
        chat_rsp.msgType = CSMsg_pb2.CSChatMsgType.EN_SEND
        chat_rsp.isSuccess = is_success
        chat_rsp.sendPlayer.CopyFrom(self.create_player_info())
        
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_CHAT
        cs_msg_rsp.chatRsp.CopyFrom(chat_rsp)
        
        return self.create_base_message(cs_msg_rsp.SerializeToString(), BaseMsg_pb2.MsgBodyType.EN_RSP)
    
    def build_channel_create_rsp(self, is_success: bool = True, channel_name: str = "test_channel") -> bytes:
        """构造创建频道响应"""
        channel_rsp = CSMsg_pb2.CSChannelMsgRsp()
        channel_rsp.msgType = CSMsg_pb2.CSChannelMsgType.EN_CREATE
        channel_rsp.isSuccess = is_success
        channel_rsp.sendPlayer.CopyFrom(self.create_player_info())
        channel_rsp.channelInfo.channelName = channel_name
        
        cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
        cs_msg_rsp.msgType = CSMsg_pb2.CSMsgType.EN_CHANNEL
        cs_msg_rsp.channelRsp.CopyFrom(channel_rsp)
        
        return self.create_base_message(cs_msg_rsp.SerializeToString(), BaseMsg_pb2.MsgBodyType.EN_RSP)

def print_hex_message(message_bytes: bytes, description: str):
    """以16进制格式打印消息"""
    print(f"\n{'='*60}")
    print(f"消息类型: {description}")
    print(f"消息长度: {len(message_bytes)} 字节")
    print(f"{'='*60}")
    
    # 以16进制格式打印，每行16字节
    hex_str = message_bytes.hex().upper()
    for i in range(0, len(hex_str), 32):  # 32个字符 = 16字节
        line = hex_str[i:i+32]
        # 每两个字符加一个空格
        formatted_line = ' '.join(line[j:j+2] for j in range(0, len(line), 2))
        print(f"{i//2:04X}: {formatted_line}")
    
    # 也打印完整的十六进制字符串（便于复制）
    print(f"\n完整hex字符串:")
    print(hex_str)

def main():
    parser = argparse.ArgumentParser(description='Protocol Buffer 消息构造器')
    parser.add_argument('--type', required=True, 
                       choices=[
                           'login_req', 'logout_req', 'login_rsp',
                           'chat_send_req', 'chat_history_req', 'chat_send_rsp',
                           'channel_create_req', 'channel_destroy_req', 'channel_join_req', 
                           'channel_send_msg_req', 'channel_create_rsp'
                       ],
                       help='要构造的消息类型')
    parser.add_argument('--player-id', type=int, default=1001, help='玩家ID')
    parser.add_argument('--player-name', default='TestUser', help='玩家名称')
    parser.add_argument('--player-token', default='test_token_123', help='玩家Token')
    parser.add_argument('--message', default='Hello World!', help='消息内容')
    parser.add_argument('--recipient', default='TargetUser', help='消息接收者')
    parser.add_argument('--channel', default='test_channel', help='频道名称')
    parser.add_argument('--success', action='store_true', help='响应是否成功(仅对rsp消息有效)')
    
    args = parser.parse_args()
    
    # 创建消息构造器
    builder = MessageBuilder()
    builder.set_player_info(args.player_id, args.player_name, args.player_token)
    
    # 根据类型构造消息
    message_bytes = None
    description = ""
    
    if args.type == 'login_req':
        message_bytes = builder.build_login_req(args.player_name)
        description = f"登录请求 (用户名: {args.player_name})"
    
    elif args.type == 'logout_req':
        message_bytes = builder.build_logout_req()
        description = f"登出请求 (用户名: {args.player_name})"
    
    elif args.type == 'login_rsp':
        message_bytes = builder.build_login_rsp(args.success, args.player_id, args.player_name)
        description = f"登录响应 (成功: {args.success})"
    
    elif args.type == 'chat_send_req':
        message_bytes = builder.build_chat_send_req(args.message, args.recipient)
        description = f"聊天发送请求 (给 {args.recipient}: {args.message})"
    
    elif args.type == 'chat_history_req':
        message_bytes = builder.build_chat_history_req()
        description = "聊天历史请求"
    
    elif args.type == 'chat_send_rsp':
        message_bytes = builder.build_chat_send_rsp(args.success)
        description = f"聊天发送响应 (成功: {args.success})"
    
    elif args.type == 'channel_create_req':
        message_bytes = builder.build_channel_create_req(args.channel)
        description = f"创建频道请求 (频道: {args.channel})"
    
    elif args.type == 'channel_destroy_req':
        message_bytes = builder.build_channel_destroy_req(args.channel)
        description = f"销毁频道请求 (频道: {args.channel})"
    
    elif args.type == 'channel_join_req':
        message_bytes = builder.build_channel_join_req(args.channel)
        description = f"加入频道请求 (频道: {args.channel})"
    
    elif args.type == 'channel_send_msg_req':
        message_bytes = builder.build_channel_send_msg_req(args.channel, args.message)
        description = f"频道消息请求 (频道: {args.channel}, 消息: {args.message})"
    
    elif args.type == 'channel_create_rsp':
        message_bytes = builder.build_channel_create_rsp(args.success, args.channel)
        description = f"创建频道响应 (频道: {args.channel}, 成功: {args.success})"
    
    if message_bytes:
        print_hex_message(message_bytes, description)
    else:
        print("错误: 无法构造指定类型的消息")

if __name__ == "__main__":
    main()
