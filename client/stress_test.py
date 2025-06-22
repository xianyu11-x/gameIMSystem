#!/usr/bin/env python3
"""
游戏IM系统压力测试工具
支持同时启动多个客户端进行登录、聊天、频道等功能的压力测试
"""

import time
import threading
import random
import argparse
import json
import os
import sys
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from testClient import TestClient, generate_random_username, generate_random_message, generate_random_channel_name

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

class StressTestManager:
    """压力测试管理器"""
    
    def __init__(self, host: str = "localhost", port: int = 8888):
        self.host = host
        self.port = port
        self.clients: List[TestClient] = []
        self.user_names: List[str] = []  # 预生成的用户名列表
        self.admin_client: Optional[TestClient] = None  # 频道管理客户端
        self.test_results: Dict[str, Any] = {
            'total_clients': 0,
            'successful_connections': 0,
            'successful_logins': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'total_errors': 0,
            'test_duration': 0,
            'start_time': None,
            'end_time': None,
            'client_details': []
        }
        self.lock = threading.Lock()
        
    def on_login_success(self, client_id: int, username: str):
        """登录成功回调"""
        with self.lock:
            print(f"✓ Client {client_id} ({username}) 登录成功")
    
    def on_error(self, error_msg: str):
        """错误回调"""
        with self.lock:
            print(f"✗ {error_msg}")
    
    def on_message_received(self, client_id: int, msg):
        """消息接收回调"""
        with self.lock:
            # 可以根据需要处理接收到的消息
            pass
    
    def create_clients(self, num_clients: int) -> List[TestClient]:
        """创建测试客户端并分配用户名"""
        # 先生成所有用户名
        self.user_names = self.generate_user_names(num_clients)
        
        clients = []
        for i in range(num_clients):
            client = TestClient(client_id=i, host=self.host, port=self.port)
            client.on_login_success = self.on_login_success
            client.on_error = self.on_error
            client.on_message_received = self.on_message_received
            
            # 为客户端分配预生成的用户名
            client.assigned_username = self.user_names[i]
            
            clients.append(client)
        return clients
    
    def connect_client(self, client: TestClient) -> bool:
        """连接单个客户端"""
        return client.connect()
    
    def login_client(self, client: TestClient) -> bool:
        """登录单个客户端，使用预分配的用户名"""
        username = getattr(client, 'assigned_username', f"TestUser_{client.client_id}")
        return client.login(username)
    
    def run_client_scenario(self, client: TestClient, scenario_config: Dict[str, Any]):
        """运行客户端测试场景"""
        success = False
        try:
            # 连接
            if not client.connect():
                return False
            
            # 等待随机时间避免瞬间冲击
            time.sleep(random.uniform(0, scenario_config.get('login_delay', 10.0)))
            
            # 登录，使用预分配的用户名
            username = getattr(client, 'assigned_username', f"TestUser_{client.client_id}")
            if not client.login(username):
                return False
            
            # 等待登录完成
            # login_wait_time = 20.0
            # login_start = time.time()
            # while time.time() - login_start < login_wait_time:
            #     if client.player_name:
            #         break
            #     time.sleep(0.5)
            time.sleep(20)
            # 检查是否登录成功
            if not client.player_name:
                self.on_error(f"Client {client.client_id} login timeout after 20s")
                return False
            
            # 执行测试场景
            self._execute_test_actions(client, scenario_config)
            success = True
            return True
            
        except Exception as e:
            self.on_error(f"Client {client.client_id} scenario failed: {str(e)}")
            return False
        finally:
            # 确保清理，无论是否成功
            time.sleep(20)
            try:
                # 使用新的安全清理方法
                client.safe_cleanup()
            except Exception as cleanup_error:
                self.on_error(f"Client {client.client_id} cleanup error: {str(cleanup_error)}")
                # 即使清理失败，也要强制断开连接
                try:
                    client.disconnect()
                except:
                    pass
    
    def _execute_test_actions(self, client: TestClient, config: Dict[str, Any]):
        """执行测试动作"""
        test_duration = config.get('test_duration', 30)  # 默认30秒
        chat_interval = config.get('chat_interval', 5)   # 默认5秒发一条消息
        channel_test = config.get('enable_channel_test', True)
        joined_channels = []
        start_time = time.time()
        
        # 如果启用频道测试，随机加入一些频道
        if channel_test:
            channels_to_join = config.get('channels_to_join', ['test_room_1', 'test_room_2', 'general'])
            for channel in random.sample(channels_to_join, min(1, len(channels_to_join))):
                client.join_channel(channel)
                joined_channels.append(channel)
                time.sleep(0.5)
        
        # 主测试循环
        while time.time() - start_time < test_duration:
            # 发送私聊消息 - 必须指定接收者
            if random.random() < 0.4:  # 70%概率发送私聊消息
                message = generate_random_message()
                
                # 从预生成的用户名列表中随机选择接收者
                # 确保不发送给自己
                available_recipients = [name for name in self.user_names 
                                      if name != getattr(client, 'assigned_username', None)]
                
                if available_recipients:
                    recipient_name = random.choice(available_recipients)
                    client.send_chat_message(message, recipient_name)
                else:
                    # 如果没有可用的接收者，跳过这次发送
                    if self.on_error:
                        self.on_error(f"Client {client.client_id} no available recipients")
            
            # 发送频道消息
            if channel_test and random.random() < 0.1:  # 30%概率发送频道消息
                channel = random.choice(joined_channels)
                message = generate_random_message()
                client.send_channel_message(channel, message)
            
            # 等待下次发送
            time.sleep(random.uniform(chat_interval * 0.5, chat_interval * 1.5))
    
    def run_stress_test(self, num_clients: int, scenario_config: Dict[str, Any]):
        """运行压力测试"""
        print(f"开始压力测试: {num_clients} 个客户端")
        print(f"目标服务器: {self.host}:{self.port}")
        print("注意: 所有聊天消息都需要指定接收者（私聊模式）")
        print("-" * 50)
        
        self.test_results['start_time'] = time.time()
        self.test_results['total_clients'] = num_clients
        
        print("-" * 50)
        
        # 步骤2: 创建客户端（包含用户名生成）
        self.clients = self.create_clients(num_clients)
        
        # 步骤3: 使用线程池执行测试
        max_workers = min(num_clients, scenario_config.get('max_concurrent_clients', 50))
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有客户端任务
                future_to_client = {
                    executor.submit(self.run_client_scenario, client, scenario_config): client
                    for client in self.clients
                }
                
                # 等待所有任务完成
                for future in as_completed(future_to_client):
                    client = future_to_client[future]
                    try:
                        success = future.result()
                        if success:
                            self.test_results['successful_connections'] += 1
                            if client.stats['login_success'] > 0:
                                self.test_results['successful_logins'] += 1
                    except Exception as e:
                        self.on_error(f"Client {client.client_id} failed: {str(e)}")
            
            self.test_results['end_time'] = time.time()
            self.test_results['test_duration'] = self.test_results['end_time'] - self.test_results['start_time']
            
            # 收集统计信息
            self._collect_statistics()
            
            # 输出结果
            self._print_results()
            
        finally:
            # 步骤4: 清理测试频道
            print("-" * 50)
            if not self.cleanup_test_channels(scenario_config):
                print("⚠️  频道清理可能未完全成功")
    
    def _collect_statistics(self):
        """收集统计信息"""
        for client in self.clients:
            stats = client.get_stats()
            self.test_results['total_messages_sent'] += stats['messages_sent']
            self.test_results['total_messages_received'] += stats['messages_received']
            self.test_results['total_errors'] += stats['errors']
            
            # 获取详细日志统计
            logs_summary = client.get_logs_summary()
            
            self.test_results['client_details'].append({
                'client_id': client.client_id,
                'assigned_username': getattr(client, 'assigned_username', None),
                'actual_username': client.player_name,
                'stats': stats,
                'logs_summary': logs_summary
            })
    
    def _print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("压力测试结果")
        print("=" * 60)
        print(f"测试时长: {self.test_results['test_duration']:.2f} 秒")
        print(f"总客户端数: {self.test_results['total_clients']}")
        print(f"成功连接数: {self.test_results['successful_connections']}")
        print(f"成功登录数: {self.test_results['successful_logins']}")
        print(f"连接成功率: {self.test_results['successful_connections']/self.test_results['total_clients']*100:.1f}%")
        print(f"登录成功率: {self.test_results['successful_logins']/self.test_results['total_clients']*100:.1f}%")
        print(f"总发送消息数: {self.test_results['total_messages_sent']}")
        print(f"总接收消息数: {self.test_results['total_messages_received']}")
        print(f"总错误数: {self.test_results['total_errors']}")
        
        if self.test_results['test_duration'] > 0:
            msg_per_sec = self.test_results['total_messages_sent'] / self.test_results['test_duration']
            print(f"平均消息发送速率: {msg_per_sec:.2f} 消息/秒")
        
        # 添加详细日志统计
        print("\n" + "-" * 60)
        print("详细日志统计")
        print("-" * 60)
        
        total_sent_commands = 0
        total_received_private = 0
        total_received_channel = 0
        
        for client_detail in self.test_results['client_details']:
            if 'logs_summary' in client_detail:
                logs = client_detail['logs_summary']
                total_sent_commands += logs.get('sent_commands_count', 0)
                total_received_private += logs.get('received_private_chats_count', 0)
                total_received_channel += logs.get('received_channel_chats_count', 0)
        
        print(f"总发送命令数: {total_sent_commands}")
        print(f"总接收私聊消息数: {total_received_private}")
        print(f"总接收群聊消息数: {total_received_channel}")
        
        # 显示部分客户端的详细信息（前5个和后5个）
        if len(self.test_results['client_details']) > 0:
            print("\n" + "-" * 60)
            print("客户端详细信息示例")
            print("-" * 60)
            
            # 显示前5个客户端
            show_count = min(5, len(self.test_results['client_details']))
            for i in range(show_count):
                client_detail = self.test_results['client_details'][i]
                logs = client_detail.get('logs_summary', {})
                print(f"客户端 {client_detail['client_id']} ({client_detail['actual_username']}):")
                print(f"  发送命令: {logs.get('sent_commands_count', 0)}")
                print(f"  接收私聊: {logs.get('received_private_chats_count', 0)}")
                print(f"  接收群聊: {logs.get('received_channel_chats_count', 0)}")
                print(f"  登录事件: {logs.get('login_events_count', 0)}")
                print(f"  频道事件: {logs.get('channel_events_count', 0)}")
                print()
            
            # 如果客户端数量超过10个，显示后5个
            if len(self.test_results['client_details']) > 10:
                print("...")
                for i in range(len(self.test_results['client_details']) - 5, len(self.test_results['client_details'])):
                    client_detail = self.test_results['client_details'][i]
                    logs = client_detail.get('logs_summary', {})
                    print(f"客户端 {client_detail['client_id']} ({client_detail['actual_username']}):")
                    print(f"  发送命令: {logs.get('sent_commands_count', 0)}")
                    print(f"  接收私聊: {logs.get('received_private_chats_count', 0)}")
                    print(f"  接收群聊: {logs.get('received_channel_chats_count', 0)}")
                    print(f"  登录事件: {logs.get('login_events_count', 0)}")
                    print(f"  频道事件: {logs.get('channel_events_count', 0)}")
                    print()
        
        print("=" * 60)
    
    def save_results(self, filename: str):
        """保存测试结果到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        print(f"测试结果已保存到: {filename}")
    
    def save_detailed_logs(self, filename: str):
        """保存详细日志到文件"""
        detailed_logs = {
            'test_info': {
                'total_clients': self.test_results['total_clients'],
                'test_duration': self.test_results['test_duration'],
                'start_time': self.test_results['start_time'],
                'end_time': self.test_results['end_time']
            },
            'client_logs': []
        }
        
        for client in self.clients:
            if hasattr(client, 'get_detailed_logs'):
                client_logs = client.get_detailed_logs()
                detailed_logs['client_logs'].append(client_logs)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(detailed_logs, f, indent=2, ensure_ascii=False)
        print(f"详细日志已保存到: {filename}")
    
    def generate_user_names(self, num_clients: int) -> List[str]:
        """预生成所有客户端的用户名"""
        user_names = []
        timestamp = int(time.time()) % 10000  # 使用时间戳避免重复
        
        for i in range(num_clients):
            # 生成格式: StressUser_{timestamp}_{id}
            username = f"StressUser_{timestamp}_{i:04d}"
            user_names.append(username)
        
        print(f"已生成 {len(user_names)} 个用户名")
        print(f"用户名格式示例: {user_names[0]} ~ {user_names[-1]}")
        return user_names
    
    def setup_test_channels(self, scenario_config: Dict[str, Any]) -> bool:
        """在测试前设置频道"""
        if not scenario_config.get('enable_channel_test', False):
            return True
        
        channels_to_create = scenario_config.get('channels_to_join', [])
        if not channels_to_create:
            return True
        
        print(f"正在创建测试频道: {channels_to_create}")
        
        # 创建一个专门的管理客户端
        self.admin_client = TestClient(client_id=-1, host=self.host, port=self.port)
        self.admin_client.assigned_username = f"ChannelAdmin_{int(time.time()) % 10000}"
        
        # 保存管理员用户名供清理时使用
        self.admin_username = self.admin_client.assigned_username
        
        try:
            # 连接和登录
            if not self.admin_client.connect():
                print("❌ 管理客户端连接失败")
                return False
            
            if not self.admin_client.login(self.admin_client.assigned_username):
                print("❌ 管理客户端登录失败")
                return False
            
            # 等待登录完成
            time.sleep(2.0)
            
            if not self.admin_client.player_name:
                print("❌ 管理客户端登录验证失败")
                return False
            
            print(f"✓ 管理客户端登录成功: {self.admin_client.player_name}")
            
            # 创建所有需要的频道
            success_count = 0
            for channel_name in channels_to_create:
                if self.admin_client.create_channel(channel_name):
                    print(f"✓ 频道创建请求已发送: {channel_name}")
                    success_count += 1
                    time.sleep(0.5)  # 避免请求过快
                else:
                    print(f"❌ 频道创建失败: {channel_name}")
            
            # 等待频道创建完成
            time.sleep(2.0)
            
            print(f"频道创建完成: {success_count}/{len(channels_to_create)} 个频道")
            
            if not self.admin_client.logout():
                print("❌ 管理客户端登出失败")
                return False
            print("✓ 管理客户端登出成功")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ 频道设置过程出错: {str(e)}")
            return False

    def cleanup_test_channels(self, scenario_config: Dict[str, Any]) -> bool:
        """在测试后清理频道"""
        if not scenario_config.get('enable_channel_test', False):
            return True
        
        channels_to_destroy = scenario_config.get('channels_to_join', [])
        if not channels_to_destroy:
            return True
        
        # 检查是否有保存的管理员用户名
        if not hasattr(self, 'admin_username') or not self.admin_username:
            print("⚠️  没有找到原始管理员用户名，跳过频道清理")
            return True
        
        print(f"正在清理测试频道: {channels_to_destroy}")
        print(f"使用原始管理员用户名: {self.admin_username}")
        
        try:
            # 创建一个全新的清理客户端，使用原始管理员用户名
            cleanup_client = TestClient(client_id=-2, host=self.host, port=self.port)
            cleanup_client.assigned_username = self.admin_username
            
            print(f"创建新的清理客户端，用户名: {self.admin_username}")
            
            # 连接
            print("正在连接到服务器...")
            if not cleanup_client.connect():
                print("❌ 清理客户端连接失败")
                return False
            print("✓ 清理客户端连接成功")
            
            # 登录
            print(f"正在登录用户: {self.admin_username}")
            if not cleanup_client.login(self.admin_username):
                print("❌ 清理客户端登录请求发送失败")
                cleanup_client.disconnect()
                return False
            
            # 等待登录完成并验证
            login_wait_time = 10.0
            login_start = time.time()
            while time.time() - login_start < login_wait_time:
                if cleanup_client.player_name:
                    break
                time.sleep(0.5)
            
            # 验证登录成功
            if not cleanup_client.player_name:
                print(f"❌ 清理客户端登录超时，等待了 {login_wait_time} 秒")
                print(f"  - 连接状态: {cleanup_client.connected}")
                print(f"  - player_name: {cleanup_client.player_name}")
                cleanup_client.disconnect()
                return False
                
            print(f"✓ 清理客户端登录成功: {cleanup_client.player_name}")
            print(f"  - 玩家ID: {cleanup_client.player_id}")
            print(f"  - Token: {cleanup_client.player_token}")
            
            # 等待一下确保登录完全处理完成
            time.sleep(1.0)
            
            # 销毁所有频道
            success_count = 0
            for i, channel_name in enumerate(channels_to_destroy):
                print(f"正在销毁频道 [{i+1}/{len(channels_to_destroy)}]: {channel_name}")
                print(f"  - 使用管理员: {cleanup_client.player_name}")
                
                # 再次验证客户端状态
                if not cleanup_client.player_name:
                    print(f"❌ 客户端player_name为空，无法继续销毁频道")
                    break
                    
                if not cleanup_client.connected:
                    print(f"❌ 客户端连接已断开，无法继续销毁频道")
                    break
                
                try:
                    if cleanup_client.destroy_channel(channel_name):
                        print(f"✓ 频道销毁请求已发送: {channel_name}")
                        success_count += 1
                    else:
                        print(f"❌ 频道销毁失败: {channel_name}")
                        print(f"  - 连接状态: {cleanup_client.connected}")
                        print(f"  - 玩家名称: {cleanup_client.player_name}")
                        print(f"  - 玩家ID: {cleanup_client.player_id}")
                    
                    # 每次销毁后稍等
                    time.sleep(0.8)
                    
                except Exception as e:
                    print(f"❌ 销毁频道 {channel_name} 时出错: {str(e)}")
            
            # 等待销毁完成
            print("等待频道销毁完成...")
            time.sleep(2.0)
            
            print(f"频道清理完成: {success_count}/{len(channels_to_destroy)} 个频道")
            
            # 清理客户端
            print("正在登出清理客户端...")
            if cleanup_client.player_name:
                if cleanup_client.logout():
                    print("✓ 清理客户端登出成功")
                else:
                    print("❌ 清理客户端登出失败")
                time.sleep(0.5)
            
            cleanup_client.disconnect()
            print("✓ 清理客户端已断开连接")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ 频道清理过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理管理客户端
            if hasattr(self, 'admin_client') and self.admin_client:
                if self.admin_client.player_name:
                    self.admin_client.logout()
                    time.sleep(0.5)
                self.admin_client.disconnect()
                self.admin_client = None

def main():
    parser = argparse.ArgumentParser(description='游戏IM系统压力测试工具')
    parser.add_argument('--host', default='localhost', help='服务器地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=8888, help='服务器端口 (默认: 8888)')
    parser.add_argument('--clients', type=int, default=100, help='客户端数量 (默认: 100)')
    parser.add_argument('--duration', type=int, default=30, help='测试持续时间(秒) (默认: 30)')
    parser.add_argument('--chat-interval', type=float, default=5.0, help='消息发送间隔(秒) (默认: 5.0)')
    parser.add_argument('--login-delay', type=float, default=2.0, help='登录延迟范围(秒) (默认: 2.0)')
    parser.add_argument('--max-concurrent', type=int, default=50, help='最大并发客户端数 (默认: 50)')
    parser.add_argument('--disable-channel', action='store_true', help='禁用频道测试')
    parser.add_argument('--channel-names', nargs='+', default=['stress_test_room1', 'stress_test_room2','stress_test_room3','stress_test_room4','stress_test_room5','stress_test_room6','stress_test_room7'], 
                       help='测试频道名称列表 (默认: stress_test_room1 stress_test_room2)')
    parser.add_argument('--output', help='结果输出文件名')
    
    args = parser.parse_args()
    
    # 配置测试场景
    scenario_config = {
        'test_duration': args.duration,
        'chat_interval': args.chat_interval,
        'login_delay': args.login_delay,
        'max_concurrent_clients': args.max_concurrent,
        'enable_channel_test': not args.disable_channel,
        'channels_to_join': args.channel_names if not args.disable_channel else []
    }
    
    # 创建测试管理器
    test_manager = StressTestManager(host=args.host, port=args.port)
    
    # 运行测试
    try:
        # 设置频道
        test_manager.setup_test_channels(scenario_config)
        
        test_manager.run_stress_test(args.clients, scenario_config)
        
        # 保存结果
        if args.output:
            test_manager.save_results(args.output)
            # 也保存详细日志
            detailed_log_filename = args.output.replace('.json', '_detailed.json')
            test_manager.save_detailed_logs(detailed_log_filename)
        else:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            test_manager.save_results(f'stress_test_results_{timestamp}.json')
            test_manager.save_detailed_logs(f'stress_test_detailed_{timestamp}.json')
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试失败: {str(e)}")
    # finally:
    #     # 清理频道
    #     test_manager.cleanup_test_channels(scenario_config)

if __name__ == "__main__":
    main()
