#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions微博监控脚本
零成本、全自动的微博监控解决方案
"""

import os
import json
import requests
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


class GitHubActionsMonitor:
    """GitHub Actions微博监控器"""
    
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
        
        # RSS源配置
        self.rss_sources = [
            {
                "name": "RSSHub官方",
                "url": "https://rsshub.app/weibo/user/{uid}",
                "timeout": 15
            },
            {
                "name": "RSS2JSON",
                "url": "https://api.rss2json.com/v1/api.json?rss_url=https://rsshub.app/weibo/user/{uid}",
                "timeout": 20,
                "type": "json"
            },
            {
                "name": "RSSHub镜像",
                "url": "https://rsshub.rssforever.com/weibo/user/{uid}",
                "timeout": 15
            }
        ]
    
    def setup_logging(self):
        """设置日志系统"""
        log_file = self.logs_dir / 'latest.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.logger.info(f"✅ 加载配置成功，监控 {len(config.get('accounts', []))} 个账号")
                    return config
            except Exception as e:
                self.logger.error(f"❌ 配置文件加载失败: {e}")
        
        # 使用默认配置
        default_config = {
            "accounts": [
                {
                    "uid": "2803301701",
                    "name": "人民日报",
                    "enabled": True
                }
            ],
            "settings": {
                "max_posts_per_account": 10,
                "save_full_content": True,
                "enable_notifications": False
            }
        }
        
        self.save_config(default_config)
        return default_config
    
    def save_config(self, config: Dict):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("✅ 配置文件保存成功")
        except Exception as e:
            self.logger.error(f"❌ 配置文件保存失败: {e}")
    
    def run_monitor(self):
        """运行监控任务"""
        self.logger.info("🚀 开始GitHub Actions微博监控")
        
        total_new_posts = 0
        results = {}
        
        for account in self.config.get('accounts', []):
            if not account.get('enabled', True):
                continue
                
            uid = account['uid']
            name = account.get('name', f'用户_{uid}')
            
            self.logger.info(f"📡 监控账号: {name} ({uid})")
            
            try:
                # 获取微博数据
                posts = self.fetch_weibo_posts(uid)
                
                if posts:
                    # 过滤新帖子
                    new_posts = self.filter_new_posts(uid, posts)
                    
                    if new_posts:
                        # 保存数据
                        self.save_posts(uid, name, new_posts)
                        total_new_posts += len(new_posts)
                        
                        results[uid] = {
                            'name': name,
                            'new_count': len(new_posts),
                            'posts': new_posts[:3]  # 只保存前3条用于展示
                        }
                        
                        self.logger.info(f"✅ {name}: 发现 {len(new_posts)} 条新微博")
                    else:
                        self.logger.info(f"ℹ️ {name}: 没有新微博")
                        results[uid] = {'name': name, 'new_count': 0}
                else:
                    self.logger.warning(f"⚠️ {name}: 未获取到微博数据")
                    results[uid] = {'name': name, 'new_count': 0, 'error': '获取失败'}
                    
            except Exception as e:
                self.logger.error(f"❌ {name} 监控失败: {e}")
                results[uid] = {'name': name, 'new_count': 0, 'error': str(e)}
            
            # GitHub Actions有时间限制，避免超时
            time.sleep(2)
        
        # 生成汇总报告
        self.generate_summary_report(results, total_new_posts)
        
        self.logger.info(f"🎯 监控完成！共发现 {total_new_posts} 条新微博")
        
        return results
    
    def fetch_weibo_posts(self, uid: str) -> List[Dict]:
        """获取微博帖子"""
        for source in self.rss_sources:
            try:
                self.logger.info(f"🔍 尝试 {source['name']}")
                
                url = source['url'].format(uid=uid)
                timeout = source.get('timeout', 15)
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; GitHub Actions Bot)',
                    'Accept': 'application/rss+xml, application/xml, text/xml, application/json'
                }
                
                response = requests.get(url, headers=headers, timeout=timeout)
                
                if response.status_code == 200:
                    if source.get('type') == 'json':
                        posts = self.parse_json_rss(response.json(), uid)
                    else:
                        posts = self.parse_xml_rss(response.text, uid)
                    
                    if posts:
                        self.logger.info(f"✅ {source['name']} 获取到 {len(posts)} 条微博")
                        return posts
                    
            except Exception as e:
                self.logger.debug(f"❌ {source['name']} 失败: {e}")
                continue
        
        self.logger.warning(f"⚠️ 所有RSS源都失败，用户 {uid}")
        return []
    
    def parse_xml_rss(self, rss_content: str, uid: str) -> List[Dict]:
        """解析XML格式的RSS"""
        posts = []
        
        try:
            root = ET.fromstring(rss_content)
            items = root.findall('.//item')
            
            for item in items:
                title_elem = item.find('title')
                desc_elem = item.find('description')
                date_elem = item.find('pubDate')
                link_elem = item.find('link')
                
                if desc_elem is not None:
                    # 清理HTML内容
                    content = BeautifulSoup(desc_elem.text, 'html.parser').get_text()
                    
                    post = {
                        'uid': uid,
                        'content': content.strip(),
                        'published': self.format_date(date_elem.text if date_elem is not None else ''),
                        'link': link_elem.text if link_elem is not None else f'https://weibo.com/u/{uid}',
                        'title': title_elem.text if title_elem is not None else content[:50],
                        'source': 'RSS-XML'
                    }
                    posts.append(post)
                    
        except Exception as e:
            self.logger.error(f"XML解析失败: {e}")
        
        return posts
    
    def parse_json_rss(self, json_data: Dict, uid: str) -> List[Dict]:
        """解析JSON格式的RSS"""
        posts = []
        
        try:
            if json_data.get('status') == 'ok':
                items = json_data.get('items', [])
                
                for item in items:
                    # 清理HTML内容
                    content = BeautifulSoup(item.get('description', ''), 'html.parser').get_text()
                    
                    post = {
                        'uid': uid,
                        'content': content.strip(),
                        'published': self.format_date(item.get('pubDate', '')),
                        'link': item.get('link', f'https://weibo.com/u/{uid}'),
                        'title': item.get('title', content[:50]),
                        'source': 'RSS-JSON'
                    }
                    posts.append(post)
                    
        except Exception as e:
            self.logger.error(f"JSON解析失败: {e}")
        
        return posts
    
    def format_date(self, date_str: str) -> str:
        """格式化日期"""
        if not date_str:
            return datetime.now().isoformat()
        
        try:
            from dateutil.parser import parse
            dt = parse(date_str)
            return dt.isoformat()
        except:
            return datetime.now().isoformat()
    
    def filter_new_posts(self, uid: str, posts: List[Dict]) -> List[Dict]:
        """过滤新帖子"""
        history_file = self.data_dir / f"{uid}_history.json"
        
        # 加载历史记录
        seen_posts = set()
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    seen_posts = set(history.get('seen_posts', []))
            except:
                pass
        
        # 过滤新帖子
        new_posts = []
        for post in posts:
            # 使用内容前100字符作为唯一标识
            post_id = hash(post['content'][:100])
            
            if post_id not in seen_posts:
                new_posts.append(post)
                seen_posts.add(post_id)
        
        # 更新历史记录（保留最近500个）
        seen_posts_list = list(seen_posts)[-500:]
        history = {
            'uid': uid,
            'seen_posts': seen_posts_list,
            'last_update': datetime.now().isoformat()
        }
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存历史记录失败: {e}")
        
        return new_posts
    
    def save_posts(self, uid: str, name: str, posts: List[Dict]):
        """保存微博数据"""
        # 按日期保存
        today = datetime.now().strftime('%Y-%m-%d')
        daily_file = self.data_dir / f"{uid}_{today}.json"
        
        # 加载当天已有数据
        daily_posts = []
        if daily_file.exists():
            try:
                with open(daily_file, 'r', encoding='utf-8') as f:
                    daily_data = json.load(f)
                    daily_posts = daily_data.get('posts', [])
            except:
                pass
        
        # 添加新帖子
        daily_posts.extend(posts)
        
        # 保存数据
        daily_data = {
            'uid': uid,
            'name': name,
            'date': today,
            'posts': daily_posts,
            'total_count': len(daily_posts),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            with open(daily_file, 'w', encoding='utf-8') as f:
                json.dump(daily_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
    
    def generate_summary_report(self, results: Dict, total_new_posts: int):
        """生成汇总报告"""
        report_file = self.data_dir / 'latest_report.json'
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_accounts': len(results),
            'total_new_posts': total_new_posts,
            'results': results,
            'github_actions_info': {
                'runner_os': os.environ.get('RUNNER_OS', 'unknown'),
                'github_repository': os.environ.get('GITHUB_REPOSITORY', 'unknown'),
                'github_run_id': os.environ.get('GITHUB_RUN_ID', 'unknown')
            }
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            # 也生成一个markdown格式的报告用于展示
            self.generate_markdown_report(report)
            
        except Exception as e:
            self.logger.error(f"生成汇总报告失败: {e}")
    
    def generate_markdown_report(self, report: Dict):
        """生成Markdown格式的报告"""
        report_file = self.data_dir / 'README.md'
        
        md_content = f"""# 📊 微博监控报告

