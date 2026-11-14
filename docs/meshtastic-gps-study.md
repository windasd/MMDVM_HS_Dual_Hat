# MMDVM + Meshtastic + GPS + 18650 電池：可行性研究

研究日期：2026-11-14（分支 `meshtastic-gps-study`）
狀態：**研究／提案**，尚未開始畫線路。標「待確認」的項目需要實測或使用者決定。

## 0. 結論摘要

| 問題 | 結論 |
|---|---|
| 能不能加 Meshtastic？ | **可以，但 ADF7021 不能做 LoRa**，要另外加一顆 SX1262。台灣用 TW 區 920–925 MHz，跟熱點的 430–440 MHz 分得很開，互擾低。 |
| 現有板子塞得下嗎？ | **塞不下。** r1.3 上層最大空位約 7×11 mm，r2.0-mini 只有 65×30 mm、穩壓器 300 mA。需要出一張新板。 |
| 用 Bubblegum-96 當主機？ | **可以。** mainline kernel 沒有 S900 的 USB host、SPI 控制器、Wi-Fi DT、PMIC，但使用者自己的 kernel 已經補上 USB 和 Wi-Fi，目前用 USB 網卡上網，開關機正常。SPI 控制器仍然沒有，所以新板以 UART + I2C + GPIO 跟主機溝通，USB 只當選配（給 Meshtastic MCU 更新韌體）。 |
| Meshtastic 怎麼接？ | **建議板上放一顆 nRF52840 + SX1262，跑官方 Meshtastic 韌體**，GPS 接在它身上。不依賴 S900 kernel，主機關機時 Meshtastic 也能單獨用電池跑上一週左右。 |
| GPS 給誰用？ | GPS 由 Meshtastic MCU 控制；NMEA 同時分一路給主機（經 I2C 轉 UART），讓 gpsd、APRS／閘道器也拿得到位置。 |
| 4 顆 18650 並聯 + 供電給 Bubblegum？ | **可行，建議 1S4P。** 電池升壓到 12 V，經擴充座的 SYS_DCIN 反向餵 Bubblegum（96Boards 規格明確允許）。充電建議 USB-C PD 9 V，只用 5 V 的話，帶主機運作時幾乎充不進去。 |
| 螢幕 TJC8048X550 | 接 MMDVM 板的 NXT 透傳埠（STM32 USART2），`Port=modem`。**X5 系列的 TX 是 5 V，STM32 的 PA3 不耐 5 V，要串 1 kΩ**；排針腳序也跟 r1.3 相反。目前的 MMDVM-Host 已把螢幕功能拆到 MMDVM-Display（走 MQTT）。沒有現成 800×480 的 TJC 畫面檔，要自己用 TJC 編輯器做。詳見第 6 節。 |
| Meshtastic 小螢幕 | **可以，不用改韌體。** 官方韌體會自動偵測 I2C 0x3C 上的 OLED（Heltec V3 用 0.96 吋 SSD1306）。本案建議 1.3 吋 SH1106 128×64，放在 5 吋螢幕下方的前面板，MESH 按鍵在旁邊。詳見第 3.2 節。 |
| 外盒 | **3D 列印、直立式桌上型**：螢幕朝前、後仰 12°，四支天線從頂邊朝上，頂部 30 mm 風扇往上排風，底部進風形成煙囪氣流。5 吋螢幕下方有前面板（Meshtastic OLED＋MESH 鍵）。外形約 136（高）× 156（寬）× 52（深）mm。詳見第 7 節。 |

## 1. 需求

1. 保留 MMDVM_HS_Dual_Hat 的雙 ADF7021 雙工熱點功能（DMR／D-Star／YSF／P25／NXDN）。
2. 加 Meshtastic（LoRa，台灣 920–925 MHz）。
3. 整合 GPS。
4. 主機暫定 Bubblegum-96（Ubuntu 24.04，新版 kernel）。
5. 4 顆 18650 直接裝在板上，可充放電，同時供電給 Bubblegum-96。
6. 外盒，裝 TJC8048X550_011 5 吋螢幕給 MMDVM 用。
7. GPS 開關：硬體滑動開關斷電，加上 Meshtastic 的軟體切換（兩者都做；有 OLED 時軟體切換在 GPS 頁選單，見 10.4）。
8. 外盒用 3D 列印，要能立在桌上直接看螢幕。
9. 加小型散熱風扇，設計時考慮安裝與風道。
10. Bubblegum 的 TTL console 直接在板上做好接口，方便接 USB-TTL。
11. Meshtastic 要像 Heltec WiFi LoRa 32 V3 一樣有一塊小螢幕。

## 2. 主機：Bubblegum-96 現況

### 2.1 硬體
- Actions S900，85×54 mm（96Boards CE）。
- DC 輸入：線路圖標 8–18 V，手冊建議 12 V／2 A。插頭 4.8/1.7 mm。
- 沒有有線網路。Wi-Fi／BT 是 BCM43438。USB 3.0 A ×1、USB 2.0 A ×1、micro-USB OTG ×1。
- 已停產，市面上幾乎買不到。
- **耗電沒有公開數據，要實測**，下文先假設 3–8 W。

### 2.2 mainline kernel 支援（torvalds master 7.4-rc2）

| 功能 | 狀態 | 對本設計的影響 |
|---|---|---|
| UART（owl-uart） | 有。uart5 當 console，其餘預設關閉 | 擴充座 UART0 要用 DT overlay 打開 |
| I2C（owl-i2c） | 有，i2c1／i2c2 已啟用 | 可直接用 |
| GPIO／pinctrl | 有 | 可直接用（libgpiod） |
| SPI 控制器 | **沒有驅動** | 不用硬體 SPI；Meshtastic 改用板上 MCU |
| USB host | mainline **沒有**；**使用者的 kernel 已補上**，USB 網卡可用 | 主要介面不靠 USB；USB 只用在選配功能 |
| Wi-Fi（SDIO） | 驅動有，mainline DT 沒啟用；**使用者的 kernel 已可用** | 外盒用塑膠（3D 列印），Wi-Fi 不會被擋 |
| PMIC | mainline 沒有驅動；使用者表示開關機正常 | 本板偵測 LS +1V8（pin 35）消失，就關掉 12 V（待實測）；`gpio-poweroff` 當備案 |

> **使用者回報（2026-11-14）：** 自行維護的 kernel 已讓 Wi-Fi 與 USB 正常，目前用 USB 網卡上網，開關機正常。仍要注意：USB 2.0 A 口不支援 hub，USB 網卡最好插在 USB 3.0 口或 USB 2.0 口直插。
>
> **實測先跳過（使用者決定，2026-11-14）。** 設計改成兩種情況都能應付，板子做好後再用板子本身量：
>
> | 未知數 | 設計怎麼處理 |
> |---|---|
> | 12 V 耗電 | 12 V 升壓照 18 W（12 V／1.5 A）設計；輸出端加 INA226 電流／功率監測，主機直接讀實際耗電 |
> | 關機後 +1V8 會不會掉 | 偵測 +1V8 消失**或**主機用 `gpio-poweroff` 拉 KILL，任一成立就延遲斷 12 V；長按電源鍵強制斷電當最後手段 |
> | SYS_DCIN 上電會不會自動開機 | 預留電路接 LS pin 4（PWR_BTN_N），12 V 送上後由本板代按一次開機鍵；用不到就不焊 |
> | S900 位置 | 氣流本來就流過整片 Bubblegum；散熱片用黏貼式；風扇的溫度感測放在 SoC 柱的出風口，不依賴 SoC 確切位置 |

