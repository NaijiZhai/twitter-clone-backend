#!/usr/bin/env bash
echo 'Start!'

sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2

cd /vagrant

sudo apt-get update
sudo apt-get install -y tree python3-pip python3-setuptools wget default-libmysqlclient-dev


if ! [ -e /usr/bin/pip ]; then
  sudo ln -s /usr/bin/pip3 /usr/bin/pip
fi


pip install --upgrade setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install --ignore-installed wrapt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple


sudo apt-get install -y mysql-server


sudo mysql -e "
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yourpassword';
FLUSH PRIVILEGES;
CREATE DATABASE IF NOT EXISTS twitter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

echo 'All Done!'
