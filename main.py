# -*- coding:utf-8 -*-
import pickle, time, re, os, json, random, datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 配置区 ---
CHROME_DRIVER_PATH = '/usr/bin/chromedriver'
COOKIE_FILE = "wechat_cookies.pkl"
JSON_FILE = "rewards.json"
RETURN_FILE = "return.json"
FAIL_LOG = "manual_check.txt"

# --- 时间调度逻辑 (核心修改) ---
def get_dynamic_interval():
    """根据当前小时数返回休眠秒数"""
    hour = datetime.datetime.now().hour
    
    # 17:00 - 23:00 (晚间黄金档: 3分钟)
    if 17 <= hour < 23:
        interval = 180
        desc = "晚间高峰"
        
    # 09:00 - 17:00 (白天工作时间: 4分钟)
    elif 9 <= hour < 17:
        interval = 240
        desc = "白天常态"
        
    # 06:00 - 09:00 (早晨: 10分钟)
    elif 6 <= hour < 9:
        interval = 600
        desc = "早晨"
        
    # 02:00 - 06:00 (深夜: 1小时)
    elif 2 <= hour < 6:
        interval = 3600
        desc = "深夜休眠"
        
    # 23:00 - 02:00 (午夜/修仙党: 30分钟)
    # 包含了 23点, 0点, 1点
    else:
        interval = 1800
        desc = "午夜轮询"
    
    return interval, desc

# --- 辅助函数 ---
def get_current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    print(f"[{get_current_time()}] {msg}")

def get_auto_reply_content(article_title):
    if not os.path.exists(RETURN_FILE): return None
    try:
        with open(RETURN_FILE, 'r', encoding='utf-8') as f:
            replies = json.load(f)
        if replies.get(article_title): return replies[article_title]
        if replies.get(article_title.strip()): return replies[article_title.strip()]
        return None
    except: return None

def format_random_msg(content):
    tmpl_1 = f"这份打赏对我来说，不仅仅是一杯咖啡，更是一份“请继续坚持下去”的鼓励。\n\n📩 给你的回礼：{content}\n\n愿这里的每一部剧，都能治愈你的某个深夜。🌙"
    tmpl_2 = f"在茫茫人海中，遇到品味相似的人，本就是一件幸事。\n\n📩 给你的回礼：{content}\n\n愿这里的每一部剧，都能治愈你的某个深夜。🌙"
    return random.choice([tmpl_1, tmpl_2])

def is_record_processed(nickname, title, money, time_str):
    if not os.path.exists(JSON_FILE): return False
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return any(
            r['name'] == nickname and 
            r['article'] == title and 
            r['time'] == time_str and 
            r['money'] == money
            for r in data
        )
    except: return False

def save_record_final(nickname, title, money, status, time_str):
    data = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except: data = []
    
    record = {
        "name": nickname, "article": title, 
        "money": money, "status": status.replace('\n', ' ').strip(), "time": time_str
    }
    
    # 查重
    if not any(r['name'] == record['name'] and r['time'] == record['time'] for r in data):
        data.append(record)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        log(f"记录已归档: {nickname}")

def record_failure(nickname, title, money):
    with open(FAIL_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{get_current_time()}] 用户: {nickname} | 金额: {money} | 文章: {title} | 原因: 搜索不到(可能超过48h)\n")
    log(f"⚠️ 已将 {nickname} 加入人工处理名单")

def get_existing_count(title):
    if not os.path.exists(JSON_FILE): return -1
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return sum(1 for r in data if r.get('article') == title)
    except: return -1

# --- 核心动作 ---
def send_private_msg(driver, token, nickname, content_info):
    log(f"正在跳转私信页联系: {nickname}...")
    wait = WebDriverWait(driver, 20)
    try:
        msg_url = f"https://mp.weixin.qq.com/cgi-bin/message?t=message/list&count=20&day=7&token={token}&lang=zh_CN"
        driver.get(msg_url)
        time.sleep(5)

        try:
            user_xpath = f"//span[contains(@class, 'user-info__name') and normalize-space(text())='{nickname}']"
            target_user = wait.until(EC.element_to_be_clickable((By.XPATH, user_xpath)))
            driver.execute_script("arguments[0].click();", target_user)
            time.sleep(2)
        except:
            log(f"❌ 列表中未找到用户 {nickname}")
            return False

        full_msg = format_random_msg(content_info)
        
        try:
            editor = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".edit_area")))
            editor.click()
            time.sleep(0.5)
            
            driver.execute_script("arguments[0].innerText = arguments[1];", editor, full_msg)
            editor.send_keys(" ")
            time.sleep(0.1)
            editor.send_keys(Keys.BACK_SPACE)
            time.sleep(1.5)

            send_btn = driver.find_element(By.CSS_SELECTOR, ".msg-sender-btn button")
            if "disabled" not in send_btn.get_attribute("class"):
                send_btn.click()
                log(f"✅ 私信发送成功")
                return True
            else:
                driver.execute_script("arguments[0].removeAttribute('disabled'); arguments[0].classList.remove('weui-desktop-btn_disabled'); arguments[0].click();", send_btn)
                log(f"✅ (强制)发送成功")
                return True
        except:
            log("❌ 输入框/按钮异常")
            return False
    except Exception as e:
        log(f"❌ 私信异常: {e}")
        return False