### 2.3 擴充座（96Boards LS，40-pin，2.0 mm）
- **所有訊號都是 1.8 V**，跟 3.3 V 的元件之間要加電壓轉換。
- 板間距 8 mm，建議 4 根 M2.5 × 8 mm 銅柱。主機板端是 Molex 87381-4063 母座，擴充板端用 Molex 87831-4029 或同等品。
- SYS_DCIN（pin 36、38）：擴充板可以反向供電給主機板，規格允許 8–18 V，建議 12 V。**Bubblegum 的 SYS_DCIN 跟 DC 插座直接相連，沒有 OR-ing**，所以我們的 12 V 出口必須加理想二極體。
- +1V8（pin 35）：最多 0.1 A，只拿來當電壓轉換晶片的 1.8 V 參考。

## 3. 系統架構（建議）

```
                 ┌──────────────── Bubblegum-96（Ubuntu 24.04）────────────────┐
                 │ LS UART0（S900 UART2，1.8 V） I2C0（S900 I2C1） GPIO-A..L  SYS_DCIN │
                 └──────┬─────────────────────┬──────────────┬──────────▲────────┘
                  電壓轉換 1.8↔3.3 V      TCA9406         電壓轉換        │ 12 V
                        │                     │              │            │
   ┌────────────────────▼───┐   ┌─────────────▼─────────┐    │      ┌─────┴──────┐
   │ MMDVM（沿用 r1.3 線路） │   │ 3.3 V I2C 匯流排        │    │      │ 電源（第 4 節）│
   │ STM32F103 + 2×ADF7021   │   │ SC16IS752 雙 UART ─A──┼────┼──┐   └────────────┘
   │ TCXO 14.7456 MHz        │   │ BQ25895 充電 IC        │    │  │
   │ USART2 → TJC 螢幕（XH）  │   │ MAX17048 電量計         │    │  │
   │ SMA ×2（433 TX／RX）     │   └───────────────────────┘    │  │ B（只收 NMEA）
   └─────────────────────────┘                                 │  │
                                     ┌─────────────────────────▼──▼────┐
                                     │ Meshtastic：nRF52840 + SX1262    │
                                     │ 官方韌體，BLE 給手機 App            │
                                     │ GPS（L76K／MAX-M10S）──NMEA──┬──→ │
                                     │ SMA（920 MHz），GPS SMA（有源天線） │
                                     └──────────────────────────────────┘
```

### 3.1 MMDVM
- 沿用 r1.3 的 STM32／ADF7021 線路與射頻佈局，這是驗證過的設計。原本 5 V → 3.3 V 的 LDO 改成第 4 節的電源。
- 主機連線：LS UART0（TX／RX，RTS／CTS 預留）。韌體設定維持 `STM32_USART1_HOST`。
- 燒錄：`stm32flash -i` 用 GPIO-A 控制 BOOT0、GPIO-B 控制 NRST。S900 的 sysfs GPIO 編號從 512 以上起跳，要查 `/sys/class/gpio/gpiochip*/base`；ttyOWL 的 RTS／DTR 不能用軟體控制。
- 備註：雙工模式要求收發頻率相差至少 5 MHz，韌體 README 也提到 DMR 有已知問題。

### 3.2 Meshtastic：三個方案

| | **A. 板上 MCU（建議）** | B. 主機跑 meshtasticd（軟體 SPI） | C. 主機跑 meshtasticd（CH341 USB） |
|---|---|---|---|
| 硬體 | nRF52840 + SX1262（模組），跑官方韌體 | SX1262 模組接 LS SPI0 | 板上 CH341 USB 轉 SPI + SX1262，接主機 USB |
| 主機依賴 | 不依賴，主機關機也能用 | 要 spi-gpio DT overlay（未驗證），外加 BUSY／IRQ／RESET GPIO | 要主機 USB（使用者的 kernel 可用），多一條 USB 線 |
| 手機 App | BLE 直連 | 要經主機網路 | 要經主機網路 |
| 主機關機時 | 繼續跑（約 0.15 W，第 4.4 節） | 停止 | 停止 |
| 韌體 | 沿用官方 variant 的腳位配置，就不用維護 fork | meshtasticd，Ubuntu noble arm64 有 PPA | meshtasticd 2.5.18 起支援 `spidev: ch341` |
| 主機存取 | 透過 SC16IS752 UART-A，可用 Meshtastic CLI／Python API；USB 選配 | 原生 | 原生 |

**為什麼選 A：** S900 沒有硬體 SPI；B 要靠未驗證的軟體 SPI，C 要多佔一個 USB 口（USB 2.0 口不支援 hub）。A 只需要 UART，風險最低。另外，用電池時可以把主機關掉、只留 Meshtastic 跑，續航從幾小時拉長到一週左右。nRF52840 的 USB 拉到板上的內部排針，需要時可以接主機或電腦更新韌體。

**已定案：RAK4630 模組，腳位照官方 `rak4631` 板型**（見第 10 節）。

#### Meshtastic 小螢幕（使用者需求，2026-11-14）

- **可行，不用改韌體：** Meshtastic 官方韌體開機時會偵測 I2C 位址 0x3C 上的 OLED，自動顯示節點、訊息、位置等頁面。
  - Heltec WiFi LoRa 32 V3 板上就是 0.96 吋 128×64 SSD1306。
  - nRF52840 板型一樣支援，例如 RAK4631 的 OLED 擴充模組就是 SSD1306。
- **建議 1.3 吋 SH1106 128×64：**
  - 介面、解析度跟 0.96 吋相同，但字大約 1.4 倍，放桌上約 50 cm 外看比較清楚。
  - 可視區約 29.4×14.7 mm，面板外形約 34.5×23 mm（依實際料號確認）。
  - 也可以用跟 Heltec 一樣的 0.96 吋 SSD1306，外盒開窗改小即可。
- **接法：** 接在 **nRF52840 的 I2C**（不是主機的 I2C），照所選官方板型定義的 SDA／SCL 腳位，韌體才會自動抓到。
- **操作：** MESH 按鍵移到 OLED 旁邊。有螢幕時，官方韌體按一下切下一頁、按住 0.5 秒開選單、按住約 3.9 秒關機；**連按三下切 GPS 只在沒有螢幕時有效**（見 10.4）。
- **耗電：** OLED 亮著時約 10–25 mA（依亮點多寡），韌體閒置一段時間會自動關螢幕，按鍵喚醒；對主機關機時一週左右的續航影響很小。
- **不建議改用 Heltec V3 的 ESP32-S3：**
  - 雖然多了 Wi-Fi，但耗電約是 nRF52840 的 5–10 倍，只跑 Meshtastic 時的續航會從一週掉到一兩天。
  - Meshtastic 要上 MQTT 的話，可以用 MQTT Client Proxy 借主機或手機的網路。
- **機構：** 5 吋螢幕四周邊框只有約 8–13 mm，放不下 OLED。所以外盒底部往下加高 26 mm，做成前面板（「下巴」）：
  - OLED 模組直接用 4 根 M2 螺柱鎖在前蓋上，用 4 線杜邦線接到前面板小板。小板放 MESH 按鍵和藍燈，用 6-pin JST-SH 排線（3.3 V、GND、SDA、SCL、按鍵、藍燈）接回主板 J44（見 10.6）。
  - 下巴的空腔剛好是底部進風口後面的進氣室，兩個氣流柱的進風更均勻。

### 3.3 GPS
- 候選模組：
  - Quectel L76K：UART，約 25 mA，Meshtastic 可自動偵測。
  - u-blox MAX-M10S：UART／I2C，約 10 mA，有 LNA_EN 與 VCC_RF，可直接供電給有源天線。
- 天線：**建議用 SMA 外接有源天線。** 機殼內有 SoC、DC-DC 和高階時脈諧波（見第 5 節），板載陶瓷天線容易受干擾。
- GPS 的 TX 分兩路：一路接 Meshtastic MCU（它負責設定 GPS），另一路接 SC16IS752 UART-B，只收 NMEA，主機用 gpsd 讀。注意：Meshtastic 的省電模式可能關掉 GPS，主機那邊就收不到；要設定 GPS 常開。
- PPS 經電壓轉換接到一根 GPIO，主機可以用 `pps-gpio` + chrony 校時。主機沒有 RTC、沒網路時特別有用。

