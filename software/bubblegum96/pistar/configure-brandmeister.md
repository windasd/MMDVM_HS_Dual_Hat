# 用 Pi-Star 網頁設定：從全新安裝到 BrandMeister 上的 DMR

**未測試。** 步驟是依照鎖定版本儀表板（Dashboard）的程式碼（`admin/configure.php`）和 Pi-Star 的服務包裝腳本寫的；沒有在板子上實際操作過，也沒有試過登入 BrandMeister 主控站。欄位名稱照儀表板英文（UK）介面的標籤。

## 0. 開始之前

- 在 <https://brandmeister.network> 上有綁定你 DMR ID 的 BrandMeister 帳號。
- 在 **SelfCare**（右上角，你的呼號 > SelfCare）：打開 **Hotspot Security** 並設定密碼。熱點就是用這個密碼登入。請先做這一步：Pi-Star 起始用的預設檔裡有一個佔位密碼，如果第 3 步的欄位留空，送出去的就是那個佔位密碼。
- 數據機已經有韌體（見文末的「數據機韌體」），而且 `/dev/ttyOWL2` 存在。
- 已經執行過 `sudo bash install-pistar.sh`，板子也已重新開機。

## 1. 安裝腳本已經設好的

`/etc/mmdvmhost` 裡（先是 Pi-Star 來自 `config_clean.zip` 的預設檔，再經過 `board/pistar-b96-presets --defaults`）：

| 區段 | 設定項 | 值 | 原因 |
|---|---|---|---|
| `[Modem]` | `Port`、`UARTPort` | `/dev/ttyAMA0` | `/dev/ttyOWL2` 的 udev 別名；頁面為 GPIO hat 寫入的就是這個名稱 |
| `[Modem]` | `Protocol` | `uart` | |
| `[Modem]` | `UARTSpeed` | `115200` | MMDVM_HS 韌體的主機端鮑率 |
| `[General]` | `Duplex` | `1` | 兩顆 ADF7021 |
| `[General]` | `Display` | `Nextion` | TJC 螢幕 |
| `[Nextion]` | `Port` | `modem` | 螢幕接在數據機的透傳埠上 |
| `[Nextion]` | `ScreenLayout` | `3` | 「ON7LDS L3」；`display/tjc8048x550` 是照 3 畫的 |

其他都是 Pi-Star 的預設值：呼號 `M1ABC`、ID `1234567`、所有模式關閉、438.800 MHz。用這些佔位值時，任何無線電服務都不會啟動（包裝腳本會拒絕），而且在第一次按「Apply」之前沒有 `/etc/dstar-radio.mmdvmhost`，所以儀表板會顯示「No Mode Defined」。

刻意沒有預先設定的：呼號、DMR ID、頻率、DMR 主控站、密碼、數據機類型的選擇（第 2 步會寫入）。

## 2. 第一個頁面：Configuration

開啟 `http://<board address>/admin/configure.php`。以 `pi-star` 登入（密碼：安裝時你輸入的那個，或 Pi-Star 的預設密碼——見 README.md；在這個頁面的最底下修改：「Remote Access Password」、「Set Password」）。

Pi-Star 會一步一步顯示各個區段；每填完一個區塊就按 **Apply Changes**，並等頁面重新載入（每次都會停止並重新啟動服務）。

**Control Software**

| 欄位 | 選擇 |
|---|---|
| Controller Software | `MMDVMHost` |
| Controller Mode | `Duplex Repeater` |

按 Apply。現在 `/etc/dstar-radio.mmdvmhost` 已經存在，其他區段也會出現。

**MMDVMHost Configuration**

| 欄位 | 選擇 |
|---|---|
| DMR Mode | 開 |
| 其他所有模式 | 關（和你原本在 Pi-Star 上一樣） |
| MMDVM Display Type | `Nextion`，Port `modem`，Nextion Layout `ON7LDS L3`（已經選好） |

按 Apply。「DMR Configuration」區段會出現。

**General Configuration**

| 欄位 | 值 |
|---|---|
| Node Callsign | 你的呼號 |
| CCS7/DMR ID | 你的 7 位數 DMR ID |
| Radio Frequency RX / TX | 兩個頻率（雙工），例如相差 5 MHz，在你的頻率規劃範圍內；RX 是熱點*接收*的頻率 |
| Latitude, Longitude, Town, Country, URL | 隨意；這些會送到主控站 |
| **Radio/Modem Type** | **`MMDVM_HS_Duplex_Hat (DB9MAT, DF2ET & DO7EN) for Pi (GPIO)`** |
| Node Type | `Private`（只有你的 DMR ID 能使用這個熱點）或 `Public` |
| System Time Zone, Dashboard Language | 隨意（有 `chinese_tw`） |

關於數據機類型：這塊板子是 MMDVM_HS_Dual_Hat（STM32、兩顆 ADF7021、14.7456 MHz TCXO），接在一個不是樹莓派 GPIO UART 的序列埠上。在 Pi-Star 的清單裡，「(GPIO)」只代表「埠是 `/dev/ttyAMA0`」。這個選項（`mmdvmhsdualhatgpio`，`admin/configure.php:2243-2251`）會設定 `[Modem] Port=/dev/ttyAMA0`、`Protocol=uart`、`UARTPort` 設成同一個、`Duplex=1`、FM 關閉，不會設定任何和 GPIO 有關的東西。`/dev/ttyAMA0` 在這裡是 `/dev/ttyOWL2` 的別名。**不要**選「(USB)」版本（`/dev/ttyACM0`）、ZUMspot／DV-Mega 的項目，或帶有「12.xxxMHz」的項目。頁面不會為這個類型設定 `UARTSpeed`；安裝腳本設的 `115200` 會保留。

