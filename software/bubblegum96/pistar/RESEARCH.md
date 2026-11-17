# Pi-Star 系統由哪些部分組成

2026-11-16 從上游儲存庫讀取，版本是 `pins.conf` 裡鎖定的 commit。文中的檔名和行號都是指這些 commit：

| 簡稱 | 儲存庫 | Commit |
|---|---|---|
| dash | `AndyTaylorTweet/Pi-Star_DV_Dash` | `ca50804e`（2026-10-22，`config/version.php`：20261008） |
| sbin | `AndyTaylorTweet/Pi-Star_Binaries_sbin` | `3c736123`（2026-10-22） |
| bin | `AndyTaylorTweet/Pi-Star_v43_Binaries_Bin` | `f851131d`（2025-09-25） |

這裡的內容都不是在執行中的 Pi-Star 上觀察到的；也沒有解開過任何 Pi-Star 映像檔。如果某項事實只存在於映像檔中（因此不在任何儲存庫裡），就標為 **僅映像檔**，關於它的描述是從引用它的腳本推論出來的。

GitHub 上這三個 Pi-Star 儲存庫都沒有標示授權。它們的內容沒有任何一部分被複製到這個儲存庫；這裡描述的是檔名、路徑、選項名稱和腳本的行為，不轉載它們的文字。

## 1. 組成部分

- **儀表板**（Dashboard，dash）：`/var/www/dashboard` 裡的 PHP 頁面，是一個由 `pistar-update` 拉取更新的 git checkout。它從不直接和無線電程式溝通：它解析這些程式的**記錄檔**，並編輯它們的 **ini 檔**。
- **管理腳本**（sbin）：一個 git checkout，*本身就是* `/usr/local/sbin`（`sbin:pistar-update:176`，`git_update /usr/local/sbin`）。
- **程式**（bin）：一個 git checkout，*本身就是* `/usr/local/bin`：預先建置好的無線電程式、`platformDetect.sh`、`config_clean.zip`、`firmware/`、`Nextion/`，以及包裝腳本 `apt`、`apt-get`、`aptitude`、`dpkg`，它們會先把根檔案系統重新掛載為可讀寫，再呼叫真正的工具。
- **映像檔**：Raspberry Pi OS，唯讀根目錄、nginx、php-fpm、systemd unit 檔、`/etc/rc.local`、`/etc/crontab` 項目、tmpfs 掛載、使用者帳號。**僅映像檔。**

## 2. 無線電軟體：原始碼、版本、執行檔

### 2.1 現成的執行檔不能用

對 `bin:MMDVMHost` 和 `bin:DMRGateway` 執行 `file` 的結果：*ELF 32-bit LSB executable, ARM, EABI5, dynamically linked, interpreter /lib/ld-linux-armhf.so.3*。動態相依項目（從檔案裡的字串得知）：

| 執行檔 | 除了 libc／libstdc++ 之外還需要 |
|---|---|
| `MMDVMHost`、`RemoteCommand` | `libwiringPi.so`、`libwiringPiDev.so`、`libArduiPi_OLED.so.1` |
| `dstarrepeaterd` | `libwiringPi.so`、`libwx_baseu-3.0`、`libasound`、`libusb-1.0` |
| `ircddbgatewayd`、`timeserverd` | `libwx_baseu-3.0`、`libwx_baseu_net-3.0` |
| 閘道器、parrot 程式、跨模式程式 | 不需要其他的 |

引用到的最高 glibc 符號版本：2.28。要在 Ubuntu 24.04 **arm64** 上使用，需要加入 armhf 架構（multiarch）、有 `CONFIG_COMPAT` 的 kernel、armhf 版的 WiringPi 和 ArduiPi_OLED，以及 Ubuntu 24.04 沒有的 wxWidgets 3.0。因此全部從原始碼建置。

### 2.2 執行檔是從哪份原始碼建置的

g4klx 的程式會印出 `Built ... (GitID #xxxxxxx)`；完整的 40 位 ID 在執行檔裡。用 `grep -a` 從 bin `f851131d` 的檔案中取出，再到 g4klx 的儲存庫查詢（全部都在預設分支上）：