#### GPS 開關（使用者需求，2026-11-14）

外殼上加一個滑動開關，決定 GPS 模組要不要開。

- **線路：** GPS 電源 = 滑動開關 **AND** Meshtastic MCU 的 GPS_EN，經負載開關（TPS22916 類，或 P-MOSFET）供給 GPS VCC。
  - 開關 OFF：GPS 完全斷電，不會有位置，最省電。
  - 開關 ON：交給 Meshtastic 控制，它的省電模式照常運作。
- **備援電源：** GPS 的 V_BCKP 腳由常開的 3.3 V 經二極體供電。開關關掉時星曆仍保留，再打開可以熱啟動，幾秒內定位。
- **指示燈：** 開關旁一顆綠色 LED，GPS 有電就亮；也可以改接 PPS，定位後每秒閃一次。
- **讓韌體知道：** 開關狀態經電壓轉換接到主機 GPIO-I。
  - 主機上的小服務偵測到切換後，用 GPIO-G 重開 Meshtastic MCU，讓韌體重新偵測 GPS。
  - Meshtastic 主要在開機時偵測 GPS，執行中插拔的行為要用實機確認。
  - 主機沒開時，切到 ON 會在 Meshtastic 下次重開後生效。
- **軟體開關（使用者決定兩者都做）：** 「MESH」按鍵（在正面 OLED 旁邊）接 RAK4631 的 user button（P0.09）。因為有 OLED，軟體切換是「切到 GPS 頁 → 按住 0.5 秒 → Toggle GPS」；沒有螢幕時才是連按三下。
  - 兩者的關係：硬體開關 OFF 時 GPS 一定沒電；開關 ON 時，可以用選單在軟體上開關 GPS。
  - 外殼標示：按一下＝下一頁、按住＝選單、長按約 4 秒＝Meshtastic 關機。
- **注意：** 主機的 gpsd 也吃同一顆 GPS，所以開關 OFF 時，APRS／閘道器的位置也會停。
- **想要 GPS 開著、但 Meshtastic 不廣播位置：** 這要用軟體設定，例如 App 裡的 `position.gps_mode`、位置精度、固定位置，不需要硬體開關。
- MMDVM-Host 本身已經沒有 GPSD；位置功能在 DMRGateway、YSFGateway 等閘道器，要編譯時打開 `USE_GPSD`。WPSD 手冊（2026-11）說它的 gpsd 功能目前不能用。

### 3.4 主機腳位分配（提案）

| LS pin | 功能 | 接到 |
|---|---|---|
| 5、7（9、3） | UART0 TX／RX（RTS／CTS） | STM32 USART1，MMDVM 主機連線 |
| 11、13 | UART1（console，ttyOWL5，115200） | 1.8↔3.3 V 轉換 → **外盒側面的 console 接頭**（第 3.5 節） |
| 15、17 | I2C0 | TCA9406 → SC16IS752（0x48）、BQ25895（0x6A）、MAX17048（0x36）、INA226 12 V 監測（0x40）、AMC6821 風扇控制（位址依 ADDR 腳） |
| 19、21 | I2C1 | 保留 |
| 8、10、12、14 | SPI0 | 保留（方案 B 用） |
| 4 | PWR_BTN_N | 本板電源控制代按開機鍵（open-drain，預留、可不焊） |
| 6 | RST_BTN_N | 預留：板上小按鍵 HOST RESET（open-drain，可不焊） |
| 23 GPIO-A | 輸出 | STM32 BOOT0 |
| 24 GPIO-B | 輸出 | STM32 NRST |
| 25 GPIO-C | 輸入 | SC16IS752 IRQ |
| 26 GPIO-D | 輸入 | 充電 IC INT、電量計 ALRT（open-drain 共線） |
| 27 GPIO-E | 輸入 | 電源鍵 INT（要求關機） |
| 28 GPIO-F | 輸出 | KILL 備案（`gpio-poweroff`）；主要靠偵測 +1V8 |
| 29 GPIO-G | 輸出 | Meshtastic MCU RESET |
| 30 GPIO-H | 輸入 | GPS PPS |
| 31 GPIO-I | 輸入 | GPS 開關狀態 |
| 32 GPIO-J | 輸入 | 風扇控制器 ALERT／THERM |
| 33–34 GPIO-K..L | — | 預留 |
| 35 | +1V8 | 電壓轉換晶片 A 側參考 |
| 36、38 | SYS_DCIN | 本板 12 V 出口（經理想二極體） |

### 3.5 Bubblegum console 接頭（使用者需求，2026-11-14）

使用者目前用 USB-TTL 操作 Bubblegum 的 console，希望直接在這張板上做好接口。

- **訊號來源：** LS pin 11（UART1_TxD）、pin 13（UART1_RxD），即 S900 UART5／`ttyOWL5`，115200 8N1。
- **一定要轉電位：** 擴充座是 **1.8 V**，一般 USB-TTL 是 3.3 V 或 5 V，直接接會傷到 S900。
  - 用固定方向的雙電源轉換晶片：兩顆 SN74LVC1T45，或一顆每位元可設方向的 SN74AXC4T774。
  - A 側接 LS +1V8（pin 35），B 側接本板 3.3 V。
  - 這類晶片有 Ioff 斷電隔離：任一側沒電時兩邊都是高阻抗。Bubblegum 關機時，插著的 USB-TTL 不會經 RX 倒灌、讓 SoC 處於半上電狀態；本板沒電時也一樣。
  - B 側輸入可耐 5 V，輸出 3.3 V，所以 3.3 V 和 5 V 的 USB-TTL 都能用（建議設在 3.3 V）。
- **接頭：** 6-pin 2.54 mm 臥式排針，腳序照 FTDI 線（TTL-232R-3V3）。FTDI 線可以直接插；4-pin 的 CH340／CP2102 小板用杜邦線接 GND、TXD、RXD 三條。

  | Pin | 名稱 | 說明 |
  |---|---|---|
  | 1 | GND | |
  | 2 | CTS | 不接 |
  | 3 | VCC | **不接**（避免 USB-TTL 的 5 V／3.3 V 灌進板子） |
  | 4 | TXD（電腦→Bubblegum） | 經轉換到 LS pin 13 |
  | 5 | RXD（Bubblegum→電腦） | 由 LS pin 11 轉換而來 |
  | 6 | RTS | 不接（避免終端機程式切 DTR／RTS 時誤觸 reset） |

- **位置：** 主板延伸端的板邊，直立時在左側面最下方。外盒開 17.4×4.0 mm 的孔，杜邦／FTDI 線頭可以從外面直接插進去，不用拆殼。外殼旁邊壓印「CONSOLE 3.3V」和腳位。
- **選配：** 板上直接放 CH340／CP2102N＋USB 接頭，一條 USB 線就能接電腦（由 USB 供電，不受本板開關影響）。這樣會多一個 USB 口，跟充電用的 USB-C 容易混淆，先列為選配。
- **另外保留：** STM32 的 SWD 接點（原 r1.3 的 STlink 排針），MMDVM 韌體變磚時可以救回；放在板內，不開外盒孔。

## 4. 電源：1S4P

### 4.1 為什麼選 1S4P（4 顆並聯）
- 並聯不用平衡充電，使用者自己換電池也不會出現串聯電芯不平衡的問題。
- 4 顆分攤電流：最壞情況電池端約 4.4 A，每顆約 1.1 A，電池座接點壓力小。
- 1S 的充電 IC、保護 IC、電量計選擇最多、最便宜。
- 代價：要升壓到 12 V，效率約 88–91%；電池到升壓器之間電流大，走線要粗。
- 2S2P 或 4S 在本案不划算：要平衡電路，使用者換電池時也容易造成電芯不平衡。

