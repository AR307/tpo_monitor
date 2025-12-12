# TPO Monitor - 项目文件结构

## 核心代码 (9个文件)

### 主程序
- `main.py` - 系统主控制器
- `config.yaml` - 配置文件

### 数据层
- `data_feed.py` - WebSocket数据接收
- `models.py` - 数据模型定义

### 分析层
- `tpo_analyzer.py` - TPO分析
- `vwap_calculator.py` - VWAP计算
- `orderflow_analyzer.py` - 订单流分析
- `signal_engine.py` - 信号生成引擎

### 工具层
- `alert_manager.py` - 警报管理（Telegram）
- `utils.py` - 工具函数

## 配置文件 (3个)

- `requirements.txt` - Python依赖（本地）
- `requirements-server.txt` - Python依赖（服务器）
- `.env.example` - 环境变量模板
- `.gitignore` - Git忽略规则

## 文档 (4个)

### 必读文档
- `README.md` - 项目介绍和快速开始
- `DEPLOYMENT_GUIDE.md` - 部署指南
- `SERVER_DEPLOYMENT_SUCCESS.md` - 服务器部署总结
- `PRIVATE_CONFIG.md` - 私有配置说明

## 脚本 (2个)

- `start.bat` - Windows启动脚本
- `deploy.bat` - 部署辅助脚本

## 总计

- **核心代码**: 10个Python文件
- **配置**: 4个文件
- **文档**: 4个Markdown文件
- **脚本**: 2个批处理文件

**总文件数**: 20个 ✅（精简后）

---

## 已删除的冗余文件

### 测试文件
- ~~test_complete_system.py~~
- ~~test_orderflow.py~~

### 重复的部署脚本
- ~~deploy_clean.sh~~
- ~~deploy_server.sh~~

### 过时的文档
- ~~FINAL_FIX.md~~
- ~~ORDERFLOW_FIX.md~~
- ~~SIGNAL_DEBUG.md~~
- ~~STATUS.md~~
- ~~DEPLOY_GUIDE.md~~
- ~~START_GUIDE.md~~
- ~~QUICKSTART.md~~

---

**建议**: 保持简洁，只留必要文件！