| 程式 | Pi-Star 執行檔中的版本字串 | 內嵌的 commit | 儲存庫、commit 日期 |
|---|---|---|---|
| MMDVMHost | `20250925_PS4` | `05b10ac5` | `g4klx/MMDVM-Host`（原名 `MMDVMHost`），2025-09-25，「Merge pull request #849 from MW0MWZ/master」 |
| DMRGateway | `20250318_PS4` | `ec5c32b5` | `g4klx/DMRGateway`，2025-03-15 |
| YSFGateway | `20250616_PS4` | `598854b2` | `g4klx/YSFClients`，2025-06-15 |
| YSFParrot、DGIdGateway | `20250521_PS4` | `75c84508` | `g4klx/YSFClients`，2025-05-21 |
| P25Gateway、P25Parrot | `20250405_PS4` | `298b9b4d` | `g4klx/P25Clients`，2025-04-04 |
| NXDNGateway、NXDNParrot | `20250320_PS4` | `5e235f73` | `g4klx/NXDNClients`，2025-03-19 |
| DAPNETGateway | `20250408_PS4` | `dde4c01a` | `g4klx/DAPNETGateway`，2025-03-18 |
| APRSGateway | `20240130_PS4` | `7fd8ad32` | `g4klx/APRSGateway`，2024-01-29 |
| M17Gateway | `20250318_PS4` | `2be36e45` | `g4klx/M17Gateway`，2025-03-17 |

`_PS4` 後綴和日期不在上游的 `Version.h` 裡（`05b10ac5` 的 MMDVMHost 寫的是 `20250828`）：Pi-Star 建置時改了版本字串。是否還改了別的地方，不知道。在這裡從原始碼建置的程式會回報上游的字串，所以儀表板「SysInfo」頁面上的版本會和真正的 Pi-Star 不同，差別就只在這一點。

`05b10ac5` 的 MMDVMHost 正是儀表板需要的、還沒有 MQTT 的版本：`MMDVM.ini` 有 `[Log] FilePath / FileRoot / FileLevel / FileRotate`、帶 `RemoteAddress` 和 `Password` 的 `[DMR Network] Type=Direct|Gateway`、內建的 `[Nextion]` 區段（含 `Port=modem`），而且 Makefile 列出 `Nextion.o`、`DMRDirectNetwork.o`、`Log.o`；沒有任何 MQTT 的原始碼檔。

下列程式沒有內嵌 commit ID；鎖定版本是推定的（見 `pins.conf`）：

| 程式 | 依據 | 鎖定版本 |
|---|---|---|
| YSF2DMR、YSF2NXDN、YSF2P25、DMR2YSF、DMR2NXDN、NXDN2DMR | 版本 `20240908_PS4`；`juribeparada/MMDVM_CM` 從 2024-09-07 之後就沒有新的 commit | `7328c9e9`（HEAD） |
| MMDVMCal | 執行檔最後一次由 bin 的 commit `bedf7f2`（2025-04-16）更新 | `f530cc9f`（2024-01-12），在那之前最新的一個 |
| NextionDriver | 執行檔最後一次由 bin 的 commit `7ff54f4`（2025-04-11）更新 | `on7lds/NextionDriver` `1437e4e2`（2024-12-24） |
| ircddbgatewayd、remotecontrold、timeserverd、starnetserverd | wx 3.0 的執行檔，找不到版本 | `g4klx/ircDDBGateway` `6680e4b7`（2025-04-27），MQTT 分支合併（2026-02-18）前的最後一個 commit |
| dstarrepeaterd | 需要 WiringPi；只用於非 MMDVM 數據機 | 不建置 |
| MobileGPS | 版本 `20200517_Pi-Star` | 不建置（原因見 `FEATURES.md` 設定頁面的 Mobile GPS） |
| AMBEserver、timercontrold、文字／語音／APRS 發送工具 | - | 不建置 |

## 3. 目錄結構

