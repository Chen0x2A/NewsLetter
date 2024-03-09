import requests
from bs4 import BeautifulSoup
import csv
import datetime
import pandas as pd
import time
import openai
import os
from dateutil import parser
from urllib.parse import urlparse
import re
import numpy as np
# from transformers import AutoTokenizer, AutoModel
from datetime import datetime, timedelta

import sys
import proxy_tester
import random
import configparser
# update notion
from notion_client import Client
from urllib.parse import urljoin

# 获取文章函数
def getArticle(web, keywords, proxies):
    # 从代理池中随机选择一个代理
    proxy = None
    if proxies:
        proxy = random.choice(proxies)

    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    # 加载CSV文件以获取现有的URLs
    existing_urls = set()
    existing_titles = set()

    #若不存在, 则创建一个csv
    if os.path.exists("relevant_articles.csv") and os.path.getsize("relevant_articles.csv") > 0:
        existing_df = pd.read_csv('relevant_articles.csv', header=None)
        existing_urls = set(existing_df[3])  # URL位于第四列
        existing_titles = set(existing_df[2])  # 标题位于第三列

    try:
        time.sleep(1)
        response = requests.get(web, headers=headers, proxies=proxy, timeout=10)
        # 检查是否成功访问
        if response.status_code == 200:
            # 显式设置Beautiful Soup的编码方式
            response.encoding = 'utf-8'
            # 使用Beautiful Soup解析网页内容
            soup = BeautifulSoup(response.text, 'html.parser')
            # 查找包含文章标题和URL的元素（这里以<a>标签为例，具体情况可能有所不同）
            article_links = soup.find_all('a')
            # 初始化一个空的列表来存储相关文章的标题和URL
            relevant_articles = []

            # 遍历所有链接以查找关键词
            for link in article_links:
                link_text = link.get_text()
                link_url = link.get('href')
                # 如果URL已经存在，跳过这个链接
                if link_url in existing_urls or link_text in existing_titles:
                    continue

                # 检查关键词是否出现在链接文本中
                if any(keyword.lower() in link_text.lower() for keyword in keywords):
                    # 在这里调用 extract_date 函数
                    article_date = extract_date(soup, web)
                    if article_date is None:  # 补充当前日期的%Y-%m-%d格式
                        article_date = datetime.now().strftime("%Y-%m-%d")
                    print(f"article_date:{article_date}")
                    relevant_articles.append((article_date, web, link_text, link_url))
                    existing_urls.add(link_url)
                    existing_titles.add(link_text)

            if relevant_articles:
                print(f"{web}中有相关内容。")
                with open('relevant_articles.csv', mode='a', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    for article in relevant_articles:
                        writer.writerow(
                            [article[0], article[1], article[2], article[3], "Not yet summarized"])  # 决定了cvs有几列，这里是五列
            else:
                print(f"{web}中没有找到相关内容。")
        else:
            print(f"无法访问{web}。")

    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")


# 去重函数
def dataProcess():
    # 删除无效行
    # 读取CSV文件到一个DataFrame
    df = pd.read_csv('relevant_articles.csv', header=None, skip_blank_lines=True)
    # 删除表中空白元素
    for col in df.columns:
        if df[col].dtype == object:  # 只选择字符串列
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True).str.strip()  # 替换所有空白字符为单个空格
    # 筛除无效行
    filterWords = read_from_config_file('config.ini', 'filters')
    df = df[~df.iloc[:, 2].isin(filterWords)]

    # 补全URL
    df.iloc[:, 3] = df.apply(lambda row: urljoin(row[1], row[3]), axis=1)


    # TODO 去重
    # 将日期列转为日期类型
    df.iloc[:, 0] = df.iloc[:, 0].str.split(" ").str[0]  # 保留空格前的部分（即日期部分）
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], format="%Y-%m-%d")
    # # 对数据按日期排序
    # df = df.sort_values(by=[df.columns[0]])
    # 去重
    df = df.drop_duplicates(subset=df.columns[3], keep='first')
    # 倒序排序
    df = df.sort_values(by=[df.columns[0]], ascending=False)
    df.fillna("", inplace=True)
    print(f"处理后的df:{df}")
    return df


