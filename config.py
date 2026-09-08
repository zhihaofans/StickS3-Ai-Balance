# ============================================================
#  StickS3 AI 余额查询 - 配置文件（旧格式，已废弃）
#  ============================================================
#  配置已迁移到 config.json，请优先编辑 config.json。
#  本文件仅作为旧格式回退保留（当 config.json 缺失时才会被读取）。
#  建议删除本文件，只用 config.json。
#
#  JSON 字段说明（config.json）：
#    wifi_list           多 SSID 列表，[["名称", "密码"], ...]
#    wifi_ssid           单个 WiFi 名称（wifi_list 为空时生效）
#    wifi_password       单个 WiFi 密码
#    deepseek_api_key    DeepSeek API Key
#    siliconflow_api_key 硅基流动 API Key
#    moonshot_api_key    Moonshot API Key

WIFI_LIST = [
    ("WiFi名称1", "密码1"),
    ("WiFi名称2", "密码2"),
    ("WiFi名称3", "密码3"),
]

WIFI_SSID = ""
WIFI_PASSWORD = ""

DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SILICONFLOW_API_KEY = ""
MOONSHOT_API_KEY = ""
