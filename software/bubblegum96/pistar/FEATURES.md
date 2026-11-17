# Pi-Star 各項功能在 Bubblegum-96 上的狀態

**這份表格裡的項目都沒有試過。** 手邊沒有裝上這塊板子的 Bubblegum-96，也沒有 Ubuntu arm64 的機器；表中的狀態是從閱讀上游程式碼（RESEARCH.md）和 `install-pistar.sh` 對系統的設定推論出來的。「預期」的意思是「找不到不行的理由」，不是「看過它正常運作」。

狀態用語：

- **原樣**：上游程式碼照原樣執行；預期可以運作。
- **修改**：上游程式碼，加上安裝腳本做的修改（備註中寫明）。
- **替換**：由 `board/` 裡的檔案或其他機制負責這項工作。
- **不可用**：在這塊板子上無法運作；備註寫使用者實際會看到什麼。
- **未知**：取決於無法從程式碼判斷的事情。

## 儀表板（Dashboard）公開部分（`/`）

| 功能 | 狀態 | 備註 |
|---|---|---|
| 即時畫面：模式、TX／RX 狀態、頻率、數據機韌體、TCXO（`mmdvmhost/repeaterinfo.php`） | 原樣 | 解析 `/var/log/pi-star/MMDVM-<UTC date>.log`。需要 `FileLevel` 為 1 或 2，和 Pi-Star 的預設設定檔相同 |
| 閘道器活動／最近收聽（`mmdvmhost/lh.php`）、本地射頻活動（`localtx.php`） | 原樣 | 同一個記錄檔；名稱取自 `/usr/local/etc/DMRIds.dat`（需要成功更新過一次主機清單檔） |
| 左側的服務指示燈（綠／紅） | 原樣 | 對這裡建置的程式名稱執行 `pgrep`／`ps` |
| BrandMeister 連線面板（`bm_links.php`） | 原樣 | 透過 HTTPS 向 BM API 查詢你的 DMR ID |
| D-Star 面板（`dstarrepeater/*.php`：連結、最近收聽、CCS、StarNet） | 未知 | 只有加 `--with-dstar` 時才有；見下方 D-Star |
| POCSAG／DAPNET 訊息（`mmdvmhost/pages.php`） | 原樣 | 讀取 DAPNETGateway 的記錄檔 |
| 硬體資訊列：主機名稱、kernel、平台、CPU 負載、CPU 溫度 | 修改 | 平台：`board/platformDetect.sh`（device tree 的 model）。溫度：`board/pistar-b96-temp`；**顯示的是 TMP102 量到的出風口氣溫，標籤卻是「CPU Temp」**，除非 kernel 提供 `thermal_zone0`；兩者都沒有時顯示 0 |
| 自動重新整理（jQuery 計時器） | 原樣 | |
| JSON／API：`/api/last_heard.php`、`/api/index.php` | 原樣 | 不需要管理登入，和上游相同 |
| 語言包（`lang/*.php`，24 種語言，含 `chinese_tw`） | 原樣 | 在設定頁面選擇；存在 `config/language.php` |
| CSS／配色（`css/pistar-css.php`、`/etc/pistar-css.ini`） | 原樣 | |

## 管理頁面（`/admin/`）

