# Serial 輸出格式規格

> Stage 2 - Uno → PC Serial 通訊協議

## 1. 基本參數

| 參數 | 值 |
|------|-----|
| Baud Rate | 115200 |
| Data Bits | 8 |
| Stop Bits | 1 |
| Parity | None |
| Line Ending | `\r\n` (CRLF) |

## 2. 資料格式

### 2.1 CSV 資料行

每筆感測資料輸出為一行 CSV，頻率為 **100Hz**（每 10ms 一行）。

**欄位順序：**

```
seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
```

**欄位定義：**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `seq` | uint16 | 封包序號（0~65535 循環） |
| `t_remote_ms` | uint32 | 遠距端 millis() 時間戳 |
| `btn` | uint8 | 按鈕狀態（0=未按，1=按下） |
| `ax1` | int16 | MPU1 加速度 X 軸 raw 值 |
| `ay1` | int16 | MPU1 加速度 Y 軸 raw 值 |
| `az1` | int16 | MPU1 加速度 Z 軸 raw 值 |
| `gx1` | int16 | MPU1 陀螺儀 X 軸 raw 值 |
| `gy1` | int16 | MPU1 陀螺儀 Y 軸 raw 值 |
| `gz1` | int16 | MPU1 陀螺儀 Z 軸 raw 值 |
| `ax2` | int16 | MPU2 加速度 X 軸 raw 值 |
| `ay2` | int16 | MPU2 加速度 Y 軸 raw 值 |
| `az2` | int16 | MPU2 加速度 Z 軸 raw 值 |
| `gx2` | int16 | MPU2 陀螺儀 X 軸 raw 值 |
| `gy2` | int16 | MPU2 陀螺儀 Y 軸 raw 值 |
| `gz2` | int16 | MPU2 陀螺儀 Z 軸 raw 值 |

**範例：**

```
1234,100500,0,16384,-200,16000,50,-30,10,16200,-150,16100,45,-25,8
1235,100510,0,16380,-205,16005,48,-32,12,16195,-148,16098,43,-27,9
1236,100520,1,16390,-198,16010,52,-28,8,16210,-152,16105,47,-23,7
```

### 2.2 狀態/統計行（以 `#` 開頭）

所有非資料行以 `#` 開頭，解析器應忽略這些行。

**開機訊息：**

```
#Mechtronic Base Station v2.0
#[OK] RF receiver ready
#seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
```

**統計訊息（每 5 秒）：**

```
#pps=98.5,dropped=2,rx=4925,loss=0.0%
```

| 欄位 | 說明 |
|------|------|
| `pps` | 每秒封包數 (packets per second) |
| `dropped` | 累計掉包數 |
| `rx` | 累計接收封包數 |
| `loss` | 掉包率百分比 |

**警告訊息：**

```
#[WARN] Bad version: 2
```

## 3. 單位換算（PC 端）

接收端需將 raw 值轉換為物理單位：

### 3.1 加速度

目前量程：**±2g**

```
acc_g = raw / 16384.0
```

| Raw 值 | 對應 g 值 |
|--------|-----------|
| 16384 | +1.0g |
| 0 | 0g |
| -16384 | -1.0g |

### 3.2 陀螺儀

目前量程：**±250 dps**

```
gyro_dps = raw / 131.0
```

| Raw 值 | 對應角速度 |
|--------|------------|
| 131 | +1 °/s |
| 0 | 0 °/s |
| -131 | -1 °/s |

## 4. 解析器實作建議

### 4.1 Python 範例

```python
import serial

def parse_line(line: str) -> dict | None:
    """解析一行 Serial 資料"""
    line = line.strip()

    # 忽略空行和狀態行
    if not line or line.startswith('#'):
        return None

    parts = line.split(',')
    if len(parts) != 15:
        return None  # 格式錯誤

    try:
        return {
            'seq': int(parts[0]),
            't_remote_ms': int(parts[1]),
            'btn': int(parts[2]),
            'ax1': int(parts[3]),
            'ay1': int(parts[4]),
            'az1': int(parts[5]),
            'gx1': int(parts[6]),
            'gy1': int(parts[7]),
            'gz1': int(parts[8]),
            'ax2': int(parts[9]),
            'ay2': int(parts[10]),
            'az2': int(parts[11]),
            'gx2': int(parts[12]),
            'gy2': int(parts[13]),
            'gz2': int(parts[14]),
        }
    except ValueError:
        return None  # 解析失敗

# 使用範例
ser = serial.Serial('/dev/ttyUSB0', 115200)
while True:
    line = ser.readline().decode('utf-8', errors='ignore')
    sample = parse_line(line)
    if sample:
        # 處理資料
        acc_g = sample['ax1'] / 16384.0
        print(f"seq={sample['seq']}, acc_x={acc_g:.3f}g")
```

### 4.2 掉包偵測

透過 `seq` 欄位檢測掉包：

```python
last_seq = None

def check_drop(current_seq: int) -> int:
    global last_seq
    if last_seq is None:
        last_seq = current_seq
        return 0

    expected = (last_seq + 1) % 65536
    if current_seq != expected:
        # 計算掉包數（處理 uint16 溢位）
        dropped = (current_seq - expected) % 65536
        last_seq = current_seq
        return dropped

    last_seq = current_seq
    return 0
```

## 5. 注意事項

1. **Serial Buffer**: 100Hz × 約 50 bytes/行 ≈ 5KB/s，確保讀取緩衝區足夠
2. **時間戳**: `t_remote_ms` 來自遠距端，用於計算採樣間隔和時序分析
3. **btn 狀態**: 為 level（0/1），事件生成需在 PC 端處理
4. **掉包處理**: 掉包後繼續正常讀取，不需重連

## 6. 版本歷史

| 版本 | 日期 | 說明 |
|------|------|------|
| v2.0 | 2025-12-22 | Stage 2 - 標準 CSV 格式（100Hz，每筆一行） |
| v1.0 | 2025-12-22 | Stage 1 - 多行可讀格式（降頻輸出） |
