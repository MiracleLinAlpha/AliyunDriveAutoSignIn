FROM python:3.9
MAINTAINER miraclelin
ADD . /root/aliyun_drive_auto_sign_in
WORKDIR /root/aliyun_drive_auto_sign_in
RUN pip3 install -r ./requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' > /etc/timezone
CMD ["python3","./main.py"]
