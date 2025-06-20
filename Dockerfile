FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
# COPY . /app
COPY requirements.txt /app/
COPY scrapy.cfg /app/
COPY run.py /app/
COPY run_export_to_ebooks.py /app/
COPY seventeen_novels/ /app/seventeen_novels/
# 将本地的 chromedriver-linux64.zip 复制到镜像中
# 将 chromedriver-linux64.zip 放入项目根目录
COPY chromedriver-linux64.zip /app/chromedriver-linux64.zip

# 安装依赖
RUN pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ && \
    python -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ 

# 安装 Chrome 和 ChromeDriver（适配 selenium）
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget gnupg unzip && \
    # 安装 Chrome
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >/etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    # 检查本地缓存是否存在，否则从网络下载
    if [ -f /app/chromedriver-linux64.zip ]; then \
        echo "--> Using local chromedriver.zip from cache." && \
        mv /app/chromedriver-linux64.zip /tmp/chromedriver.zip; \
    else \
        echo "--> Local chromedriver.zip not found, downloading..." && \
        wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.119/linux64/chromedriver-linux64.zip; \
    fi && \
    # 设置 ChromeDriver
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    # 清理安装工具和临时文件
    rm -rf /var/lib/apt/lists/* /tmp/chromedriver.zip && \
    apt-get clean && \
    rm -rf /usr/share/doc /usr/share/man /usr/share/info /usr/share/lintian /usr/share/linda
    

# 设置环境变量，防止 Chrome 无头模式报错
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 默认命令行（可被 docker run 覆盖）
CMD ["python", "/app/run.py", "--help"]
