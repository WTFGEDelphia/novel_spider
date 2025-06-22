FROM python:3.13-slim as base

# 升级pip
RUN pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/

# 安装Chrome和ChromeDriver运行所需的系统库
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip && \
    # 安装Chrome - 使用更稳定的方式
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    # 下载并安装ChromeDriver
    wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.119/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    # 清理
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/chromedriver.zip /usr/share/doc /usr/share/man /usr/share/info /usr/share/lintian /usr/share/linda

# 设置环境变量
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV TZ=Asia/Shanghai

FROM base as app

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt /app/
COPY scrapy.cfg /app/
COPY run.py /app/
COPY run_export_to_ebooks.py /app/
COPY seventeen_novels/ /app/seventeen_novels/

# 创建虚拟环境并安装依赖
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip cache purge && \
    rm -rf /tmp/* /var/tmp/*

# 默认命令行（可被 docker run 覆盖）
CMD ["python", "/app/run.py", "--help"]
