# Protocol Buffer 消息构造器使用说明

## 简介

`message_builder.py` 是一个用于构造和序列化各种CSMsgReq和CSMsgRsp消息的工具。它可以帮助您：

- 构造各种类型的Protocol Buffer消息
- 以16进制格式查看序列化后的消息内容
- 调试和分析消息格式

## 安装要求

确保已经编译了proto文件并生成了Python绑定：

```bash
cd /home/dev/gameIMSystem
make  # 或者您的编译命令
```

## 使用方法

### 基本语法

```bash
python message_builder.py --type <消息类型> [其他参数]
```

### 支持的消息类型

#### 请求消息 (Req)
- `login_req` - 登录请求
- `logout_req` - 登出请求
- `chat_send_req` - 发送聊天消息请求
- `chat_history_req` - 获取聊天历史请求
- `channel_create_req` - 创建频道请求
- `channel_destroy_req` - 销毁频道请求
- `channel_join_req` - 加入频道请求
- `channel_send_msg_req` - 发送频道消息请求

#### 响应消息 (Rsp)
- `login_rsp` - 登录响应
- `chat_send_rsp` - 聊天发送响应
- `channel_create_rsp` - 创建频道响应

### 参数说明

- `--type` (必需): 要构造的消息类型
- `--player-id`: 玩家ID (默认: 1001)
- `--player-name`: 玩家名称 (默认: TestUser)
- `--player-token`: 玩家Token (默认: test_token_123)
- `--message`: 消息内容 (默认: Hello World!)
- `--recipient`: 消息接收者 (默认: TargetUser)
- `--channel`: 频道名称 (默认: test_channel)
- `--success`: 响应是否成功 (仅对响应消息有效)

## 使用示例

### 1. 构造登录请求

```bash
python message_builder.py --type login_req --player-name "TestUser123"
```

输出示例：
```
============================================================
消息类型: 登录请求 (用户名: TestUser123)
消息长度: 45 字节
============================================================
0000: 08 01 10 01 18 01 12 1F 08 01 0A 1B 12 0B 54 65
0010: 73 74 55 73 65 72 31 32 33 1A 0C 74 65 73 74 5F
0020: 74 6F 6B 65 6E 5F 31 32 33

完整hex字符串:
08011001181212F1F08010A1B120B546573745573657231323311A0C746573745F746F6B656E5F313233
```

### 2. 构造聊天消息请求

```bash
python message_builder.py --type chat_send_req \
    --player-name "Alice" \
    --recipient "Bob" \
    --message "Hello Bob, how are you?"
```

### 3. 构造频道创建请求

```bash
python message_builder.py --type channel_create_req \
    --channel "game_room_1" \
    --player-name "GameMaster"
```

### 4. 构造登录成功响应

```bash
python message_builder.py --type login_rsp \
    --success \
    --player-id 2001 \
    --player-name "NewUser"
```

### 5. 构造登录失败响应

```bash
python message_builder.py --type login_rsp \
    --player-name "InvalidUser"
# 注意：不加 --success 参数，默认为失败
```

### 6. 构造频道消息发送请求

```bash
python message_builder.py --type channel_send_msg_req \
    --channel "general" \
    --message "Welcome everyone!" \
    --player-name "Moderator"
```

## 输出格式说明

工具会输出两种格式的16进制数据：

1. **格式化显示**: 每行显示16个字节，便于阅读
2. **完整hex字符串**: 连续的16进制字符串，便于复制和使用

## 调试技巧

### 1. 比较不同参数的影响

```bash
# 比较不同用户名的消息差异
python message_builder.py --type login_req --player-name "User1"
python message_builder.py --type login_req --player-name "User2"
```

### 2. 验证消息格式

构造的消息可以用于：
- 测试服务器的消息解析
- 验证客户端的消息构造是否正确
- 调试网络传输问题

### 3. 集成到测试脚本

```python
import subprocess
import json

def get_message_hex(msg_type, **kwargs):
    cmd = ['python', 'message_builder.py', '--type', msg_type]
    for key, value in kwargs.items():
        cmd.extend([f'--{key.replace("_", "-")}', str(value)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    # 解析输出获取hex字符串
    return result.stdout
```

## 注意事项

1. 确保Protocol Buffer模块已正确编译和安装
2. 某些消息类型可能需要特定的参数组合
3. 响应消息通常由服务器生成，这里主要用于测试和调试
4. 输出的hex字符串可以直接用于网络调试工具

## 故障排除

### 导入错误
如果出现"无法导入Protocol Buffers模块"错误：
1. 检查proto文件是否已编译
2. 确认build/protocol目录存在
3. 重新编译项目

### 参数错误
如果参数不正确，工具会显示帮助信息：
```bash
python message_builder.py --help
```