按 Apply。

## 3. DMR Configuration

| 欄位 | 值 |
|---|---|
| DMR Master (MMDVMHost) | 一個 `BM_...` 項目：你以前用的那個主控站。BrandMeister 在台灣沒有主控站（2026-11-16 查過，見 `../README.md`）；最近的是 4501 韓國、4602 中國、5021 馬來西亞、5151 菲律賓 |
| Hotspot Security | SelfCare 裡的 Hotspot Security 密碼。這一列要在選了 `BM_` 主控站**並且套用**之後才會出現（`admin/configure.php:4759-4762`），所以：先選主控站、按 Apply，再輸入密碼、再按一次 Apply |
| ESSID（如果頁面有顯示） | 只有一台熱點時選 `None`；同一個 ID 下有好幾台時用 01-99 |
| DMR Colour Code | `1`（必須和無線電機的頻道設定相同） |
| DMR EmbeddedLCOnly, DMR DumpTAData | 預設值 |

按 Apply。

這一步做的事（`admin/configure.php:1513-1540`）：`[DMR Network]` 的 `Address`／`RemoteAddress` = 主控站、`Port`／`RemotePort`、`Type=Direct`、`Password` = 你的 Hotspot Security 密碼。MMDVMHost 自己登入主控站——和你的樹莓派上一樣，但和最小套件不同，最小套件是由 DMRGateway 登入。只有在主控站選 **`DMRGateway`** 這一項時（同時使用 BrandMeister 和 DMR+／XLX／TGIF 的情況），才會啟動 DMRGateway；這時頁面會改為顯示「BrandMeister Master」、「BM Hotspot Security」和「BrandMeister Network ESSID」。

密碼以明文存在 `/etc/mmdvmhost`（以及 `/etc/dstar-radio.mmdvmhost`）裡，權限 644，每台 Pi-Star 都是如此。

主控站清單來自 `/usr/local/etc/DMR_Hosts.txt`。如果下拉選單是空的，表示主機清單檔從來沒有下載過：在網路正常時執行 `sudo pistar-update`（或 Admin > Update）。

## 4. 檢查

- 儀表板（`/`）：Modes Enabled 底下的「DMR」是綠色，「DMR Net」是綠色，「DMR Master」底下顯示主控站名稱，Radio Info 方塊裡有數據機韌體版本。
- Admin > Live Logs：出現 `DMR, Logged into the master successfully` 這樣的行。`Login to the master has failed` = Hotspot Security 密碼錯誤，或 SelfCare 裡沒有開啟 Hotspot Security。
- 無線電機：頻道設 TX = 熱點的 RX 頻率、RX = 熱點的 TX 頻率、色碼 1、時槽 2、聯絡人設為通話群組。在 TG 9990（BrandMeister 的 parrot，私人呼叫）按 PTT 發話，就能聽到自己的聲音回放。

## 5. 靜態通話群組

和以前一樣，在 BrandMeister 網站上操作：在 SelfCare 開啟你的熱點（「My hotspots」；選單名稱是憑記憶寫的，寫這份文件時沒有打開網站），把通話群組加為時槽 2 的靜態群組（雙工熱點也有時槽 1）。變更在主控站上生效；板子上不會存任何東西。

選用：若要從儀表板做同樣的事（Admin 頁面的 BrandMeister manager）：在你的 BrandMeister 個人資料裡建立 API key，貼到 Expert > API Keys。manager 會讀取 `/etc/bmapi.key`（`mmdvmhost/bm_manager.php:38`）。

## 6. 從你的樹莓派搬過來

舊 Pi-Star 上的 Admin > Backup/Restore 會產生一個 zip，可以在這裡還原，取代第 2-3 步。還原頁面已經修補過，還原之後會把數據機埠、UART 速率和 `[Nextion] Port=modem` 放回去（`patches/dashboard/0001-...`）。它也會還原舊的**主機名稱**，以及樹莓派的 Wi-Fi 網路。還原之後請檢查 Radio/Modem Type。

## 數據機韌體

用 `sudo flash-mmdvm-hs <file.bin>`（板子套件），或用 Expert > FW >「MMDVM_HS_Dual_Hat (14.7456MHz TCXO) GPIO」，後者會燒錄 Pi-Star 附帶的 `hs_dual_hat.bin`。這個檔案沒有檢查過：它的序列透傳（serial repeater）鮑率是否和 TJC 螢幕相符（畫面檔裡的 `bauds=`，研究文件第 6.3 節）並不清楚。如果燒錄後 DMR 正常但螢幕一直是暗的，這是第一個要查的地方。

## 不能運作時

| 症狀 | 檢查 |
|---|---|
| 頁面載入時沒有樣式／「File not found」 | `/var/log/nginx/error.log`；`systemctl status php8.3-fpm` |
| 「Apply」好像沒有作用，數值又變回原樣 | sudo：`sudo -l -U www-data`；被拒絕的指令在 `journalctl -t sudo` 和 nginx 錯誤 log 裡 |
| 儀表板上 MMDVMHost 是紅色 | `sudo /usr/local/sbin/mmdvmhost.service start` 會印出拒絕的原因；`ls -l /dev/ttyAMA0 /dev/ttyOWL2`（別名在不在？群組是不是 `mmdvm`？）；最新的 `/var/log/pi-star/MMDVM-*.log` |
| Log：`Unable to read the firmware version` | 數據機被卡在重置，或停在開機載入程式（boot loader）裡：`sudo mmdvm-gpio status`、`sudo pistar-mmdvmhshatreset`；鮑率 |
| DMR Net 是紅色 | 主控站／密碼；往主控站連接埠（62031）的對外 UDP 是不是被擋了？ |
