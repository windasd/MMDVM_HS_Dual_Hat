# Bubblegum-96 上 r3.0 研究版擴充板的主機軟體

`hardware/r3.0-study/` 這張板子在 Ubuntu 24.04（arm64）這一端的軟體：MMDVM 雙 ADF7021 熱點（STM32）、Meshtastic 無線電（RAK4630）、GPS（MAX-M10S）、1S4P 電池系統、風扇、LAN7500 乙太網路。

**這個目錄裡的東西都沒有執行過。** 板子從來沒有做出來，手邊也沒有 Bubblegum-96；裝置樹沒有編譯過（撰寫的那台機器上沒有 `dtc`），`install.sh` 也從來沒有執行過。shell 腳本通過 `bash -n`，這是唯一做過的檢查。使用任何檔案之前，請先讀「未測試／假設」一節。

設計紀錄：`docs/meshtastic-gps-study.md`（第 2、3、6、8、10-13、16.10 節）。網路與 I2C 位址：`hardware/r3.0-study/gen/r30_parts.py` 和 `r30_parts2.py`。

## 檔案

| 檔案 | 安裝位置 | 用途 |
|---|---|---|
| `dts/mmdvm-mesh-overlay.dts` | （手動） | 裝置樹疊加檔（overlay）：`uart2` + `serial2` 別名、SC16IS752、EMC2301、TMP102、INA226、MAX17048、BQ25895、`pps-gpio`、`gpio-keys`（電源鍵）、`gpio-poweroff`（停用） |
| `dts/build-dtbo.sh` | - | 編譯疊加檔；可選擇用 `fdtoverlay` 合併進基礎 DTB |
| `gpio/mmdvm-gpio.sh` | `/usr/local/sbin/mmdvm-gpio` | 經 sysfs GPIO 控制 BOOT0／STM32 重置／RAK4630 重置／GPS 開關 |
| `gpio/mmdvm-gpio-init.service` | `/etc/systemd/system/` | 開機時把這些線設到閒置狀態 |
| `mmdvm/MMDVM.ini` | `/etc/MMDVM-Host.ini` | MMDVM-Host 設定（上游已把設定檔和執行檔改名為 `MMDVM-Host`） |
| `mmdvm/MMDVM-Display.ini` | `/etc/MMDVM-Display.ini` | MMDVM-Display：TJC 螢幕用 `[Nextion] Port=modem` |
| `mmdvm/build.sh` | - | 安裝編譯相依套件，下載並編譯 MMDVM-Host 和 MMDVM-Display |
| `mmdvm/mmdvmhost.service`、`mmdvm/mmdvm-display.service` | `/etc/systemd/system/` | systemd 單元 |
| `mmdvm/flash-mmdvm-hs.sh` | `/usr/local/sbin/flash-mmdvm-hs` | 用 GPIO-A／GPIO-B 的 `stm32flash` 包裝腳本 |
| `fan/mmdvm-fan.sh`、`.service`、`.default` | `/usr/local/sbin/mmdvm-fan`、單元、`/etc/default/mmdvm-fan` | 溫度曲線：TMP102 -> EMC2301 PWM，hwmon 路徑在執行時依名稱尋找 |
| `mmdvm/build-gateways.sh` | - | 編譯開啟 `USE_GPSD` 的 DMRGateway 和 YSFGateway；還沒有設定檔時，安裝上游的範例 `.ini` 檔 |
| `mmdvm/setup-brandmeister.sh` | - | 在 `/etc/MMDVM-Host.ini` 和 `/etc/DMRGateway.ini` 設定呼號、DMR ID、頻率和 BrandMeister master（只有 DMR，就像接 BM master 的 Pi-Star 熱點） |
| `mmdvm/dmrgateway.service`、`mmdvm/ysfgateway.service` | `/etc/systemd/system/`（由 `build-gateways.sh` 安裝） | systemd 單元，未啟用 |
| `power/mmdvm-battery.sh`、`.service`、`.default` | `/usr/local/sbin/mmdvm-battery`、單元、`/etc/default/mmdvm-battery` | MAX17048 回報電池組電量低且沒有接充電器時，正常關機 |
| `gps/gpsd.default` | `/etc/default/gpsd` | gpsd 使用 `/dev/ttySC1`，唯讀 |
| `gps/mmdvm-gps-switch.sh`、`.service` | `/usr/local/sbin/mmdvm-gps-switch`、單元 | GPS 電源接通時重新啟動 RAK4630（研究文件 3.3） |
| `gps/chrony-gps-pps.conf` | `/etc/chrony/conf.d/mmdvm-gps-pps.conf` | chrony：經 gpsd SHM 取得 NMEA，加上 `/dev/pps0` |
| `meshtastic/README.md` | - | 主機與 RAK4630 的連線、首次開機步驟、STM32 燒錄說明 |
| `meshtastic/provision.sh` | `/usr/local/sbin/mmdvm-mesh-provision` | 研究文件第 10.3 節的 Meshtastic 設定 |
| `network/10-mmdvm-lan7500.link` | `/etc/systemd/network/` | 把 LAN7500（`smsc75xx`）的網路介面命名為 `lan0` |
| `network/60-mmdvm-lan.yaml` | `/etc/netplan/` | `lan0` 使用 DHCP |
| `network/kernel-config.fragment` | - | 以上所有東西需要的 kernel 選項 |
| `install.sh` | - | 把檔案複製到定位 |

