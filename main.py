import os
import argparse
import logging
import yaml
from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_random, RetryError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DingDingMessage:
    def __init__(self, webhook_url, webhook_secret):
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret

    def sign(self, secret):
        import time
        import hmac
        import hashlib
        import base64
        import urllib.parse

        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def send(self, message):
        timestamp, signStr = self.sign(self.webhook_secret)
        headers = {"content-type": "application/json"}
        data = {"msgtype": "markdown", "markdown": {"title": "阿里云盘签到", "text": message}}
        sign_webhook_url = self.webhook_url + "&timestamp={}".format(timestamp) + "&sign={}".format(signStr)
        res = requests.post(sign_webhook_url, headers=headers, json=data).json()
        logger.info(res)

    def build_message(self, status: bool, username, sign_in_count, reward, task, message):
        message_info = "### <font color={}>[{}]</font> <font color=#000000>阿里云盘签到</font>\n *** \n".format('#409eff' if status else '#f56c6c', '成功' if status else '失败')
        message_info += "##### 用户：{} \n".format(username)
        if status:
            message_info += "##### 签到：本月已签到 {} 次 \n ##### 签到奖励：{} \n ##### 当日任务：{}\n".format(sign_in_count, reward, task)
        else:
            message_info += "##### 接口返回信息：{}".format(message)

        message_info += "\n *** \n \n 播报时间：{}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        logger.info(message_info)
        self.send(message_info)


class SignIn:
    def __init__(self, access_token, refresh_token, webhook_instance):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.webhook_instance = webhook_instance

    @retry(stop=stop_after_attempt(2), wait=wait_random(min=5, max=30))
    def get_access_token(self):
        url = 'https://auth.aliyundrive.com/v2/account/token'
        data = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token}

        response = requests.post(url, json=data, timeout=5)
        res = response.json()
        logger.info(res)

        if 'code' in res and res['code'] in ['RefreshTokenExpired', 'InvalidParameter.RefreshToken']:
            return False, None, res['message']

        self.access_token = res['access_token']
        self.refresh_token = res['refresh_token']
        return True, res['user_name'] if res['user_name'] else res['nick_name'], None

    @retry(stop=stop_after_attempt(2), wait=wait_random(min=5, max=30))
    def sign_in(self):
        url = 'https://member.aliyundrive.com/v1/activity/sign_in_list'
        data = {'isReward': False}
        params = {'_rx-s': 'mobile'}
        headers = {'Authorization': f'Bearer {self.access_token}'}

        response = requests.post(url, json=data, params=params, headers=headers, timeout=5)
        res = response.json()
        logger.info(res)

        if 'success' not in res:
            return False, -1, res['message']
        return res['success'], res['result']['signInCount'], None

    @retry(stop=stop_after_attempt(2), wait=wait_random(min=5, max=30))
    def get_reward(self, sign_day: int):
        url = 'https://member.aliyundrive.com/v1/activity/sign_in_reward'
        data = {'signInDay': sign_day}
        params = {'_rx-s': 'mobile'}
        headers = {'Authorization': f'Bearer {self.access_token}'}

        response = requests.post(url, json=data, params=params, headers=headers, timeout=5)
        res = response.json()
        logger.info(res)

        if 'result' not in res:
            return False, res['message']

        return res['success'], None

    @retry(stop=stop_after_attempt(2), wait=wait_random(min=10, max=30))
    def get_task(self):
        url = 'https://member.aliyundrive.com/v2/activity/sign_in_list'
        data = {}
        params = {'_rx-s': 'mobile'}
        headers = {'Authorization': f'Bearer {self.access_token}'}

        response = requests.post(url, json=data, params=params, headers=headers, timeout=5)
        res = response.json()
        logger.info(res)

        if 'result' not in res:
            return False, None, None, res['message']

        signInInfos = res['result']['signInInfos']

        day = res['result']['signInCount']
        rewards = filter(lambda info: int(info.get('day', 0)) == day, signInInfos)

        reward_notice = ''
        task_notice = ''

        for reward in next(rewards)['rewards']:
            name = reward['name']
            remind = reward['remind']
            type = reward['type']

            if type == "dailySignIn":
                reward_notice = name
            if type == "dailyTask":
                task_notice = f'{remind}（{name}）'
        return res['success'], reward_notice, task_notice, None

    def do_sign_in(self):
        def handle_error(error_message: str):
            self.webhook_instance.build_message(False, '', None, None, None, error_message)
            return

        try:
            # 获取 access_token
            status, user_name, message = self.get_access_token()
            if not status:
                return handle_error('get_access_token error: {}'.format(message))

            # 签到
            status, signin_count, message = self.sign_in()
            if not status:
                return handle_error('sign_in error: {}'.format(message))

            # 获取奖励
            status, message = self.get_reward(signin_count)
            if not status:
                return handle_error('get_reward error: {}'.format(message))

            # 获取任务
            status, reward_notice, task_notice, message = self.get_task()
            if not status:
                return handle_error('get_task error: {}'.format(message))

            # 发送签到成功消息
            self.webhook_instance.build_message(True, user_name, signin_count, reward_notice, task_notice, None)

        except Exception as e:
            logger.error(str(e))
            handle_error(str(e))


if __name__ == '__main__':
    # 获取配置文件
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f.read())

    # 通过 docker 挂载环境变量
    if config['access_token'] is None or config['refresh_token'] is None:
        access_token = os.environ.get('access_token')
        refresh_token = os.environ.get('refresh_token')

    else:
        access_token = config['access_token']
        refresh_token = config['refresh_token']
    dingding_webhook_url = os.environ.get('dingding_webhook_url')
    dingding_webhook_secret = os.environ.get('dingding_webhook_secret')

    logger.info('access_token {}'.format(access_token))
    logger.info('refresh_token {}'.format(refresh_token))
    logger.info('dingding_webhook_url {}'.format(dingding_webhook_url))
    logger.info('dingding_webhook_secret {}'.format(dingding_webhook_secret))

    webhook_instance = None
    if dingding_webhook_url is not None or dingding_webhook_secret is not None:
        webhook_instance = DingDingMessage(dingding_webhook_url, dingding_webhook_secret)

    sign_in_job = SignIn(access_token, refresh_token, webhook_instance)
    sign_in_job.do_sign_in()

    config['access_token'] = sign_in_job.access_token
    config['refresh_token'] = sign_in_job.refresh_token
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f)