| 路徑 | 內容 | 來源 |
|---|---|---|
| `/etc/mmdvmhost` | MMDVMHost 的 ini（是一個*檔案*，不是目錄） | `dash:config/config.php:24-25`（`MMDVMINIPATH` `/etc`，名稱 `mmdvmhost`）、`sbin:mmdvmhost.service:16` |
| `/etc/dmrgateway`、`ysfgateway`、`p25gateway`、`nxdngateway`、`m17gateway`、`dgidgateway`、`dapnetgateway`、`aprsgateway`、`ysf2dmr`、`ysf2nxdn`、`ysf2p25`、`dmr2ysf`、`dmr2nxdn`、`nxdn2dmr`、`mobilegps` | 每個程式一個 ini 檔 | 各個 `sbin:*.service` 裡的 `CONFIG=`；`dash:admin/configure.php:120-200` |
| `/etc/ircddbgateway`、`/etc/dstarrepeater`、`/etc/timeserver`、`/etc/starnetserver` | D-Star 程式的 `key=value` 檔，沒有分區段 | `dash:config/ircddblocal.php:22-27` |
| `/etc/dstar-radio.mmdvmhost` 或 `/etc/dstar-radio.dstarrepeater` | 標記檔 + `[Modem] Hardware=<id>`：表示使用哪一套控制軟體。兩者都沒有時，系統處於「未設定」狀態，不會啟動任何無線電服務 | `sbin:mmdvmhost.service:30-46`、`dash:admin/configure.php:215-218` |
| `/etc/pistar-release` | ini：`[Pi-Star]`、`Version = x.y.z`、`Hardware = RPi` ... | `dash:index.php:93`、`sbin:pistar-upgrade:279-281` |
| `/etc/pistar-css.ini` | 儀表板配色（CSS 工具） | `dash:index.php` |
| `/etc/pistar-remote`、`/etc/pistar-keeper` | 兩個 Python 程式的設定 | `sbin:pistar-watchdog`、`sbin:pistar-keeper` |
| `/etc/bmapi.key`、`/etc/dapnetapi.key`、`/etc/tgifapi.key` | API 金鑰，權限 600，屬於 `www-data` | `dash:mmdvmhost/bm_manager.php:38`、`sbin:pistar-upgrade:86-88` |
| `/etc/hostfiles.nodextra`、`/etc/timeserver.dissable`、`/etc/hostap.off` | 旗標檔 | `sbin:pistar-upgrade:151-161` |
| `/usr/local/bin` | 無線電程式、`RemoteCommand`、`platformDetect.sh`、`config_clean.zip`、`firmware/` | bin；`dash:config/config.php:26` |
| `/usr/local/sbin` | sbin 的所有腳本 | sbin |
| `/usr/local/etc` | `DMRIds.dat`、`NXDN.csv`、`*_Hosts.txt`／`*Hosts.txt`、`TGList_*.txt`、`XLXHosts.txt`、`RSSI.dat`、`DMR_Audio/`、`P25_Audio/`、`nextionGroups.txt`、`nextionUsers.csv` | `sbin:HostFilesUpdate.sh`、`bin:config_clean.zip`（`mmdvmhost`、`dmrgateway` 裡的路徑） |
| `/var/log/pi-star` | `MMDVM-YYYY-MM-DD.log`、`DMRGateway-...`、`YSFGateway-...`、`P25Gateway-...`、`Links.log`、`Headers.log`、`pi-star_update.log`、`pi-star_upgrade.log`、`pi-star_modemflash.log`、`pi-star_icmptest.log`；擁有者 `root:mmdvm`，權限 775 | `dash:config/config.php:22-43`、`sbin:mmdvmhost.service:54-59`、`dash:admin/update.php:50-52` |
| `/var/www/dashboard` | 網頁文件根目錄 | `sbin:pistar-update:193`、`sbin:pistar-upgrade:405` |
| `/var/www/.htpasswd` | basic auth 帳號密碼檔，使用者 `pi-star` | `dash:admin/configure.php:448` |
| `/root/ipv4.fw`、`/root/ipv6.fw`、`/root/DMR_Hosts.txt`、`/root/YSFHosts.txt`、`/root/P25Hosts.txt` ... | 使用者自行加入的內容，更新後會保留 | `sbin:pistar-firewall`、`sbin:HostFilesUpdate.sh` |
| `/tmp` | 暫存區：儀表板以 `www-data` 身分寫出新檔案，再用 `sudo install` 安裝 | `dash:config/config_writer.php:320-346` |

`bin:config_clean.zip` 存有其中 16 個檔案的出廠預設值（`dgidgateway dmr2nxdn dmr2ysf dmrgateway dstarrepeater ircddbgateway
mmdvmhost nxdngateway p25gateway pistar-remote starnetserver timeserver
ysf2dmr ysf2nxdn ysf2p25 ysfgateway`），日期是 2018-2021；設定頁面存檔時會在這些檔案加入較新的區段。`m17gateway`、`dapnetgateway`、`aprsgateway`、`nxdn2dmr`、`mobilegps` 則沒有預設檔（**僅映像檔**，或需要時才下載：`sbin:mobilegps.service` 會從 GitHub 抓 `MobileGPS.ini`）。