### 4.2 方塊圖

```
USB-C ─TVS─ CH224K（PD 誘騙，要 9 V；來源不支援就退回 5 V）
              │ VBUS 5–9 V
              ▼
        BQ25895（1S，NVDC 電源路徑，最大充電 5 A，I2C）── TS ← 10 k NTC（貼在電池之間）
              │ VSYS 3.5–4.35 V（拔掉電池也能從 USB 繼續供電）
              │ BAT
              └─ BQ2980 高側保護（1 mΩ 取樣）─┬─ 保險絲 ─ 18650 #1（Keystone 1042P 有極性電池座）
                                              ├─ 保險絲 ─ 18650 #2
                                              ├─ 保險絲 ─ 18650 #3
                                              └─ 保險絲 ─ 18650 #4    MAX17048 電量計跨在電池上
  VSYS ──┬─ TPS61178 升壓 12 V／1.5 A（有 load disconnect）─ INA226 監測 ─ LM74700 理想二極體 ─ SYS_DCIN → Bubblegum
         ├─ TPS61022 升壓 5 V／2 A ─┬─ TJC 螢幕（XH 4-pin）
         │                          └─ AMC6821 → N-MOSFET → 30 mm 風扇（溫控、轉速回授）
         └─ TPS63020 升降壓 3.5 V（固定 2.4 MHz，可同步）─ π 濾波 ─┬─ LDO 3.3 V → STM32＋ADF7021
                                                                  ├─ LDO 3.3 V → nRF52840＋SX1262（常開電源域）
                                                                  └─ LDO 3.3 V → 負載開關（GPS 開關 AND GPS_EN）→ GPS
                                                                                 └→ V_BCKP（常開，保留星曆）
  電源鍵控制（LTC2954 類）：按鍵 → INT 通知主機 → 主機關機 → LS +1V8 消失「或」gpio-poweroff 拉 KILL → 延遲後關 12 V／5 V
  長按電源鍵：強制斷電；開機時（預留）代按 LS PWR_BTN_N
  Meshtastic + GPS 的電源域獨立，可以不跟主機一起關
```

### 4.3 選料理由

| 功能 | 料號 | 理由 |
|---|---|---|
| 充電 | **BQ25895** | 1S，3.9–14 V 輸入，5 A 充電，NVDC 電源路徑，LCSC C80200 便宜。I2C watchdog 逾時後會恢復預設值（2 A、4.208 V），不接主機也能安全充電。 |
| PD 誘騙 | CH224K | 用電阻設定要 9 V，簡單（LCSC C970725）。進階可換 STUSB4500。 |
| 保護 | BQ2980 | 高側 N-FET，GND 不中斷，用取樣電阻精準設定過流（例：8 A）。比 DW01A＋8205A（約 2.5–4 A 就會跳）適合 4P。 |
| 每顆保險絲 | SMD 5–7 A（NANO2 類） | 有人把電池裝反時，其他 3 顆對它短路，靠這顆熔斷。 |
| 電池座 | Keystone 1042P ×4 | SMT、有極性（第一道防反插），77.1×20.7 mm，高 14.86 mm。沒有公布額定電流，每顆 1.1 A 在合理範圍，仍要實測溫升。 |
| 電量計 | MAX17048 | 1S，不用取樣電阻，ALRT 腳接主機。 |
| 12 V | TPS61178 | 2.7–20 V 輸入，峰值電流可設到 10 A，有 load disconnect（關機真正斷電），可外部同步。 |
| 12 V 防逆流 | LM74700-Q1 + N-FET | 防止有人同時把變壓器插在 Bubblegum 上時倒灌。 |
| 5 V | TPS61022 | 8 A 谷值限流，3.6→5 V 約 95%。 |
| 3.3 V | TPS63020 → 3.5 V，再接 LDO | 固定 2.4 MHz、可同步，好規劃頻率。射頻每區各一顆 LDO（TPS7A20 類）。 |

### 4.4 電流與續航估算（3000 mAh 電芯 ×4 = 43 Wh，可用約 39 Wh）

| 負載 | 估計 | 電池端 |
|---|---|---|
| Bubblegum-96（12 V） | 3–8 W **待實測** | 3.3–9.1 W |
| TJC 5 吋螢幕（5 V） | 背光 0 約 150 mA，全亮約 280–330 mA → 0.75–1.65 W | 0.8–1.8 W |
| MMDVM＋Meshtastic＋GPS（3.3 V） | 約 0.7 W | 約 0.9 W |
| Meshtastic OLED（3.3 V，亮著時） | 10–25 mA → 0.03–0.08 W | 約 0.1 W |
| 風扇（5 V，溫控） | 0–0.6 W | 0–0.65 W |
| **合計** | | **約 5–12.5 W → 續航約 3–7.5 小時** |
| 主機關機，只跑 Meshtastic＋GPS | 約 0.15 W | **約一週** |
| 主機關機，Meshtastic 開、GPS 開關 OFF | 約 0.05–0.1 W | **約兩週以上** |

- 最壞情況電池端電流：12.5 W ÷ 3.0 V ≈ 4.2 A，每顆約 1.05 A。
- **充電：** PD 9 V／3 A（27 W）時，扣掉系統用電，約 3–4.5 A 可以充進電池 → 約 3.5–4.5 小時充滿。
- **只有 5 V／3 A（約 13.5 W）時，主機開著幾乎沒有餘力充電**，螢幕全亮時甚至還在放電。所以 PD 是必要的。

### 4.5 安全注意
- **換電池時，4 顆電壓要接近**（相差 0.1 V 以內）再裝。並聯時，電壓高的會對電壓低的大電流灌電，每顆保險絲是最後防線。外殼要貼警示。
- 18650 有保護板版本長約 69–70 mm，要確認裝得進電池座；**建議用無保護板的平頭電芯**，由板上的保護 IC 負責。
- NTC 要貼在電池之間，接充電 IC 的 TS 腳（JEITA）。電池要遠離 SoC 和升壓電感的熱。
- 長期插電當 UPS 用時，建議主機開機後用 I2C 把充電電壓降到 4.1 V，延長電池壽命。
- 主機要讀電量計，低電量時自動關機；BQ2980 欠壓保護是最後防線。

## 5. 射頻共存

| 來源 | 頻率 | 結果 |
|---|---|---|
| ADF7021 熱點 | 430–440 MHz | 2 倍頻 860–880 MHz、3 倍頻 1290–1320 MHz，都不落在 920–925 或 GPS L1 |
| LoRa TW | 920–925 MHz | 2 倍頻 1840–1850 MHz，不落在 GPS |
| 互調（\|m\|+\|n\|≤5） | 熱點 × LoRa | 沒有產物落在 GPS L1／BDS B1I／GAL E1 |
| TCXO 14.7456 MHz | 第 107 次諧波 1577.78 MHz | 距 GPS L1 約 2.4 MHz，很弱 |
| Y1 8 MHz（STM32） | 第 197 次諧波 1576.00 MHz | 距 L1 約 0.6 MHz，極弱，但 GPS 天線仍要外接 |
| DC-DC 開關頻率 | 0.75–2.4 MHz | GPS 頻帶內一定會有某次諧波，靠佈局、屏蔽、濾波處理；所有 DC-DC 同步在同一時脈 |

- 天線：433 TX、433 RX、920 LoRa、GPS，共 4 個 SMA。LoRa 天線跟 433 天線盡量拉開距離。
- Bubblegum 的 Wi-Fi 天線在板上，**外殼不要用全金屬**，或在 Wi-Fi 位置留塑膠窗。

