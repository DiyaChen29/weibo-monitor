#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions微博监控脚本 - 网页抓取版本
直接抓取微博移动版页面，更稳定可靠
"""

import os
import json
import requests
import time
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re


class WeiboWebMonitor:
    """微博网页版监控器"""
    
    def __init__(self):
        self.config_file = Path('config.json')
        self.data_dir = Path('data')
        self.logs_dir = Path('logs')
        
        # 确保目录存在
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        
        # 加载配置
        self.config = self.load_config()
        
        # 请求会话
        self.session = requests.Session()
        self.setup_session()
    
    def setup_logging(self):
        """设置日志配置"""
        log_file = self.logs_dir / 'weibo_monitor.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def setup_session(self):
        """设置请求会话"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(headers)
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_file.exists():
            default_config = {
                "accounts": [
                    {
                        "uid": "7852949543",
                        "name": "测试账号",
                        "enabled": True
                    }
                ],
                "settings": {
                    "max_posts_per_account": 10,
                    "save_full_content": True,
                    "check_interval_hours": 4,
                    "request_delay": [2, 5]  # 随机延迟范围
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            return default_config
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_weibo_profile_info(self, uid: str) -> Optional[Dict]:
        """获取用户基本信息"""
        url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}"
        
        try:
            # 随机延迟
            delay = random.uniform(*self.config['settings']['request_delay'])
            time.sleep(delay)
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1:
                    userInfo = data.get('data', {}).get('userInfo', {})
                    return {
                        'name': userInfo.get('screen_name', '未知用户'),
                        'followers_count': userInfo.get('followers_count', 0),
                        'verified': userInfo.get('verified', False),
                        'description': userInfo.get('description', '')
                    }
            else:
                self.logger.warning(f"获取用户信息失败，状态码: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"获取用户信息异常: {e}")
        
        return None
    
    def get_user_weibo_posts(self, uid: str, count: int = 10) -> List[Dict]:
        """获取用户微博列表"""
        # 先获取containerid
        containerid = self.get_container_id(uid)
        if not containerid:
            return []
        
        url = f"https://m.weibo.cn/api/container/getIndex"
        params = {
            'containerid': containerid,
            'page': 1,
            'count': count
        }
        
        try:
            # 随机延迟
            delay = random.uniform(*self.config['settings']['request_delay'])
            time.sleep(delay)
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1:
                    cards = data.get('data', {}).get('cards', [])
                    posts = []
                    
                    for card in cards:
                        if card.get('card_type') == 9:  # 微博卡片
                            mblog = card.get('mblog', {})
                            if mblog:
                                post = self.parse_weibo_post(mblog)
                                if post:
                                    posts.append(post)
                    
                    return posts
            else:
                self.logger.warning(f"获取微博失败，状态码: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"获取微博异常: {e}")
        
        return []
    
    def get_container_id(self, uid: str) -> Optional[str]:
        """获取用户的containerid"""
        url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}"
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1:
                    tabsInfo = data.get('data', {}).get('tabsInfo', {})
                    tabs = tabsInfo.get('tabs', [])
                    for tab in tabs:
                        if tab.get('tab_type') == 'weibo':
                            return tab.get('containerid')
        except Exception as e:
            self.logger.error(f"获取containerid失败: {e}")
        
        return None
    
    def parse_weibo_post(self, mblog: Dict) -> Optional[Dict]:
        """解析微博数据"""
        try:
            # 清理HTML标签
            text = self.clean_html(mblog.get('text', ''))
            
            # 解析时间
            created_at = mblog.get('created_at', '')
            post_time = self.parse_time(created_at)
            
            # 基本信息
            post = {
                'id': mblog.get('id', ''),
                'mid': mblog.get('mid', ''),
                'text': text,
                'created_at': created_at,
                'post_time': post_time,
                'reposts_count': mblog.get('reposts_count', 0),
                'comments_count': mblog.get('comments_count', 0),
                'attitudes_count': mblog.get('attitudes_count', 0),
                'source': mblog.get('source', ''),
                'url': f"https://m.weibo.cn/detail/{mblog.get('id', '')}"
            }
            
            # 图片
            if 'pics' in mblog and mblog['pics']:
                post['pics'] = [pic.get('url', '') for pic in mblog['pics']]
            
            # 视频
            if 'page_info' in mblog and mblog['page_info'].get('type') == 'video':
                post['video_url'] = mblog['page_info'].get('media_info', {}).get('mp4_720p_mp4', '')
            
            return post
            
        except Exception as e:
            self.logger.error(f"解析微博失败: {e}")
            return None
    
    def clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ''
        
        # 使用BeautifulSoup清理HTML
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text().strip()
    
    def parse_time(self, time_str: str) -> str:
        """解析时间字符串"""
        try:
            if not time_str:
                return ''
            
            # 处理相对时间
            if '分钟前' in time_str:
                minutes = int(re.search(r'(\d+)分钟前', time_str).group(1))
                return (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
            elif '小时前' in time_str:
                hours = int(re.search(r'(\d+)小时前', time_str).group(1))
                return (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            elif '今天' in time_str:
                time_part = re.search(r'今天 (\d+:\d+)', time_str)
                if time_part:
                    today = datetime.now().date()
                    time_str = f"{today} {time_part.group(1)}:00"
                    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            elif '昨天' in time_str:
                time_part = re.search(r'昨天 (\d+:\d+)', time_str)
                if time_part:
                    yesterday = (datetime.now() - timedelta(days=1)).date()
                    time_str = f"{yesterday} {time_part.group(1)}:00"
                    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            
            return time_str
            
        except Exception as e:
            self.logger.warning(f"时间解析失败: {e}, 原始时间: {time_str}")
            return time_str
    
    def monitor_account(self, account: Dict) -> Dict:
        """监控单个账号"""
        uid = account['uid']
        name = account['name']
        
        self.logger.info(f"开始监控账号: {name} ({uid})")
        
        try:
            # 获取用户信息
            profile_info = self.get_weibo_profile_info(uid)
            if profile_info:
                self.logger.info(f"用户信息: {profile_info['name']} (粉丝数: {profile_info['followers_count']})")
            
            # 获取微博列表
            posts = self.get_user_weibo_posts(uid, self.config['settings']['max_posts_per_account'])
            
            if posts:
                self.logger.info(f"✅ {name} ({uid}): 成功获取 {len(posts)} 条微博")
                
                # 保存数据
                data_file = self.data_dir / f'{uid}_latest.json'
                save_data = {
                    'account': account,
                    'profile': profile_info,
                    'posts': posts,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_count': len(posts)
                }
                
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                return {
                    'status': 'success',
                    'count': len(posts),
                    'message': f'成功获取{len(posts)}条微博'
                }
            else:
                self.logger.warning(f"❌ {name} ({uid}): 未获取到微博数据")
                return {
                    'status': 'error',
                    'count': 0,
                    'message': '未获取到微博数据'
                }
                
        except Exception as e:
            error_msg = f"监控失败: {str(e)}"
            self.logger.error(f"❌ {name} ({uid}): {error_msg}")
            return {
                'status': 'error',
                'count': 0,
                'message': error_msg
            }
    
    def run_monitor(self):
        """运行监控任务"""
        self.logger.info("🚀 开始微博监控任务")
        start_time = datetime.now()
        
        results = []
        
        for account in self.config['accounts']:
            if account.get('enabled', True):
                result = self.monitor_account(account)
                result['account'] = account
                results.append(result)
        
        # 生成报告
        total_success = sum(1 for r in results if r['status'] == 'success')
        total_posts = sum(r['count'] for r in results)
        
        report = {
            'run_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_accounts': len(results),
            'success_accounts': total_success,
            'total_posts': total_posts,
            'results': results,
            'duration': str(datetime.now() - start_time)
        }
        
        # 保存报告
        report_file = self.data_dir / 'latest_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📊 监控完成: {total_success}/{len(results)} 成功, 共获取 {total_posts} 条微博")
        
        return report


def main():
    """主函数"""
    monitor = WeiboWebMonitor()
    monitor.run_monitor()


if __name__ == '__main__':
    main()