## 主機介面

對照過 Bubblegum-96 硬體手冊 V1.1（第 5 節，LS 接頭表）和 mainline `s900-bubblegum-96.dts` 的 `gpio-line-names` 表；兩者彼此一致，也與研究文件第 3.4 節一致。

| LS 腳位 | 96Boards | S900 | Linux | 用途 |
|---|---|---|---|---|
| 5 / 7 | UART0 TxD / RxD | UART2, GPIOB15 / GPIOB14 | `/dev/ttyOWL2` | MMDVM 數據機（STM32 USART1），115200 |
| 11 / 13 | UART1 | UART5, GPIOA27 / GPIOA25 | `/dev/ttyOWL5` | console（不變） |
| 15 / 17 | I2C0 SCL / SDA | I2C1, GPIOB22 / GPIOB23 | `&i2c1` | 0x48 SC16IS752、0x2f EMC2301、0x49 TMP102、0x40 INA226、0x36 MAX17048、0x6a BQ25895 |
| 23 | GPIO-A | GPIOA0 | line 0 | 輸出：STM32 BOOT0 |
| 24 | GPIO-B | GPIOA1 | line 1 | 輸出：STM32 NRST（低 = 重置） |
| 25 | GPIO-C | GPIOA2 | line 2 | 輸入：SC16IS752 IRQ |
| 26 | GPIO-D | GPIOA3 | line 3 | 輸入：充電 IC INT + 電量計 ALRT |
| 27 | GPIO-E | GPIOA4 | line 4 | 輸入：電源鍵請求（STM6601 INT） |
| 28 | GPIO-F | GPIOA5 | line 5 | 輸出：電源保持，只在 JP2 接 2-3 時 |
| 29 | GPIO-G | GPIOA6 | line 6 | 輸出：RAK4630 重置（低 = 重置） |
| 30 | GPIO-H | GPIOA7 | line 7 | 輸入：GPS PPS |
| 31 | GPIO-I | GPIOA8 | line 8 | 輸入：GPS 電源開關狀態 |
| 32 | GPIO-J | GPIOA9 | line 9 | 輸入：EMC2301 ALERT（軟體沒有用到） |

六顆 I2C 裝置都在 TCA9406（U34）後面的 3.3 V 常時供電匯流排上，主機都存取得到。nRF52840 不在這條匯流排上。

`/dev/ttySC0` = SC16IS752 通道 A = Meshtastic 序列 API，`/dev/ttySC1` = 通道 B = GPS NMEA（只收）。

## 安裝順序

這些腳本是在 Windows 上寫的，在工作目錄裡沒有執行權限位元：用 `bash <script>` 執行，或先 `chmod +x`。

