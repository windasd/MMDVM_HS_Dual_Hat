# Bubblegum-96 擴充板上的 Pi-Star

一支安裝腳本，在 Ubuntu 24.04 arm64 上組出一套 **Pi-Star 4.3.10** 系統——網頁儀表板（Dashboard）和它的設定、管理頁面，管理腳本，以及這些腳本所搭配的 MQTT 之前版本 MMDVMHost／閘道器程式——給 r3.0 研究版的板子使用（MMDVM_HS 雙工板在 `/dev/ttyOWL2`，TJC 螢幕接在數據機後面，GPS 走 gpsd）。

> ## 未測試（UNTESTED）
>
> **這個目錄裡的東西都沒有在目標機器上執行過。** 板子從來沒有做出來，手邊沒有 Bubblegum-96，也沒有 Ubuntu arm64 的機器。沒有編譯過任何程式，沒有用瀏覽器開過任何頁面，沒有啟動過任何服務，也沒有登入過 BrandMeister。
>
> 實際做過的（在一台裝了 Git Bash 的 Windows PC 上）：
> - 這裡每一支腳本都跑過 `bash -n`（全部通過）；
> - `install-pistar.sh --dry-run` 能跑到結束；
> - 把安裝腳本的修改套用到兩個鎖定版本 Pi-Star repo 的全新 clone 上：`patches/` 裡的修補檔能套用，sed 修改都剛好找到預期的那幾行，改過的上游 bash 腳本仍然通過 `bash -n`；
> - 安裝腳本取出的 sudoers 檔通過 `visudo -c -f`；
> - 用 Pi-Star 預設的 `mmdvmhost` 檔跑過 `board/pistar-b96-presets`；
> - 安裝腳本的檔案輔助函式（安裝／保留／移到一旁／清單）和移除腳本的「刪除並還原」迴圈，在一個暫存目錄上跑過，變更擁有者的部分用空函式代替。
>
> 這些測試用的上游暫時 clone 事後已經刪除。
>
> 修補後的 PHP 檔**沒有跑過 `php -l`**：手邊沒有 PHP 直譯器。修補檔只在一個檔案裡加了一個 `if` 區塊（只有一個 `shell_exec` 呼叫）。
>
> 各項假設列在下方的「假設」一節。請做好除錯的準備。

## 授權狀況

GitHub 上 `AndyTaylorTweet/Pi-Star_DV_Dash`、`Pi-Star_Binaries_sbin` 和 `Pi-Star_v43_Binaries_Bin` **沒有標示授權**。因此：

- **這個 repo 裡沒有任何 Pi-Star 的東西。** 沒有儀表板的檔案、沒有腳本、沒有設定檔、沒有韌體。
- `install-pistar.sh` 從上游把它們下載到你的板子上，取 `pins.conf` 裡指定的 commit，並在板子上修改。修改內容是安裝腳本裡的幾條 `sed` 指令（每條都附理由），加上 `patches/` 裡的一個 unified diff。
- `board/` 裡的檔案是這個 repo 自己寫的，用來取代在這裡無法運作的 Pi-Star 腳本。它們只沿用上游的檔案*名稱*（儀表板依名稱呼叫它們），其他什麼都沒有沿用。
- 無線電程式（g4klx、juribeparada、on7lds；GPL）在板子上從原始碼編譯。

Pi-Star 是 Andy Taylor（MW0MWZ）和其他貢獻者的作品：<https://www.pistar.uk/>。這不是 Pi-Star 的發行版，也不受 Pi-Star 專案支援；遇到問題請不要拿到 Pi-Star 的支援群組詢問。

## 這個套件或最小套件：二選一

`software/bubblegum96/` 有兩套給同一個數據機用的無線電軟體：

| | 最小套件（`../mmdvm`） | Pi-Star（這個目錄） |
|---|---|---|
| MMDVM 主機程式 | 目前的 `MMDVM-Host`（MQTT） | 2025-09-25 的 `MMDVMHost`（log 檔、內建 Nextion 驅動、直接登入 DMR 主控站） |
| 螢幕 | `MMDVM-Display` | MMDVMHost 本身，`Port=modem` |
| BrandMeister | 經 DMRGateway，`setup-brandmeister.sh` | MMDVMHost 直接連線，在網頁上設定 |
| 設定 | 編輯 ini 檔 | 網頁 |
| 檔案 | `/etc/MMDVM-Host.ini`、`/etc/DMRGateway.ini` | `/etc/mmdvmhost`、`/etc/dmrgateway`、... |

