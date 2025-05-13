#!/usr/bin/env bash
echo 'Start!'

# 将 python 默认指向 python3
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2

cd /vagrant

# 安装基本工具
sudo apt-get update
sudo apt-get install -y tree python3-pip python3-setuptools wget default-libmysqlclient-dev

# pip 软链接
if ! [ -e /usr/bin/pip ]; then
  sudo ln -s /usr/bin/pip3 /usr/bin/pip
fi

# pip 换源 + 安装依赖
pip install --upgrade setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install --ignore-installed wrapt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 MySQL 服务
sudo apt-get install -y mysql-server

# 修改 root 用户密码并创建数据库
sudo mysql -e "
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yourpassword';
FLUSH PRIVILEGES;
CREATE DATABASE IF NOT EXISTS twitter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

echo 'All Done!'