def extract_date(soup, url):
    # 获取特定网站的日期
    site_specific_selectors = {
        "https://foreignpolicy.com/": {"tag": "time", "class": "date-time"},
        "https://www.ft.com/": {"tag": "time", "class": "o-date"},
        "https://www.politico.eu/": {"tag": "div", "class": "header__info--date"},
        "https://www.reuters.com/": {"tag": "time", "class": "ArticleHeader_date"},
        "https://finance.sina.com.cn/": {"tag": "span", "class": "date"},
        "https://www.huxiu.com/": {'tag': 'meta', 'property': 'article:published_time'},
        "https://www.bbc.com/news": {'tag': 'div', 'class': 'date'},
        "https://www.huxiu.com/brief/": {'tag': 'div', 'class': 'content__time'},
        "https://sspai.com/":{'tag': 'div', 'class': 'timer'},
    }
    #
    general_date_identifiers = [
        {'tag': 'time', 'datetime': True},
        {'tag': 'span', 'class': 'date'},
        {'tag': 'div', 'class': 'date'},
        {'tag': 'span', 'class': 'date'},
        {'tag': 'time', 'datetime': True},
        {'tag': 'span', 'class': 'date'},
        {'tag': 'div', 'class': 'date'},
        {'tag': 'span', 'class': 'date'},
        {'tag': 'meta', 'property': 'article:published_time'},
        {'tag': 'div', 'class': 'content__time'},
        {'tag': 'span', 'class': 'date'},
        {"tag": "time", "class": "date-time"},
        {"tag": "time", "class": "o-date"},
        {"tag": "div", "class": "header__info--date"},
        {"tag": "time", "class": "ArticleHeader_date"}
    ]

    date = None
    date_str = None

    # 检查是否有针对特定网站的选择器
    if url in site_specific_selectors:
        selector = site_specific_selectors[url]
        date_element = soup.find(selector['tag'], class_=selector.get('class'))
        print(f"date_element:{date_element}")
        if date_element:
            # If date_element has text content, get it; otherwise, try to get 'datetime' attribute
            date_str = date_element.get_text(strip=True) if date_element.get_text() else date_element.get('datetime')

        # Ensure date_str is a string before attempting regex substitution
        if date_str is not None and isinstance(date_str, str):
            # Remove unwanted parts from date_str
            date_str = re.sub(r'(<!--.*?-->)|(\s*\b\w{3,9}\b,)|(\s*·\s*)', '', date_str)
        else:
            # Handle cases where date_str is None or not a string. For example, set it to an empty string or a placeholder.
            date_str = ""

    else:
        # 尝试使用通用选择器
        for identifier in general_date_identifiers:
            if 'datetime' in identifier:
                date_element = soup.find(identifier['tag'], {'datetime': True})
                if date_element:
                    date_str = date_element.get('datetime')
                    break
            else:
                date_element = soup.find(identifier['tag'], class_=identifier.get('class'))
                if date_element:
                    date_str = date_element.get_text(strip=True)
                    break

    # 如果找到日期字符串，尝试将其解析为日期对象
    if date_str:
        try:
            date = parser.parse(date_str)
        except ValueError:
            # 对于“yesterday”这种特殊情况的处理，可以根据实际情况添加逻辑
            if 'yesterday' in date_str.lower():
                date = datetime.now() - timedelta(hours=1)
            if 'hours ago' in date_str.lower():
                date = datetime.now()
    # 如果date超过今天,则返回今天
    if date and date.replace(tzinfo=None) > datetime.now():
        date = datetime.now()
    return date


def read_gpt_config(file_path):
    # 创建一个配置解析器对象
    config = configparser.ConfigParser()
    # 读取配置文件
    config.read(file_path, encoding='utf-8')
    # 获取 GPT 配置
    use_gpt = config.get('gpt', 'use_gpt')
    print(f"use_gpt:{use_gpt}")
    print(f"gpt_token:{gpt_token}")
    return use_gpt


def getSummary(df):
    # 读取 GPT 配置
    use_gpt, gpt_token = read_gpt_config('config.ini')
    openai.api_key = gpt_token
    # 检查是否需要使用 GPT
    if use_gpt != "yes" :
        return df
    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    urls = df.iloc[:, 3]
    for url in urls:
        # if np.isnan(df.iloc[i, 4]) or df.iloc[i, 4] != "":
        if "Not yet summarized" == df.loc[df[3] == url, 4].item():
            try:
                response = requests.get(url, headers=headers)
                # 检查是否成功访问
                if response.status_code == 200:
                    # 获取文章全文内容
                    full_content = response.text
                    # 使用Beautiful Soup解析HTML
                    soup = BeautifulSoup(full_content, 'html.parser')
                    paragraphs = soup.find_all('p')
                    article_content = ""
                    for paragraph in paragraphs:
                        article_content += paragraph.get_text() + "\n"
                    print(f"article_content:{article_content}")
                    try:
                        print("调用GPT API生成文章摘要")
                        # 调用 GPT 模型生成总结
                        summary = ChatWithGPT(article_content)
                        print(f"GPT摘要为:{summary}")
                        # 将生成的总结内容赋值给第五列的相应行
                        df.loc[df[3] == url, 4] = summary
                        # 如果成功调用，则等待20秒, 避免超出API限额
                        time.sleep(20)
                    except openai.error.InvalidRequestError as e:
                        print("Token out of bound:", e)  # 打印错误消息
                        df.loc[df[3] == url, 4] = "Not yet summarized"
                else:
                    print("无法访问该网页")
                    df.loc[df[3] == url, 4] = "Not yet summarized"

            except requests.exceptions.RequestException as e:
                print(f"请求错误: {e}")
                df.loc[df[3] == url, 4] = "Not yet summarized"  # 如果请求错误，则将空字符串赋值给第五列的相应行

    return df