| 功能 | 狀態 | 備註 |
|---|---|---|
| 登入（HTTP basic auth，使用者 `pi-star`） | 替換 | 由安裝腳本寫入的 nginx 站台設定；沿用同一個帳號密碼檔 `/var/www/.htpasswd` |
| 預設密碼警示橫幅與強制變更（`change_password_required.php`） | 原樣 | 變更網頁密碼（`htpasswd`）和 Linux 使用者 `pi-star` 的密碼（`chpasswd`）；在這裡這個使用者沒有登入 shell |
| 服務狀態列（MMDVMHost、DMRGateway、...、PiStar-Watchdog、PiStar-Remote、PiStar-Keeper） | 原樣 | `board/pistar-watchdog` 執行時，Watchdog 顯示為執行中。PiStar-Remote 和 PiStar-Keeper 永遠是紅色（不可用） |
| BrandMeister 管理（`bm_manager.php`：新增／移除靜態 TG、移除動態 TG） | 原樣 | 需要把你的 BM API 金鑰放在 `/etc/bmapi.key`（Expert > API Keys） |
| TGIF 管理、TGIF 靜態通話群組 | 原樣 | 需要 TGIF 金鑰 |
| YSF／P25／NXDN／M17 連結管理 | 原樣 | 使用 `sudo /usr/local/bin/RemoteCommand`（在這裡建置）；設定頁面存檔時，會在閘道器的設定檔加上 `[Remote Commands] Enable=1`（`admin/configure.php:3087-3156`） |
| D-Star 連結管理 | 未知 | 只有 `--with-dstar` 才有；使用 `remotecontrold` |
| 系統資訊（`sysinfo.php`）：記憶體、磁碟、程式版本 | 原樣 | 版本字串是上游的（`20250828`），不是 Pi-Star 的 `..._PS4`；沒有建置的程式顯示空白 |
| 即時數據機記錄（`live_modem_log.php`）、下載記錄檔 | 原樣 | |
| 電源：重新開機、關機（`power.php`） | 修改 | 移除 `remount,ro`；`sudo reboot`／`sudo shutdown -h now` 和上游相同。關機最後由板子的 PMIC／STM6601 行為決定（研究文件第 16.10 節） |
| 更新（`update.php` → `pistar-update`） | 替換 | `board/pistar-update`：只更新主機清單檔／ID 檔，並印出已安裝的鎖定版本。不做 `git pull`，不用 `apt` |
| 升級（`expert/upgrade.php` → `pistar-upgrade`） | 不可用 | `board/pistar-upgrade` 會在頁面顯示的記錄檔寫入「Upgrade is not available on this board」。版本維持 4.3.10 |
| 備份（`config_backup.php`，下載 zip） | 原樣 | 包含 Wi-Fi 設定檔和 API 金鑰；`/etc/dhcpcd.conf` 不存在，頁面會略過 |
| 還原（上傳 zip） | 修改 | `patches/dashboard/0001-...`：安裝檔案之後，把這塊板子的數據機埠、UART 速率和 `[Nextion] Port=modem` 寫回去。可以還原樹莓派上的備份；備份裡的**主機名稱**和 `/etc/hosts` 也會一起還原（上游的行為）。樹莓派備份裡的固定 IP（`dhcpcd.conf`）會安裝成檔案，但沒有作用 |
| 恢復原廠設定（設定頁面上的按鈕） | 替換 | `board/pistar-factory-reset`：預設設定取自 `config_clean.zip`，再加上這塊板子的預設值。不會重設儀表板／腳本（它們是鎖定版本），也不會重設管理密碼 |
| 校正（`calibration.php`，透過本機 UDP 主控台使用 MMDVMCal） | 未知 | MMDVMCal 有建置（鎖定版本為推定）。`pistar-calibration-start` 串接 `nc -ulp ... -s ...` 和 `script`；Ubuntu 的 `netcat-openbsd` 可能不接受這種參數寫法 |

## 設定頁面（`/admin/configure.php`）