### 法規備註（台灣）
- Meshtastic 韌體的 TW 區：920–925 MHz、上限 27 dBm、佔空比 100%。
- NCC LP0002 第 5.8.1 節：920–925 MHz 室內 ≤1 W、室外 ≤0.5 W，但**只適用跳頻，或 6 dB 頻寬 ≥500 kHz 的數位調變**。Meshtastic 預設 LongFast 是 250 kHz 頻寬，有可能落入第 5.8.2 節（3 m 處 50 mV/m）這個嚴格得多的限制。**這是我的解讀，要請 NCC 認可的實驗室確認。**
- 授權業餘電台可以考慮 Meshtastic 的 licensed 模式，但頻段與調變方式要另外依業餘電台法規確認。

## 6. 螢幕 TJC8048X550_011

來源：TJC X5 規格書（`TJC8048X550_011R/N/C.pdf`，p.7–14）、TJC wiki FAQ（QA3／QA110）、g4klx/MMDVM-Display、juribeparada/MMDVM_HS。

### 6.1 規格

| 項目 | 數值 |
|---|---|
| 面板 | 5.0 吋 800×480，TN，300 nit；視角上／下／左／右 50／70／70／70° |
| 系列 | X5（TJC 最高階）：ARM9 200 MHz、128 MB flash、512 KB RAM、RTC、8 GPIO、音訊 |
| 後綴 | `_011R` 電阻觸控、`_011C` 電容觸控、`_011N` 無觸控。**使用者的這片是 R（電阻觸控）**：板上只印 `TJC8048X550_011`，但觸控排線 HST050008 是 4 pin（4 線電阻觸控）；面板另印 HST050040 |
| 電源 | 4.65–6.5 V（建議 5 V／1 A）；全亮 R 330 mA／N 327 mA／C 281 mA，背光 0 約 150 mA |
| UART | **5 V TTL**（X3／X5 是 5 V，其他系列 3.3 V），預設 9600 8N1，可到 921600；`bauds=` 寫入開機預設值 |
| 接頭 | XH2.54 4-pin 臥式：**1 GND、2 RX、3 TX、4 5V** |
| 外形 | 裸板無外框；PCB 136.90×84.00 mm（R3 圓角），Ø3.2 孔 ×4，孔距 130.50×77.60 |
| 顯示區 | LCD 外框 120.70×75.80；可視區 108.00×64.80，短邊方向偏離中心約 1.9 mm |
| 厚度 | 前方疊層 N 3.3／R 4.5／C 5.08 mm；PCB 1.6；背面最高 6.0（XH 接頭）→ 總深約 10.9／12.1／12.7 mm |
| 其他 | 背面有 microSD（更新 TFT 用）；工作溫度 −20～+70 °C |

### 6.2 接線注意（本板要改的地方）

- **5 V 的 TX 不能直接進 STM32 PA3：** PA2／PA3 不耐 5 V。TJC 官方建議串 1 kΩ；新板在螢幕 TX → PA3 之間放 1 kΩ（或單向電壓轉換）。反方向 PA2 → 螢幕 RX 是 3.3 V 訊號，螢幕可以直接收。
- **腳序：** r1.3／r2.0 的 NXT 排針是 1=5V、2=RXD、3=TXD、4=GND，跟 TJC 的 XH 剛好相反，1:1 線會把 5 V 接到螢幕 GND。**新板改用 XH 4-pin、腳序照 TJC（1 GND、2 螢幕 RX、3 螢幕 TX、4 5V）**，用一般 1:1 XH 線就好。
- **電源：** 由 5 V 升壓（TPS61022）供電，約 0.33 A。

### 6.3 軟體

- **MMDVM_HS 韌體：** Dual Hat 的設定檔已定義 `SERIAL_REPEATER`（USART2、PA2／PA3、9600）。發送緩衝 256 bytes，滿了會**直接丟資料**，沒有流量控制。800×480 畫面欄位多，建議重編韌體把 `SERIAL_REPEATER_BAUD` 調高（例如 115200），螢幕端用 `bauds=115200` 配合。
- **MMDVM-Host：** 2023-06 起螢幕程式碼已移到 **MMDVM-Display**，透過 MQTT 取得資料（要 mosquitto）。設定檔 `[Nextion]`：`Port=modem`、`ScreenLayout` 只剩 0／2／3。也可以用 2023-06 以前的 MMDVMHost（`[Nextion] Port=modem`）。
- **ON7LDS NextionDriver：** 支援 modem 埠，但跟新版 MMDVM-Display 分拆後的設定能不能一起用，**尚未驗證**。
- **畫面檔：** 找不到現成的 TJC 800×480 MMDVM 畫面。
  - Nextion 的 `.tft` 不能用在 TJC 上；`.HMI` 匯入 TJC 編輯器的回報不一致。
  - PD0DIB 有 Nextion 5 吋 800×480 版本可參考，但只適用 Nextion，而且授權禁止商用。
  - 要用 TJC 的 USART HMI 編輯器（中文介面）照 G4KLX／ON7LDS 的頁面與欄位名稱自己做。
- **編碼：** TJC 預設 GB2312；MMDVM 送溫度時的「°」是單一位元組 176，可能顯示成亂碼，要調字型編碼或改顯示方式（未實測）。
- **更新畫面檔：** 透過螢幕背面的 microSD（要拆前蓋），或用 USB-TTL 接 XH。經 MMDVM 透傳埠應該無法更新（推論）。
- **社群經驗：** 有人在 Pi-Star 用 3.2 吋 TJC 搭 `Port=modem` 成功；沒找到 X5／800×480 TJC 搭 MMDVM 的案例。

## 7. 機構與外盒（概念）

使用者決定：**3D 列印**、**直立在桌上直接看螢幕**、加**小型散熱風扇**。

- 模型：`case/meshtastic-concept/enclosure_concept.py`（CadQuery 2.8，參數化）。輸出 STEP 組合檔、`enclosure_tub.stl`、`front_plate.stl`、`stand_cradle.stl` 與預覽圖。
- 這是配置研究用的模型，還不能直接列印：電池蓋、卡扣、圓角、列印公差都還沒做。
- 已用程式檢查零件之間的干涉（實體交集體積），目前為 0。
- 材料：**PETG 或 ASA，不要用 PLA**。PLA 約 55–60 °C 就會軟化，盒內有 SoC、升壓電路和鋰電池。

### 7.1 方向與疊層

- **直立：** 螢幕朝前，機身後仰 12°。
  - Bubblegum 的 x=85 長邊（96Boards 規格的 Wi-Fi 天線區）朝上，對 Wi-Fi 有利。
  - 原本的「底殼」變成背面，電池蓋在背面。
- **由後往前：** 背板 → Bubblegum-96 → 8 mm → 主板 → 螢幕 → 前蓋。
  - 主板 85×146.5 mm，比 Bubblegum 長出約 92 mm，延伸區背面放 4 顆 18650（Keystone 1042P，間距 21 mm），**電池直立**。
- **兩根氣流柱：**
  - SoC 柱：Bubblegum 那一側，主板上方是 MMDVM 區。
  - 電池柱：電池那一側，主板上方是 Meshtastic／GPS（下段）和電源區（上段，熱往上直接排出，不經過電池）。
- **固定方式：**
  - 背板立柱鎖 Bubblegum 四孔（M2.5），主板延伸端另有兩孔在最後一顆電池座外側。
  - Bubblegum 與主板之間用 8 mm 銅柱。
- **外殼結構：** 「桶身＋前蓋」兩件。
  - 桶身：背板＋四面牆，所有側面開孔、SMA、風扇都在這一件，強度最好。
  - 前蓋：裝螢幕。用 4 根 M3 螺絲鎖到桶身的熱熔螺母；兩根在頂部空腔，兩根在加厚的底邊（7 mm），都避開電路板，整疊電路板可以從前面直接放進去。