1. **Kernel。** 把 `network/kernel-config.fragment` 合併進 kernel 設定後重新編譯。DTB 要帶符號編譯：`make DTC_FLAGS=-@ dtbs`。
2. **裝置樹。** 執行 `KSRC=<kernel tree> dts/build-dtbo.sh <base.dtb>`，把合併後的 DTB 裝到 bootloader 載入它的位置（或在 U-Boot 套用 `.dtbo`，或在板子的 `.dts` 裡 include 這個檔案；見疊加檔開頭的說明）。重新開機。檢查：`/dev/ttyOWL2`、`/dev/ttySC0`、`/dev/ttySC1`、`/dev/pps0`、`sensors`、`ls /sys/class/power_supply`。
3. **套件。**
   `sudo apt-get install -y mosquitto mosquitto-clients stm32flash gpsd gpsd-clients chrony pps-tools lm-sensors i2c-tools gpiod pipx`
4. **編譯 MMDVM。** `mmdvm/build.sh`
5. **檔案。** `sudo ./install.sh --dry-run`，然後 `sudo ./install.sh`
6. **GPIO 預設狀態與風扇。** `sudo systemctl enable --now mmdvm-gpio-init mmdvm-fan`
7. **STM32 韌體**（數據機是空白的話）：
   `sudo flash-mmdvm-hs mmdvm_hs_dual_hat_fw.bin`
8. **MMDVM。** 編輯 `/etc/MMDVM-Host.ini`（呼號、DMR ID、頻率、色碼），然後 `sudo systemctl enable --now mosquitto mmdvmhost mmdvm-display`。看 log：`mosquitto_sub -t 'host/#' -v` 和 `journalctl -u mmdvmhost`。
9. **GPS／時間。** `sudo systemctl enable gpsd && sudo systemctl restart gpsd chrony`；用 `gpsmon`、`sudo ppstest /dev/pps0`、`chronyc sources` 檢查。
10. **Meshtastic。** `pipx install meshtastic`，然後照 `meshtastic/README.md` 做（第一次設定要經 USB 或 BLE）。
11. **網路。** `sudo netplan try`；`ip link show lan0`。

## 熱點的兩種跑法：二選一

1. **精簡套件**（這個目錄裡除了 `pistar/` 以外的全部）：目前版本的 MMDVM-Host 加上 MMDVM-Display 和 DMRGateway，直接編輯檔案或用 `mmdvm/setup-brandmeister.sh` 設定。沒有網頁。
2. **Pi-Star 移植版**，在 `pistar/`：從原始碼編譯 Pi-Star 所跑的軟體（舊版、把 log 寫到檔案的 MMDVMHost，以及 Pi-Star 所附版本的各閘道器），Pi-Star 自己的儀表板和管理頁面在安裝時從上游下載，並改成適合這張板子。哪些能用、哪些被取代、哪些在這裡沒有，見 `pistar/README.md` 和 `pistar/FEATURES.md`。

兩者使用相同的單元名稱和執行檔，所以只能啟用其中一個；精簡套件的單元還在啟用狀態時，`pistar/install-pistar.sh` 會拒絕執行。裝置樹疊加檔、`gpio/`、`fan/`、`power/`、`gps/` 和 `network/` 兩者都需要。兩者都沒有在實機上跑過。

## 在 BrandMeister 上跑 DMR（從 Pi-Star 轉過來）

Pi-Star 本身是以映像檔發布，給 Raspberry Pi 和其他幾種板子用；沒有 Bubblegum-96 的版本，所以這個套件用手動方式做出相同的設定。重要的差異是：Pi-Star 跑的是舊版 MMDVMHost，它直接登入 BrandMeister master。目前的 MMDVM-Host 只跟本機的閘道器溝通，所以要經過 DMRGateway 連到 BrandMeister。

    bash mmdvm/build.sh
    bash mmdvm/build-gateways.sh
    sudo bash install.sh
    sudo bash mmdvm/setup-brandmeister.sh --callsign BX4XXX --id 4661234          --master 4501 --rx 433000000 --tx 438000000 --cc 1
    sudo systemctl enable --now mmdvm-gpio-init mosquitto dmrgateway mmdvmhost mmdvm-display

