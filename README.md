# StickS3 AI 余额查询（MicroPython 版）

用 **M5Stack StickS3 + UIFlow2 固件** 实现的小工具：开机自动连 WiFi，查询多家 AI 平台的账户余额，显示在屏幕上，按键可刷新、切换平台。

## 一、功能

- **多平台余额查询**：DeepSeek、硅基流动、Moonshot（Kimi）
- **多 SSID 自动切换**：按顺序逐个尝试 WiFi，连上即停，屏幕显示连接进度 `WiFi 1/4`
- **按键操作**：
  - 单击 **A 键** = 刷新当前平台余额
  - 单击 **B 键** = 切换下一个平台并自动刷新
- **屏幕显示**：站点名、电量、币种+余额、状态、刷新时间
- **串口日志**：每次查询在串口打印完整过程，便于排查
- **配置独立**：WiFi 和 API Key 全在 `config.json`，改配置不用动主程序

## 二、使用方法

### 1. 烧录固件

1. 下载 [M5Burner](https://docs.m5stack.com/en/download)
2. 选设备 **StickS3**，烧录 **UIFlow2** 固件
3. 烧录时 **Boot Option 选 `Run main.py directly`**

### 2. 安装上传工具

推荐 [Thonny](https://thonny.org/)：工具 → 选项 → 解释器 → 选「MicroPython (ESP32)」，端口选设备的 COM 口。

### 3. 填写配置

编辑 `config.json`（**JSON 格式，不能写注释**）：

```json
{
  "wifi_list": [
    ["WiFi名称1", "密码1"],
    ["WiFi名称2", "密码2"]
  ],
  "wifi_ssid": "",
  "wifi_password": "",
  "deepseek_api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "siliconflow_api_key": "",
  "moonshot_api_key": ""
}
```

字段说明：

| 字段 | 含义 |
|---|---|
| `wifi_list` | 多 SSID 列表，`[["名称", "密码"], ...]`，按顺序逐个尝试 |
| `wifi_ssid` / `wifi_password` | 单个 WiFi（仅当 `wifi_list` 为空时生效） |
| `deepseek_api_key` | DeepSeek Key（[platform.deepseek.com](https://platform.deepseek.com/)） |
| `siliconflow_api_key` | 硅基流动 Key（[cloud.siliconflow.cn](https://cloud.siliconflow.cn/)） |
| `moonshot_api_key` | Moonshot Key（[platform.moonshot.cn](https://platform.moonshot.cn/)） |

### 4. 上传文件

用 Thonny 把 `main.py` 和 `config.json` 上传到 **`/flash/`** 目录（不是根目录 `/`）。

### 5. 删除 boot.py（关键）

在 Thonny 的 Shell 里执行：

```python
import os
os.remove('/flash/boot.py')
```

这一步跳过 UIFlow2 的启动菜单，让设备直接跑 `main.py`。

### 6. 重启

重启后自动运行：连 WiFi → 同步时间 → 查余额 → 显示。

## 三、常见问题

- **开机报 `ESP_ERR_NVS_NOT_FOUND`**：`/flash/boot.py` 没删干净，删掉即可。
- **开机黑屏**：脚本没放对位置，确认在 `/flash/` 目录，不是根目录 `/`。
- **连接 Thonny 后屏幕卡住、按键失效**：Thonny 连接时会发 Ctrl+C 中断程序。平时使用**不要连 Thonny**，用电源/充电宝直接供电；要看日志用纯串口工具（如 PuTTY）。
- **WiFi 卡在第二个 SSID 不再往下试**：已修复，连下一个 SSID 前会先主动断开清状态。
- **`requests` 导入失败**：确认烧的是 UIFlow2 固件（版本 ≥ 2.5.0 内置 requests）。
- **中文显示方块**：用了纯 ASCII 字体，改成 `EFontCN24` 中文字体即可。
- **硅基流动查询失败**：其接口已迁移到 `.com` 域名并由 Cloudflare 防护，ESP32 的 mbedTLS 握手被拦截（返回 426/410），当前 MicroPython 环境下暂无法绕过，属已知问题。
- **改配置不生效**：确认改的是 `config.json`（不是旧的 `config.py`），上传到 `/flash/` 后重启设备。

## 文件清单

| 文件 | 作用 |
|---|---|
| `main.py` | 主程序（连 WiFi → 查余额 → 显示 + 按键交互） |
| `config.json` | 配置文件（WiFi + 各平台 API Key） |
| `config.py` | 旧格式配置（已废弃，仅作回退，可删除） |
