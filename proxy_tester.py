import requests
from bs4 import BeautifulSoup
import concurrent.futures
from datetime import datetime


def get_all_proxies():
    url = 'https://free-proxy-list.net/' #第一个代理网页
    #url = 'https://www.proxyscrape.com/free-proxy-list'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print('Failed to retrieve the page: status code', response.status_code)
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    proxy_table = soup.find('table', {'class': 'table table-striped table-bordered'})
    # proxy_table = soup.find('tbody', id='proxytable')
    if proxy_table is None:
        print('Failed to find proxy list on the page')
        return []

    proxies = []

    for row in proxy_table.find_all('tr'):
        columns = row.find_all('td')
        if len(columns) > 0:
            ip = columns[0].text.strip()
            port = columns[1].text.strip()
            https = "https" if "yes" in columns[6].text.strip().lower() else "http"

            proxy_info = {
                'ip': ip,
                'port': port,
                'protocol': https
            }
            proxies.append(proxy_info)

    return proxies  # 确保返回整个列表


def get_some_proxies(proxy_num):
    url = 'https://free-proxy-list.net/' #第一个代理网页
    #url = 'https://www.proxyscrape.com/free-proxy-list'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print('Failed to retrieve the page: status code', response.status_code)
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    proxy_table = soup.find('table', {'class': 'table table-striped table-bordered'})
    # proxy_table = soup.find('tbody', id='proxytable')
    if proxy_table is None:
        print('Failed to find proxy list on the page')
        return []

    proxies = []
    count = 0
    for row in proxy_table.find_all('tr'):
        columns = row.find_all('td')
        if len(columns) > 0:
            ip = columns[0].text.strip()
            port = columns[1].text.strip()
            https = "https" if "yes" in columns[6].text.strip().lower() else "http"

            proxy_info = {
                'ip': ip,
                'port': port,
                'protocol': https
            }
            #加入到列表中
            proxies.append(proxy_info)
            count+=1
            if count ==  proxy_num:
                return proxies
    return proxies  # 返回proxy_num个可用的代理
def test_proxy(proxy_info):
    url = "https://www.c5game.com/"
    protocol = proxy_info['protocol']
    if protocol == 'http':
        proxy_dict = {
            "http": f"http://{proxy_info['ip']}:{proxy_info['port']}"
        }
        try:
            response = requests.get(url, proxies=proxy_dict, timeout=10)
            if response.status_code == 200:
                print(f"代理可用: {proxy_dict}")
                return proxy_info
            else:
                print(f"代理返回了非正常状态: {response.status_code}")
        except requests.RequestException as e:
            print(f"代理不可用: {proxy_info['ip']} - {e}")
    else:
        print("protocol is not http, drop")
    return None

def test_proxies_concurrently(proxies_list):
    valid_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxies_list}
        for future in concurrent.futures.as_completed(future_to_proxy):
            proxy = future_to_proxy[future]
            try:
                result = future.result()
                if result:
                    valid_proxies.append(result)
            except Exception as exc:
                print(f"代理测试生成了异常: {proxy} {exc}")

    return valid_proxies




def main():
    proxies_list = get_all_proxies()
    if proxies_list:
        valid_proxies = test_proxies_concurrently(proxies_list)
        print("有效代理列表:")
        for proxy in valid_proxies:
            print(proxy)

    else:
        print("No proxies found.")

if __name__ == "__main__":
    # 获取当前日期和时间
    start_time = datetime.now()
    main()
    # 获取当前日期和时间
    end_time = datetime.now()
    total_time=end_time-start_time
    print(total_time)