- `--master` 是你在 Pi-Star 裡用的 `BM_<number>_...` 項目的編號。BrandMeister 沒有列出台灣的 master（2026-11-16 查過）；最近的是 4501 南韓、4602 中國、5021 馬來西亞和 5151 菲律賓。
- 密碼是 BrandMeister SelfCare 裡的 Hotspot Security 密碼（沒開這個功能時是 `passw0rd`）。腳本會詢問密碼；除了 `/etc/DMRGateway.ini` 以外，不會存在任何地方。
- 腳本讓兩個時槽都通過所有通話群組和私人通話，並關掉範例檔裡的反射器模擬和 XLX 網路。靜態通話群組跟以前一樣在 SelfCare 管理。
- `mmdvm/MMDVM.ini` 只啟用 DMR；D-Star、YSF、P25、NXDN、POCSAG 和 FM 都關閉。
- 腳本在 PC 上對上游範例檔跑過，修改結果符合預期。沒有在 Bubblegum-96 上跑過，也沒有試過登入 master。

## 與研究文件不同的設計決定

- **風扇控制器。** 研究文件（3.4、4.2、7.3、8）寫的是 AMC6821。線路圖產生器和 BOM 用的是 EMC2301（0x2f）加 TMP102（0x49）。軟體以線路圖為準：使用 `microchip,emc2305` 驅動程式，並用一個服務取代 `fancontrol`（這個驅動程式沒有 `pwm1_enable`）。EMC2301 沒有溫度輸入，也沒有獨立運作的曲線，所以和 7.3 描述的 AMC6821 不同，主機當掉時風扇不會自己調速。
- **程式和檔案名稱。** 上游現在是 `MMDVM-Host`／`/etc/MMDVM-Host.ini`；主程式的設定檔裡已經沒有 `[Nextion]` 區段。螢幕只在 `MMDVM-Display.ini` 設定。
- **`gpio-poweroff` 有寫但停用**，因為板子的預設（JP2 1-2）沒有把 GPIO-F 接到任何東西。
- **GPIO-E 上的 `gpio-keys`** 是另外加的，讓電源鍵觸發正常關機（第 3.4 節列了這條線，第 8 節沒有列對應的軟體）。
- **疊加檔裡沒有 `gpio-line-names`**：mainline 已經把 LS 的線命名為 `GPIO-A` .. `GPIO-L`，而疊加檔只能整個取代那張 146 項的表。
- **`gpio/`** 不在研究文件的軟體清單裡。會有它，是因為下面說明的浮接輸入。

## 未測試／假設

全部都未測試。下面列的是最可能出錯或需要決定的項目；每一項在檔案裡都有對應的 `TODO` 或註記。

裝置樹（`dts/mmdvm-mesh-overlay.dts`）

1. 從沒編譯過。語法和 `&{/aliases}`／`&{/}` 的處理都未驗證。
2. 使用者映像檔的開機流程不明；疊加檔的套用方式（編譯時用 `fdtoverlay`、U-Boot `fdt apply`，或靜態 include）由使用者選擇。前兩種方式的基礎 DTB 需要 `-@`。
3. `uart2` 沒有 pinctrl 項目：`pinctrl-s900.c` 對 RX/TX 腳只有一個 `uart2_dummy` 群組。假設這代表這些腳不需要 mux 設定。
4. `owl-uart` 需要 `serial2` 別名；已經透過 `&{/aliases}` 加上。
5. `owl-uart` 在 115200 的鮑率準確度不明（它把 UART 時脈設為 8 x 鮑率）。
6. SC16IS752 的中斷在 S900 GPIO 控制器上設為 `IRQ_TYPE_LEVEL_LOW`。
7. `ttySC0`／`ttySC1` 和 `pps0` 的編號假設沒有其他同類裝置。
8. EMC2301：推挽 PWM、26 kHz、正常極性、低側開關 3 線風扇；工作週期低於 100 % 時，轉速讀值可能不能用。
9. BQ25895 的充電參數（4.208 V、3.008 A、256 mA 終止與預充電流）是暫定值，要依實際裝的電池設定。驅動程式會關掉晶片的看門狗，所以主機關機時這些設定仍然有效。
10. MAX17048 沒有中斷：它和充電 IC 共用 GPIO-D，兩個驅動程式都沒有要求共用 IRQ。它的低 SOC 警示沒有用到。
11. `gpio-keys` 搭配 `pinctrl-owl` 模擬的雙緣中斷，處理 20-44 ms 的脈衝。
12. `gpio-poweroff`（JP2 2-3）：PS_HOLD 必須在 STM6601 的 tON_BLANK（最少 5.6 s）內變高；kernel 驅動程式 probe 的時間太晚，除非 bootloader 會驅動 GPIO-F，或焊上 C142／R124。和使用者 kernel 裡既有的 PMIC 關機處理程序之間的互動不明。
13. 預設的斷電路徑（JP2 1-2）要靠 PMIC 在關機時把 +1V8 關掉，以及開機時 +1V8 在 tON_BLANK 內上來（研究文件 16.10）。兩者都不是軟體能處理的，也都沒有量過。