**最后更新:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (GitHub Actions 自动生成)

## 📈 统计信息

- 📱 监控账号: {report['total_accounts']} 个
- 🆕 新增微博: {report['total_new_posts']} 条
- ⏰ 运行间隔: 每4小时

## 🎯 账号状态

"""
        
        for uid, result in report['results'].items():
            name = result['name']
            new_count = result.get('new_count', 0)
            error = result.get('error', '')
            
            if error:
                status = f"❌ 错误: {error}"
            elif new_count > 0:
                status = f"✅ 发现 {new_count} 条新微博"
            else:
                status = "😴 无新微博"
            
            md_content += f"- **{name}** ({uid}): {status}\n"
        
        if report['total_new_posts'] > 0:
            md_content += "\n## 📝 最新微博预览\n\n"
            
            for uid, result in report['results'].items():
                if result.get('new_count', 0) > 0 and 'posts' in result:
                    name = result['name']
                    md_content += f"### {name}\n\n"
                    
                    for i, post in enumerate(result['posts'][:2], 1):  # 只显示前2条
                        content = post['content'][:150] + "..." if len(post['content']) > 150 else post['content']
                        md_content += f"{i}. {content}\n\n"
        
        md_content += f"""
---
*💡 这个报告由 GitHub Actions 自动生成，数据来源于免费的RSS服务*  
*🔄 下次运行时间: 约4小时后*  
*📊 历史数据存储在 data/ 目录中*
"""
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
        except Exception as e:
            self.logger.error(f"生成Markdown报告失败: {e}")


def main():
    """主函数"""
    try:
        monitor = GitHubActionsMonitor()
        monitor.run_monitor()
        print("✅ GitHub Actions微博监控执行完成")
    except Exception as e:
        print(f"❌ 监控执行失败: {e}")
        logging.error(f"监控执行失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()