## 4. 服務

每個無線電程式都有一個**包裝腳本** `sbin:<name>.service`（是 start/stop/restart/status 的 shell 腳本，不是 systemd unit），由它決定程式到底該不該執行：執行檔或 ini 檔不存在、系統未設定、檔案裡還留著預設的呼號 `M1ABC`／ID `1234567`，或該模式在 `/etc/mmdvmhost` 裡被關閉時，它就安靜地結束（`sbin:dmrgateway.service:27-41`、`sbin:mmdvmhost.service:26-52`）。`dmrgateway.service` 另外只在 `[DMR Network] Address=127.0.0.1` 時才啟動，也就是 DMR 主控站選了「DMRGateway」的時候；如果直接選 BrandMeister 主控站，MMDVMHost 會自己登入，DMRGateway 不會執行。

呼叫這些包裝腳本的 systemd unit 屬於**僅映像檔**，但 `sbin:pistar-upgrade` 會建立其中幾個，從中可以看出寫法（第 330-341 行 mobilegps、467-485 aprsgateway、529-541 pistar-upnp、563-580 dgidgateway、687-706 m17gateway、928-943 nextiondriver）：`Type=forking`、`ExecStart=/usr/local/sbin/<name>.service start`、`ExecStop=... stop`、`ExecReload=... restart`、`WantedBy=multi-user.target`，再加上 `OnStartupSec=20` 的 `<name>.timer`；啟用的是 *timer*。它們放在 `/lib/systemd/system`（儀表板用 sed 編輯 `/lib/systemd/system/mmdvmhost.timer` 和 `dstarrepeater.timer`，`dash:admin/configure.php:1786-1787`）。

儀表板和腳本使用的 unit 名稱（`dash:admin/configure.php:
551-576`、`sbin:pistar-update:106-135`、`sbin:pistar-upgrade:50-76`）：`mmdvmhost dstarrepeater ircddbgateway timeserver starnetserver dmrgateway
ysfgateway ysfparrot dgidgateway p25gateway p25parrot nxdngateway nxdnparrot
m17gateway dapnetgateway aprsgateway ysf2dmr ysf2nxdn ysf2p25 dmr2ysf dmr2nxdn
nxdn2dmr mobilegps nextiondriver pistar-watchdog pistar-remote pistar-upnp
pistar-keeper pistar-ap cron`，以及 timer `mmdvmhost.timer`、`pistar-watchdog.timer`、`pistar-upnp.timer`。

儀表板判斷「執行中／未執行」用的是 `pgrep <program name>`（`dash:admin/admin.php:52-57`、`dash:mmdvmhost/tools.php:75-80`），不是 systemd。

無線電程式以 `Daemon=1` 執行：它們會 fork 並切換成使用者 `mmdvm`（`getpwnam("mmdvm")`、`setgid`、`setuid`；鎖定 commit 的 `MMDVMHost.cpp:207-250`）。沒有設定附加群組，所以這個使用者的主要群組必須能開啟數據機埠並寫入 `/var/log/pi-star`。Pi-Star 映像檔如何處理前者，屬於**僅映像檔**。

## 5. 網頁伺服器、PHP、驗證