兩者不能同時執行：都使用 `/dev/ttyOWL2`，也都定義了 `mmdvmhost.service`、`dmrgateway.service` 和 `ysfgateway.service`。

- 只要最小套件有任何一個 unit 是啟用或執行中，`install-pistar.sh` 就**拒絕執行**，並告訴你要停用哪些。
- 如果最小套件已安裝但已關閉，它的三個 unit 檔和 `DMRGateway`／`YSFGateway` 執行檔會被移到 `/var/lib/pistar-b96/displaced/`，`uninstall-pistar.sh` 會把它們放回去。`/etc/MMDVM-Host.ini`、`/etc/DMRGateway.ini`、`MMDVM-Host`、`MMDVM-Display` 和 mosquitto 都不會被動到。
- 之後如果再執行一次 `../install.sh`，它會在 `/etc/systemd/system` 重新建立最小套件的 `mmdvmhost.service`，蓋過 Pi-Star 的那一個；之後請再執行一次 `install-pistar.sh`（它會再把那個檔案移到一旁）。
- 兩者都需要 `../install.sh` 的**板子檔案**：device tree、`mmdvm-gpio` + `mmdvm-gpio-init.service`、`flash-mmdvm-hs`、風扇、電池、gpsd／chrony、網路。請先安裝這些。這裡的 Pi-Star 會呼叫 `mmdvm-gpio` 和 `flash-mmdvm-hs`。

## 安裝

1. Kernel、device tree 和板子檔案照 `../README.md` 的步驟 1-3、5、6 和 9 安裝（不包括 MMDVM 的編譯，也不要做 `enable ... mmdvmhost`）。確認 `/dev/ttyOWL2` 存在。
2. 把這個目錄複製到板子上，腳本要保持完整（LF 換行；用 git checkout 時，這裡的 `.gitattributes` 會處理）。
3. 先看看它會做什麼：

       bash install-pistar.sh --dry-run

4. 安裝（需要網路；在四核 Cortex-A53 上編譯要花一段時間）：

       sudo bash install-pistar.sh

   它會詢問一次網頁管理密碼（輸入時不顯示）。直接按 Enter 則先使用 Pi-Star 的預設密碼。

   選項：`--no-gpsd`（閘道器不使用 gpsd）、`--with-dstar`（另外編譯 ircDDBGateway；見 FEATURES.md）、`--with-firewall`（每次開機都執行 Pi-Star 的 iptables 腳本）、`--hostname pi-star`、`--skip-apt`、`--skip-build`。
5. 重新開機。
6. 數據機如果是空的，先燒錄韌體：`sudo flash-mmdvm-hs <firmware.bin>`。
7. 用瀏覽器開啟 `http://<board address>/`，照著 `configure-brandmeister.md` 操作。

再次執行安裝腳本是安全的：它只取代自己安裝過的檔案，保留所有既有的設定檔，而且只有在某個程式的鎖定版本改變時才重新編譯它。要換到較新的上游版本，就修改 `pins.conf` 再執行一次——這時也要重新確認那些修改仍然能套用（不能套用時安裝腳本會停下來）。

移除：`sudo bash uninstall-pistar.sh`（保留你的設定）或 `... --purge`。那裡也接受 `--dry-run`。

## 網頁登入

- 位址：`http://<board address>/`；管理頁面在 `/admin/` 底下。
- 使用者：**`pi-star`**。
- 密碼：安裝腳本詢問時你輸入的那個。如果你直接按了 Enter（或安裝腳本執行時沒有終端機）：就是 Pi-Star 眾所皆知的預設密碼 **`raspberry`**。
- **請修改密碼**，在 Configuration（設定）頁的最後一節（「Remote Access Password」）。使用預設密碼時，儀表板會顯示紅色橫幅，並把來自板子本身子網路以外的用戶端導到一個只能設定新密碼的頁面。儀表板不接受用 `raspberry` 當新密碼。
- 同一個動作也會設定 `pi-star` 帳號的 Linux 密碼。這個帳號在這裡只為了這個用途而建立，沒有登入 shell。
- 連線是未加密的 HTTP，和 Pi-Star 一樣。

