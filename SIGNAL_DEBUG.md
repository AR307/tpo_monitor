# 🔍 信号检测问题诊断

## 问题分析

### 为什么一整天没有信号？

经过检查，发现**信号检测条件过于严格**，几乎不可能同时满足：

#### 当前配置问题

```yaml
signals:
  long:
    require_all_orderflow: true  # ❌ 必须满足所有4个订单流条件
    min_confidence: 0.7          # ❌ 需要70%置信度
```

#### 信号生成流程

```
1. TPO事件 (REQUIRED) ✓/✗
   ├─ VAL_BOUNCE
   ├─ POC_RECLAIM  
   └─ VAH_BREAKOUT

2. VWAP对齐 (REQUIRED) ✓/✗
   └─ 价格>VWAP或pullback

3. 订单流 (require_all_orderflow=true时)
   ├─ Delta > 0        ✓/✗
   ├─ CVD Bullish      ✓/✗
   ├─ OI > 0           ✓/✗
   └─ 连续买入>=2      ✓/✗
   
   ALL 4 必须满足! ❌ 太严格

4. 置信度检查
   如果 confidence < 0.7 → 拒绝 ❌
```

### 实际问题

1. **TPO事件很少发生** - VAL_BOUNCE, POC_RECLAIM等事件不是每小时都有
2. **所有订单流条件同时满足很难** - Delta+, CVD上升, OI上升, 连续买入>=2 同时出现的概率很低
3. **置信度计算严格** - 最高0.25(TPO) + 0.25(VWAP) + 0.40(OrderFlow) = 0.9，但要求所有条件才能达到

### 估算信号频率

在当前配置下：
- TPO事件发生: ~每2-4小时
- 订单流4个条件全满足: ~每20-30分钟
- 两者同时出现: **每天0-2次** ❌

---

## 🔧 解决方案

### 方案1: 降低阈值 (推荐)

```yaml
signals:
  long:
    require_all_orderflow: false  # ✅ 4个条件满足3个即可
    min_confidence: 0.5           # ✅ 50%置信度
  
  short:
    require_all_orderflow: false
    min_confidence: 0.5
    
  failure:
    min_confidence: 0.6           # ✅ 降低到60%
```

**预期效果**: 每天5-10个信号

### 方案2: 添加更多TPO触发条件

当前只有3种Long触发:
- VAL_BOUNCE
- POC_RECLAIM
- VAH_BREAKOUT

可以添加:
- PRICE_ABOVE_VAH (价格持续在VAH之上)
- PRICE_AT_POC (价格在POC附近)
- STRONG_MOMENTUM (强势突破)

### 方案3: 调试模式

添加详细日志，看看哪些条件经常失败：

```python
# 修改signal_engine.py
self.logger.info(f"Long check: TPO={tpo_valid}, VWAP={vwap_valid}, OF={of_conditions_met}/4, 置信度={confidence:.2f}")
```

---

## 📊 修复后的配置对比

| 配置项 | 当前值 | 优化后 | 说明 |
|--------|--------|--------|------|
| require_all_orderflow | true | **false** | 4个满足3个即可 |
| min_confidence (long/short) | 0.7 | **0.5** | 降低到50% |
| min_confidence (failure) | 0.8 | **0.6** | 降低到60% |
| cooldown_seconds | 300 | 300 | 保持5分钟 |

---

## 🚀 立即修复

### 1. 修改config.yaml

```bash
# 修改以下行
require_all_orderflow: false  # 改为false
min_confidence: 0.5           # 改为0.5
```

### 2. 启用DEBUG日志

```yaml
logging:
  components:
    signal_engine: "DEBUG"  # 改为DEBUG
```

### 3. 重启系统

```bash
# 停止当前运行
Ctrl+C

# 重新启动
python main.py
```

---

## 📝 预期结果

修复后应该看到:
- ✅ 每小时1-2个信号
- ✅ 每天10-20个信号
- ✅ Telegram推送正常

---

## 🔍 调试检查清单

如果修改后仍无信号，检查:

1. **系统是否在运行?**
   ```bash
   # 查看进程
   tasklist | findstr python
   ```

2. **WebSocket是否连接?**
   ```
   日志应显示: ✅ WebSocket已连接 BTCUSDT
   ```

3. **数据是否接收?**
   ```
   日志应显示: Bar finalized. Delta: xxx, CVD: xxx
   ```

4. **TPO是否计算?**
   ```
   日志应显示: TPO session started, POC: xxx, VAH: xxx, VAL: xxx
   ```

5. **信号检查是否执行?**
   ```
   # DEBUG模式下应该每分钟看到检查日志
   ```

---

**立即行动: 修改config.yaml并重启系统！**
