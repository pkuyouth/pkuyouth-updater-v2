# pkuyouth-updater-v2
《北大青年》后台数据更新器

## 安装方法

确保已经安装了 [Python 3](https://www.python.org/)

下载这个 repo 到本地
```console
$ git clone https://github.com/pkuyouth/pkuyouth-updater-v2.git
```

安装依赖包
```console
$ pip3 install lxml Pillow PyMySQL qiniu requests simplejson
```

## 使用方法

进入项目根目录
```console
$ cd pkuyouth-updater-v2/
```

配置好 `config.ini`
```console
$ cp config.sample.ini config.ini
$ vim config.ini
```

运行 `main.py`
```console
$ python3 main.py
```
