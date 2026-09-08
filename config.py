# ============================================================
#  StickS3 AI 余额查询 - 配置文件
#  ============================================================
#  在这里填写你的 WiFi 和各站点 API Key，改完保存后重启设备即可生效。
#  （无需重新编译固件，只需重新上传本文件）

# WiFi 配置（两种方式任选，推荐用 WIFI_LIST 多 SSID 逐个尝试）
# 方式一：多 SSID 列表（会按顺序一个个尝试连接，连上即停）
WIFI_LIST = [
    ("WiFi名称1", "密码1"),
    ("WiFi名称2", "密码2"),
    ("WiFi名称3", "密码3"),
]

# 方式二：单个 WiFi（兼容旧格式，仅当 WIFI_LIST 为空时生效）
WIFI_SSID = ""
WIFI_PASSWORD = ""

# DeepSeek API Key（在 https://platform.deepseek.com/ 申请）
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 硅基流动 SiliconFlow API Key（在 https://cloud.siliconflow.cn/ 申请）
# 注意：国内站用 .cn 接口，国际站用 .com 接口（本程序默认 .cn）
SILICONFLOW_API_KEY = ""

# Moonshot Kimi API Key（在 https://platform.moonshot.cn/ 申请）
# 注意：国内站用 .cn 接口，国际站用 .ai 接口（本程序默认 .cn）
MOONSHOT_API_KEY = ""