## 安全性：網頁密碼的分量

儀表板透過 `sudo` 修改系統。安裝腳本給 `www-data` 的，是 Pi-Star 自 4.3.x 起自己使用的指令允許清單（`/etc/sudoers.d/pistar-dashboard`，從鎖定版本的 `pistar-upgrade` 取出，去掉唯讀重新掛載那一項），再加上一條它自己的指令（`/etc/sudoers.d/pistar-b96`）。它絕不會加入 `NOPASSWD: ALL`。

這份允許清單仍然包括改寫 `/etc/crontab`、把檔案安裝到 `/etc`、用 `chpasswd` 修改密碼、重新開機和關機。**知道網頁管理密碼的人，就能以 root 身分控制這台機器**，能以 `www-data` 身分執行指令的任何東西也一樣。DMR 網路的密碼以明文存在所有使用者都能讀取的檔案裡（`/etc/mmdvmhost`），每台 Pi-Star 都是如此。請像對待 Pi-Star 一樣對待這塊板子：放在可信任的區域網路內，不要把連接埠 80 轉送給它。

連接埠：安裝腳本不開放任何連接埠，也不安裝任何防火牆規則，除非你加上 `--with-firewall`；這個選項會原封不動地執行 Pi-Star 自己的 `pistar-firewall`。uPnP 連接埠對應在你於儀表板上打開之前都是關閉的。

## 安裝腳本對系統做的變更

| 位置 | 內容 |
|---|---|
| 套件 | nginx、php-fpm（+ cli、mbstring、zip）、apache2-utils、git、build-essential、zip／unzip、psmisc、netcat-openbsd、net-tools、wireless-tools、iw、wpasupplicant、miniupnpc、iptables、stm32flash、gpsd + libgps-dev（使用 `--with-dstar` 時另加 libwxgtk3.2-dev） |
| `/var/www/dashboard` | 儀表板，鎖定版本的 git checkout，已修改 |
| `/opt/pistar-b96/src` | 其他原始碼樹 |
| `/usr/local/sbin` | Pi-Star 腳本和包裝腳本、`board/` 裡的替代版本 |
| `/usr/local/bin` | `MMDVMHost`、`RemoteCommand`、閘道器、parrot 程式、跨模式程式、`MMDVMCal`、`NextionDriver`、`platformDetect.sh`、`config_clean.zip`、`firmware/hs_dual_hat.bin` |
| `/usr/local/etc` | `RSSI.dat`、語音提示、主機清單／ID 檔、`pistar-b96-pins` |
| `/etc` | `mmdvmhost`、`dmrgateway`、...（Pi-Star 預設值，只在檔案不存在時）、`pistar-release`、`sudoers.d/pistar-dashboard`、`sudoers.d/pistar-b96`、`cron.d/pistar-b96`、`logrotate.d/pistar-b96`、`udev/rules.d/99-pistar-b96-modem.rules`、`nginx/sites-available/pi-star`、`php/<ver>/fpm/conf.d/99-pistar-hardening.ini`、`netplan/61-pistar-b96-wlan.yaml`、`wpa_supplicant/wpa_supplicant.conf`、`/etc/crontab` 裡一行被註解掉的設定 |
| `/lib/systemd/system` | 每個 Pi-Star 常駐程式的 `<name>.service` + `<name>.timer`、`nextiondriver`、`pistar-watchdog`、`pistar-upnp`（停用）、`pistar-b96-wifi.path`／`.service` |
| `/lib/crda/db.txt` | Wi-Fi 頁面用的國家代碼 |
| `/var/www/.htpasswd` | 管理密碼的雜湊值，權限 600、`www-data` |
| `/var/log/pi-star` | log，`root:mmdvm` 775 |
| 使用者 | `mmdvm`（沒有時才建立）、`pi-star`（沒有登入 shell） |
| 移到一旁 | nginx 的 `sites-enabled/default`；最小套件的 unit 和執行檔 |
| `/var/lib/pistar-b96` | 以上全部的清單（manifest）、被移開的原檔、編譯標記 |