- **nginx**，站台檔 `/etc/nginx/sites-available/pi-star`（`sbin:pistar-upgrade:803`），`listen 80 default_server`，從 4.1.10／4.2.3 起還有 `listen [::]:80 default_server`（第 804-806 行）。PHP 由引入的 `/etc/nginx/default.d/php.conf` 處理（第 417 行，在同一支腳本寫出的強制入口網頁（captive portal）站台設定裡）。那個 captive portal 區塊也顯示了管理頁面的 location：`location ^~ /admin { ... client_max_body_size 512K; ... }` 和 `location ~ /\.git { deny all; }`（第 409-422 行）。`pi-star` 站台檔本身屬於**僅映像檔**。
- **php-fpm**；版本取決於映像檔的 Debian 版本。`sbin:pistar-upgrade:1287-1295` 會逐一處理 `/etc/php/*/fpm`，寫入 `conf.d/99-pistar-hardening.ini`（`session.upload_progress.enabled = 0`）。儀表板用到的 PHP 擴充：`mbstring`（`mb_strimwidth`）、`zip`（`admin/config_backup.php` 裡的 `ZipArchive`）、`json`。
- **文件根目錄** `/var/www/dashboard`；每個頁面都用 `$_SERVER['DOCUMENT_ROOT']`。
- **驗證**：`/admin` 使用 HTTP basic auth，檔案 `/var/www/.htpasswd`，使用者 `pi-star`。儀表板用 `htpasswd -i /var/www/.htpasswd pi-star`（以 `www-data` 執行，不用 sudo）變更密碼，同時用 `sudo -n /usr/sbin/chpasswd` 變更 Linux 使用者 `pi-star` 的密碼（`dash:admin/configure.php:428-475`、`dash:admin/change_password_required.php:110-161`）。初始密碼是 `raspberry`：`dash:config/banner_warnings.inc:132-139` 會把送來的 basic auth 密碼和這個字串比對，顯示紅色警示橫幅，並把不在本地子網路的用戶端導向 `change_password_required.php`（第 277-318 行）。
- **CSRF token 與安全標頭**：`dash:config/csrf.php`、`dash:config/security_headers.php`（PHP session）。
- **公開部分**：`/`（即時儀表板）、`/api/` 不需要驗證。

## 6. sudo

直到 Pi-Star 4.1.10／4.3.x 初期，`/etc/sudoers` 都含有 `www-data ALL=(ALL) NOPASSWD: ALL`。`sbin:pistar-upgrade:24-264`（`deploy_sudoers_tightening`）把它換成 `/etc/sudoers.d/pistar-dashboard`：16 個指令別名（`PISTAR_DASH_SYSTEMCTL`、`_MOUNT`、`_INSTALL`、`_CP_STAGE`、`_STAGE_PERMS`、`_LOGS`、`_MARKERS`、`_SED`、`_READ_PRIV`、`_PASSWD`、`_NETWORK`、`_TIME`、`_POWER`、`_BACKUP`、`_MISC`、`_SCRIPTS`）和 `www-data ALL=(root) NOPASSWD: PISTAR_DASH_ALL`。安裝前後都用 `visudo -c` 驗證。第 815-890 行的註解說明了三輪新增，「driven by an empirical sudo -ln probe of every distinct command pattern in the dashboard」。

儀表板透過 sudo 執行的指令（對 dash 統計，`grep -o "sudo ..."`）：`mount -o remount,rw|ro /`（73）、`install -m ... /tmp/x <target>`（51）、`sed -i`（30）、`systemctl start|stop|restart`（72）、`cp <config> /tmp/x`、`chown www-data:www-data`、`chmod 600`（各 19）、`sync`、`/usr/local/bin/RemoteCommand`、`remotecontrold`、`rm -rf`、`truncate -s 0`、`timedatectl set-timezone`、`reboot`、`shutdown -h now`、`zip -j`、`wpa_cli`、`ip link`、`ifup`／`ifdown`、`chpasswd`、`touch`、`mkdir`、對 Wi-Fi 檔案的 `cat`／`grep`，以及腳本 `pistar-update`、`pistar-upgrade`、`pistar-modemupgrade`、`pistar-jittertest`、`pistar-calibration-start`、`pistar-factory-reset --really`。

這份允許清單對知道管理密碼的人來說並不是安全邊界：它允許的指令包括 `sed -i <anything> /etc/crontab`、`install ... /tmp/* /etc/hosts`、`chpasswd` 和 `zip *`。

## 7. Cron、timer、更新

