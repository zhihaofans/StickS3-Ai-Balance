# ============================================================
#  StickS3 AI 余额查询 - MicroPython 版（多站点）
#  ============================================================
#  运行环境：M5Stack StickS3 + UIFlow2 固件（MicroPython 1.27.0）
#  功能：
#    1. 开机连接 WiFi（凭据在 config.py）
#    2. 查询 AI 站点余额，屏幕显示 + 串口打印
#    3. 按键 A 单击 = 刷新当前站点余额
#    4. 按键 B 单击 = 切换站点（DeepSeek / 硅基流动 / Moonshot）
#
#  修改 WiFi / API Key：直接编辑 config.py 后重启即可
#  ============================================================

import M5
from M5 import Widgets, BtnA, BtnB
import network
import time
import json
import ntptime

# 尝试导入配置
try:
    import config
    WIFI_SSID = getattr(config, "WIFI_SSID", "")
    WIFI_PASSWORD = getattr(config, "WIFI_PASSWORD", "")
    DEEPSEEK_API_KEY = getattr(config, "DEEPSEEK_API_KEY", "")
    SILICONFLOW_API_KEY = getattr(config, "SILICONFLOW_API_KEY", "")
    MOONSHOT_API_KEY = getattr(config, "MOONSHOT_API_KEY", "")
except ImportError:
    WIFI_SSID = ""
    WIFI_PASSWORD = ""
    DEEPSEEK_API_KEY = ""
    SILICONFLOW_API_KEY = ""
    MOONSHOT_API_KEY = ""

# 屏幕尺寸
SCREEN_W = 135
SCREEN_H = 240

# 全局标签（屏幕元素）
label_title = None      # 标题（站点名）
label_currency = None   # 币种+余额（大数字）
label_balance = None    # 余额（备用）
label_status = None     # 状态
label_time = None       # "刷新" 中文
label_time_val = None   # 时间数字
label_hint = None       # 底部提示

# 当前站点索引
current_site = 0


# ------------------------------------------------------------
# 站点定义：名称 + 接口 + 解析
# ------------------------------------------------------------
def parse_deepseek(payload):
    """DeepSeek: {balance_infos:[{currency, total_balance}], is_available}"""
    data = json.loads(payload)
    infos = data.get("balance_infos", [])
    if not infos:
        return None, None
    info = infos[0]
    currency = info.get("currency", "CNY")
    total = info.get("total_balance", "0")
    status = "OK" if data.get("is_available", False) else "LOW"
    return currency + " " + total, status


def parse_siliconflow(payload):
    """硅基流动: {status, data:{totalBalance}}"""
    data = json.loads(payload)
    d = data.get("data", {})
    if not data.get("status", False) or not d:
        return None, None
    total = d.get("totalBalance", "0")
    return "CNY " + str(total), "OK"


def parse_moonshot(payload):
    """Moonshot: {status, data:{available_balance}}"""
    data = json.loads(payload)
    d = data.get("data", {})
    if not data.get("status", False) or not d:
        return None, None
    total = d.get("available_balance", "0")
    return "CNY " + str(total), "OK"


SITES = [
    {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/user/balance",
        "key": lambda: DEEPSEEK_API_KEY,
        "parse": parse_deepseek,
    },
    {
        "name": "SiliconFlow",
        "url": "https://api.siliconflow.cn/v1/user/info",
        "key": lambda: SILICONFLOW_API_KEY,
        "parse": parse_siliconflow,
    },
    {
        "name": "Moonshot",
        "url": "https://api.moonshot.cn/v1/users/me/balance",
        "key": lambda: MOONSHOT_API_KEY,
        "parse": parse_moonshot,
    },
]


# ------------------------------------------------------------
# 时间同步（NTP）
# ------------------------------------------------------------
def sync_time():
    try:
        ntptime.host = "ntp.aliyun.com"
        ntptime.timeout = 5
        ntptime.settime()
        print("[NTP] 时间同步成功")
        return True
    except Exception as e:
        print("[NTP] 同步失败: " + str(e))
        return False


def get_time_str():
    try:
        t = time.localtime()
        h = (t[3] + 8) % 24
        return "%02d:%02d:%02d" % (h, t[4], t[5])
    except Exception:
        return "--:--:--"


def update_refresh_time():
    global label_time, label_time_val
    if label_time:
        label_time.setText("刷新")
    if label_time_val:
        label_time_val.setText(get_time_str())


# ------------------------------------------------------------
# 连接 WiFi
# ------------------------------------------------------------
def connect_wifi():
    if not WIFI_SSID:
        return False, "No WiFi config\nEdit config.py"

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True, wlan.ifconfig()[0]

    print("[WiFi] 连接中: " + WIFI_SSID)

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for _ in range(30):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("[WiFi] 已连接, IP: " + ip)
            return True, ip
        time.sleep(0.5)

    return False, "WiFi failed"