# --- 单次任务 ---
def run_once():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)
    wait = WebDriverWait(driver, 20)
    
    did_work = False 

    try:
        driver.get("https://mp.weixin.qq.com/")
        if not os.path.exists(COOKIE_FILE):
            log("Cookie 缺失")
            return False
        cookies = pickle.load(open(COOKIE_FILE, "rb"))
        for c in cookies: driver.add_cookie(c)
        driver.get("https://mp.weixin.qq.com/")
        time.sleep(3)
        
        try:
            token = re.search(r'token=(\d+)', driver.current_url).group(1)
        except:
            log("登录失效，请重新扫码")
            return False
            
        reward_url = f"https://mp.weixin.qq.com/merchant/reward?action=getlatestreward&token={token}&lang=zh_CN"
        driver.get(reward_url)
        time.sleep(5)
        
        try:
            total_list_pages = int(driver.find_elements(By.CLASS_NAME, "weui-desktop-pagination__num")[-1].text)
        except: total_list_pages = 5

        # 遍历列表
        for current_list_page in range(1, total_list_pages + 1): 
            # 翻页
            if current_list_page > 1:
                driver.get(reward_url)
                time.sleep(3)
                try:
                    for _ in range(1, current_list_page):
                        nb = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '下一页')]")))
                        driver.execute_script("arguments[0].click();", nb)
                        time.sleep(1.5)
                except: break
            
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".article-list__item:not(.article-list__item-head)")))
                items = driver.find_elements(By.CSS_SELECTOR, ".article-list__item:not(.article-list__item-head)")
            except: items = []

            if not items: continue
            
            for i in range(len(items)):
                try:
                    items = driver.find_elements(By.CSS_SELECTOR, ".article-list__item:not(.article-list__item-head)")
                    if i >= len(items): break
                    target = items[i]
                    
                    should_check_detail = False
                    title = "Unknown"
                    
                    try:
                        title = target.find_element(By.CSS_SELECTOR, ".article-list__item-title").get_attribute("innerText").split('\n')[0].strip()
                        count_el = target.find_element(By.CLASS_NAME, "article-list__item-total-count")
                        live_count = int(re.search(r'(\d+)', count_el.text).group(1))
                        
                        if live_count > 0 and live_count > get_existing_count(title):
                            log(f"检测到更新: 《{title}》")
                            should_check_detail = True
                    except:
                        log("检测到页面结构变化，强制检查...")
                        should_check_detail = True

                    if should_check_detail:
                        target.click()
                        time.sleep(5)
                        
                        try:
                            d_pager = driver.find_element(By.ID, "commentlist").find_element(By.XPATH, "following-sibling::div")
                            total_detail_pages = int(d_pager.find_elements(By.CLASS_NAME, "weui-desktop-pagination__num")[-1].text)
                        except: total_detail_pages = 1

                        for d_p in range(1, total_detail_pages + 1):
                            rows = driver.find_elements(By.CSS_SELECTOR, "tbody.weui-desktop-table__bd tr")
                            for row in rows:
                                try:
                                    n = row.find_element(By.CSS_SELECTOR, ".comment-rich-buddy-target span").get_attribute("textContent").strip()
                                    m = row.find_element(By.CSS_SELECTOR, ".reward_money_cell").get_attribute("textContent").strip()
                                    s = row.find_element(By.CSS_SELECTOR, ".reward_status_cell").get_attribute("textContent").strip()
                                    t = row.find_element(By.CSS_SELECTOR, ".reward_time_cell").get_attribute("textContent").strip()
                                    
                                    if is_record_processed(n, title, m, t): continue 
                                    
                                    log(f"处理新打赏: {n} - {m}元")
                                    reply_info = get_auto_reply_content(title)
                                    
                                    if not reply_info:
                                        log(f"⚠️ 暂无回复配置，跳过: {title}")
                                        continue
                                    
                                    # 尝试发送
                                    send_success = send_private_msg(driver, token, n, reply_info)
                                    
                                    if send_success:
                                        save_record_final(n, title, m, s, t)
                                    else:
                                        save_record_final(n, title, m, s, t)
                                        record_failure(n, title, m)
                                    
                                    log(">>> 本次处理完毕，立即准备重启扫描...")
                                    did_work = True
                                    return True 
                                    
                                except: continue
                            
                            if d_p < total_detail_pages:
                                try:
                                    d_next = driver.find_element(By.XPATH, "//div[@class='comment-list-container']//a[contains(@class, 'weui-desktop-btn_mini') and contains(text(), '下一页')]")
                                    driver.execute_script("arguments[0].click();", d_next)
                                    time.sleep(3)
                                except: break
                        
                        # 回列表
                        driver.get(reward_url)
                        time.sleep(3)
                        try:
                            for _ in range(1, current_list_page):
                                nb = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '下一页')]")))
                                driver.execute_script("arguments[0].click();", nb)
                                time.sleep(1.5)
                        except: break

                except: continue

    except Exception as e:
        log(f"运行出错: {e}")
    finally:
        driver.quit()
        return did_work

# --- 守护进程 ---
if __name__ == "__main__":
    print(f"=== 微信自动回复机器人启动 (智能分时版) ===")
    
    while True:
        try:
            log(">>> 开始扫描...")
            has_action = run_once()
            
            if has_action:
                log(">>> 刚才有任务处理，开启连续作战模式 (5秒后重试)...")
                time.sleep(5) 
            else:
                # 获取当前时段的休眠时间
                interval, desc = get_dynamic_interval()
                log(f"本轮无新数据，进入[{desc}]模式，休眠 {interval} 秒...")
                time.sleep(interval)
                
        except Exception as e:
            log(f"主进程错误: {e}")
            time.sleep(60)