- `sbin:pistar-daily.cron`（189 行）：`HostFilesUpdate.sh`；在所有服務停止的狀態下，對儀表板、`/usr/local/bin` 和 `/usr/local/sbin` 執行 `git pull`；刪除 `/var/log/pi-star/*.log` 中超過一天的檔案，以及 `/var/log` 底下所有超過一天的 `*.gz`；設定檔遷移；如果 WiringPi 版本較舊，就從 GitHub 安裝 `wiringpi_3.14_armhf.deb`（第 116-144 行）；在 `nginx.service` 加上 `ExecStartPre=mkdir /var/log/nginx`（記錄檔目錄在 tmpfs 上）。
- `sbin:pistar-hourly.cron`：把 nginx 錯誤記錄截到 500 行、`journalctl --vacuum-time=24h --vacuum-size=5M`、把 `/` 和 `/boot` 重新掛載為唯讀。
- 這兩者如何排程屬於**僅映像檔**（`/etc/crontab` 和 `/etc/rc.local`，後者會打散每日工作的執行時間：`sbin:pistar-upgrade:449-452`）。
- `sbin:pistar-update`（手動執行，以及儀表板的「Update」頁面）：停止服務、從終端機執行時做 `apt-get upgrade`、對三個目錄樹做 `git pull`（包含自我更新，失敗時 `git reset --hard origin/master`）、`HostFilesUpdate.sh`、`pistar-firewall`、設定檔遷移、WiringPi、重新啟動服務、重新掛載為唯讀。記錄檔：不在終端機上執行時寫到 `/var/log/pi-star/pi-star_update.log`。
- `sbin:pistar-upgrade`：對 `/etc/pistar-release` 裡的版本做 `case`，每個發行步驟一個分支（4.1.0 ... 4.1.13、4.2.0 ... 4.2.6、4.3.0 ... 4.3.10）；每個分支修改映像檔裡的檔案並提升版本號。最後一個完整的分支產生 **4.3.10**；`dash:config/banner_warnings.inc` 在版本低於 4.3.10 時會要求升級。
- `sbin:HostFilesUpdate.sh`：用 `curl --user-agent
  "Pi-Star_<version>"` 從 `http://www.pistar.uk/downloads/` 下載 17 份清單和兩份 Nextion 清單到 `/usr/local/etc`，保留一份帶日期的備份，附加使用者的 `/root/*Hosts.txt`，並改寫 `/etc/dmrgateway` 的部分內容。
- uPnP：`sbin:pistar-upnp.service`（一支呼叫 `upnpc` 的腳本）由 `/etc/crontab` 裡的一行每 5 分鐘執行一次，也由 `pistar-upnp.timer` 執行；儀表板會註解／取消註解那一行，以及腳本裡個別的連接埠設定行（`dash:admin/configure.php:2416-2448`、`5599-5660`）。

## 8. 防火牆與看門狗

- `sbin:pistar-firewall`（389 行）：清空所有 iptables／ip6tables 表，把 INPUT **和 OUTPUT** 的預設政策設為 `DROP`，接著是允許清單（輸入：22、80、443/tcp、來自私人網路的 445/tcp 和 137-139、5353、1900、DHCP、10022/udp、2460/udp、來自私人網路的 20000/udp、D-Star／YSF／P25／NXDN／M17 的 UDP 連接埠範圍；輸出也類似）、語音連接埠的 DSCP 標記、選用的 `/root/ipv4.fw`、`/etc/hostapd/hostapd.conf` 存在時的 hostapd NAT，最後存到 `/etc/iptables.rules`／`/etc/ip6tables.rules`。開機時由什麼載入它，屬於**僅映像檔**。
- `sbin:pistar-watchdog`（`#!/usr/bin/python`，Python 2：`import
  ConfigParser`）：等 90 s 後進入迴圈；對每個無線電程式做 `pgrep`，沒有在執行的就 `systemctl stop`／`start`（再由包裝腳本決定）；`/var/log` 使用超過 90 % 時，刪除 `/var/log` 底下已輪替的記錄檔並截短記錄檔。由 `sbin:pistar-watchdog.service`（`/usr/bin/python /usr/local/sbin/pistar-watchdog`）啟動。
- `sbin:pistar-remote`（Python 2）：透過記錄檔中出現的特殊呼號做射頻遙控。`sbin:pistar-keeper`（Python 2，`import bluetooth`）。

## 9. 樹莓派專屬的地方

### 9.1 儀表板（dash）

