# 阿里云盘自动签到

## 使用

### 直接运行

修改 config.yaml 文件
添加阿里云盘的 access_token 与 refresh_token

### Docker 运行

docker build -t aliyun_drive_auto_sign_in .

docker run -d -e access_token=你的access_token -e refresh_token=你的refresh_token aliyun_drive_auto_sign_in

如需使用钉钉机器人通知
则添加
-e dingding_webhook_url=你的dingding_webhook_url
-e dingding_webhook_secret=你的dingding_webhook_secret

### Docker Compose 运行
