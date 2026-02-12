import pickle

# 将你刚才看到的 set-cookie 里的值填入这个字典
raw_cookies = {
    "slave_user": "xxxxxx",
    "slave_sid": "xxxxxxx",
    "bizuin": "xxxxx",
    "data_bizuin": "xxxxxx",
    "data_ticket": "xxxxxx",
    "slave_bizuin": "xxxxx",
    "rand_info": "xxxxxx"
}

formatted_cookies = []
for name, value in raw_cookies.items():
    formatted_cookies.append({
        'name': name,
        'value': value,
        'domain': '.mp.weixin.qq.com', # 微信公众号后台的域名
        'path': '/',
    })

with open("wechat_cookies.pkl", "wb") as f:
    pickle.dump(formatted_cookies, f)

print("Cookies 转换完成！")