| 區段 | 狀態 | 備註 |
|---|---|---|
| Control Software：MMDVMHost／DStarRepeater、Simplex／Duplex | 原樣 | 選 MMDVMHost + Duplex Repeater。DStarRepeater：不可用（程式沒有建置；它是給非 MMDVM 數據機用的） |
| MMDVMHost Configuration：模式開關 DMR／D-Star／YSF／P25／NXDN／M17／POCSAG、跨模式、保持時間 | 原樣 | 跨模式程式 YSF2DMR、YSF2NXDN、YSF2P25、DMR2YSF、DMR2NXDN 有建置（鎖定版本為推定）。NXDN2DMR 也有建置，但沒有 `/etc/nxdn2dmr`（`config_clean.zip` 裡也沒有），所以頁面不會提供這個選項 |
| MMDVM Display Type／Port／Nextion Layout | 原樣 | 安裝腳本已預先設好：`Nextion`、埠 `modem`、版面 `ON7LDS L3`（= `ScreenLayout=3`）。OLED／HD44780／TFT Serial／LCDproc：不可用（沒有這些硬體；MMDVMHost 建置時不含這些功能） |
| 一般設定：呼號、CCS7／DMR ID、頻率、位置、URL | 原樣 | |
| Radio/Modem Type | 原樣 | 使用「**MMDVM_HS_Duplex_Hat (DB9MAT, DF2ET & DO7EN) for Pi (GPIO)**」（`mmdvmhsdualhatgpio`）。頁面寫入的是 `/dev/ttyAMA0`；在這裡這個名稱是 `/dev/ttyOWL2` 的 udev 別名。其他類型也能選，但描述的是這塊板子上沒有的硬體 |
| 節點類型（公開／私人）、APRS 主機、時區、儀表板語言 | 原樣 | 時區：`timedatectl set-timezone` |
| 主機名稱欄位 | 原樣 | 用 sed 修改 `/etc/hostname` 和 `/etc/hosts`，重新開機後生效。使用 cloud-init 的映像檔可能會在開機時把名稱重設回去（`preserve_hostname`） |
| DMR：主控站、BM Hotspot Security、ESSID、色碼、EmbeddedLCOnly、DumpTAData | 原樣 | 見 `configure-brandmeister.md` |
| 經由 DMRGateway 的 DMR（BM + DMR+ + XLX + TGIF） | 原樣 | DMRGateway 以 Pi-Star 執行檔所用的 commit 建置 |
| D-Star（反射器、RPT1/2、ircDDB、報時） | 未知 | 預設不建置。`--with-dstar` 會以 wxWidgets 3.2（而不是 Pi-Star 用的 3.0）建置 g4klx/ircDDBGateway（鎖定版本和目錄都是推定的）；從來沒有編譯過 |
| YSF（開機連線的主機、UPPERCASE 主機名稱、WiresX 透傳、YSF2DMR ...） | 原樣 | |
| P25、NXDN、M17 | 原樣 | M17Gateway 的設定檔是上游範例，不是 Pi-Star 的檔案：頁面上的 M17 欄位是否和它相符，**未知** |
| POCSAG／DAPNET | 未知 | `/etc/dapnetgateway` 是上游範例，不是 Pi-Star 的檔案 |
| APRSGateway | 未知 | `/etc/aprsgateway` 是上游範例 |
| Mobile GPS（序列埠上的 MobileGPS 常駐程式） | 不可用 | 這個區段被隱藏（沒有 `/etc/mobilegps`）。GPS 歸 `/dev/ttySC1` 上的 gpsd 使用。**改用** gpsd：閘道器建置時開啟 `USE_GPSD`，並加上 `Enable=0` 的 `[GPSD]` 區段；想把你的位置送到網路上，就在 Expert > DMR GW / YSF GW / NXDN GW 設 `Enable=1` |
| Wireless Configuration（掃描、新增網路、國家） | 修改／未知 | 和樹莓派上同一個檔案（`/etc/wpa_supplicant/wpa_supplicant.conf`），由 `wpa_supplicant@wlan0` 使用；存檔後由一個 path unit 重新載入；DHCP 由 netplan／networkd 負責；國家清單是產生出來的。需要 Wi-Fi 介面名稱是 `wlan0`（有一個 `.link` 檔會把唯一的 Wi-Fi 介面改名），而且你的 kernel 要有能用的 Wi-Fi 驅動。如果 NetworkManager 或 netplan 的 `wifis:` 區段已經在管 Wi-Fi，就整個略過 |
| 「Reset WiFi Adapter」 | 修改 | `ifdown`／`ifup` → `ip link set wlan0 down`／`up` |
| Auto AP（找不到已知網路時用 hostapd 建立存取點）、Auto AP SSID／PSK | 不可用 | 建立在 ifupdown、`wlan0_ap` 和 Pi-Star 的強制入口網頁（captive portal）之上。沒有安裝 hostapd，所以這些欄位被隱藏 |
| 防火牆區段：儀表板／ircDDB 遠端／SSH「Public」或「Private」、uPnP | 原樣 | 這些設定只控制**你路由器上的 uPnP 連接埠對應**。安裝後 uPnP 是關閉的（`/etc/crontab` 裡被註解掉的一行）；在頁面上開啟後，每 5 分鐘執行一次 `upnpc` |
| Pi-Star 防火牆（`pistar-firewall`，iptables） | 原樣，選用 | 除非安裝時加 `--with-firewall`，否則不啟用。它會清除所有規則，把 INPUT 和 OUTPUT 設為 DROP，再套用 Pi-Star 的允許清單；沒有評估過它對 Meshtastic、gpsd／chrony 或這塊板子其他服務的影響 |
| 遠端存取密碼／「pi-star」密碼 | 原樣 | 見管理頁面 |

## 專家頁面（`/admin/expert/`）

| 功能 | 狀態 | 備註 |
|---|---|---|
| 快速編輯：MMDVMHost、DMR GW、YSF GW、P25 GW、NXDN GW、DAPNET GW | 原樣 | 檔案先放在 `/tmp`，用 `sudo install` 安裝，再重新啟動服務 |
| 快速編輯：DStarRepeater、ircDDBGateway、TimeServer、StarNetServer | 未知 | 檔案存在（預設值）；程式只有 `--with-dstar` 時才有（DStarRepeater 完全沒有） |
| 完整編輯：DMR GW、RSSI Dat | 原樣 | |
| 完整編輯：PiStar-Remote | 不可用 | 檔案可以編輯；程式（Python 2）沒有安裝 |
| 完整編輯：WiFi（`wpa_supplicant.conf`） | 原樣 | 見 Wireless Configuration |
| 完整編輯：API 金鑰（BM、DAPNET、TGIF） | 原樣 | |
| 完整編輯：System Cron | 原樣 | 編輯的是 **Ubuntu 的 `/etc/crontab`**；這個移植版的 Pi-Star 排程工作在 `/etc/cron.d/pistar-b96`，不在那裡 |
| CSS Tool（`edit_dashboard.php`） | 原樣 | |
| 數據機韌體升級（`modem_fw_upgrade.php` → `pistar-modemupgrade`） | 替換 | `board/pistar-modemupgrade` 只提供一個項目 `hs_dual_hat`，透過 `/usr/local/sbin/flash-mmdvm-hs` 燒錄 Pi-Star 的 `hs_dual_hat.bin`（有檢查 MD5）。其他所有數據機 ID：「not available on this board」。那個韌體版本是否適用這塊板子：**未知** |
| `pistar-mmdvmhshatflash`、`pistar-zumspotflash`、...（舊的各板燒錄指令） | 不可用 | 上游已經沒有這些指令；由 `pistar-modemupgrade` 取代 |
| SSH Access（框架裡的 shellinabox） | 不可用 | 沒有安裝 shellinabox；頁面顯示「SSH Feature not yet installed」。請用一般的 SSH 用戶端 |
| Jitter 測試（`jitter_test.php` → `pistar-jittertest`） | 原樣 | |
| 升級 | 不可用 | 見管理頁面 |

