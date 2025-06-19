FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
# COPY . /app
COPY requirements.txt /app/
COPY scrapy.cfg /app/
COPY run.py /app/
COPY seventeen_novels/ /app/seventeen_novels/

# 安装依赖
RUN pip install --upgrade pip && \
    python -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt

# 安装 Chrome 和 ChromeDriver（适配 selenium）
RUN apt-get update && apt-get install -y wget gnupg unzip && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >/etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.119/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /var/lib/apt/lists/* /tmp/chromedriver.zip && \
    apt-get purge -y --auto-remove wget gnupg unzip

# 设置环境变量，防止 Chrome 无头模式报错
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 默认命令行（可被 docker run 覆盖）
CMD ["python", "/app/run.py", "--help"]