GPIO（`gpio/`）

14. 需要 `CONFIG_GPIO_SYSFS`（有 `CONFIG_GPIO_SYSFS_LEGACY` 的話也要開）。晶片是透過 `gpiochipN/device/of_node/compatible` 找的；這個 sysfs 路徑是假設的。
15. 假設 `stm32flash` 執行後，原本已經 export 的 GPIO 仍然保持 export。

MMDVM（`mmdvm/`）

16. `MMDVM.ini` 的暫定值：`Callsign=N0CALL`、`Id=1234567`、`RXFrequency=0`、`TXFrequency=0`、`ColorCode=1`。呼號是 `N0CALL` 時，服務單元會拒絕啟動。頻率為 0 時韌體的行為沒有確認過。
17. `[DMR Network] Enable=0`：這個套件不安裝閘道器（DMRGateway 等），所以在加裝之前，熱點只有射頻功能。
18. 螢幕資料路徑（`Port=modem` -> MQTT -> MMDVM-Host -> STM32 USART2 -> TJC）是從上游原始碼看來的；從沒看過它搭配 TJC X5 實際運作。沒有現成的 800x480 TJC 畫面檔。沒有安裝 MMDVM-Info。
19. `build.sh` 的相依套件清單是從上游的 Makefile 和 include 整理出來的；這裡沒有在 arm64 上編譯過。
20. 燒錄：`ttyOWL2` 用 8E1，GPIO 時序照抄韌體的 Raspberry Pi 腳本。

風扇（`fan/`）

21. 曲線數值（30 / 33 / 45 degC、PWM 90..255、充電時 150）是猜的。TMP102 量的是出風口的空氣，不是 SoC。
22. 判斷充電狀態用的 power supply 名稱萬用字元 `*bq25890*` 是假設的。

GPS（`gps/`）

23. 主機不能設定 GPS（只收）。鮑率（9600）和 NMEA 語句取決於 Meshtastic 韌體的設定。
24. gpsd 選項 `-s 9600`：假設 Ubuntu 24.04 的 gpsd 有這個選項。
25. chrony 對 NMEA 設的 `offset 0.2` 是猜的，需要校正。假設 Ubuntu 給 chrony 的 AppArmor 設定檔允許存取 `/dev/pps0`。
26. GPS 開關關閉、Meshtastic 關機，或（可能）Meshtastic 讓接收機省電時，都沒有 GPS 資料。

Meshtastic（`meshtastic/`）

27. 第一次設定不能用 `/dev/ttySC0`（這條連線要靠序列模組啟用）；至少要用一次 USB（J43）或 BLE。
28. `--gps-always-on`（`position.gps_update_interval 5`）是為了讓接收機保持供電而猜的做法，未驗證。
29. 序列模組的腳位 19 / 20、115200 取自研究文件 10.2 / 10.3。
30. `gps/mmdvm-gps-switch.sh`：GPIO-I 反映的是 GPS 電源，韌體自己關掉 GPS 時它也會掉，所以監看程式只在 0 -> 1 的邊緣重新啟動 MCU，而且最多每 120 s 一次。Meshtastic 到底需不需要這次重新啟動並不清楚（設 `RESET_MESH=0` 就只記錄）。

網路（`network/`）