# ------------------------------------------------------------
# 查询余额（通用，按站点索引）
# ------------------------------------------------------------
def query_site(site_idx):
    """查询指定站点余额，返回 (是否成功, '币种 余额' 或错误信息)"""
    site = SITES[site_idx]
    name = site["name"]
    api_key = site["key"]()

    if not api_key or len(api_key) < 10:
        print("[结果] " + name + " 查询失败: No Key")
        return False, "No Key"

    print("[API] 查询 " + name + " 余额...")

    try:
        import requests

        headers = {
            "Authorization": "Bearer " + api_key,
            "Accept": "application/json",
        }

        url = site["url"]
        print("[API] URL: " + url)

        response = requests.get(url, headers=headers, timeout=15)

        code = response.status_code
        print("[API] HTTP 状态码: " + str(code))

        if code == 200:
            payload = response.text
            response.close()
            print("[API] 响应: " + payload)

            currency_balance, status = site["parse"](payload)
            if currency_balance is None:
                print("[结果] " + name + " 解析失败: " + payload)
                return False, "Parse Err"

            update_refresh_time()
            print("[结果] " + name + " 余额: " + currency_balance + " (" + status + ")")
            return True, currency_balance + "\n" + status
        else:
            err_body = response.text
            response.close()
            print("[API] 错误响应: " + err_body)
            print("[结果] " + name + " 查询失败: HTTP " + str(code))
            return False, "HTTP " + str(code)
    except ImportError:
        print("[结果] " + name + " 查询失败: requests not avail")
        return False, "requests not avail"
    except Exception as e:
        print("[API] 异常: " + str(e))
        print("[结果] " + name + " 查询失败: " + str(e))
        return False, "Error"


# ------------------------------------------------------------
# 屏幕显示结果
# ------------------------------------------------------------
def show_result(result, ok):
    """把查询结果显示到屏幕"""
    global label_currency, label_balance, label_status
    if ok:
        parts = result.split("\n")
        # parts[0] = "币种 余额"（如 "CNY 125.80"），parts[1] = 状态
        if label_currency:
            label_currency.setColor(0x00FF00)  # 成功 = 绿色
            label_currency.setText(parts[0] if len(parts) > 0 else "")
        if label_status:
            label_status.setText(parts[1] if len(parts) > 1 else "")
    else:
        # 失败：余额行显示"FAIL"红色，状态行显示错误原因
        if label_currency:
            label_currency.setColor(0xFF0000)  # 失败 = 红色
            label_currency.setText("FAIL")
        if label_status:
            label_status.setText(result)


# ------------------------------------------------------------
# 按键回调
# ------------------------------------------------------------
def btn_click_cb(state):
    """单击 A = 刷新当前站点"""
    print("[按键] A 单击，刷新")
    ok, result = query_site(current_site)
    show_result(result, ok)


def btn_b_click_cb(state):
    """单击 B = 切换站点 + 刷新"""
    global current_site
    current_site = (current_site + 1) % len(SITES)
    name = SITES[current_site]["name"]
    print("[按键] B 单击，切换到 " + name)
    if label_title:
        label_title.setText(name)
    ok, result = query_site(current_site)
    show_result(result, ok)


# ------------------------------------------------------------
# 主初始化
# ------------------------------------------------------------
def setup():
    global label_title, label_currency, label_balance, label_status, label_time, label_time_val, label_hint

    M5.begin()
    Widgets.setRotation(0)
    Widgets.fillScreen(0x000000)

    # 标题（站点名）
    label_title = Widgets.Label(
        "DeepSeek", 5, 5, 1.0,
        0xFFFFFF, 0x000000,
        Widgets.FONTS.DejaVu18
    )

    # 币种+余额（大数字，绿色）
    label_currency = Widgets.Label(
        "", 5, 45, 1.0,
        0x00FF00, 0x000000,
        Widgets.FONTS.DejaVu24
    )

    # 余额（备用，暂未用）
    label_balance = Widgets.Label(
        "", 5, 80, 1.0,
        0x00FF00, 0x000000,
        Widgets.FONTS.DejaVu24
    )

    # 状态
    label_status = Widgets.Label(
        "", 5, 115, 1.0,
        0x888888, 0x000000,
        Widgets.FONTS.DejaVu12
    )

    # "刷新" 中文
    label_time = Widgets.Label(
        "", 5, 140, 1.0,
        0x888888, 0x000000,
        Widgets.FONTS.EFontCN24
    )

    # 时间数字
    label_time_val = Widgets.Label(
        "", 55, 148, 1.0,
        0x888888, 0x000000,
        Widgets.FONTS.DejaVu12
    )

    # 底部提示
    label_hint = Widgets.Label(
        "A刷新 B换站", 5, 200, 1.0,
        0x555555, 0x000000,
        Widgets.FONTS.EFontCN24
    )

    print("\n==============================")
    print("StickS3 AI 余额查询（多站点）")
    print("==============================")

    BtnA.setCallback(
        type=BtnA.CB_TYPE.WAS_CLICKED,
        cb=btn_click_cb
    )

    BtnB.setCallback(
        type=BtnB.CB_TYPE.WAS_CLICKED,
        cb=btn_b_click_cb
    )

    ok, info = connect_wifi()
    if ok:
        sync_time()
        ok2, result = query_site(current_site)
        show_result(result, ok2)
    else:
        if label_status:
            label_status.setText("WiFi failed")


def loop():
    M5.update()
    time.sleep(0.1)


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        print("Error: " + str(e))
        if label_status:
            label_status.setText("Error: " + str(e)[:20])
        time.sleep(5)
