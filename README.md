# StickS3 AI 余额查询 — MicroPython 版

用 **MicroPython（UIFlow2 固件）** 实现的 StickS3 固件，开机自动连 WiFi、查询多家 AI 平台余额并显示在屏幕上。

> 项目文件全部在本目录（根目录）：`main.py`、`config.py`、`README.md`。

## 已支持的平台

| 平台 | 余额接口 | 状态 |
|---|---|---|
| DeepSeek | `GET https://api.deepseek.com/user/balance` | ✅ 可用 |
| Moonshot（Kimi） | `GET https://api.moonshot.cn/v1/users/me/balance` | ✅ 可用 |
| 硅基流动 SiliconFlow | `GET https://api.siliconflow.cn/v1/user/info` | ⚠️ 暂不可用 |

> 硅基流动暂不可用原因：其接口已迁移到 `.com` 域名并由 Cloudflare 防护，ESP32 的 mbedTLS 握手被拦截（返回 426/410）。当前无法在 MicroPython 环境下绕过，已暂时保留在站点列表但会查询失败。

## 已踩坑验证的关键结论

| 项目 | 结论 |
|---|---|
| HTTP 库 | 用 **`requests`**（UIFlow2 内置），**不是** `urequests`（该版本已移除） |
| 开机启动 | **删除 `/flash/boot.py`**，跳过 UIFlow2 启动菜单，直接跑 `main.py` |
| 黑屏根因 | UIFlow2 的 `startup` 模块读 NVS 报 `ESP_ERR_NVS_NOT_FOUND`，删 boot.py 即解 |
| 文件位置 | 脚本必须放 **`/flash/`** 目录（不是根目录 `/`） |
| 中文字体 | 用 `EFontCN24`（纯 ASCII 字体如 DejaVu 不显示中文，会变方块） |
| Label 改色 | `Widgets.Label` 有 `setColor()` 方法，可动态改文字颜色 |

## 文件清单

| 文件 | 作用 |
|---|---|
| `main.py` | 主程序（连 WiFi → 查余额 → 显示 + 按键交互） |
| `config.py` | 配置文件（WiFi + 各平台 API Key） |

## 环境准备

### 1. 烧录 UIFlow2 固件

1. 下载 [M5Burner](https://docs.m5stack.com/en/download)
2. 选设备 **StickS3**，烧录 **UIFlow2** 固件
3. 烧录配置：**Boot Option 选 `Run main.py directly`**

### 2. 安装上传工具

推荐 **Thonny**：
1. 下载安装 [Thonny](https://thonny.org/)
2. 工具 → 选项 → 解释器 → 选「MicroPython (ESP32)」，端口选设备 COM 口

## 使用步骤

### 1. 填写配置

编辑 `config.py`：

```python
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"

DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SILICONFLOW_API_KEY = ""   # 暂不可用，留空即可
MOONSHOT_API_KEY = ""      # 填入你的 Moonshot Key
```

### 2. 上传文件到 /flash

用 Thonny 打开设备文件面板，把 `main.py` 和 `config.py` 上传到 **`/flash/`** 目录（务必确认路径，不是根目录）。

### 3. 删除 boot.py（关键）

在 Thonny 设备文件面板里，删除 `/flash/boot.py`（或在 Shell 执行）：

```python
import os
os.remove('/flash/boot.py')
```

### 4. 重启设备

重启后自动运行：连 WiFi → 同步时间 → 查余额 → 显示。

## 屏幕显示

**成功时：**

```
DeepSeek          ← 白字（站点名）
CNY 125.80        ← 绿字大数字（币种+余额）
OK                ← 灰字（状态）
刷新 15:30:05     ← 刷新时间（"刷新"中文 + 数字）
A刷新 B换站        ← 底部提示
```

**失败时：**

```
SiliconFlow       ← 白字（站点名）
FAIL              ← 红字大数字（查询失败）
No Key            ← 灰字（错误原因）
```

## 按键操作

| 操作 | 功能 |
|---|---|
| 单击 A 键 | 刷新当前站点余额 |
| 单击 B 键 | 切换到下一站点并自动刷新 |

## 修改 WiFi / API Key

直接编辑 `config.py` 后重新上传到 `/flash/`，重启即可（无需重编译固件）。

## 串口日志

每次查询都会在串口打印清晰的日志，包含 `[结果]` 汇总行：

```
[API] 查询 DeepSeek 余额...
[API] URL: https://api.deepseek.com/user/balance
[API] HTTP 状态码: 200
[结果] DeepSeek 余额: CNY 125.80 (OK)
```

## 常见问题

- **开机报 `ESP_ERR_NVS_NOT_FOUND`**：`/flash/boot.py` 没删干净，删掉即可。
- **连接 Thonny 后屏幕卡住、按键失效**：Thonny 连接时会发送 Ctrl+C 中断程序，导致主循环停止。平时使用请**不要连 Thonny**，直接用电源/充电宝供电；要看日志用纯串口监视工具（如 PuTTY）而非 Thonny。
- **`requests` 导入失败**：确认烧的是 UIFlow2 固件（版本 ≥ 2.5.0 内置 requests）。
- **中文显示方块**：用了纯 ASCII 字体，换成 `EFontCN24` 中文字体即可。

## 添加新的 AI 平台

在 `main.py` 里做两件事：

1. 新增一个 `parse_xxx(payload)` 解析函数
2. 在 `SITES` 列表里加一项（name / url / key / parse）

即可让 B 键切换到新平台。注意先确认目标平台的余额接口是否会被 Cloudflare 拦截（可用沙箱 curl 先测）。