| 檔案:行號 | 內容 | 這裡的處理方式 |
|---|---|---|
| 28 個檔案，73 次 `sudo mount -o remount,rw /`／`remount,ro /`，例如 `config/config_writer.php:411,560`、`admin/configure.php:3944`、`admin/power.php:107,113`、每一個 `admin/expert/*.php` | 唯讀根目錄 | `remount,ro` → `true`（安裝腳本）；`remount,rw` 保留 |
| `admin/configure.php:73`、`dstarrepeater/system.php:46` | `cat /sys/class/thermal/thermal_zone0/temp` | → `pistar-b96-temp` |
| `admin/configure.php:345`、`dstarrepeater/system.php:65` | `/usr/local/bin/platformDetect.sh` | 自己寫的腳本 |
| `admin/configure.php:1815-2399` | 依數據機類型約 60 處 `$configmmdvm['Modem']['Port'] = "/dev/ttyAMA0"`（也有 `ttyACM0`、`ttyUSB0`、`ttyS2`、`ttySC0`），並複製到 `UARTPort` | udev 別名 `/dev/ttyAMA0` |
| `admin/configure.php:2823` | `[TFT Serial] Port=/dev/ttyAMA0` | 沒有使用 |
| `admin/configure.php:4252`、`5566` | 從 `ls /dev \| egrep "ttyA\|ttyUSB"` 取得的埠清單 | 別名會以 `ttyAMA0` 出現 |
| `admin/configure.php:4257,4360` | NanoPi 的 `/dev/ttyS2` 選項 | 不存在 |
| `admin/configure.php:1797-1799` | Icom 中繼台：在 `/etc/network/interfaces` 加上 `eth0:1` | 不適用（沒有這個檔案） |
| `admin/configure.php:520-521`、`2674-2678`、`5637`；`config/config_writer.php:127` | `/etc/hostapd/hostapd.conf`（自動 AP 的 SSID／PSK） | 沒有 hostapd：區段隱藏 |
| `admin/configure.php:2655-2671` | 用 sed 改 `/etc/hostname`、`/etc/hosts` 裡的主機名稱 | 不改 |
| `admin/configure.php:5668-5673` | `/sys/class/net/wlan0`、`wlan1` 或 `wlan0_ap` 存在時顯示 Wi-Fi iframe | 介面命名為 `wlan0` |
| `admin/wifi.php:75-262` | `ifconfig wlan0`、`iwconfig wlan0`、`iw dev wlan0 link` | 套件 `net-tools`、`wireless-tools`、`iw` |
| `admin/wifi.php:181,190,197` | `sudo ifdown wlan0`／`ifup wlan0` | 第 197 行 → `ip link`；181／190 在被註解掉的按鈕後面 |
| `admin/wifi.php:244,266,446,466`、`admin/expert/fulledit_wpaconfig.php:66,83` | `/etc/wpa_supplicant/wpa_supplicant.conf` | 同一個檔案，由 `wpa_supplicant@wlan0` 使用 |
| `admin/wifi.php:316-320` | 國家清單取自 `/lib/crda/regulatory.bin` 或 `/lib/crda/db.txt`，否則用 AU FR DE GB US JP | 產生 `db.txt` |
| `admin/wifi.php:470,478,480` | `ip link set wlan0`、`wpa_cli scan -i wlan0` | 不改 |
| `admin/config_backup.php:90,219-223` | `/etc/dhcpcd.conf` 有固定位址時會備份它 | 檔案不存在：頁面略過 |
| `admin/expert/ssh_access.php:29-32` | `/etc/default/shellinabox` | 不存在：頁面顯示「not yet installed」 |
| `admin/expert/modem_fw_upgrade.php:208-242` | 樹莓派 hat 韌體 ID 的名稱 | 清單來自替換後的腳本 |
| `config/banner_warnings.inc:349-362` | `Hardware == 'RPi'` 的舊版本警示橫幅 | `Hardware = Bubblegum96` |
| `admin/configure.php:337` | 提示文字「running on this Raspberry Pi」 | 只影響外觀，不改 |

這個 commit 的儀表板裡沒有任何 `vcgencmd`、`/boot`、`rpi-rw`、`raspi-config`、`/proc/cpuinfo` 或 WiringPi 呼叫。

### 9.2 腳本（sbin）