- **前面板（下巴）：** 5 吋螢幕下方加高 26 mm，放 1.3 吋 OLED（Meshtastic）和前面板小板（MESH 按鍵＋藍燈），細節見 10.6。
- **外形：** 約 136（高）× 156（寬）× 52（深）mm；含天線站高約 360 mm。

### 7.2 天線（頂邊，垂直朝上）

- 面板式（bulkhead）SMA 母座鎖在頂牆，主板與 GPS 端用 IPEX（u.FL）座，中間接 IPEX→SMA pigtail（1.13 mm 線，約 10–15 cm）。天線的重量和扭力由外殼承受。
- 開孔 Ø6.5 mm D 形孔（平邊 5.9 mm）止轉，適用 1/4"-36 牙 bulkhead SMA。**實際尺寸依採購的接頭再確認。**
- 頂部有約 13 mm 的空腔（plenum）放接頭本體和 pigtail，主板上不需要再留天線禁區。

| 頂邊位置（由 Bubblegum 端算起） | 天線 | 備註 |
|---|---|---|
| y≈12 | 433 TX | 跟 RX 分在兩端，相距約 116 mm |
| y≈23–53 | （風扇） | 在 SoC 柱正上方 |
| y≈70 | GPS | 接外接有源天線（磁吸，拉到窗邊）；也可在頂部空腔放有源陶瓷天線、朝上收訊 |
| y≈100 | LoRa 920 | 鞭狀天線約 11 cm |
| y≈128 | 433 RX | |

- 直立後天線本來就是垂直的，用直的鞭狀天線即可（或可轉向的款式方便微調）。433 MHz 天線約 19–20 cm。

### 7.3 散熱與風道

**熱源估計：**
- SoC 3–8 W（待實測）。
- 螢幕 0.75–1.65 W。
- 電源轉換損耗 0.5–1 W；快充時充電 IC 另外約 1.5–2 W。
- 射頻與 MCU 約 0.7 W。
- 合計約 6–12 W。

**為什麼要風扇：**
- 外殼表面積約 0.06 m²，自然對流加輻射約 8–10 W/m²K，平均溫升約 10–20 °C，熱點更高。
- 夏天 35 °C 室溫時，盒內會超過 50 °C，超出鋰電池充電的 45 °C 上限（JEITA）。

**風量需求：**
- 用 CFM ≈ 1.76 × W ÷ ΔT(°C) 估算：10 W、允許溫升 10 °C，約需 1.8 CFM。
- 30 mm 風扇自由風量約 3–5 CFM（依型號），扣掉格柵損失仍夠用。

**風扇：**
- 30×30×10 mm、5 V，選低噪音、有轉速訊號的型號。
- 鎖在頂牆內側（頂部空腔，24 mm 孔距），**往上排風**，格柵直接印在頂牆上。

**風道：**

```
   頂牆：  [TX]  [風扇↑排風]  [GPS]  ‖  [LoRa] 〃〃被動散熱槽〃〃 [RX]
            ┌──────── SoC 柱 ────────┐‖┌──────── 電池柱 ────────┐
            │ ↑ Bubblegum 與主板間 8 mm │‖│ ↑ 電源區（上段）        │
            │ ↑ 夾層＝煙囪，經過 SoC    │‖│ ↑ Meshtastic／GPS（下段）│
            │ ↑ 散熱片（≤6 mm，規格允許）│‖│ ↑ 4 顆 18650（背面）    │
            │ ↑ 前方：MMDVM 區、螢幕背面 │‖│ ↑                       │
            └──────────────────────────┘‖└──────────────────────────┘
   底邊：  〃〃 進風槽 〃〃               ‖  〃〃 進風槽 〃〃   （支架留 8 mm 進風間隙）
                             頂部空腔隔板 ‖
```

- **SoC 柱：** 底邊進風 → 往上經過 Bubblegum 與主板之間的 8 mm 夾層（S900 上加 ≤6 mm 散熱片，96Boards 規格允許），以及前方的 MMDVM 區和螢幕背面 → 風扇抽出。背板在 SoC 後方也開進風槽。
- **電池柱：** 底邊進風 → 自然對流往上 → 頂牆被動散熱槽。電源區在這一柱的上段，熱往上走、不經過電池。
- **頂部空腔隔板**（y≈56）讓風扇主要抽 SoC 柱，SoC 的熱風不會繞到電池那邊。
- **控制：** 用 **AMC6821**（I2C 風扇控制器，mainline Linux 有 hwmon 驅動）。
  - 內建溫度曲線，主機當掉也會自己轉；有轉速回授。
  - 遠端溫度用一顆 MMBT3904，放在主板背面、正對 SoC 散熱片的出風側。
  - ALERT 接 GPIO-J。
  - 快充時由主機強制提高轉速。
  - 簡化版：溫度開關＋主機 GPIO（OR）控制 MOSFET。
- 底邊進風口可加防塵濾網。
- **驗證：** 35 °C 環境下用熱電偶量 SoC、電池、充電 IC、升壓電感；電池要維持在 45 °C 以下。

### 7.4 螢幕安裝（前蓋）

- 前蓋開窗 = 可視區 108.0×64.8 mm 每邊再加 0.5 mm，並照規格書偏移 1.9 mm。
- 前蓋內側 4 根螺柱對準螢幕 Ø3.2 孔（130.5×77.6），高度 = 前方疊層 + 0.5 mm 間隙。電阻觸控不能被框壓到，否則會誤觸。
- 螢幕的 XH 接頭在一個短邊背面，排線拉到主板 MMDVM 區的 XH 座；microSD 在另一個短邊，要更新畫面檔時拆前蓋（4 顆螺絲）。
- TN 面板上方視角較窄（50°）。機身後仰、從上往下看時，要實測決定面板要不要轉 180° 安裝；畫面方向可以在 TJC 編輯器旋轉。

### 7.5 側面開孔

- **右側面**（Bubblegum 端，直立時在使用者右手邊）：microSD、HDMI、micro-USB、USB-A ×2（USB 網卡插這裡）。Bubblegum 的 DC 插座不開孔，避免同時插變壓器。
- **左側面**（主板延伸端，由上往下）：GPS LED 導光孔、GPS 滑動開關、電源鍵、USB-C 充電、**Bubblegum console 接頭**（6-pin，3.3 V）。
- **正面**：5 吋 TJC 螢幕；下方前面板有 1.3 吋 OLED 開窗和 MESH 按鍵。
- **背面**：電池蓋（待設計成獨立零件，附警示標籤）、SoC 後方進風槽。

預覽圖：

- `preview_desk_front.png`：桌上直立，正面（5 吋螢幕、下方 OLED 與 MESH 鍵）。
- `preview_desk_back.png`：背面，電池蓋與風扇格柵。
- `preview_airflow.png`：拿掉前蓋，藍色箭頭是氣流。
- `preview_side_ports.png`：左側面的按鍵、開關、USB-C 與 console 接頭開孔。
- `preview_inside.png`：內部配置。

## 8. 軟體（Ubuntu 24.04 on Bubblegum-96）

- **DT overlay：**
  - 打開 uart2（LS UART0）。
  - SC16IS752 掛在 i2c1（sc16is7xx 是 mainline 驅動），IRQ 接 GPIO-C。
  - `gpio-poweroff` 用 GPIO-F（備案）。
  - `pps-gpio` 用 GPIO-H。
  - `gpio-line-names`。
