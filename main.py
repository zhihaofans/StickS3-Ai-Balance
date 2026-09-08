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

# ------------------------------------------------------------
# 字体常量（统一管理，改字体只需改这里）
# ------------------------------------------------------------
FONT_TITLE = Widgets.FONTS.DejaVu18      # 标题（站点名）
FONT_BALANCE = Widgets.FONTS.DejaVu24    # 余额大数字
FONT_STATUS = Widgets.FONTS.DejaVu12     # 状态 / 时间数字
FONT_CN = Widgets.FONTS.EFontCN24        # 中文（电量 / 刷新 / 提示）

# 尝试导入配置
try:
    import config
    WIFI_LIST = getattr(config, "WIFI_LIST", [])
    WIFI_SSID = getattr(config, "WIFI_SSID", "")
    WIFI_PASSWORD = getattr(config, "WIFI_PASSWORD", "")
    DEEPSEEK_API_KEY = getattr(config, "DEEPSEEK_API_KEY", "")
    SILICONFLOW_API_KEY = getattr(config, "SILICONFLOW_API_KEY", "")
    MOONSHOT_API_KEY = getattr(config, "MOONSHOT_API_KEY", "")
except ImportError:
    WIFI_LIST = []
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
label_battery = None    # 电量
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


def get_battery_level():
    """平滑读取电量：连读 3 次取中值，返回整数百分比"""
    try:
        samples = []
        for _ in range(3):
            samples.append(M5.Power.getBatteryLevel())
            time.sleep(0.05)
        samples.sort()
        return samples[1]  # 中值
    except Exception as e:
        print("[电量] 读取失败: " + str(e))
        return None


# 上一次显示的电量（用于变化阈值判断）
_last_battery_level = None


def get_battery_str():
    """返回电量字符串，充电中显示 'BAT 100% +'"""
    level = get_battery_level()
    if level is None:
        return "BAT --"
    try:
        charging = M5.Power.isCharging()
        s = "BAT " + str(level) + "%"
        if charging:
            s += " +"
        return s
    except Exception:
        return "BAT " + str(level) + "%"


def update_battery():
    """更新屏幕电量，仅当变化 ≥ 2% 时刷新，避免频繁跳动"""
    global label_battery, _last_battery_level
    level = get_battery_level()
    if level is None:
        return
    # 首次显示，或变化超过阈值才更新
    if _last_battery_level is None or abs(level - _last_battery_level) >= 2:
        _last_battery_level = level
        if label_battery:
            label_battery.setText(get_battery_str())


# ------------------------------------------------------------
# 连接 WiFi
# ------------------------------------------------------------
def connect_wifi():
    """逐个尝试 WiFi（优先 WIFI_LIST，回退单 SSID），返回 (是否成功, IP 或错误)"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True, wlan.ifconfig()[0]

    # 构造待尝试的 WiFi 列表
    candidates = []
    if WIFI_LIST:
        for item in WIFI_LIST:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                candidates.append((item[0], item[1]))
    # 回退到单 SSID
    if not candidates and WIFI_SSID:
        candidates.append((WIFI_SSID, WIFI_PASSWORD))

    if not candidates:
        return False, "No WiFi config"

    # 过滤空 SSID，保证序号/总数准确
    candidates = [(s, p) for s, p in candidates if s]
    if not candidates:
        return False, "No WiFi config"

    total = len(candidates)

    # 逐个尝试
    for i, (ssid, password) in enumerate(candidates, 1):
        print("[WiFi] 尝试连接: " + ssid)

        # 屏幕提示正在连接哪个 SSID（用中文字体，兼容中文/英文 SSID）
        if label_title:
            # 标题带进度：统一显示 i/N（单个时即 1/1）
            label_title.setText("WiFi %d/%d" % (i, total))
        if label_currency:
            label_currency.setFont(FONT_CN)
            label_currency.setColor(0x00CCFF)
            label_currency.setText(ssid)

        # 尝试新 SSID 前先断开上一个失败的连接，清空 WiFi 状态机，
        # 否则连续 connect 会阻塞（卡在第二个 SSID 不再往下试）
        wlan.disconnect()
        time.sleep(0.5)

        wlan.connect(ssid, password)

        # 等待 8 秒（16 次 × 0.5s）
        for _ in range(16):
            if wlan.isconnected():
                ip = wlan.ifconfig()[0]
                print("[WiFi] 已连接: " + ssid + " IP: " + ip)
                # 恢复余额标签字体
                if label_currency:
                    label_currency.setFont(FONT_BALANCE)
                return True, ip
            time.sleep(0.5)

        # 连接失败，主动断开，确保下次尝试状态干净
        wlan.disconnect()
        time.sleep(0.3)
        print("[WiFi] 连接失败: " + ssid + "，尝试下一个")

    # 全部失败，恢复字体
    if label_currency:
        label_currency.setFont(FONT_BALANCE)
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
    global label_title, label_battery, label_currency, label_balance, label_status, label_time, label_time_val, label_hint

    M5.begin()
    Widgets.setRotation(0)
    Widgets.fillScreen(0x000000)

    # 标题（站点名）
    label_title = Widgets.Label(
        "DeepSeek", 5, 5, 1.0,
        0xFFFFFF, 0x000000,
        FONT_TITLE
    )

    # 电量（英文，小字）
    label_battery = Widgets.Label(
        "", 5, 30, 1.0,
        0x00CCFF, 0x000000,
        FONT_STATUS
    )

    # 币种+余额（大数字，绿色）
    label_currency = Widgets.Label(
        "", 5, 60, 1.0,
        0x00FF00, 0x000000,
        FONT_BALANCE
    )

    # 余额（备用，暂未用）
    label_balance = Widgets.Label(
        "", 5, 95, 1.0,
        0x00FF00, 0x000000,
        FONT_BALANCE
    )

    # 状态
    label_status = Widgets.Label(
        "", 5, 130, 1.0,
        0x888888, 0x000000,
        FONT_STATUS
    )

    # "刷新" 中文
    label_time = Widgets.Label(
        "", 5, 155, 1.0,
        0x888888, 0x000000,
        FONT_CN
    )

    # 时间数字
    label_time_val = Widgets.Label(
        "", 55, 163, 1.0,
        0x888888, 0x000000,
        FONT_STATUS
    )

    # 底部提示
    label_hint = Widgets.Label(
        "A刷新 B换站", 5, 205, 1.0,
        0x555555, 0x000000,
        FONT_CN
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

    # 初始化电量显示
    update_battery()

    ok, info = connect_wifi()
    if ok:
        # 恢复标题为当前站点名
        if label_title:
            label_title.setText(SITES[current_site]["name"])
        sync_time()
        ok2, result = query_site(current_site)
        show_result(result, ok2)
    else:
        if label_status:
            label_status.setText("WiFi failed")


# 电量定时刷新计数器
_battery_tick = 0


def loop():
    """主循环：定时刷新电量"""
    global _battery_tick
    M5.update()
    _battery_tick += 1
    # 每 10 秒（100 次 × 0.1s）刷新一次电量
    if _battery_tick >= 100:
        _battery_tick = 0
        update_battery()
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