針對這塊板子的調整，每一項都是 `install-pistar.sh` 裡一個附註解的函式：

| 調整 | 函式 | 做法 |
|---|---|---|
| 唯讀根檔案系統（`rpi-rw`／`rpi-ro`、`mount -o remount,ro`） | `neutralise_remount_ro`、`board/rpi-rw`、`board/rpi-ro` | 儀表板和腳本裡的每個 `remount,ro` 都改成 `true`；這兩個指令什麼都不做 |
| 數據機埠 | `adapt_modem_port`、`board/pistar-b96-presets` | udev：`/dev/ttyAMA0` -> `ttyOWL2`，群組 `mmdvm` |
| 平台字串 | `board/platformDetect.sh` | device tree 的 model |
| CPU 溫度 | `adapt_dashboard`（2）、`board/pistar-b96-temp` | `thermal_zone0`，沒有的話用 TMP102 |
| Wi-Fi | `adapt_wifi` | `wpa_supplicant@wlan0` 使用 Pi-Star 的檔案、netplan DHCP、用 path unit 觸發重新載入 |
| 數據機韌體燒錄 | `board/pistar-modemupgrade` | `flash-mmdvm-hs` 的包裝腳本 |
| 數據機重置／偵測 | `board/pistar-mmdvmhshatreset`、`board/pistar-findmodem` | `mmdvm-gpio`；不做探測 |
| 螢幕 | `board/pistar-b96-presets` | `Port=modem`、`ScreenLayout=3` |
| GPS | `build_radio`（`USE_GPSD`）、presets | 閘道器直接跟 gpsd 溝通；不使用 MobileGPS |
| 更新／升級／回復原廠設定 | `board/pistar-update`、`-upgrade`、`-factory-reset` | 不做 git pull，不用 apt |
| 看門狗 | `board/pistar-watchdog` | 用 bash 取代 Python 2 |
| 每日排程 | `cron_and_logs`、`board/pistar-b96-daily` | 主機清單檔、清理 log |
| 防火牆 | `adapt_firewall` | 只在加上 `--with-firewall` 時 |
| 主機名稱 | `adapt_hostname` | 只在加上 `--hostname` 時 |
| 還原頁面 | `patches/dashboard/0001-...` | 還原之後套用板子的預設值 |

## 假設

以下每一項都沒有驗證過。依照造成第一次開機無法正常運作的可能性排序。

**網頁**

1. 鎖定版本的儀表板能在 PHP 8.3 下執行（Pi-Star 4.3 用的是它 Debian 基底的 PHP，推測是 8.2）。
2. 在 Ubuntu 24.04 上，從 php-fpm 執行 `sudo` 可以運作（`php8.3-fpm` unit 沒有 `NoNewPrivileges`，也沒有沙箱限制），而且 php-fpm 的 `/tmp` 和經 sudo 執行的指令看到的 `/tmp` 是同一個。
3. Pi-Star 的 sudoers 允許清單用 `/bin/...`、`/sbin/...` 指定指令；在 Ubuntu 上這些目錄是指向 `/usr` 的符號連結。假設 sudo 會認得它們（它比對的是檔案本身，不只是路徑字串），這在 Pi-Star 自己採用 merged-`/usr` 的 Debian 上也必須成立。
4. sbin 鎖定版本的允許清單，涵蓋 dash 鎖定版本儀表板的每一個 sudo 呼叫（兩者都是同一天的上游 HEAD）。
5. 這裡的 nginx 網站設定是從頭寫的；Pi-Star 自己的沒有公開。`snippets/fastcgi-php.conf` 和 `/run/php/php<ver>-fpm.sock` 是 Ubuntu 的命名。
6. HTTP basic-auth 的帳號密碼會傳到 PHP（`PHP_AUTH_PW`），預設密碼檢查需要它。

**無線電程式**

