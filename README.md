# 阿里云盘自动签到

## 运行环境

````
版本
python 3.8

依赖包
PyYAML
requests
tenacity
````

## 使用

### 配置

````
1、打开阿里云盘网页端

2、F12 切换到 应用程序选项卡

3、定位到 Local storage --> https:www.alipan.com --> token

4、找到 access_token 与 refresh_token

5、编辑配置文件 config.yaml

access_token: 前边找到的 access_token
refresh_token: 前边找到的 refresh_token
dingding_webhook_url: （无则无需填写）钉钉 webhook_url 
dingding_webhook_secret: （无则无需填写）钉钉 webhook_secret

````

### 运行

````
pip3 install -r ./requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

python3 main.py
````

### 添加到定时任务

````
crontab -e

0 8 * * * /bin/python3 /root/aliyun_drive_auto_sign_in/main.py >/dev/null 2>&1

每天8点执行脚本

脚本放置位置：

````

### 引用
部分代码参考自以下作者：
- @libuke: [libuke/aliyundrive-checkin](https://github.com/libuke/aliyundrive-checkin)

