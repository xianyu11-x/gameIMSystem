#!/usr/bin/env python3
"""
简单的压力测试示例
演示如何使用 TestClient 和 StressTestManager
"""

import time
import threading
from testClient import TestClient
from stress_test import StressTestManager

def simple_single_client_test():
    """单个客户端测试示例"""
    print("=== 单个客户端测试 ===")
    
    def on_login_success(client_id, username):
        print(f"客户端 {client_id} 登录成功: {username}")
    
    def on_error(error_msg):
        print(f"错误: {error_msg}")
    
    # 创建客户端
    client = TestClient(client_id=1, host="localhost", port=8888)
    client.on_login_success = on_login_success
    client.on_error = on_error
    
    # 手动分配用户名
    timestamp = int(time.time()) % 10000
    client.assigned_username = f"StressUser_{timestamp}_0001"
    
    try:
        # 连接
        if client.connect():
            print("连接成功")
            
            # 登录
            if client.login(client.assigned_username):
                print("登录请求已发送")
                time.sleep(2)  # 等待登录完成
                
                if client.player_name:
                    print(f"当前用户: {client.player_name}")
                    
                    # 发送私聊消息 - 必须指定接收者
                    # 创建一个模拟的接收者用户名
                    target_user = f"StressUser_{timestamp}_0002"
                    print(f"尝试发送消息给: {target_user}")
                    client.send_chat_message("Hello, this is a test message!", target_user)
                    time.sleep(1)
                    
                    # 加入频道
                    client.join_channel("test_room")
                    time.sleep(1)
                    
                    # 发送频道消息
                    client.send_channel_message("test_room", "Hello from test room!")
                    time.sleep(1)
                    
                    # 登出
                    client.logout()
                    time.sleep(1)
                else:
                    print("登录失败")
        else:
            print("连接失败")
            
    finally:
        client.disconnect()
        print("测试完成")
        print(f"统计信息: {client.get_stats()}")

def simple_stress_test():
    """简单压力测试示例"""
    print("\n=== 压力测试示例 ===")
    
    # 测试配置
    scenario_config = {
        'test_duration': 20,      # 测试20秒
        'chat_interval': 3,       # 每3秒发送一条消息
        'login_delay': 1.0,       # 登录延迟1秒内
        'max_concurrent_clients': 20,  # 最大并发20个客户端
        'enable_channel_test': True,
        'channels_to_join': ['simple_test_room1', 'simple_test_room2']
    }
    
    # 创建测试管理器
    test_manager = StressTestManager(host="localhost", port=8888)
    
    # 运行小规模压力测试 (20个客户端)
    test_manager.run_stress_test(20, scenario_config)

def gradual_stress_test():
    """渐进式压力测试"""
    print("\n=== 渐进式压力测试 ===")
    
    # 配置不同规模的测试
    test_scales = [10, 50, 100, 200]
    
    for num_clients in test_scales:
        print(f"\n开始 {num_clients} 客户端测试...")
        
        scenario_config = {
            'test_duration': 15,
            'chat_interval': 4,
            'login_delay': 2.0,
            'max_concurrent_clients': min(num_clients, 50),
            'enable_channel_test': True,
            'channels_to_join': [f'gradual_test_room_{num_clients}']
        }
        
        test_manager = StressTestManager(host="localhost", port=8888)
        test_manager.run_stress_test(num_clients, scenario_config)
        
        # 保存结果
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        test_manager.save_results(f'gradual_test_{num_clients}clients_{timestamp}.json')
        
        # 等待一段时间再进行下一轮测试
        print(f"等待10秒后进行下一轮测试...")
        time.sleep(10)

if __name__ == "__main__":
    import sys
    
    print("选择测试类型:")
    print("1. 单个客户端测试")
    print("2. 简单压力测试 (20个客户端)")
    print("3. 渐进式压力测试 (10, 50, 100, 200个客户端)")
    print("4. 自定义1000客户端压力测试")
    
    try:
        choice = input("请输入选择 (1-4): ").strip()
        
        if choice == "1":
            simple_single_client_test()
        elif choice == "2":
            simple_stress_test()
        elif choice == "3":
            gradual_stress_test()
        elif choice == "4":
            print("开始1000客户端压力测试...")
            scenario_config = {
                'test_duration': 60,      # 测试60秒
                'chat_interval': 5,       # 每5秒发送一条消息
                'login_delay': 3.0,       # 登录延迟3秒内
                'max_concurrent_clients': 100,  # 最大并发100个客户端
                'enable_channel_test': True,
                'channels_to_join': ['extreme_1000_room1', 'extreme_1000_room2', 'extreme_1000_general']
            }
            
            test_manager = StressTestManager(host="localhost", port=8888)
            test_manager.run_stress_test(1000, scenario_config)
            
            # 保存结果
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            test_manager.save_results(f'stress_test_1000clients_{timestamp}.json')
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试出错: {str(e)}")