## 命令列與背景程式

| 功能 | 狀態 | 備註 |
|---|---|---|
| `rpi-rw`、`rpi-ro` | 替換 | 什麼都不做，並印出訊息說明這一點；根檔案系統一直是可讀寫的 |
| 唯讀根檔案系統 | 不可用 | 儀表板和腳本裡的每一個 `mount -o remount,ro` 都改成 `true` |
| `pistar-update`、`pistar-upgrade`、`pistar-factory-reset` | 替換／不可用 | 同上 |
| `pistar-firewall`、`HostFilesUpdate.sh`、`pistar-bmapi`、`pistar-tgifapi`、`pistar-dapnetapi`、`pistar-link`、`pistar-ysflink`、`pistar-p25link`、`pistar-nxdnlink`、`pistar-mmdvmremote`、`pistar-jittertest`、`pistar-mmdvmhost-module` | 原樣 | |
| `pistar-mmdvmcal`、`pistar-calibration-start` | 修改 | 移除 `remount,ro`。從 `/etc/mmdvmhost` 讀取 `UARTPort`／`UARTSpeed` |
| `pistar-findmodem`、`pistar-mmdvmhshatreset`、`pistar-modemupgrade` | 替換 | 上游版本會驅動 GPIO 20／21，在 S900 上那是別的腳 |
| `pistar-watchdog` | 替換 | 用 bash 取代 Python 2；以逐步拉長間隔（back-off）的方式重新啟動停掉的常駐程式；不刪除系統記錄檔 |
| `pistar-remote`（射頻遙控）、`pistar-keeper` | 不可用 | Python 2 程式；Ubuntu 24.04 沒有 Python 2 |
| `pistar-nextiontext.py`、`pistar-oledtext.py` | 不可用 | 前者把資料寫到 `/dev/ttyAMA0`，當作那裡接著螢幕（在這裡那是數據機）；沒有 OLED |
| `pistar-expand`、`pistar-clone`、`pistar-bootconfig.sh`（開機分割區上的設定 zip／`wpa_supplicant.conf`）、`pistar-motdgen`、`pistar-sslgenerate`、`pistar-sendcw` | 不可用 | 屬於樹莓派映像檔的管理，或是沒有看得夠仔細、不足以安裝 |
| 每日工作（主機清單檔、清理記錄檔） | 替換 | `/etc/cron.d/pistar-b96` → `board/pistar-b96-daily`；不做 git pull，不下載 WiringPi；記錄檔保留 2 天 |
| 每小時工作（journal 清理、nginx 記錄檔截短） | 不可用 | 沒有重做；套用 Ubuntu 的 journald 和 logrotate 設定 |
| 記錄檔放在 tmpfs | 不可用 | `/var/log/pi-star` 在根檔案系統上 |
| 從 www.pistar.uk 下載主機清單檔（host files） | 未知 | 上游腳本，沒有修改；伺服器會不會把這些檔案提供給這個系統，不知道 |
| NextionDriver | 原樣 | 有建置（鎖定版本為推定），unit 已安裝；只有螢幕埠設為 `/dev/ttyNextionDriver` 時才會執行，而這塊板子不是這樣設定的 |
| 數據機埠上的 TJC 螢幕 | 未知 | `Port=modem`、`ScreenLayout=3`。`display/tjc8048x550` 的畫面檔是照 MMDVM-Display 的版面 3 畫的；MMDVMHost 舊的內建驅動是否送出相同的欄位，沒有逐行比對過 |
| GPS 位置／時間 | 替換 | 由板子套件提供的 gpsd 和 chrony，這個安裝腳本不會改動 |
| 風扇、電池關機、Meshtastic、乙太網路介面命名 | 替換 | 板子套件（`../install.sh`），和 Pi-Star 無關；沒有儀表板頁面 |