7. 所有鎖定版本的原始碼都能用 Ubuntu 24.04 的 GCC 13 在 arm64 上編譯，閘道器也能搭配它的 libgps 編譯。沒有編譯過任何東西。如果 `USE_GPSD` 的編譯失敗，改用 `--no-gpsd`。
8. MMDVMHost 的一般 `Makefile`（沒有 OLED／HD44780／WiringPi）是正確的那一個。Pi-Star 的執行檔有連結 WiringPi 和 ArduiPi_OLED。
9. MMDVMCal、MMDVM_CM 系列程式、NextionDriver 和 ircDDBGateway 是從*推測出來的* commit 編譯的（`pins.conf`）。
10. 在 make 指令列上傳入 `CFLAGS=`／`LIBS=`，就能選用閘道器 Makefile 的 gpsd 版本，而且沒有副作用。
11. `--with-dstar`：g4klx/ircDDBGateway 能搭配 wxWidgets 3.2 編譯，執行檔會出現在安裝腳本複製的來源路徑上，而且選定的 `LOGDIR`／`CONFDIR`／`DATADIR` 和儀表板讀取的位置一致。

**服務**

12. systemd unit 是照著 `pistar-upgrade` 裡看得到的模式產生的；真正的 unit 沒有公開。假設一個 `Type=forking` 的 unit，若它的包裝腳本什麼都沒啟動就以 0 結束，最後會處於 inactive 狀態，而不會報錯。
13. MMDVMHost 在 `Daemon=1` 時會切換成使用者 `mmdvm`，而且只帶這個使用者的主要群組；udev 規則把數據機埠開放給這個群組。Pi-Star 映像檔是不是這樣做，並不清楚。
14. `/dev/ttyAMA0` 在 S900 的 kernel 上不是真實存在的裝置，所以這個別名可以使用。（如果存在，安裝腳本會停下來。）
15. tty 上的 udev `SYMLINK` 對 MMDVMHost、MMDVMCal 和 `stm32flash` 來說就夠了。
16. 在 `mmdvmhost.timer` 觸發（開機後 30 s）之前，`mmdvm-gpio-init.service` 已經把 BOOT0／NRST 設在閒置狀態。
17. 替代版看門狗的程序名稱，正是管理頁面用 `pgrep -f /usr/local/sbin/pistar-watchdog` 要找的名稱。

**數據機與螢幕**

18. Pi-Star 的 `hs_dual_hat.bin` 適用這塊板子：主機接 USART1、USART2 的序列透傳（serial repeater）已啟用、透傳鮑率等於 TJC 螢幕的 `bauds=`。這個檔案沒有檢查過。`stm32flash` 是否成功只靠結束碼判斷。
19. 舊版內建 Nextion 驅動的 `ScreenLayout=3` 送出的欄位，正是 `display/tjc8048x550` 畫面檔（為 MMDVM-Display 的 layout 3 繪製）所預期的。事後比對過兩份 `Nextion.cpp` 原始碼的指令字串：舊驅動沒有用到這個 layout 缺少的頁面或物件。但仍然沒有在螢幕上實際看過。
20. `UARTSpeed=115200` 是韌體的主機端速率。

**網路與資料**

21. `www.pistar.uk` 會提供主機清單／ID 檔給這個系統。沒有這些檔案，設定頁上的 DMR 主控站清單會是空的。
22. Wi-Fi：介面名稱已經是、或可以改名成 `wlan0`；netplan 在 networkd renderer 下接受把 Wi-Fi 介面列在 `ethernets` 底下；`wpa_supplicant@wlan0.service` 和 `netdev` 群組存在；`ifconfig`／`iwconfig` 的輸出就是頁面所解析的格式。Bubblegum-96 板上的 Wi-Fi 需要的驅動，你的 kernel 可能沒有。
23. `--with-firewall`：Pi-Star 的規則組（OUTPUT policy DROP）不會擋到這塊板子需要的東西（gpsd 在本機；chrony／NTP、apt 和 Meshtastic 工具沒有對照規則清單檢查過）。
24. M17Gateway、DAPNETGateway 和 APRSGateway 使用的範例 ini 檔（Pi-Star 自己的沒有公開）裡有設定頁預期的那些 key。

**其他**

