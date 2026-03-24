# 🤖 GitHub Actions 微博监控

[![微博监控](https://github.com/你的用户名/微博监控仓库名/actions/workflows/monitor.yml/badge.svg)](https://github.com/你的用户名/微博监控仓库名/actions/workflows/monitor.yml)

**零成本、全自动的微博账号监控解决方案**

## 🚀 快速开始

### 第1步：Fork这个仓库
1. 点击右上角的 "Fork" 按钮
2. 选择你的GitHub账号

### 第2步：配置监控账号
编辑 `config.json` 文件，添加你要监控的微博账号：

```json
{
  "accounts": [
    {
      "uid": "2803301701",
      "name": "人民日报",
      "enabled": true
    },
    {
      "uid": "你要监控的用户ID",
      "name": "用户名称",
      "enabled": true
    }
  ]
}
```

### 第3步：启用GitHub Actions
1. 进入仓库的 "Actions" 标签页
2. 点击 "I understand my workflows, go ahead and enable them"
3. 监控将每4小时自动运行一次

### 第4步：查看结果
- 📊 监控报告：`data/README.md`
- 📁 详细数据：`data/` 目录下的JSON文件
- 📝 运行日志：`logs/latest.log`

## ✨ 功能特点

### 🆓 **完全免费**
- ✅ 使用GitHub Actions免费额度（每月2000分钟）
- ✅ 无需服务器，无需付费API
- ✅ 数据存储在GitHub仓库中

### 🔄 **全自动化**
- ✅ 每4小时自动检查一次
- ✅ 自动过滤重复内容
- ✅ 自动生成监控报告
- ✅ 支持手动触发

### 📊 **多数据源**
- ✅ 3个RSS源自动轮换
- ✅ 智能容错机制
- ✅ 高可用性保障

### 📱 **易于管理**
- ✅ 简单的JSON配置
- ✅ 直观的监控报告
- ✅ 完整的历史记录

## 📋 如何获取微博用户ID

### 方法1：从微博链接
访问用户主页，链接格式为：`https://weibo.com/u/1234567890`  
数字部分 `1234567890` 就是用户ID

### 方法2：使用在线工具
搜索"微博UID查询"，输入用户名即可获取

### 方法3：浏览器开发者工具
1. 打开用户主页
2. F12打开开发者工具
3. 在Network中查找包含用户ID的请求

## ⚙️ 配置说明

### 基础配置
```json
{
  "accounts": [
    {
      "uid": "用户ID",
      "name": "显示名称", 
      "enabled": true
    }
  ],
  "settings": {
    "max_posts_per_account": 10,
    "save_full_content": true,
    "enable_notifications": false,
    "check_interval_hours": 4
  }
}
```

### 字段说明
- `uid`: 微博用户ID（必需）
- `name`: 显示名称（可选）
- `enabled`: 是否启用监控（可选，默认true）
- `max_posts_per_account`: 每次最多获取多少条微博
- `save_full_content`: 是否保存完整内容
- `check_interval_hours`: 检查间隔（仅用于显示）

## 📁 数据存储结构

```
data/
├── README.md                 # 监控报告
├── latest_report.json        # 最新运行结果
├── {uid}_{date}.json        # 每日微博数据
├── {uid}_history.json       # 历史记录（防重复）
└── ...

logs/
└── latest.log               # 运行日志
```

### 数据格式示例
```json
{
  "uid": "2803301701",
  "name": "人民日报",
  "date": "2026-03-24", 
  "posts": [
    {
      "content": "微博内容文本",
      "published": "2026-03-24T15:30:00",
      "link": "https://weibo.com/...",
      "source": "RSS-XML"
    }
  ]
}
```

## 🔧 自定义设置

### 修改运行频率
编辑 `.github/workflows/monitor.yml`：

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 改为每6小时运行
```

### 添加更多账号
在 `config.json` 中添加更多账号：

```json
{
  "accounts": [
    {"uid": "2803301701", "name": "人民日报", "enabled": true},
    {"uid": "1974576991", "name": "央视新闻", "enabled": true},
    {"uid": "你的用户ID", "name": "用户名称", "enabled": true}
  ]
}
```

### 手动触发监控
1. 进入 "Actions" 页面
2. 选择 "微博监控"
3. 点击 "Run workflow"

## 📊 监控报告

每次运行后，会在 `data/README.md` 中生成监控报告，包含：
- 📈 统计信息
- 🎯 各账号状态  
- 📝 最新微博预览

## 🛠️ 故障排除

### 常见问题

**Q: Actions运行失败怎么办？**  
A: 查看Actions日志，通常是网络问题，等待几小时后自动恢复

**Q: 没有获取到微博数据？**  
A: RSS服务可能临时不可用，系统会自动重试其他源

**Q: 如何查看详细错误？**  
A: 查看 `logs/latest.log` 文件或Actions运行日志

**Q: 可以监控多少个账号？**  
A: 建议不超过10个，避免触发GitHub Actions限制

### 优化建议

1. **合理设置运行频率**：建议4-6小时一次
2. **控制监控账号数量**：不超过10个账号
3. **定期清理旧数据**：避免仓库过大

## 🌟 高级功能

### 添加Webhook通知
可以配置Webhook将新微博推送到其他服务：

```json
{
  "settings": {
    "webhook_url": "https://your-webhook-url.com",
    "enable_notifications": true
  }
}
```

### 集成Telegram机器人
可以将监控结果推送到Telegram：

1. 创建Telegram机器人
2. 在仓库Secrets中添加TOKEN
3. 修改监控脚本添加推送逻辑

## 📞 技术支持

- 🐛 问题报告：在Issues中提交
- 💡 功能建议：欢迎提交PR
- 📖 更多文档：查看Wiki

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🎯 立即开始使用

1. **Fork这个仓库**
2. **编辑config.json添加监控账号**  
3. **启用GitHub Actions**
4. **等待4小时查看结果**

**就这么简单！零成本拥有自己的微博监控系统** 🎉