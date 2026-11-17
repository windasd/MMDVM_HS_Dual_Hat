# MMDVM Nextion 驅動程式送給螢幕的內容

這個目錄裡的畫面檔就是依照這份約定做的。內容是從原始碼讀出來的，不是從執行中的系統觀察到的。
以下全部出自這裡列出的檔案與 commit；原始碼沒有交代清楚的地方，列在[第 9 節](#9-未解問題與原始碼裡的怪異之處)，而不是用猜的。

| 來源 | 讀的 commit | 用途 |
|---|---|---|
| `g4klx/MMDVM-Display` `Nextion.cpp`、`Nextion.h`、`Display.cpp`、`MMDVM-Display.cpp`、`Conf.cpp`、`ModemSerialPort.cpp`、`NextionUpdater.cpp`、`MMDVM-Display.ini` | `76cd3c3`（2026-11-05） | 本設計針對的驅動程式 |
| `g4klx/MMDVM-Display` `Nextion_ON7LDS/README.md`、`README-L2`、`README-L3` | 同上 | ON7LDS 的欄位與狀態碼說明 |
| `g4klx/MMDVMHost` `Nextion.cpp` | `d709c2b`（2023-06-06），螢幕程式碼在 `f12604b`（2023-06-16）被移除之前的最後一版 | 拆分前的驅動程式，用於第 8 節的差異比較 |
| `g4klx/MMDVMHost` `DMRSlot.cpp`、`MMDVM-Host.cpp`、`Modem.cpp` | `6c849ab`（2026-11-15） | 螢幕程式收到的 JSON 裡有什麼；數據機的透傳 |
| `on7lds/NextionDriver` `Nextion/README-extra-fields-and-status-codes` | `03b9042`（2025-10-01） | 額外欄位 `t20`-`t32`、`cpuload` |

## 1. 傳輸

- 每個指令都是 ASCII 文字，後面接三個 `0xFF` 位元組（`CNextion::sendCommand`）。沒有其他的訊框格式。
- 驅動程式一律**用名稱**指定對象：`page <pagename>`、`<objname>.txt="..."`、`<objname>.val=N`、`MMDVM.status.val=N`、`click S0,1`。
  它從不使用頁面 id 或元件 id。名稱如果不存在於目前顯示的頁面，螢幕會回 `0x1A`（頁面是 `0x03`，`click` 是 `0x02`），而且什麼都不會畫。
- 沒有加頁面前綴的名稱（`t0.txt=`）會送到**螢幕當下顯示的那一頁**。
  所以每一頁都要有自己的 `t0`、`t1`...，意義見下文。
- `CNextion::open` 會送 `bkcmd=3`，所以螢幕對每個指令都會回應（`0x01` = 完成）。
  `CNextion::clockInt` 把指令分批送出，每批最多 120 bytes（`MAX_BATCH_LENGTH`），每個指令都要等到一個回應才送下一批，等 500 ms 沒有回應就放棄（`m_waitingTimer`）。
  所以要全速運作就需要回傳線（螢幕 TX 到數據機）：沒有這條線螢幕還是能用，但每一批都要多花 500 ms。
- 用 `Port=modem` 時，資料的路徑是 `MMDVM-Display` -> MQTT 主題 `<host>/display-in` -> `MMDVM-Host`（`CMMDVMHost::writeSerial`，每段最多 252 bytes）-> 數據機 `MMDVM_SERIAL_DATA`（0x80）-> 數據機的 UART，回程走 `<host>/display-out`（`CModemSerialPort`、`MMDVM-Host.cpp`）。
  鮑率由數據機韌體決定（`SERIAL_REPEATER_BAUD`，出廠為 9600）；`[Nextion] Speed=` 只用在螢幕接在自己的序列埠時。
- 螢幕送來、以 `0x2A` 開頭的訊息會發布到 `<name>/nextion-out`；MMDVM-Display 裡沒有任何程式處理它（`CNextion::processReply`）。
  觸控事件和其他訊息都會被忽略。
  發布到 `<name>/nextion-in` 的任何內容，會當成一個指令送給螢幕（`CNextion::writeCommandInt`）。

## 2. ScreenLayout 的值

`CNextion::CNextion` 只接受 0、2、3（用 `assert` 檢查；`CMMDVMDisplay::createDisplay` 遇到其他值會以「Unknown」拒絕）。

| ScreenLayout | 名稱 | 功能位元（`feature_set[]`） | 實際送出的內容有何不同 |
|---|---|---|---|
| 0 | G4KLX | 無 | 只有基本欄位。沒有 Talker Alias、沒有溫度、沒有 `t4`/`t5`。 |
| 2 | ON7LDS | `TA_ENABLE`、`TA_COLOUR`、`TA_FONTSIZE` | Talker Alias 放在 `t8`/`t9`。驅動程式還會送 **`t0.pco=0`、`t2.pco=0`**（黑字）、**`t0.font=4`、`t2.font=4`**、`t8.pco=1024`、`t9.pco=1024`（深綠），並依別名長度送 `t8.font=3/2/1`、`t9.font=3/2/1`。 |
| 3 | ON7LDS DIY | `TA_ENABLE`、`DIY` | Talker Alias 放在 `t8`/`t9`，**不送任何顏色或字型指令**。待機頁多送 `t4`、`t5` 和溫度 `t20`。每一項送完後會送 `MMDVM.status.val=<code>`，接著送 `click S0,1`（`CNextion::sendCommandAction`）。 |
| 1, 4 | （僅舊版 MMDVMHost） | - | MMDVM-Display 不接受。在舊版 MMDVMHost 裡，4 是「3 加上 115200 鮑率」：這是速度設定，不是更高的解析度。 |

### 選用：ScreenLayout=3

- **版面 2 會強制指定顏色和字型 id。** 它對 DMR 來源行送 `pco=0`（黑色），對別名送 `pco=1024`（深綠），在深色主題上看不清楚；字型 id 送的是為 320 x 240 螢幕選的 1 到 4。
  版面 3 完全不送顏色和字型指令，所以外觀完全由畫面檔決定。
- **版面 3 送的比較多：** 呼號和 id 分開送（`t4`、`t5`），還有 CPU 溫度（`t20`）。版面 0 和 2 這兩樣都不送。
- **狀態碼讓畫面可以補上驅動程式的漏洞：** 進入錯誤狀態時，目前的驅動程式完全不送文字（第 9 節第 1 點）；只有版面 3 會用狀態 13 告訴螢幕發生了錯誤。
- **代價：** 每一項多兩個指令（約 36 bytes）。鮑率 9600 時，一次 DMR 通話開始約佔 0.3 s 的序列傳輸時間。
  用版面 3 的代價是畫面**必須**在 `MMDVM` 頁有全域變數 `status`，而且每一頁都要有元件 `S0`。

「高解析度」不是驅動程式的設定：根本沒有這個設定。不管面板是哪一種，驅動程式送的文字都一樣；解析度完全是畫面檔的事。

## 3. 頁面名稱

用 `page <name>` 送出；名稱有分大小寫。

| 頁面名稱 | 由誰送出 | 時機 |
|---|---|---|
| `MMDVM` | `setIdleInt`、`setErrorInt`、`setLockoutInt`、（`setQuitInt`） | 待機、錯誤、鎖定。每次重畫待機頁都會再送一次。 |
| `DStar` | `writeDStarInt` | 從其他模式切過來後的第一個 D-Star 標頭 |
| `DMR` | `writeDMRInt` | 從其他模式切過來後第一次 DMR 開始 |
| `YSF` | `writeFusionInt` | 第一次 YSF 開始 |
| `P25` | `writeP25Int` | 第一次 P25 開始 |
| `NXDN` | `writeNXDNInt` | 第一次 NXDN 開始 |
| `POCSAG` | `writePOCSAGInt` | 第一則 POCSAG 訊息 |
| `FM` | `writeFMInt` | 第一個不是「listening」的 FM 狀態 |

MMDVM-Display 沒有 M17 頁（舊版 MMDVMHost 有 `page M17`）。
repo 裡原附的 G4KLX 與 ON7LDS `.HMI` 檔有 MMDVM、DStar、DMR、YSF、P25、NXDN、POCSAG、M17 這些頁面，**沒有 `FM` 頁**，所以用那些檔案時，FM 狀態會寫進當下顯示的那一頁。
本設計有 `FM` 頁。

## 4. 每一頁都會送的指令

| 指令 | 函式 | 時機 |
|---|---|---|
| `bkcmd=3` | `open` | 啟動時送一次 |
| `dim=<Brightness>` | 每個 `write...Int`、`setErrorInt`、`setLockoutInt` | 每次通話開始／標頭時，只在 `Brightness` > 0 時 |
| `dim=<IdleBrightness>` | `setIdleInt` | 進入待機時，只在 `Brightness` > 0 時 |
| `MMDVM.status.val=<n>` + `click S0,1` | `sendCommandAction` | 只有版面 3，每一項之後；狀態碼見第 7 節。第一個是緊接在 `bkcmd=3` 後面的 `status 0`，送到螢幕上電時正在顯示的那一頁。 |

`click S0,1` 會執行 `S0` 的 **Touch Press**（按下）事件。

## 5. 頁面 `MMDVM`

| 元件 | 需要的類型 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|---|
| `t0` | Text | `"<callsign>/<id>"`，id 為 0 時是 `"<callsign>"` | `setIdleInt` | 每次重畫待機頁 |
| `t0` | Text | `"LOCKOUT"` | `setLockoutInt` | 主機模式「lockout」 |
| `t0` | Text | `"MMDVM STOPPED"` | `setQuitInt` | 在 MMDVM-Display 中從不發生：沒有任何程式呼叫 `CDisplay::setQuit`（第 9 節第 14 點）。舊版 MMDVMHost 在結束時會送。 |
| `t1` | Text | `"MMDVM IDLE"` | `setIdleInt`、`clearCWInt` | 待機 |
| `t1` | Text | `"Sending CW Ident"` | `writeCWInt` | 主機模式「CW」 |
| `t2` | Text | `strftime("%x %X")`：依 **MMDVM-Display 行程的語系**格式化的日期與時間，本地時間或 UTC（`UTC=`） | `sendClock` | 每次重畫待機頁時送，之後在待機或 CW 期間每 400 ms 送一次（`m_clockDisplayTimer`）；只在 `DisplayClock=1` 時 |
| `t3` | Text | IPv4 位址，沒有的話是 IPv6 位址，再沒有就是 `"(ip unknown)"` | `setIdleInt` | 每次重畫待機頁 |
| `t4` | Text | `"<callsign>"` | `setIdleInt` | 只有版面 3 |
| `t5` | Text | `"<id>"`，id 為 0 時是 `""` | `setIdleInt` | 只有版面 3 |
| `t20` | Text | `"?"` | `setIdleInt` | 只有版面 0 和 2（！） |
| `t20` | Text | `"%2.1f \xB0C"`，例如 `45.2 °C`；設了 `[General] TemperatureInF=1` 時是 `°F`。度數符號是**單一位元組 176（0xB0）**。 | `sendCPU` | 只有版面 3，而且要等到有溫度資料之後 |
| `t21` | Text | `"%0.0f MHz"`（CPU 時脈 / 1000），或 `"?"` | `sendCPU` | 每次重畫待機頁；版面 3 在待機中每次收到 CPU 報告也會送（`writeCPUInt`） |
| `t22` | Text | `"%0.2f"`（系統負載），或 `"?"` | `sendCPU` | 同上 |
| `cpuload` | 任何有 `.val` 的元件 | `cpuload.val=<load x 100>`，或 `0` | `sendCPU` | 同上 |
| `t30` | Text | `"%.4f MHz"` RX 頻率，或 `"?"` | `setIdleInt` | 每次重畫待機頁 |
| `t32` | Text | `"%.4f MHz"` TX 頻率，或 `"?"` | `setIdleInt` | 每次重畫待機頁 |
| `t31` | Text | 位置，永遠是 `"?"`（第 9 節第 4 點） | `setIdleInt` | 每次重畫待機頁 |
| `status` | Variable，**全域** | `MMDVM.status.val=<n>` | `sendCommandAction` | 版面 3 |
| `S0` | 任何有 Touch Press 事件的元件 | `click S0,1` | `sendCommandAction` | 版面 3 |

這些值的來源（`MMDVM-Display.cpp`）：呼號、id、頻率來自主機的設定，透過 MQTT 查詢（`parseHostConfig`）；IP 位址取 MMDVM-Info 回報的第一個網路介面（`parseAddresses`）；溫度、CPU 時脈和負載來自 MMDVM-Info 定期送出的 CPU 訊息（`parseCPU`）。
沒有執行 MMDVM-Info 的話，`t3` 是 `(ip unknown)`，`t21` 和 `t22` 是 `?`，`t20` 永遠不會被寫入。

主機進入待機時，以及待機中呼號、id、頻率或位址變動時，待機頁都會整頁重畫（再送一次 `page MMDVM` 和每一個欄位；`redrawIdle`）。

## 6. 各模式的頁面

`<R/N>`：RF 是 `R`，網路是 `N`。

### `DStar`

| 元件 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|
| `t0` | `"<R/N> <my1, max 8>/<my2, 4>"` | `writeDStarInt` | 標頭（開始或中途加入） |
| `t1` | `"<your, max 8>"` | `writeDStarInt` | 標頭 |
| `t2` | `"via <reflector, max 8>"` | `writeDStarInt` | 標頭，除非反射器是八個空格 |
| `t3` | `"<n>dBm"` | `writeDStarRSSIInt` | 每次 RSSI 回報 |
| `t4` | `"<n.n>%"` | `writeDStarBERInt` | 每次 BER 回報 |
| `t5` | 慢速資料（slow data）的文字訊息，20 個字元 | `writeDStarTextInt` | 解碼出來時 |
| `t0` | `"Listening"`；`t1`...`t5` 設為 `""` | `clearDStarInt` | 傳輸結束 |

### `DMR`

| 元件 | 時槽 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|---|
| `t0` | 1 | `"1 <R/N> <src_info>"` | `writeDMRInt` | 開始或中途加入 |
| `t1` | 1 | `"TG<dst>"`（群組）或 `"<dst>"`（個人） | `writeDMRInt` | 開始 |
| `t4` | 1 | `"<n>dBm"` | `writeDMRRSSIInt` | 每次 RSSI 回報 |
| `t6` | 1 | `"<n.n>%"` | `writeDMRBERInt` | 每次 BER 回報 |
| `t8` | 1 | 到目前為止解出的 Talker Alias | `writeDMRTAInt` | 版面 2 和 3，每次多解出一段時 |
| `t0` | 1 | `"1 Listening"`；`t1`、`t4`、`t6`、`t8` 設為 `""` | `clearDMRInt` | 時槽 1 通話結束 |
| `t2` | 2 | `"2 <R/N> <src_info>"` | `writeDMRInt` | 開始或中途加入 |
| `t3` | 2 | `"TG<dst>"` 或 `"<dst>"` | `writeDMRInt` | 開始 |
| `t5` | 2 | `"<n>dBm"` | `writeDMRRSSIInt` | |
| `t7` | 2 | `"<n.n>%"` | `writeDMRBERInt` | |
| `t9` | 2 | Talker Alias | `writeDMRTAInt` | 版面 2 和 3 |
| `t2` | 2 | `"2 Listening"`；`t3`、`t5`、`t7`、`t9` 設為 `""` | `clearDMRInt` | 時槽 2 通話結束 |

頁面剛切過來時，`writeDMRInt` 先把 `"<n> Listening"` 寫進**另一個**時槽的來源行，再把通話寫進自己的時槽。
`src_info` 是從 DMR id 表查到的呼號，表裡沒有的話就是 id 數字（`CDMRLookup::find`）。

### `YSF`

| 元件 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|
| `t0` | `"<R/N> <source, max 10>"` | `writeFusionInt` | 開始或中途加入 |
| `t1` | `"DG-ID <n>"` | `writeFusionInt` | 開始 |
| `t2` | `"at <reflector, max 10>"` | `writeFusionInt` | 開始，除非反射器是十個空格 |
| `t3` | `"<n>dBm"` | `writeFusionRSSIInt` | 每次 RSSI 回報 |
| `t4` | `"<n.n>%"` | `writeFusionBERInt` | 每次 BER 回報 |
| `t0` | `"Listening"`；`t1`...`t4` 設為 `""` | `clearFusionInt` | 結束 |

### `P25` 和 `NXDN`（相同）

| 元件 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|
| `t0` | `"<R/N> <source, max 10>"` | `writeP25Int` / `writeNXDNInt` | 開始或中途加入 |
| `t1` | `"TG<dst>"` 或 `"<dst>"` | 同上 | 開始 |
| `t2` | `"<n>dBm"` | `writeP25RSSIInt` / `writeNXDNRSSIInt` | 每次 RSSI 回報 |
| `t3` | `"<n.n>%"` | `writeP25BERInt` / `writeNXDNBERInt` | 每次 BER 回報 |
| `t0` | `"Listening"`；`t1`...`t3` 設為 `""` | `clearP25Int` / `clearNXDNInt` | 結束 |

### `POCSAG`

| 元件 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|
| `t0` | `"RIC: <n>"` | `writePOCSAGInt` | 每則訊息 |
| `t1` | 訊息文字（緩衝區約可放 190 個字元） | `writePOCSAGInt` | 每則訊息 |
| `t0` | `"Waiting"`；`t1` 設為 `""` | `clearPOCSAGInt` | 結束 |

### `FM`

| 元件 | 寫入的文字 | 函式 | 時機 |
|---|---|---|---|
| `t0` | `"R: Kerchunk"`、`"R: Relaying"`、`"R: Wait"`、`"R: Timeout"`、`"N: Kerchunk"`、`"N: Relaying"`、`"N: Wait"`、`"N: Timeout"`，不在這份清單裡的狀態則直接用原始的狀態名稱 | `writeFMInt`（文字在 `CMMDVMDisplay::parseFM` 決定） | 每次 FM 狀態改變 |
| `t2` | `"<n>dBm"` | `writeFMRSSIInt` | 每次 RSSI 回報 |
| `t0` | `"Listening"`；`t2` 設為 `""` | `clearFMInt` | 狀態「listening」 |

FM 頁沒有 `t1`。

## 7. 狀態碼（版面 3）

以 `MMDVM.status.val=<n>` 加上 `click S0,1` 送出，在所描述的欄位**之後**才送。
狀態碼取自 MMDVM-Display 的 `Nextion.cpp`，意義依 ON7LDS 的說明（`README-L3`）：

| 代碼 | 意義 | 代碼 | 意義 |
|---|---|---|---|
| 0 | 啟動（`open`） | 61 / 69 | DMR 時槽 1 / 2 守聽中 |
| 1 | 頁面 MMDVM | 62 / 70 | DMR 來源（`t0` / `t2`） |
| 2 | 頁面 DStar | 63 / 71 | DMR Talker Alias（`t8` / `t9`） |
| 3 | 頁面 DMR | 65 / 73 | DMR 目的地（`t1` / `t3`） |
| 4 | 頁面 YSF | 66 / 74 | DMR RSSI（`t4` / `t5`） |
| 5 | 頁面 P25 | 67 / 75 | DMR BER（`t6` / `t7`） |
| 6 | 頁面 NXDN | 81 | YSF 守聽中 |
| 7 | 頁面 POCSAG | 82、83、84、86 | YSF 來源、DG-ID、反射器、BER |
| 9 | 頁面 FM | 101 | P25 守聽中 |
| 11 | 待機（`t1`） | 102、103、104、105 | P25 來源、目的地、RSSI、BER |
| 12 | CW 識別（`t1`） | 121 | NXDN 守聽中 |
| 13 | 錯誤 | 122、123、124、125 | NXDN 來源、目的地、RSSI、BER |
| 15 | 鎖定（`t0`） | 132、133 | POCSAG RIC、訊息 |
| 16 | IP 位址（`t3`） | 134 | POCSAG 等待中 |
| 17 | 呼號／id（`t0`、`t4`、`t5`） | 147 | FM 狀態（`t0`） |
| 19 | 已停止（`t0`），原始碼裡永遠走不到（第 9 節第 14 點） | 148 | FM RSSI（`t2`） |
| 22 | 溫度（`t20`） | 149 | FM 守聽中 |
| 41 | D-Star 守聽中 | 42、45、46、47、48、49 | D-Star 來源、your、反射器、RSSI、BER、文字 |

ON7LDS 有記載、但 MMDVM-Display **不會**送的：14（ERROR）、20、21、23（RX 頻率、TX 頻率、位置）、64 / 72（DMR 通話結束）、76 / 77（GPS）、85（YSF RSSI）。
舊版 MMDVMHost 會送 14、20、21、64 和 72。

## 8. 與 2023 年以前 MMDVMHost 驅動程式的差異

研究文件（第 6.3 節）把舊版 MMDVMHost 留作備案。同一個畫面檔也能搭配它使用；以下這些項目的行為不同：

| 項目 | 舊版 MMDVMHost（`d709c2b`） | MMDVM-Display（`76cd3c3`） |
|---|---|---|
| ScreenLayout | 0-4；4 = 版面 3 加 115200 鮑率 | 0、2、3 |
| Talker Alias | 取代來源行：`t0` / `t2` = `"<n> <R/N> <alias>"` | 獨立欄位 `t8` / `t9` |
| RSSI | `"-<n>dBm"`，平均值 | `"<n>dBm"`（帶正負號） |
| `t30`、`t32` | `"%3.6f"`，沒有單位，只有版面 3 | `"%.4f MHz"`，所有版面 |
| `t21`、`t22`、`cpuload`、`t31` | 不送（它們原本是 NextionDriver 的欄位） | 會送 |
| D-Star 文字 `t5`、FM 頁 | 無 | 有 |
| 錯誤 | `t0` = 錯誤文字，`t1` = `"ERROR"`，先送狀態 13 再送 14 | 只有狀態 13（第 9 節） |
| FM | `page MMDVM`，`t0` = `"FM"`，狀態 18 | `page FM` |
| `bkcmd` | 0（不回應） | 3 |
| 待機頁重畫 | 進入待機時 | 另外每次設定／位址變動時也會重畫 |

在 ON7LDS 的說明裡，DMR 頁的 `t8`-`t13` 是 NextionDriver 寫入的 GPS 欄位。MMDVM-Display 把 `t8` 和 `t9` 拿來放 Talker Alias。

## 9. 未解問題與原始碼裡的怪異之處

1. **錯誤狀態不送文字。** `setErrorInt` 用 `sprintf` 組好了 `t0.txt="ERROR"`，卻從來沒有交給 `sendCommand`；送出去的只有 `page MMDVM`、`dim`，以及（版面 3 的）狀態 13。
   用版面 0 和 2 時，錯誤在螢幕上看不出來。本設計的 `S0` 程式碼在收到狀態 13 時自己寫入 `ERROR`。
   這看起來是 bug，不是刻意的；上游之後可能會修，修了也不會影響這裡。
2. **時鐘格式依主機的語系**（`setlocale(LC_TIME, "")`、`%x %X`）。`LC_TIME=C` 時是 `11/16/26 14:30:00`。
   中文語系會產生多位元組文字，這個畫面檔的字型顯示不了。BUILD.md 為服務設定了 `LC_TIME=C`。
   使用者的系統目前是什麼設定，不清楚。
3. **`t20` 只有在版面 0 和 2 才是 `"?"`**，只有版面 3 才會寫入溫度。
   版面 3 若沒有收到溫度回報，這個欄位永遠不會被寫入，所以保持畫面檔裡的初始文字（本設計是空白）。
4. **位置永遠是 `"?"`。** `parseHostConfig` 裡讀取位置的程式碼被註解掉了。`t31` 仍保留在頁面上，但隱藏起來。
5. **`cpuload` 在原始碼裡標註了「TODO this is incorrect」。** 它是平均負載 x 100，不是百分比，可能超過 100。
   保留為 Variable，不顯示。
6. **反射器為空。** JSON 裡沒有反射器時，`parseDStar` 和 `parseYSF` 傳的是空字串，但驅動程式只在字串是 8（或 10）個空格時才不送這個欄位。
   所以 `t2` 可能變成後面什麼都沒有的 `"via "` 或 `"at "`。`S0` 的程式碼會把它們清空。
7. **YSF RSSI 沒有狀態碼**（`writeFusionRSSIInt` 沒有呼叫 `sendCommandAction`）；文字還是會寫入。對本設計沒有影響。
8. **ON7LDS 檔案裡 `S0` 的類型**讀不出來：`.HMI` 是二進位格式，而且沒有安裝編輯器。
   從 `Nextion_ON7LDS/NX4832T035-L3.HMI` 裡的字串只確認了它的名稱、它的 Touch Press 程式碼，以及 `MMDVM` 頁上的全域 Variable `status`。
   本設計用 Hotspot；任何有 Touch Press 事件的元件都會回應 `click S0,1`。
9. **文字超過 `txt_maxl`。** TJC 螢幕是截斷文字還是拒絕這個指令（`0x1C`），沒有驗證過。
   `layout.json` 裡的 `txt_maxl` 都設成大於或等於驅動程式緩衝區能產生的最長文字。
10. **RSSI 和 BER 取決於數據機。** 數據機沒有回報 RSSI 時，`CDMRSlot::writeJSONRSSI` 會提早返回。
    這塊板子上的 MMDVM_HS 韌體是否每種模式都回報 RSSI，沒有查過；這些欄位可能就一直是空的。
11. **TJC 與 Nextion 的差異。** 用到的指令（`page`、`.txt=`、`.val=`、`.pco=`、`dim=`、`bkcmd=`、`click`、`bauds=`、`touch_j`）依文件是兩邊指令集共有的，但這裡的東西都還沒在 TJC X5 上跑過。
12. **Talker Alias 的編碼。** 別名照收到的內容原樣轉送（`CDMRSlot::writeJSONText`）。
    ISO-8859-1 以外的字元（例如中文別名）會顯示成亂碼。
13. **經由數據機載入 `.tft`。** MMDVM-Display 的 `NextionUpdater` 有 `Port=modem` 的路徑（`uploadViaMQTT`：`whmi-wri <size>,9600,0`，每塊 4096 bytes，每塊 4 s）。
    在鮑率 9600 下 4096 bytes 要 4.3 s，超過它自己的逾時時間，而且 MMDVM_HS 的序列透傳在 256 bytes 緩衝區滿了時會丟資料。
    對這個好幾 MB 的檔案視為無法使用；BUILD.md 改用 microSD 卡。
14. **「MMDVM STOPPED」永遠不會送出。** `CNextion::setQuitInt` 存在（狀態 19），但 MMDVM-Display 裡沒有任何地方呼叫 `CDisplay::setQuit`；程式結束時只會關閉連接埠。
    軟體停止後，螢幕會停留在最後的畫面。`S0` 的程式碼仍然處理狀態 19，是給舊版 MMDVMHost 用的。