- **MMDVM-Host（g4klx/MMDVM-Host）：** 自行編譯，需要 C++17 與 `libmosquitto-dev`，log 走 MQTT，要裝 broker。閘道器（DMRGateway、YSFGateway…）要用 GPS 的話，編譯時打開 `USE_GPSD`。
- **MMDVM-Display：** 驅動 TJC 螢幕（`[Nextion] Port=modem`），也走 MQTT。
- **風扇：** `amc6821` hwmon 驅動，用 `fancontrol` 或自寫服務設溫度曲線。
- **燒 MMDVM_HS 韌體：** 用發行版的 stm32flash，不要用韌體 repo 裡 i386 的 `utils/linux` 工具。
- **Meshtastic（方案 A）：** 在 nRF52840 上燒官方韌體；主機用 `meshtastic --port /dev/ttySC0` 管理。
- **gpsd：** 讀 `/dev/ttySC1`。

## 9. 風險與待決定事項

已決定：

- ~~Bubblegum-96 的網路~~：使用者確認自行維護的 kernel 有 USB 網卡＋Wi-Fi。日後升級 kernel 時要保留這些修補。
- ~~外盒做法~~：3D 列印（PETG／ASA），直立桌上型，含風扇。
- ~~GPS 開關~~：硬體滑動開關斷電＋Meshtastic 軟體切換（有 OLED 時在 GPS 頁選單），兩者都做。
- ~~Meshtastic 方案~~：RAK4630，腳位照官方 `rak4631`；~~GPS~~：u-blox MAX-M10S。
- ~~螢幕版本~~：TJC8048X550_011R（電阻觸控）。
- ~~Bubblegum console~~：板上做 1.8↔3.3 V 轉換＋6-pin FTDI 腳序接頭，外盒側面開孔（第 3.5 節）。
- ~~Meshtastic 小螢幕~~：1.3 吋 SH1106 OLED 接 nRF52840 I2C，放在正面下巴，MESH 按鍵移到旁邊。

待決定／待實測：

1. Bubblegum-96 實測：使用者決定**先跳過**。設計已改成兩種情況都能應付（第 2.2 節表格），板子做好後用 INA226 和實際開關機行為驗證，再決定預留零件要不要焊。
2. Meshtastic 方案（建議 A），以及要沿用哪個官方 variant 的腳位（要同時支援 OLED、user button、GPS 致能腳）。
3. GPS 模組：L76K 或 MAX-M10S；GPS 天線用外接磁吸，或頂部空腔放有源陶瓷天線。
4. 電芯型號（建議同一款無保護板平頭電芯，例如 Samsung 30Q／35E），以及電池座的實測溫升。
5. TW 區 LoRa 的法規解讀。
6. ~~TJC 螢幕的後綴~~：R（電阻觸控，4 pin 觸控排線），前方疊層 4.5 mm；有卡尺時可再量一次確認。
7. 螢幕軟體路線：新版 MMDVM-Host＋MMDVM-Display（MQTT），或舊版 MMDVMHost；畫面檔要自己做。
8. S900 在 Bubblegum 上的實際位置（散熱片位置），以及風扇型號（噪音、轉速訊號）。
9. 授權：原專案是 CC BY-NC-SA，衍生設計要沿用同一授權（不可商用）。

## 10. r3.0 研究版線路圖（`hardware/r3.0-study/`）

使用者選定：Meshtastic 用 **RAK4630（腳位照 Meshtastic 官方 `rak4631` 板型）**，GPS 用 **u-blox MAX-M10S**。

### 10.1 結構與驗證

| 頁 | 檔案 | 來源 |
|---|---|---|
| 1 | `mmdvm_mesh.kicad_sch` | 根頁 |
| 2 | `mmdvm_io.kicad_sch` | 產生：r1.3 Power 頁的 LED、重置鍵、SWD、BOOT 跳線（同參考編號），TJC XH 接頭＋1 kΩ |
| 3 | `host_if.kicad_sch` | 產生：96Boards LS 擴充座、電壓轉換、console、I2C、SC16IS752、風扇、溫度 |
| 4 | `power.kicad_sch` | 產生：USB-C／CH224K、BQ25895、4×18650、保護、電量計、12 V／5 V／3.5 V、LDO、電源鍵 |
| 5 | `meshtastic.kicad_sch` | 產生：RAK4630 與周邊 |
| 6 | `gps.kicad_sch` | 產生：MAX-M10S、GPS 開關、有源天線偏壓 |
| 7 | `mmdvm_rf.kicad_sch` | 沿用 r1.3 主頁（兩顆 ADF7021），P1／P2 改 U.FL |
| 8 | `mmdvm_mcu.kicad_sch` | 沿用 r1.3 STM32 頁 |

- **產生方式：** `gen/build_all.py` 依 `gen/r30_parts*.py` 裡每顆零件「每支腳接哪個網路」的定義產生線路圖；同一頁內用網路標籤，跨頁用 global label，電源用電源符號。
- **驗證：**
  - 產生後用 kicad-cli 匯出網表，逐腳比對規格，**0 差異**。
  - **ERC 0 錯誤 0 警告**。
- 圖面是自動排版的標籤式線路圖，可讀但不美觀；之後要手動整理時，直接在 KiCad 裡移動即可，不影響連線。
- **自建零件**（`MMDVM_r30` 庫），**下單前必須對照原廠圖再核對一次**：
  - RAK4630：符號＋封裝，44 焊墊，依 RAK 官方機構圖與 land pattern 推算，各尺寸已交叉驗證。
  - TPS61178：符號＋封裝，依 TI SLVSDA7E 第 38–39 頁。
  - MAX17048：符號，腳位已確認；EP 尺寸待查 ADI 90-0065。
  - P-MOSFET（SON-8）：符號。

### 10.2 RAK4631 腳位對照（Meshtastic `env:rak4631`，develop d062220e）

| RAK4630 焊墊 | nRF52840 | 用途 |
|---|---|---|
| 4／5 | P0.13／P0.14 | I2C（Wire）→ 前面板 OLED |
| 6／7／8 | P0.15／P0.16／P0.17 | GPS RX／TX（TX 串 1 kΩ）／PPS |
| 9／10 | P0.19／P0.20 | 主機 API（Serial Module，PROTO 模式，經 SC16IS752 通道 A） |
| 13 | P0.09（NFC1） | MESH 按鍵（低態有效） |
| 26 | P1.02（3V3_EN） | GPS 電源（串 GPS 滑動開關） |
| 27／28 | P1.03／P1.04 | 綠燈（板上）／藍燈（前面板，訊息通知） |
| 40 | P0.05（AIN3） | 電池電壓，1 MΩ／1.5 MΩ 分壓（`ADC_MULTIPLIER 1.73`，不加電容） |
| 44／20／21 | — | VBAT_NRF ← VSYS；VBAT_SX、VBAT_IO_SX ← +3V3_MESH；VDD_NRF 不接 |
| 37／15 | — | LoRa／BLE RF → 板上 U.FL → pigtail（用 `-SM-NI` 焊墊版模組） |
| 17／18／19 | — | 重置、SWD → 1.27 mm 10-pin 除錯座 |

**不能接的腳：** P0.10 開機會被韌體拉高、P0.21 是蜂鳴器 PWM、P1.05／P1.07 是模組內部用。

### 10.3 RAK4630 上線步驟（新模組出廠是 RUI3 韌體）

1. 用 SWD（pyOCD 或 J-Link）讀 UICR：
   - `REGOUT0`（0x10001304）要是 3.3 V，出廠預設 1.8 V 會讓 I/O 只有 1.8 V。
   - `NFCPINS`（0x1000120C）要設成 GPIO，不然 P0.09 按鍵沒作用。
2. 燒 RAK4631 bootloader（`wiscore_rak4631_board_bootloader-0.4.4_s140_6.1.1`）。
3. 經內部 USB 座（J43）或 BLE OTA 燒 `firmware-rak4631-*.uf2`。
4. App 設定：
   - LoRa 區域設 TW。
   - Serial Module：enabled、mode PROTO、rxd 19、txd 20、115200，主機才能用 `/dev/ttySC0`。
   - 位置設定：GPS 依需求。