25. `/sys/class/thermal/thermal_zone0` 可能不存在；這時儀表板上的「CPU Temp」是風扇出風口的 TMP102。
26. `pistar-calibration-start` 裡的 `nc -ulp` 在 `netcat-openbsd` 下可以用。
27. 儀表板的主機名稱欄位：`/etc/hosts` 裡有目前的主機名稱，而且開機時沒有任何東西（例如 cloud-init）會重設 `/etc/hostname`。
28. 從樹莓派 Pi-Star 的備份還原可以正常運作（修補檔會改寫的那些 key 除外）。

## 出問題時先看這裡

1. **nginx 錯誤 log**——`sudo tail -50 /var/log/nginx/error.log`。PHP 錯誤和每一個失敗的 `sudo` 呼叫的 stderr 都會寫到這裡。頁面空白或只畫出一半，幾乎都是 PHP 錯誤。
2. **sudo**——`sudo -l -U www-data` 必須列出 `PISTAR_DASH_ALL`。`journalctl -t sudo -n 50` 會顯示被拒絕的指令（「command not allowed」）——那表示允許清單有缺漏，或路徑對不上。`sudo visudo -c` 可以檢查這些檔案。
3. **Unit 名稱**——`systemctl list-unit-files 'mmdvmhost*' 'dmrgateway*'
   'pistar-*'`。`systemctl cat mmdvmhost.service` 必須顯示 `/lib/systemd/system` 裡的 unit，內容是 `ExecStart=/usr/local/sbin/mmdvmhost.service
   start`；如果顯示的是 `/etc/systemd/system/mmdvmhost.service`，內容是 `MMDVM-Host`，就是最小套件的 unit 蓋過了它。
4. **常駐程式為什麼沒有啟動**——手動執行包裝腳本：`sudo /usr/local/sbin/mmdvmhost.service start; echo $?`，接著把 `Daemon=0` 設好後，在前景執行 `sudo /usr/local/bin/MMDVMHost /etc/mmdvmhost`。呼號仍是 `M1ABC`、ID 仍是 `1234567`，或還沒套用任何數據機類型時，包裝腳本會不出聲地直接結束。
5. **Log 路徑**——儀表板讀的是 `/var/log/pi-star/MMDVM-<UTC
   date>.log`。`ls -l /var/log/pi-star`（必須是 `root:mmdvm`、775）；`/etc/mmdvmhost` 裡要有 `[Log] FilePath=/var/log/pi-star`、`FileRoot=MMDVM`，`FileLevel` 不能是 0。沒有檔案 = MMDVMHost 沒有在執行，或無法寫入。
6. **數據機埠**——`ls -l /dev/ttyOWL2 /dev/ttyAMA0`：第二個必須是指向第一個的符號連結，第一個必須是 `root:mmdvm` `crw-rw----`。`sudo pistar-findmodem` 會把兩者都印出來。
7. **PHP 服務**——`systemctl status php8.3-fpm nginx`；`sudo nginx -t`。
8. **安裝腳本做了什麼**——`/var/lib/pistar-b96/manifest`、`manifest-conf`、`displaced/`。

## 檔案

| 檔案 | 用途 |
|---|---|
| `install-pistar.sh` | 安裝腳本（`--dry-run`，選項見上文） |
| `uninstall-pistar.sh` | 移除安裝腳本記錄下來的東西（`--purge`、`--dry-run`） |
| `pins.conf` | 鎖定的 repo 和 commit，以及每一個是怎麼選出來的 |
| `patches/dashboard/*.patch` | 對鎖定版本儀表板的 unified diff，用 `git apply` 套用；只要有一個套用不上，安裝腳本就會停下來。（`patches/sbin/` 會套用到腳本上；目前沒有） |
| `board/` | 取代在這塊板子上無法運作的 Pi-Star 腳本，以及輔助工具 |
| `RESEARCH.md` | Pi-Star 系統由哪些部分組成，附上游的檔案與行號 |
| `FEATURES.md` | 每一項 Pi-Star 功能，以及它在這塊板子上的狀態 |
| `configure-brandmeister.md` | 在 BrandMeister 上使用 DMR 的初次設定 |
