# Meshtastic 主機連線與 STM32 燒錄說明

這裡的東西都沒有在實機上跑過。

## 主機怎麼和 RAK4630 溝通

| 主機裝置 | 路徑 | 另一端 |
|---|---|---|
| `/dev/ttySC0` | SC16IS752 通道 A（LS I2C0 上的 I2C 0x48） | nRF52840 P0.19（RX）／P0.20（TX）：Meshtastic 序列模組，PROTO，115200 |
| `/dev/ttySC1` | SC16IS752 通道 B，只收 | GPS NMEA（給 gpsd 用，不是給 Meshtastic 工具用） |
| GPIO-G（LS 第 29 腳） | U26，開汲極 | RAK4630 重置，低 = 重置：`mmdvm-gpio reset-mesh` |
| GPIO-I（LS 第 31 腳） | U28 | GPS 負載開關致能（滑動開關 AND 3V3_EN）：`mmdvm-gpio gps-switch` |
| J43（內部 JST-SH） | nRF52840 USB | bootloader／UF2／首次設定；會出現為 `/dev/ttyACM0` |

通道 A 的鮑率是精確的：14.7456 MHz / 16 / 8 = 115200。

安裝 CLI（Ubuntu 24.04 不允許用 `pip install` 裝進系統的 Python）：

```sh
sudo apt-get install -y pipx
pipx install meshtastic
pipx ensurepath
```

使用方式（使用者必須在 `dialout` 群組裡）：

```sh
meshtastic --port /dev/ttySC0 --info
meshtastic --port /dev/ttySC0 --nodes
meshtastic --port /dev/ttySC0 --sendtext "hello"
```

## 首次開機（研究文件第 10.3 節）

1. SWD（J42，pyOCD 或 J-Link），不是從這台主機：UICR `REGOUT0`（0x10001304）= 3.3 V，`NFCPINS`（0x1000120C）= GPIO。
2. 燒錄 RAK4631 bootloader（`wiscore_rak4631_board_bootloader-0.4.4_s140_6.1.1`）。
3. 經 J43 複製 `firmware-rak4631-*.uf2`（或用 BLE OTA）。
4. **第一次要經 USB 或 BLE** 執行 `provision.sh`：序列模組在 P0.19/P0.20 上啟用之前，`/dev/ttySC0` 是不通的，所以讓主機連線能運作的設定，沒辦法經由主機連線送過去。

   ```sh
   ./provision.sh --port /dev/ttyACM0        # J43 plugged into this computer
   ./provision.sh --dry-run                  # only print what would be sent
   ```

   它會設定 `lora.region TW`、`serial.enabled true`、`serial.mode PROTO`、`serial.rxd 19`、`serial.txd 20`、`serial.baud BAUD_115200`、`position.gps_mode ENABLED`。選用：`--sh1106`（強制指定 OLED 型號，研究文件 10.4）、`--gps-always-on`（未驗證，見腳本）。

GPS 開關監看服務（研究文件第 3.3 節）：`../gps/mmdvm-gps-switch.sh`（服務 `mmdvm-gps-switch.service`）監看 GPS 電源（GPIO-I），在電源接通（0 -> 1）並穩定後重置 RAK4630（GPIO-G），讓韌體重新偵測 GPS；最多每 120 s 一次。韌體自己關掉 GPS 時 GPIO-I 也會掉，所以只在接通的那一邊動作。韌體到底需不需要這次重置還沒有實際觀察到（未測試）；在 `/etc/default/mmdvm-gps-switch` 設 `RESET_MESH=0` 就只記錄、不重置。手動的對應做法是先執行 `mmdvm-gpio gps-switch`，再執行 `mmdvm-gpio reset-mesh`。

## 燒錄 STM32（MMDVM_HS 韌體）

訊號線（研究文件 3.1，線路圖 `host_if` 頁）：

| 訊號線 | LS 腳位 | S900 | 路徑 | 極性 |
|---|---|---|---|---|
| BOOT0 | 23, GPIO-A | GPIOA0, line 0 | U22（SN74LVC1T45）-> R25 10 k -> BOOT0 | 高 = bootloader |
| NRST | 24, GPIO-B | GPIOA1, line 1 | U23（74LVC1G07，開汲極） | 低 = 重置 |
| UART | 5 / 7 | UART2, `/dev/ttyOWL2` | U21 / U20 | STM32 USART1（PA9/PA10） |

`../mmdvm/flash-mmdvm-hs.sh` 把下面的步驟包成一支腳本。

```sh
sudo apt-get install -y stm32flash          # not the i386 tools in the firmware repo
sudo systemctl stop mmdvmhost
B=$(sudo mmdvm-gpio number boot0)           # sysfs number = chip base + 0
R=$(sudo mmdvm-gpio number nrst)            # sysfs number = chip base + 1
sudo stm32flash -v -w mmdvm_hs_dual_hat_fw.bin -g 0x0 -R -i "$B,-$R,$R:-$B,$R" /dev/ttyOWL2
sudo mmdvm-gpio reset-modem
sudo systemctl start mmdvmhost
```

- 這個時序取自韌體的 `install_fw_hsdualhat.sh`（`-i 20,-21,21:-20,21`），換成這張板子的 GPIO 編號。
- sysfs 編號不是固定的：S900 的 GPIO 晶片會分到動態的起始編號（512 以上）。`mmdvm-gpio` 依裝置樹的 compatible 找到這顆晶片。
- `stm32flash -i` 需要 `CONFIG_GPIO_SYSFS`（見 `../network/kernel-config.fragment`）。
- bootloader 使用 8E1；`owl-uart` 有實作同位元，所以應該可以用，但未測試。
- 不能用 RTS/DTR 時序（`-i rts,-dtr...`）：`owl-uart` 不會驅動數據機控制輸出。
- 韌體：MMDVM_HS 發行版裡的 `mmdvm_hs_dual_hat_fw.bin`（14.7456 MHz TCXO），或用 `configs/MMDVM_HS_Dual_Hat.h` 自行編譯。用 800x480 TJC 螢幕時，研究文件建議調高 `SERIAL_REPEATER_BAUD`。
- 韌體壞掉時的救援：ROM bootloader 不依賴韌體，所以同一個指令照樣能用；SWD 在 P5。
