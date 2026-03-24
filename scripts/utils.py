#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博监控工具函数模块
提供微博数据抓取、解析、过滤等核心功能
"""

import re
import time
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date


class WeiboSpider:
    """微博爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        
    def setup_session(self):
        """设置请求会话"""
        # 模拟真实浏览器请求头
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(headers)
        
        # 设置会话配置
        self.session.max_redirects = 3
        self.session.timeout = 15
        
    @staticmethod
    def get_random_user_agent():
        """获取随机 User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
        ]
        return random.choice(user_agents)
    
    def get_user_info(self, uid: str) -> Optional[Dict]:
        """获取用户基本信息"""
        url = f"https://weibo.com/u/{uid}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                logging.warning(f"获取用户信息失败，状态码: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试从页面标题获取用户名
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                # 微博页面标题格式通常是 "用户名的微博_微博"
                if '的微博' in title_text:
                    name = title_text.split('的微博')[0]
                    return {
                        'uid': uid,
                        'name': name,
                        'url': url
                    }
            
            return {
                'uid': uid,
                'name': f'用户_{uid}',
                'url': url
            }
            
        except Exception as e:
            logging.error(f"获取用户 {uid} 信息时出错: {e}")
            return None
    
    def get_user_weibo_api(self, uid: str, count: int = 10) -> List[Dict]:
        """通过多种方法获取用户微博"""
        methods = [
            self._get_weibo_mobile_api,
            self._get_weibo_web_scrape,
            self._get_weibo_rss_like
        ]
        
        for i, method in enumerate(methods):
            try:
                logging.info(f"尝试方法 {i+1}/{len(methods)}: {method.__name__}")
                weibos = method(uid, count)
                if weibos:
                    logging.info(f"成功获取 {len(weibos)} 条微博")
                    return weibos
                else:
                    logging.warning(f"方法 {i+1} 未获取到数据，尝试下一种方法")
                    # 增加延时避免被限制
                    time.sleep(random.randint(3, 8))
            except Exception as e:
                logging.error(f"方法 {i+1} 失败: {e}")
                continue
        
        logging.error(f"所有方法都失败，无法获取用户 {uid} 的微博")
        return []
    
    def _get_weibo_mobile_api(self, uid: str, count: int = 10) -> List[Dict]:
        """方法1: 移动端API"""
        api_url = "https://m.weibo.cn/api/container/getIndex"
        
        # 随机化请求参数
        params = {
            'type': 'uid',
            'value': uid,
            'containerid': f'107603{uid}',
            'count': count,
            'since_id': 0,
        }
        
        # 添加移动端特有请求头
        headers = {
            'Referer': f'https://m.weibo.cn/u/{uid}',
            'X-Requested-With': 'XMLHttpRequest',
            'MWeibo-Pwa': '1',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }
        
        response = self.session.get(api_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 432:
            raise Exception("触发反爬虫限制 (432)")
        elif response.status_code != 200:
            raise Exception(f"API请求失败，状态码: {response.status_code}")
        
        data = response.json()
        if data.get('ok') != 1:
            raise Exception(f"API返回错误: {data.get('msg', 'Unknown error')}")
        
        return self._parse_mobile_api_response(data, uid)
    
    def _get_weibo_web_scrape(self, uid: str, count: int = 10) -> List[Dict]:
        """方法2: 网页版爬取"""
        url = f"https://weibo.com/u/{uid}"
        
        headers = {
            'Referer': 'https://weibo.com/',
            'User-Agent': self.get_random_user_agent()
        }
        
        response = self.session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            raise Exception(f"网页请求失败，状态码: {response.status_code}")
        
        return self._parse_web_page(response.text, uid, count)
    
    def _get_weibo_rss_like(self, uid: str, count: int = 10) -> List[Dict]:
        """方法3: RSS风格的接口"""
        # 一些第三方或者公开的接口
        api_urls = [
            f"https://rsshub.app/weibo/user/{uid}",
            f"https://weibo.com/{uid}/feed",
        ]
        
        for api_url in api_urls:
            try:
                headers = {
                    'User-Agent': self.get_random_user_agent(),
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
                
                response = self.session.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # 这里需要根据实际响应格式来解析
                    return self._parse_rss_response(response.text, uid, count)
            except Exception as e:
                logging.debug(f"RSS接口 {api_url} 失败: {e}")
                continue
        
        raise Exception("所有RSS接口都失败")
    
    def _parse_mobile_api_response(self, data: Dict, uid: str) -> List[Dict]:
        """解析移动端API响应"""
        cards = data.get('data', {}).get('cards', [])
        weibos = []
        
        for card in cards:
            if card.get('card_type') == 9:  # 微博卡片类型
                mblog = card.get('mblog', {})
                if mblog:
                    weibo = self.parse_weibo_from_api(mblog, uid)
                    if weibo:
                        weibos.append(weibo)
        
        return weibos
    
    def _parse_web_page(self, html: str, uid: str, count: int) -> List[Dict]:
        """解析网页版内容"""
        soup = BeautifulSoup(html, 'html.parser')
        weibos = []
        
        # 查找微博内容区域
        # 这里需要根据微博网页的实际结构来解析
        # 由于网页版结构复杂且经常变化，这里提供一个框架
        
        try:
            # 寻找包含微博数据的脚本标签
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'window.$CONFIG' in script.string:
                    # 提取JSON数据
                    content = script.string
                    # 解析包含微博数据的JSON
                    # 这部分需要根据实际情况实现
                    pass
        except Exception as e:
            logging.error(f"解析网页版失败: {e}")
        
        return weibos[:count]
    
    def _parse_rss_response(self, content: str, uid: str, count: int) -> List[Dict]:
        """解析RSS响应"""
        # 这里实现RSS格式的解析
        # 可以使用feedparser库来解析RSS/XML
        weibos = []
        
        try:
            soup = BeautifulSoup(content, 'xml')
            items = soup.find_all('item')[:count]
            
            for item in items:
                title = item.find('title')
                description = item.find('description')
                pub_date = item.find('pubDate')
                link = item.find('link')
                
                if title and description:
                    weibo = {
                        'account': f'用户_{uid}',
                        'uid': uid,
                        'post_id': f'rss_{hash(link.text if link else "")}',
                        'content': description.text,
                        'created_at': pub_date.text if pub_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'url': link.text if link else f'https://weibo.com/u/{uid}',
                        'type': 'original',
                        'stats': {'likes': 0, 'comments': 0, 'reposts': 0}
                    }
                    weibos.append(weibo)
                    
        except Exception as e:
            logging.error(f"解析RSS失败: {e}")
        
        return weibos
    
    def parse_weibo_from_api(self, mblog: Dict, uid: str) -> Optional[Dict]:
        """解析API返回的微博数据"""
        try:
            # 基本信息
            post_id = mblog.get('id', '')
            text = mblog.get('text', '')
            
            # 清理HTML标签
            soup = BeautifulSoup(text, 'html.parser')
            clean_text = soup.get_text()
            
            # 时间处理
            created_at = mblog.get('created_at', '')
            try:
                # API返回的时间格式需要处理
                created_time = self.parse_weibo_time(created_at)
            except:
                created_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 互动数据
            attitudes_count = mblog.get('attitudes_count', 0)
            comments_count = mblog.get('comments_count', 0)
            reposts_count = mblog.get('reposts_count', 0)
            
            # 判断是否为转发
            is_retweet = mblog.get('retweeted_status') is not None
            
            return {
                'account': mblog.get('user', {}).get('screen_name', f'用户_{uid}'),
                'uid': uid,
                'post_id': post_id,
                'content': clean_text,
                'created_at': created_time,
                'url': f'https://weibo.com/{uid}/{post_id}',
                'type': 'retweet' if is_retweet else 'original',
                'stats': {
                    'likes': attitudes_count,
                    'comments': comments_count,
                    'reposts': reposts_count
                }
            }
            
        except Exception as e:
            logging.error(f"解析微博数据时出错: {e}")
            return None
    
    def parse_weibo_time(self, time_str: str) -> str:
        """解析微博时间字符串"""
        now = datetime.now()
        
        # 处理相对时间
        if '分钟前' in time_str:
            minutes = int(re.search(r'(\d+)分钟前', time_str).group(1))
            time_obj = now - timedelta(minutes=minutes)
        elif '小时前' in time_str:
            hours = int(re.search(r'(\d+)小时前', time_str).group(1))
            time_obj = now - timedelta(hours=hours)
        elif '今天' in time_str:
            time_part = time_str.replace('今天 ', '')
            time_obj = datetime.combine(now.date(), datetime.strptime(time_part, '%H:%M').time())
        elif '月' in time_str and '日' in time_str:
            # 处理 "12月25日 14:30" 格式
            try:
                time_obj = parse_date(time_str, fuzzy=True)
                # 如果没有年份，默认当前年
                if time_obj.year == 1900:
                    time_obj = time_obj.replace(year=now.year)
            except:
                time_obj = now
        else:
            try:
                time_obj = parse_date(time_str)
            except:
                time_obj = now
        
        return time_obj.strftime('%Y-%m-%d %H:%M:%S')


class WeiboFilter:
    """微博过滤器"""
    
    def __init__(self, config: Dict):
        self.keywords_include = config.get('keywords_include', [])
        self.keywords_exclude = config.get('keywords_exclude', [])
        self.only_original = config.get('only_original', True)
        self.min_interval_hours = config.get('min_interval_hours', 1)
    
    def should_include(self, weibo: Dict) -> bool:
        """判断微博是否应该被包含"""
        content = weibo.get('content', '')
        
        # 检查排除关键词
        if self.keywords_exclude:
            for keyword in self.keywords_exclude:
                if keyword in content:
                    logging.debug(f"微博包含排除关键词 '{keyword}'，跳过")
                    return False
        
        # 检查包含关键词
        if self.keywords_include:
            found = False
            for keyword in self.keywords_include:
                if keyword in content:
                    found = True
                    break
            if not found:
                logging.debug(f"微博不包含任何包含关键词，跳过")
                return False
        
        # 检查是否只要原创微博
        if self.only_original and weibo.get('type') == 'retweet':
            logging.debug("跳过转发微博")
            return False
        
        # 检查时间间隔
        if self.min_interval_hours > 0:
            created_time = datetime.strptime(weibo.get('created_at'), '%Y-%m-%d %H:%M:%S')
            if datetime.now() - created_time > timedelta(hours=self.min_interval_hours):
                logging.debug("微博发布时间超过最小间隔，跳过")
                return False
        
        return True


class DataManager:
    """数据管理器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.data_dir / 'config.json'
        self.seen_posts_file = self.data_dir / 'seen_posts.json'
        self.accounts_data_file = self.data_dir / 'accounts_data.json'
    
    def load_config(self) -> Dict:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载配置文件出错: {e}")
        return {}
    
    def save_config(self, config: Dict):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存配置文件出错: {e}")
    
    def load_seen_posts(self) -> set:
        """加载已读微博ID"""
        if self.seen_posts_file.exists():
            try:
                with open(self.seen_posts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('posts', []))
            except Exception as e:
                logging.error(f"加载已读微博文件出错: {e}")
        return set()
    
    def save_seen_posts(self, seen_posts: set):
        """保存已读微博ID"""
        try:
            # 只保留最近1000个ID，避免文件过大
            posts_list = list(seen_posts)[-1000:]
            data = {
                'posts': posts_list,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.seen_posts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存已读微博文件出错: {e}")
    
    def add_account(self, uid: str, name: str) -> bool:
        """添加监控账号"""
        config = self.load_config()
        accounts = config.get('accounts', [])
        
        # 检查是否已存在
        for account in accounts:
            if account['uid'] == uid:
                logging.info(f"账号 {uid} 已存在")
                return False
        
        accounts.append({
            'uid': uid,
            'name': name,
            'enabled': True
        })
        
        config['accounts'] = accounts
        self.save_config(config)
        logging.info(f"已添加监控账号: {name} ({uid})")
        return True
    
    def remove_account(self, uid: str) -> bool:
        """移除监控账号"""
        config = self.load_config()
        accounts = config.get('accounts', [])
        
        original_count = len(accounts)
        accounts = [acc for acc in accounts if acc['uid'] != uid]
        
        if len(accounts) < original_count:
            config['accounts'] = accounts
            self.save_config(config)
            logging.info(f"已移除监控账号: {uid}")
            return True
        
        logging.info(f"账号 {uid} 不存在")
        return False


def setup_logging(level=logging.INFO):
    """设置日志"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def random_delay(min_seconds: int = 10, max_seconds: int = 30):
    """随机延时"""
    delay = random.randint(min_seconds, max_seconds)
    logging.debug(f"等待 {delay} 秒...")
    time.sleep(delay)