def ChatWithGPT(content):
    # 调用 GPT 模型生成总结
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes articles."},
            {"role": "user", "content": f"Summarize this article:\n\n{content}"},
        ],
    )
    # 提取生成的总结内容
    summary = completion.choices[0].message.content
    return summary


def read_from_config_file(file_path, section):
    # 创建一个配置解析器对象
    config = configparser.ConfigParser()
    # 读取配置文件
    config.read(file_path, encoding='utf-8')
    # 获取指定部分的内容，然后按行分割并去除空白符
    content = [line.strip() for line in config.get(section, 'content').split('\n') if line.strip()]
    return content


# 输入df, 保存为excel文件w
def save_to_excel(df):
    # TODO 导出为EXCEL
    df.to_csv('relevant_articles.csv', index=False, header=False)
    # 创建一个Excel写入对象
    excel_writer = pd.ExcelWriter('relevant_articles.xlsx', engine='xlsxwriter')
    df.columns = ['查询日期', '新闻网页', '文章标题', '文章地址', '文章摘要']
    # 将DataFrame写入Excel文件，设置编码为UTF-8
    df.to_excel(excel_writer, index=False)  # , encoding='utf-8'
    # 获取工作表对象
    workbook = excel_writer.book
    worksheet = excel_writer.sheets['Sheet1']
    # 设置特定行的行高
    # worksheet.set_row(0, 30)  # 设置第一行的行高为30
    # 设置列宽
    worksheet.set_column('A:B', 25)  # 设置第一、二列的列宽为20
    worksheet.set_column('C:C', 70)  # 设置第三列的列宽为30
    worksheet.set_column('D:D', 10)
    worksheet.set_column('E:E', 140)
    # 保存Excel文件
    excel_writer.close()


def read_notion_config(file_path):
    # 创建一个配置解析器对象
    config = configparser.ConfigParser()
    # 读取配置文件
    config.read(file_path, encoding='utf-8')
    update_to_notion = config.getboolean('notion', 'update_to_notion')
    return update_to_notion


def update_notion_with_articles(df):
    update_to_notion = read_notion_config('config.ini')
    if not update_to_notion:
        return
    # 获取 Notion 配置
    token = os.getenv("NOTION_TOKEN")
    print(f"token:{token}")
    page_id = os.getenv("PAGE_ID")
    print(f"page_id:{page_id}")
    # 初始化notion客户端和数据库ID
    notion = Client(auth=token)
    # 获取Notion数据库中所有页面的URL
    existing_pages = notion.databases.query(database_id=page_id)
    existing_urls = [page['properties']['文章链接']['url'] for page in existing_pages['results']]
    existing_titles= [page['properties']['文章标题']['title'][0]['text']['content'] for page in existing_pages['results']]

    for index, row in df.iterrows():
        # 文章标题
        title = row[2]
        # 文章链接
        link = row[3]
        # 文章摘要
        summary = row[4]
        # 文章日期
        date = row[0]
        # 网站
        site = row[1]

        # 检查文章是否已经存在于Notion数据库中
        if link in existing_urls or title in existing_titles:
            print(f"文章已存在于Notion: {title}")
            continue

        # 调用Notion API创建页面
        try:
            new_page = notion.pages.create(
                parent={"page_id": page_id},
                properties={
                    "文章日期": {  # 更新日期字段
                        "date": {"start": str(date)}
                    },
                    "网站": {
                        "url": site
                    },
                    "文章标题": {  # 将文章标题直接作为标题展示
                        "title": [{"text": {"content": title}}],
                    },
                    "文章链接": {
                        "url": link
                    },
                    "文章摘要": {
                        "rich_text": [{"text": {"content": summary}}],
                    }
                }
            )
            print(f"成功添加到Notion: {title}")
        except Exception as e:
            print(f"添加到Notion失败: {e}")


def main():
    notion_token = sys.argv[1]
    openai_api_key = sys.argv[2]
    page_id = sys.argv[3]
    os.environ['NOTION_TOKEN'] = notion_token
    # os.environ['OPENAI_API_KEY'] = openai_api_key
    os.environ['PAGE_ID'] = page_id
    print(notion_token, openai_api_key, page_id)
    # API密钥, 获得环境变量中的密钥
    openai.api_key = openai_api_key
    webList = read_from_config_file('config.ini', 'web_list')  # 获取Web List
    keywords = read_from_config_file('config.ini', 'keywords')  # 获取要查找的关键词
    proxies = proxy_tester.get_some_proxies(3)  # 获取代理池
    print("可用代理池:" + str(proxies))

    # # 历史对话列表
    # history = []
    #
    # # 调用getArticle(),存到csv中
    # for web in webList:
    #     getArticle(web, keywords, proxies)  #
    # # TODO 调用dataProcess(),读取csv，返回处理后的df
    # df = dataProcess()
    # # 调用gpt, 返回带有总结的df
    # df = getSummary(df)
    # # 保存为excel文件
    # save_to_excel(df)
    # # 更新到notion
    # update_notion_with_articles(df)


if __name__ == "__main__":
    main()