31. S900 的 USB host 不在 mainline 裡；LAN7500 要靠使用者的 kernel 修補，以及高速接頭上的 USB 埠能正常運作。
32. `.link` 檔是依驅動程式（`smsc75xx`）比對，也就是任何 LAN75xx 網卡都會符合。EEPROM（U64）空白時，每次開機的 MAC 位址都是隨機的，直到設定 `MACAddress=` 或燒錄 EEPROM 為止。
33. netplan 檔裡沒有設定 renderer。

後來加的（`power/`、閘道器）

34. `power/mmdvm-battery.sh` 假設 `max17040_battery` 驅動程式提供 `capacity` 和 `voltage_now`，而且充電中的電池組會回報 `Charging` 或 `Full`。門檻（8 %、3250 mV、間隔 30 s 連續三次讀值）是初始值。`DRY_RUN=1` 只記錄、不關機。
35. `mmdvm/build-gateways.sh` 用 `sed` 把上游 Makefile 切換到 `-DUSE_GPSD` 那幾行；上游如果改了那幾行，腳本會停下來。範例 `.ini` 檔除了 `[GPSD] Enable=1` 以外都照原樣使用：呼號、ID、網路和密碼要自己設定。

完全沒有提供的

36. 長期插市電時把充電電壓降到 4.1 V、INA226 記錄、MMDVM-Info、D-Star／P25／NXDN 閘道器。

## 撰寫期間對硬體的觀察

這些是關於 `hardware/` 和 `docs/` 的，這個套件不會修改它們。

- **GPIO-A、-B、-G 的浮接輸入：這個套件寫完之後已在硬體上修正**（GPIO-A 加 R57 100k 到 GND，GPIO-B／-G 加 R58／R59 100k 到 +1V8_HOST）。原本的發現留作紀錄：U22（BOOT0 電壓轉換器）、U23（STM32 NRST 緩衝器）和 U26（RAK4630 重置緩衝器）的輸入直接接主機 GPIO，沒有上下拉電阻。從主機上電到 `mmdvm-gpio init` 執行之前，除非 S900 的腳位有內部上下拉（沒有查），這些輸入的狀態是不確定的。可能的影響：STM32 被卡在重置或開進 bootloader，以及常時供電的 RAK4630 在主機開機時被重置。在 LS_GPIO_A 加下拉、在 LS_GPIO_B 和 LS_GPIO_G 加上拉（到 +1V8_HOST），就不必依賴軟體。
- **風扇控制器**：研究文件原本寫 AMC6821，之後已經改成線路圖和 BOM 上的 EMC2301 + TMP102。
- **充電 IC 的 INT 和電量計的 ALRT 共用 GPIO-D**；mainline 驅動程式不能共用這個中斷。
- **乙太網路 EEPROM**：研究文件 11.5／13.2 寫「沒有 EEPROM」；線路圖上有 U64（93LC66A），是後來加的（第 14 節）。
- **研究文件 11.1** 仍然寫 `r8152`／`smsc95xx` 驅動程式；實際裝的 LAN7500 用 `smsc75xx`（13.2 是對的）。
- **腳位對應**：研究文件 3.4、硬體手冊和 mainline 裝置樹之間沒有發現不一致。

## 參考來源

- Bubblegum-96 硬體手冊 V1.1，第 5 節：
  <https://github.com/96boards/documentation/tree/master/consumer/bubblegum-96/hardware-docs>
- mainline 的 `arch/arm64/boot/dts/actions/s900-bubblegum-96.dts`、`s900.dtsi`、`drivers/pinctrl/actions/pinctrl-s900.c`、`drivers/tty/serial/owl-uart.c`，以及疊加檔裡引用的 binding 檔（torvalds/linux master，2026-11-16）。
- <https://github.com/g4klx/MMDVM-Host>（`MMDVM-Host.ini`、`Makefile`）、<https://github.com/g4klx/MMDVM-Display>（`MMDVM-Display.ini`、`README.md`）。
- <https://github.com/juribeparada/MMDVM_HS>（`configs/MMDVM_HS_Dual_Hat.h`、`README.md`、`scripts/install_fw_hsdualhat.sh`）。
- <https://github.com/meshtastic/protobufs>（`module_config.proto`）。