### 10.4 設計變更（RAK4631 研究帶來的）

- **按鍵行為（重要）：** 官方韌體偵測到螢幕時，按鍵改為：
  - 按一下：下一頁。
  - 按住 0.5 秒：開該頁選單。GPS 頁的選單有「Toggle GPS」。
  - 按住約 3.9 秒放開：關機。開機 30 秒內不會觸發。
  - 連按兩下、三下的功能**在有螢幕時不啟用**。

  所以 GPS 的軟體開關改成「GPS 頁 → 按住 → Toggle GPS」；硬體滑動開關不變。
- **GPS 電源：** `env:rak4631` 沒有 GPS 致能腳。本板讓 GPS 電源 = 滑動開關 AND P1.02（韌體平常拉高、關機時拉低），所以 Meshtastic 關機時 GPS 也一起斷電；GPS 沒電時，MCU 的 TX 經 1 kΩ 限流。
- **GPS 有源天線：** 照 u-blox 整合手冊：VCC_RF → 10 Ω → 27 nH → RF_IN（10 nF 濾波）。官方韌體不會設定天線監控，所以 LNA_EN 不接。
- **OLED：** 用 Heltec 1.3 吋 I2C 模組（SH1106，0x3C，PCB 35.5×32 mm，M2 孔距 25.4×27.7）。少數 SH1106 冷開機會被誤判成 SSD1306，可在 App 設 `display.oled = SH1106` 強制指定。
- **CH224K：** 用 CFG1／2／3 全接地的「電位模式」固定要 9 V。這是規格書明列的組合，不靠那張沒確認型號的電阻表。
- **TPS61178：** 元件值參考 TI 2.7–4.4 V → 14 V 範例改成 12 V：
  - 電感 1.8 µH（Würth 744325180，18 A）。
  - 回授 732k／80.6k，約 12.08 V。
  - 限流 75k，典型約 9.9 A。
  - 頻率 348k，約 500 kHz。
  - 負載斷開 P-FET CSD25404Q3，閘極 150k＋22 nF。

### 10.5 還沒定案的值（線路圖上以 MPN／Note 標示 TBD）

- STM6601 的型號，要選 EN 高態有效的版本。
- BQ29700 的版本：保護門檻要配合 CSD17577Q3A 的導通電阻和 4P 電流。
- 每顆電池的保險絲：7 A 1812，型號待選。
- TPS61022 的 VREF：目前假設 0.6 V，要確認。
- CH224K 的 PG 腳：目前不接。

### 10.6 前面板小板（`hardware/r3.0-study/front_panel/`）

- **板子：** 26 × 20 mm，雙層 1.6 mm，兩面鋪 GND。用 2 顆 M2.5 鎖在前蓋的 5 mm 螺柱上。
- **正面（朝前蓋）：**
  - MESH 按鍵：6×6 mm、高 8 mm 的 THT 輕觸開關。板面距前蓋 5 mm，按鍵頭穿過 Ø4.2 孔，凸出前蓋約 0.5 mm。
  - 藍色 LED：0805，Kingbright APT2012QBC/D。前蓋開 Ø3 孔，可加 3 mm 導光柱。
- **背面：**
  - J1：JST SM06B-SRSS-TB，用 1:1 JST-SH 排線接主板 J44。腳位 1 3V3、2 GND、3 SDA、4 SCL、5 按鍵、6 藍燈。
  - J2：4-pin 2.54 mm 排針，用杜邦線接 OLED。絲印從背面看由左到右是 SDA、SCL、3V3、GND。
  - LED 限流電阻 R1 150 Ω，去耦電容 C1、C2。
- **OLED 接線：** OLED 模組鎖在前蓋上，用 4 線杜邦母頭線接 J2。部分模組的 VCC／GND 腳序相反，照模組上的印字接線即可，所以板上不用跳線。
- **Heltec 模組安裝：** 4 根 M2 螺柱，孔距 25.4 × 27.7 mm，玻璃面貼著前蓋開窗。可視區相對模組的偏移量要用實物量測，外盒參數是 `oled_va_dx`。
- **驗證：** 線路圖 ERC 0、網表比對 0 差異；PCB DRC 0 違規、0 未連線，線路圖與 PCB 一致性 0 差異。
- **生產檔：** `front_panel/production/`，只存在本機、不進 git。內含 Gerber＋鑽孔 zip、座標檔、BOM、線路圖 PDF。
- **重新產生：** `gen/front_panel.py` 產生線路圖，`gen/front_panel_pcb.py` 產生 PCB（擺件、走線、鋪銅）。

### 10.7 還沒做的

- 主板 PCB：外形依第 7 節外盒模型；射頻、電源佈局需要人工。
- BOM 與採購確認。

## 參考來源（節錄）

- **Meshtastic**
  - meshtasticd 設定：<https://github.com/meshtastic/firmware/blob/develop/bin/config-dist.yaml>
  - 硬體支援：<https://meshtastic.org/docs/meshtasticd/hardware/>
  - TW 區：<https://github.com/meshtastic/firmware/blob/develop/src/mesh/RadioInterface.cpp>
- **Bubblegum-96 與 96Boards**
  - 硬體手冊：<https://github.com/96boards/documentation/blob/master/consumer/bubblegum-96/hardware-docs/HardwareManual_Bubblegum96_S900_V1.1.pdf>
  - 96Boards CE 規格：<https://github.com/96boards/documentation/blob/master/Specifications/96Boards-CE-Specification-v2.0.pdf>
  - Mezzanine 設計指引：<https://github.com/96boards/documentation/blob/master/mezzanine/files/mezzanine-design-guidelines.pdf>
  - mainline DT：<https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/actions/s900-bubblegum-96.dts>
- **MMDVM**
  - MMDVM_HS 韌體：<https://github.com/juribeparada/MMDVM_HS>
  - MMDVM-Host：<https://github.com/g4klx/MMDVM-Host>
- **電源 IC**
  - BQ25895：<https://www.ti.com/product/BQ25895>
  - BQ2980：<https://www.ti.com/product/BQ2980>
  - TPS61178：<https://www.ti.com/product/TPS61178>
  - LM74700-Q1：<https://www.ti.com/product/LM74700-Q1>
  - MAX17048：<https://www.analog.com/en/products/max17048.html>
- **電池座**
  - Keystone 1042P：<https://www.keyelco.com/userAssets/file/K75p29.pdf>
- **RAK4630／Meshtastic**
  - RAK4630 規格書：<https://docs.rakwireless.com/product-categories/wisduo/rak4630-module/datasheet/>
  - Meshtastic rak4631 variant：<https://github.com/meshtastic/firmware/tree/develop/variants/nrf52840/rak4631>
  - MAX-M10S 整合手冊：<https://content.u-blox.com/sites/default/files/MAX-M10S_IntegrationManual_UBX-20053088.pdf>
  - TPS61178 規格書：<https://www.ti.com/lit/ds/symlink/tps61178.pdf>
  - CH224K 規格書：<https://www.wch.cn/downloads/CH224DS1_PDF.html>
- **螢幕**
  - TJC X5 規格書：<http://wiki2.tjc1688.com/product/new_datasheet/X5/TJC8048X550_011R.html>
  - TJC 串口電壓 FAQ：<http://wiki.tjc1688.com/QA/QA3.html>
  - MMDVM-Display：<https://github.com/g4klx/MMDVM-Display>
  - PD0DIB 畫面（參考）：<https://github.com/PD0DIB/Nextion_HAM-radio-screens>
- **法規**
  - NCC LP0002（非官方副本）：<https://forum.flipper.net/uploads/short-url/5qQHHxW40bD5Vs4cEaPzTiDwmmU.pdf>