| 檔案:行號 | 內容 | 這裡的處理方式 |
|---|---|---|
| `pistar-update:58-62,153-157,353-357`、`pistar-upgrade:284-288,1374-1378`、`pistar-daily.cron:10-14`、`pistar-hourly.cron:18-22`、`pistar-expand`、`pistar-ap.service`、`pistar-factory-reset`、`pistar-mmdvmcal:27,55`、`pistar-mmdvmhost-module:116`、`mobilegps.service:41-45` | `mount -o remount,rw\|ro /`、`/boot`、`/boot/firmware` | 在有安裝的腳本裡 `remount,ro` → `true` |
| `pistar-update:301-336`、`pistar-daily.cron:116-144` | 下載 `wiringpi_3.14_armhf.deb` 並 `dpkg -i` | 腳本已替換 |
| `pistar-upgrade:348-360,975,1083-1096` | `/boot/config.txt`、`/boot/cmdline.txt`、`/boot/firmware/...` | 腳本已替換 |
| `pistar-upgrade:1346-1362` | Pi 4／5 上的 `rpi-eeprom-update` | 腳本已替換 |
| `pistar-findmodem:23-41`、`pistar-mmdvmhshatreset:62-80`、`pistar-modemupgrade:326-329,497-510` | sysfs GPIO `base + 20`／`+ 21`（樹莓派排針的 BOOT0／重置），透過名稱含 `0000.gpio` 的 `gpiochip*` 找到；如果都不符合，base 是空的，腳本會匯出**全域 GPIO 20 和 21** | 三支都已替換 |
| `pistar-modemupgrade:464-469,515-527` | WiringPi `gpio mode`／`gpio write` | 已替換 |
| `pistar-modemupgrade:497-510` | `/dev/ttyAMA0` 上的 `/usr/local/bin/firmware/utils/stm32flash*`（armhf） | 已替換：透過 `flash-mmdvm-hs` 使用 Ubuntu 的 `stm32flash` |
| `pistar-mmdvmhshatreset:19,48` | `platformDetect.sh`「Pi 4 Model」，需要 `/dev/ttyAMA0` | 已替換 |
| `pistar-findmodem:141,250-260` | `/dev/ttyAMA*`、Odroid／sun8i 特例 | 已替換 |
| `pistar-nextiontext.py:34` | 把 Nextion 指令寫到 `/dev/ttyAMA0` | 不安裝（在這裡那是數據機） |
| `pistar-oledtext.py` | 透過 `luma.oled` 驅動的 I2C OLED | 不安裝 |
| `pistar-ap.service:14-163` | `wlan0`／`wlan0_ap` 上的 hostapd、`ifup`、`ifconfig`、`iw ... interface add` | 不安裝 |
| `pistar-firewall:143-148` | 設定了 hostapd 時的 `wlan0_ap` 規則 | 不會生效 |
| `pistar-remote:337-348,500-511` | `/sbin/iwconfig wlan0` | 不安裝（Python 2） |
| `pistar-bootconfig.sh:20-69` | `/boot/Pi-Star_Config_*.zip`、`/boot/firmware/...`、開機分割區上的 `wpa_supplicant.conf` | 不安裝 |
| `pistar-expand`、`pistar-clone` | SD 卡擴充容量／複製、`/boot/.expanded`、`armbianEnv.txt` | 不安裝 |
| `pistar-motdgen:46,79` | 關於 `rpi-rw` 的 MOTD 文字 | 不安裝 |
| `pistar-watchdog`、`pistar-remote`、`pistar-keeper` | `#!/usr/bin/python`（Python 2） | watchdog 已替換，其他不安裝 |

`rpi-rw`／`rpi-ro` 在三個儲存庫裡都沒有定義（**僅映像檔**；依 MOTD 文字，它們是 shell alias）。bin 的 `platformDetect.sh` 讀取 `/proc/cpuinfo` 的 `Revision`／`Hardware` 和 `/proc/device-tree/model`，印出樹莓派型號名稱、「sun8i based Pi Clone」、「Odroid XU3/XU4 System」或 `Generic <uname -p> class computer`。

## 10. 無法確定的事項

- 僅映像檔的那些檔案的內容：nginx 站台檔和 `php.conf`、systemd unit 和 timer（確切的相依關係、`OnStartupSec` 值）、`/etc/rc.local`、`/etc/crontab`、`/etc/fstab`（`/var/log`、`/tmp` 的 tmpfs）、`mmdvm` 和 `pi-star` 在 `/etc/passwd`／`group` 裡的項目、udev 規則、載入防火牆的 hook。
- Pi-Star 建置執行檔的方法（編譯旗標、版本字串以外的修補，以及 ircDDBGateway 編譯進去的目錄）。
- MMDVMCal、MMDVM_CM 程式、NextionDriver 和 ircDDBGateway 確切的原始碼 commit。
- `www.pistar.uk` 會不會把主機清單檔提供給不是 Pi-Star 映像檔的用戶端（請求看起來一樣：帶 `Pi-Star_4.3.10` user agent 的一般 `curl`）。
