#!/usr/bin/env python3
"""
Protocol Buffer 消息构造器
支持构造各种CSMsgReq和CSMsgRsp消息，并以16进制格式输出序列化结果
"""

import sys
import os
import time
import uuid
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
    
    def create_base_message(self, msg_body: bytes, body_type=BaseMsg_pb2.MsgBodyType.EN_REQ, msg_id: str = None) -> bytes:
        """创建基础消息"""
        base_msg = BaseMsg_pb2.baseMsg()
        msg_info = BaseMsg_pb2.MsgInfo()
        msg_info.msgType = BaseMsg_pb2.MsgType.EN_MSG_TYPE_CS
        msg_info.msgSender = BaseMsg_pb2.MsgSender.EN_MSG_SENDER_GATESVR
        msg_info.msgBodyType = body_type
        
        # 设置msgId，如果没有提供则生成一个
        if msg_id is None:
            msg_id = str(uuid.uuid4())
        msg_info.msgId = msg_id
        
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
    
    def parse_base_message(self, hex_data: str) -> Dict[str, Any]:
        """解析16进制格式的BaseMsg"""
        try:
            # 将16进制字符串转换为bytes
            message_bytes = bytes.fromhex(hex_data.replace(' ', '').replace('\n', ''))
            
            # 解析BaseMsg
            base_msg = BaseMsg_pb2.baseMsg()
            base_msg.ParseFromString(message_bytes)
            
            result = {
                'raw_hex': hex_data,
                'raw_bytes_length': len(message_bytes),
                'msgInfo': {
                    'msgType': base_msg.msgInfo.msgType,
                    'msgSender': base_msg.msgInfo.msgSender,
                    'msgBodyType': base_msg.msgInfo.msgBodyType,
                    'msgId': base_msg.msgInfo.msgId if base_msg.msgInfo.msgId else None
                },
                'msgBody_length': len(base_msg.msgBody),
                'msgBody_hex': base_msg.msgBody.hex()
            }
            
            # 尝试进一步解析msgBody
            if base_msg.msgInfo.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_REQ:
                cs_msg_req = CSMsg_pb2.CSMsgReq()
                cs_msg_req.ParseFromString(base_msg.msgBody)
                result['parsed_body'] = self._parse_cs_msg_req(cs_msg_req)
            elif base_msg.msgInfo.msgBodyType == BaseMsg_pb2.MsgBodyType.EN_RSP:
                cs_msg_rsp = CSMsg_pb2.CSMsgRsp()
                cs_msg_rsp.ParseFromString(base_msg.msgBody)
                result['parsed_body'] = self._parse_cs_msg_rsp(cs_msg_rsp)
            
            return result
            
        except Exception as e:
            return {
                'error': f"解析失败: {str(e)}",
                'raw_hex': hex_data
            }
    
    def _parse_cs_msg_req(self, cs_msg_req) -> Dict[str, Any]:
        """解析CSMsgReq"""
        result = {
            'CSMsgType': cs_msg_req.CSMsgType
        }
        
        if cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_LOGIN and cs_msg_req.HasField('loginReq'):
            result['loginReq'] = {
                'playerId': cs_msg_req.loginReq.playerId,
                'playerName': cs_msg_req.loginReq.playerName,
                'playerToken': cs_msg_req.loginReq.playerToken
            }
        elif cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHAT and cs_msg_req.HasField('chatReq'):
            chat_req = cs_msg_req.chatReq
            result['chatReq'] = {
                'msgType': chat_req.msgType,
                'sendPlayer': {
                    'playerId': chat_req.sendPlayer.playerId,
                    'playerName': chat_req.sendPlayer.playerName,
                    'playerToken': chat_req.sendPlayer.playerToken
                }
            }
            if chat_req.HasField('receivePlayer'):
                result['chatReq']['receivePlayer'] = {
                    'playerId': chat_req.receivePlayer.playerId,
                    'playerName': chat_req.receivePlayer.playerName
                }
            if len(chat_req.chatMessage) > 0:
                result['chatReq']['chatMessages'] = []
                for msg in chat_req.chatMessage:
                    result['chatReq']['chatMessages'].append({
                        'msg': msg.msg,
                        'time': msg.time,
                        'sendPlayer': {
                            'playerId': msg.sendPlayer.playerId,
                            'playerName': msg.sendPlayer.playerName
                        }
                    })
        elif cs_msg_req.CSMsgType == CSMsg_pb2.CSMsgType.EN_CHANNEL and cs_msg_req.HasField('channelReq'):
            channel_req = cs_msg_req.channelReq
            result['channelReq'] = {
                'msgType': channel_req.msgType,
                'sendPlayer': {
                    'playerId': channel_req.sendPlayer.playerId,
                    'playerName': channel_req.sendPlayer.playerName,
                    'playerToken': channel_req.sendPlayer.playerToken
                }
            }
            if channel_req.HasField('channelInfo'):
                result['channelReq']['channelInfo'] = {
                    'channelId': channel_req.channelInfo.channelId,
                    'channelName': channel_req.channelInfo.channelName
                }
            if len(channel_req.chatMessage) > 0:
                result['channelReq']['chatMessages'] = []
                for msg in channel_req.chatMessage:
                    result['channelReq']['chatMessages'].append({
                        'msg': msg.msg,
                        'time': msg.time,
                        'sendPlayer': {
                            'playerId': msg.sendPlayer.playerId,
                            'playerName': msg.sendPlayer.playerName
                        }
                    })
        
        return result
    
    def _parse_cs_msg_rsp(self, cs_msg_rsp) -> Dict[str, Any]:
        """解析CSMsgRsp"""
        result = {
            'msgType': cs_msg_rsp.msgType
        }
        
        if cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_LOGIN and cs_msg_rsp.HasField('loginRsp'):
            result['loginRsp'] = {
                'isSuccess': cs_msg_rsp.loginRsp.isSuccess,
                'playerId': cs_msg_rsp.loginRsp.playerId,
                'playerName': cs_msg_rsp.loginRsp.playerName,
                'playerToken': cs_msg_rsp.loginRsp.playerToken
            }
        elif cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_CHAT and cs_msg_rsp.HasField('chatRsp'):
            chat_rsp = cs_msg_rsp.chatRsp
            result['chatRsp'] = {
                'msgType': chat_rsp.msgType,
                'isSuccess': chat_rsp.isSuccess,
                'sendPlayer': {
                    'playerId': chat_rsp.sendPlayer.playerId,
                    'playerName': chat_rsp.sendPlayer.playerName,
                    'playerToken': chat_rsp.sendPlayer.playerToken
                }
            }
            if len(chat_rsp.chatMessage) > 0:
                result['chatRsp']['chatMessages'] = []
                for msg in chat_rsp.chatMessage:
                    result['chatRsp']['chatMessages'].append({
                        'msg': msg.msg,
                        'time': msg.time,
                        'sendPlayer': {
                            'playerId': msg.sendPlayer.playerId,
                            'playerName': msg.sendPlayer.playerName
                        }
                    })
        elif cs_msg_rsp.msgType == CSMsg_pb2.CSMsgType.EN_CHANNEL and cs_msg_rsp.HasField('channelRsp'):
            channel_rsp = cs_msg_rsp.channelRsp
            result['channelRsp'] = {
                'msgType': channel_rsp.msgType,
                'isSuccess': channel_rsp.isSuccess,
                'sendPlayer': {
                    'playerId': channel_rsp.sendPlayer.playerId,
                    'playerName': channel_rsp.sendPlayer.playerName,
                    'playerToken': channel_rsp.sendPlayer.playerToken
                }
            }
            if channel_rsp.HasField('channelInfo'):
                result['channelRsp']['channelInfo'] = {
                    'channelId': channel_rsp.channelInfo.channelId,
                    'channelName': channel_rsp.channelInfo.channelName
                }
            if len(channel_rsp.chatMessage) > 0:
                result['channelRsp']['chatMessages'] = []
                for msg in channel_rsp.chatMessage:
                    result['channelRsp']['chatMessages'].append({
                        'msg': msg.msg,
                        'time': msg.time,
                        'sendPlayer': {
                            'playerId': msg.sendPlayer.playerId,
                            'playerName': msg.sendPlayer.playerName
                        }
                    })
        
        return result

    def analyze_protobuf_fields(self, hex_data: str) -> Dict[str, Any]:
        """分析protobuf消息的字段结构"""
        try:
            message_bytes = bytes.fromhex(hex_data.replace(' ', '').replace('\n', ''))
            
            result = {
                'total_bytes': len(message_bytes),
                'fields': [],
                'hex_dump': []
            }
            
            # 16进制dump
            for i in range(0, len(message_bytes), 16):
                chunk = message_bytes[i:i+16]
                hex_str = ' '.join(f'{b:02x}' for b in chunk)
                ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                result['hex_dump'].append(f'{i:04x}: {hex_str:<48} {ascii_str}')
            
            # 简单的protobuf字段分析
            offset = 0
            while offset < len(message_bytes):
                if offset >= len(message_bytes):
                    break
                    
                # 读取varint tag
                tag_byte = message_bytes[offset]
                field_number = tag_byte >> 3
                wire_type = tag_byte & 0x07
                
                field_info = {
                    'offset': offset,
                    'field_number': field_number,
                    'wire_type': wire_type,
                    'wire_type_name': self._get_wire_type_name(wire_type)
                }
                
                offset += 1
                
                if wire_type == 0:  # Varint
                    value, bytes_read = self._read_varint(message_bytes, offset)
                    field_info['value'] = value
                    field_info['bytes_read'] = bytes_read
                    offset += bytes_read
                elif wire_type == 2:  # Length-delimited
                    length, bytes_read = self._read_varint(message_bytes, offset)
                    offset += bytes_read
                    if offset + length <= len(message_bytes):
                        data = message_bytes[offset:offset + length]
                        field_info['length'] = length
                        field_info['data_hex'] = data.hex()
                        # 尝试解析为字符串
                        try:
                            field_info['data_as_string'] = data.decode('utf-8')
                        except:
                            pass
                        offset += length
                    else:
                        break
                else:
                    # 其他wire type暂不处理
                    break
                
                result['fields'].append(field_info)
            
            return result
            
        except Exception as e:
            return {
                'error': f"分析失败: {str(e)}",
                'raw_hex': hex_data
            }
    
    def _get_wire_type_name(self, wire_type: int) -> str:
        """获取wire type名称"""
        wire_types = {
            0: 'Varint',
            1: 'Fixed64',
            2: 'Length-delimited',
            3: 'Start group',
            4: 'End group',
            5: 'Fixed32'
        }
        return wire_types.get(wire_type, f'Unknown({wire_type})')
    
    def _read_varint(self, data: bytes, offset: int) -> tuple[int, int]:
        """读取varint值"""
        value = 0
        shift = 0
        bytes_read = 0
        
        while offset + bytes_read < len(data):
            byte = data[offset + bytes_read]
            value |= (byte & 0x7F) << shift
            bytes_read += 1
            
            if (byte & 0x80) == 0:
                break
            shift += 7
            
            if bytes_read > 10:  # 防止无限循环
                break
        
        return value, bytes_read

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
    parser = argparse.ArgumentParser(description='Protocol Buffer 消息构造器和解析器')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 构造消息的子命令
    build_parser = subparsers.add_parser('build', help='构造消息')
    build_parser.add_argument('--type', required=True, 
                       choices=[
                           'login_req', 'logout_req', 'login_rsp',
                           'chat_send_req', 'chat_history_req', 'chat_send_rsp',
                           'channel_create_req', 'channel_destroy_req', 'channel_join_req', 
                           'channel_send_msg_req', 'channel_create_rsp'
                       ],
                       help='要构造的消息类型')
    build_parser.add_argument('--player-id', type=int, default=1001, help='玩家ID')
    build_parser.add_argument('--player-name', default='TestUser', help='玩家名称')
    build_parser.add_argument('--player-token', default='test_token_123', help='玩家Token')
    build_parser.add_argument('--message', default='Hello World!', help='消息内容')
    build_parser.add_argument('--recipient', default='TargetUser', help='消息接收者')
    build_parser.add_argument('--channel', default='test_channel', help='频道名称')
    build_parser.add_argument('--success', action='store_true', help='响应是否成功(仅对rsp消息有效)')
    
    # 解析消息的子命令
    parse_parser = subparsers.add_parser('parse', help='解析消息')
    parse_parser.add_argument('--hex', required=True, help='要解析的16进制数据')
    parse_parser.add_argument('--format', choices=['json', 'detailed'], default='detailed', help='输出格式')
    
    # 分析字段的子命令
    analyze_parser = subparsers.add_parser('analyze', help='分析protobuf字段结构')
    analyze_parser.add_argument('--hex', required=True, help='要分析的16进制数据')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建消息构造器
    builder = MessageBuilder()
    
    if args.command == 'build':
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
    
    elif args.command == 'parse':
        result = builder.parse_base_message(args.hex)
        
        if args.format == 'json':
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 详细格式输出
            if 'error' in result:
                print(f"解析失败: {result['error']}")
                return
            
            print("=== BaseMsg 解析结果 ===")
            print(f"原始16进制: {result['raw_hex']}")
            print(f"消息总长度: {result['raw_bytes_length']} 字节")
            print()
            
            print("msgInfo:")
            msg_info = result['msgInfo']
            print(f"  msgType: {msg_info['msgType']}")
            print(f"  msgSender: {msg_info['msgSender']}")
            print(f"  msgBodyType: {msg_info['msgBodyType']}")
            print(f"  msgId: {msg_info['msgId']}")
            print()
            
            print(f"msgBody长度: {result['msgBody_length']} 字节")
            print(f"msgBody(hex): {result['msgBody_hex']}")
            
            if 'parsed_body' in result:
                print()
                print("解析的msgBody内容:")
                _print_parsed_body(result['parsed_body'])
    
    elif args.command == 'analyze':
        result = builder.analyze_protobuf_fields(args.hex)
        
        if 'error' in result:
            print(f"分析失败: {result['error']}")
            return
        
        print("=== Protobuf 字段分析 ===")
        print(f"总字节数: {result['total_bytes']}")
        print()
        
        print("16进制dump:")
        for line in result['hex_dump']:
            print(line)
        print()
        
        print("字段分析:")
        for field in result['fields']:
            print(f"  字段 {field['field_number']}: 偏移量 {field['offset']}, "
                  f"类型 {field['wire_type_name']} ({field['wire_type']})")
            if 'value' in field:
                print(f"    值: {field['value']}")
            if 'length' in field:
                print(f"    长度: {field['length']}")
                print(f"    数据(hex): {field['data_hex']}")
                if 'data_as_string' in field:
                    print(f"    数据(string): {field['data_as_string']}")


def _print_parsed_body(parsed_body, indent=0):
    """递归打印解析后的消息体"""
    prefix = "  " * indent
    
    for key, value in parsed_body.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            _print_parsed_body(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [{len(value)} 项]")
            for i, item in enumerate(value):
                print(f"{prefix}  [{i}]:")
                if isinstance(item, dict):
                    _print_parsed_body(item, indent + 2)
                else:
                    print(f"{prefix}    {item}")
        else:
            print(f"{prefix}{key}: {value}")

if __name__ == "__main__":
    main()
