# MMDVM_HS_Dual_Hat
MMDVM_HS_Hat 的雙工版本
DB9MAT DF2ET DO7EN

這張電路板使用 Andy CA6JAU 的 [MMDVM_HS](https://github.com/juribeparada/MMDVM_HS)。板上有兩顆 ADF7021，可以雙工運作，DMR 的兩個時槽都能用。

![MMDVM_HS_Dual_Hat](https://github.com/phl0/MMDVM_HS_Dual_Hat/blob/master/mmdvm_hs_dual_hat.png)

## 改版紀錄

### 版本 1.0

首次發行。

### 版本 1.1

LED D4 和 D5 對調，與掃描順序一致。新增焊錫跳線 JP1，只在 Raspberry Pi 上使用時可以把它短接，它會把 BOOT1 接到 GND。BOOT0 由 GPIO 控制。這種情況下 2x3 排針可以不焊，節省空間。U1 和 U2 各放了一顆電感，用來實驗擴展 VCO，分別是 L11 和 L12，屬於選配，UHF 使用時不必安裝。背面的測試點 TP1、TP2 可以在韌體以 #define TEST_DAC 編譯時，量測解調器輸出的 SNR。

**不建議用這個版本（重新）生產！**

### 版本 1.2

電路板佈局中一條不小心被刪掉的 3v3 連線已經補回。BOM、Mouser 購物車和鋼網都與 rev1.1 相同。

### 版本 1.3

STlink 排針改成與 [MMDVM_HS_Hat](https://github.com/mathisschmieder/MMDVM_HS_Hat) 板子相同的腳位。OLED 和 STlink 排針互換位置。JP1 稍微移動。C44、C45、C46 移到更靠近 STM32F1 CPU 的位置。背面絲印加了一個表格，標示裝的是哪一種 TCXO，這對韌體很重要。BOM 和 Mouser 購物車不變。鋼網稍有變動；如果 C44-C46 用手焊，仍然可以用舊的鋼網。

### 版本 2.0 mini

全面重新設計的 4 層板佈局，採 Raspberry Pi Zero 尺寸（65 x 30 mm），用板上的陶瓷晶片天線取代 SMA 接頭。專案檔在 `hardware/r2.0-mini`，BOM 在 `hardware/r2.0-mini/BOM.csv`。

**天線注意事項：** 佈局用的晶片天線封裝／3D 模型是 Yageo ANT1204LL08R0870A，這是 870 MHz 的料。BOM 現在列的是 433 MHz 版本 ANT1204LL20R0433A（本體同為 12 x 4 mm，焊墊圖相同）。板上晶片天線一定要在實際的板子上調整匹配網路；70 cm 頻段預計要重新調整。

### 版本 3.0 研究版（未製作）

`hardware/r3.0-study` 是一張較大電路板的研究：rev1.3 的 MMDVM 部分，加上 Meshtastic（RAK4630）、GPS（u-blox MAX-M10S）、四顆並聯的 18650 電池（含充電與保護）和 1G 乙太網路（LAN7500），做成 96Boards 擴充板，主機是 Bubblegum-96。4 層，90.6 x 167.1 mm；另有一張小前面板在 `hardware/r3.0-study/front_panel`，外殼概念在 `case/meshtastic-concept`。

**這張板子從來沒有製作或測試過。** 線路圖和佈局通過 ERC／DRC，也對照過規格書，僅此而已。設計紀錄（包括還沒驗證的項目清單）是 `docs/meshtastic-gps-study.md`（以繁體中文撰寫；第 16 節是送廠準備）。下單參數在 `hardware/r3.0-study/FAB_NOTES.md`。

同樣未測試的還有：`software/bubblegum96` 裡 Bubblegum-96 的主機端軟體（裝置樹疊加檔（overlay）、MMDVM-Host／MMDVM-Display 設定、風扇、GPS、Meshtastic、網路），以及 `display/tjc8048x550` 裡 5 吋 TJC8048X550 螢幕的畫面設計（版面、示意圖與製作步驟；`.HMI`／`.tft` 檔本身要用廠商的編輯器做）。

## 移轉到 KiCad 10（2026）

兩個版本都已移轉到 KiCad 10（需要 KiCad 10.0 或更新版本才能開啟）。

* 所有符號和封裝都連結到 KiCad 10 標準庫，或 `libraries/` 裡共用的專案庫（`mmdvm_hs_dual_hat.kicad_sym`、`mmdvm_hs_dual_hat.pretty`）。「rescue」庫和快取庫已經移除。
* 接腳幾何與 KiCad 10 標準符號不同的符號（STM32F103C8Tx、ADF7021、Raspberry Pi 排針、CONN_*、USB_OTG、LD1117S33TR、GS2、天線、NC/NO 跳線）原封不動移到專案符號庫，所以不必重畫任何連線。
* 焊墊幾何很接近、DRC 也沒有出現新違規的封裝，換成 KiCad 10 的標準封裝。新的焊墊較大、會違反既有間距的零件，保留專案庫裡的原始幾何：rev1.3 的 U1、U2、U3、R15、R16、C4、C17、C18、C33、C39，以及 rev2.0-mini 的 U1、U2（散熱過孔）。rev2.0-mini 的 R15、U4、P3、P4、J2、J4 保留 `pkl` 封裝。
* **rev1.3 線路圖修正：** 2020 年重畫的線路圖把 STM32 的 VSS/VSSA 腳（8、23、35、47）留著沒接、TCXO X1 的 VDD 和 GND 畫反，OSC_IN/OSC_OUT 也對調了。電路板本身一直是正確的。線路圖已經修回與電路板及 2018 年的原始網表一致；如果在舊線路圖上執行「Update PCB from Schematic」，會讓 TCXO 反向供電。
* 線路圖與電路板一致（網路名稱、封裝、欄位）。
* ERC：為 GND、+5V、+3V3（rev1.3）以及 GND、+5V、穩壓器輸入（rev2.0-mini）加上 PWR_FLAG；ADF7021 第 33 腳（SWD，同步字偵測）改為輸出。只有 rev2.0-mini 還留著四個孤立標籤警告（SWD_TP1/2、D+/D-：rev1.3 留下來的訊號名稱）。
* DRC rev2.0-mini：焊錫跳線 J2/J4 改成 net-tie 封裝（焊墊 1-2 依設計相連），並允許防焊橋；晶片天線的絲印不再壓到焊墊；移除一段懸空的走線殘段。rev1.3：移除兩段 10 µm 的走線碎片。
* 剩下、已檢視過的 DRC 項目：rev1.3 的零件邊界（courtyard）重疊（MCU 旁的 C44/C45、U4 的縫合過孔、J1 的固定孔）、兩處只有單一輻條的散熱連接，rev2.0-mini 的兩個絲印間距警告，以及兩張板子上小於 0.8 mm 的絲印文字。
* rev2.0-mini 需要 `libraries/pkl` 子模組：用 `git clone --recursive` 複製，或執行 `git submodule update --init`。

## BOM

版本庫根目錄的 `BOM.csv`／`BOM.xlsx` 對應 rev1.3，`hardware/r2.0-mini/BOM.csv`／`BOM.xlsx` 對應 rev2.0-mini。兩者都是從線路圖匯出的。

零件供貨狀況在 2026 年 11 月查過。相對於原始 BOM 的變更：

| 元件編號 | 原料號 | 新料號 | 原因 |
|---|---|---|---|
| 100n 電容 | Vishay VJ0402V104ZXJCW1BC (Y5V) | Murata GCM155R71C104KA55D (X7R) | 已淘汰 |
| C52（rev1.3） | Murata GRM155C80J106ME11J | Murata GRT155C80J106ME13D | 停產 |
| C52（rev2.0-mini） | 0603 封裝上放了 0402 的料 | Samsung CL10A106KP8NNNC (10 V) | 尺寸錯誤 |
| C33、C34 | AVX 04025A220GAT2A | Kyocera AVX KGM05ACG1H220GH | 料號更新，同一顆料 |
| C47、C48 | Murata GRM1555C1H470FA01D | Murata GJM1555C1H470FB01D | NRND |
| C51 | AVX TPSA106K010T0900 | Kyocera AVX TPSA106K010R0900 | 規格相同，有庫存 |
| R3、R4 | Susumu RR0510P-3831-D | Panasonic ERA-2AEB3831X | 沒有庫存，改用 0.1 %（原為 0.5 %） |
| P1、P2 | TE 5-1814832-1 | TE 5-1814832-2 | 已被取代；同一份圖面 1814832 rev C，只有包裝不同（捲帶） |
| L9、L10 | 值為「100MHz」／「10u」 | 值為「70R@100MHz」 | Würth 74279277 是磁珠，MPN 本來就是對的 |
| rev2.0-mini U3、U4、J1、A1、A2 | 沒有料號 | STM32F103C8T6、TLV70233DBVR、Harwin M20-7832046、ANT1204LL20R0433A | 缺漏 |

`SPN` 欄位空白，表示無法核對 Mouser 料號（Mouser 會擋自動查詢），請用 MPN 在 Mouser 搜尋。查詢當下庫存偏少的零件：TE 36501E20NJTDG（L3、L4；替代料 Murata LQW15AN20NG80D，要重新確認射頻匹配）、Murata GCM1555C1H471JA16J（C21、C22；替代料 GRT1555C1H471JA02D）、Panasonic ERA-2AEB271X（R9、R10）。12.288 MHz 的板子，X1 用 ECS-TXO-3225-122.8-TR。

## 製造檔

`kicad-cli` 把 Gerber X2/Excellon、鑽孔圖、貼片座標 CSV、BOM 和線路圖 PDF 匯出到 `hardware/<rev>/production/`（不進 git；板子規格見該目錄的 `FAB_NOTES.md`）。rev1.3 的 0402 焊墊改了，需要新的鋼網；rev2.0-mini 背面有一顆 SMD 零件（A1）。

下面舊的 Mouser 購物車是 rev1.0/rev1.1 用的，裡面仍然是已淘汰的零件。

rev1.0 的 Mouser 購物車在[這裡](https://www.mouser.com/ProjectManager/ProjectDetail.aspx?AccessID=561bb01347)。

[這個](https://www.mouser.com/ProjectManager/ProjectDetail.aspx?AccessID=24ea9d644e)是 rev1.1 的 Mouser 購物車。L11 和 L12 是選配。

## 韌體安裝

這個裝置可以疊在 RPi 上經 GPIO 埠連接，也可以單獨使用、經 USB 連接。兩種方式在編譯和上傳韌體時的處理不同。USB 連接需要支援 bootloader 的韌體，GPIO 版本則不需要。

USB 連接一開始要先安裝 bootloader，這需要接 STlink。完成之後，MMDVM_HS 韌體就可以經 USB 升級。例如裝了設定錯誤的韌體時，可以改用 STlink 連接當作備援。

### 安裝支援 bootloader 的韌體（USB 連接）

要經 USB 埠使用這個裝置，必須安裝 bootloader，並編譯支援 bootloader 的韌體。全新的裝置還不能用 USB，所以要用 USB 轉序列轉接器或 STlink。用 STlink 的做法如下：

```
user@host:/opt/MMDVM_HS$ make stlink-bl 
././STM32F10X_Lib/utils/linux64/st-flash write ./STM32F10X_Lib/utils/bootloader/generic_boot20_pc13.bin 0x8000000
2018-03-02T10:01:04 INFO src/usb.c: -- exit_dfu_mode
2018-03-02T10:01:04 INFO src/common.c: Loading device parameters....
2018-03-02T10:01:04 INFO src/common.c: Device connected is: F1 Medium-density device, id 0x20036410
2018-03-02T10:01:04 INFO src/common.c: SRAM size: 0x5000 bytes (20 KiB), Flash: 0x10000 bytes (64 KiB) in pages of 1024 bytes
2018-03-02T10:01:04 INFO src/common.c: Attempting to write 7160 (0x1bf8) bytes to stm32 address: 134217728 (0x8000000)
Flash page at addr: 0x08001800 erased
2018-03-02T10:01:04 INFO src/common.c: Finished erasing 7 pages of 1024 (0x400) bytes
2018-03-02T10:01:04 INFO src/common.c: Starting Flash write for VL/F0/F3 core id
2018-03-02T10:01:04 INFO src/common.c: Successfully loaded flash loader in sram
  6/6 pages written
2018-03-02T10:01:05 INFO src/common.c: Starting verification of write complete
2018-03-02T10:01:05 INFO src/common.c: Flash written and verified! jolly good!
././STM32F10X_Lib/utils/linux64/st-flash write bin/mmdvm_f1bl.bin 0x8002000
2018-03-02T10:01:05 INFO src/common.c: Loading device parameters....
2018-03-02T10:01:05 INFO src/common.c: Device connected is: F1 Medium-density device, id 0x20036410
2018-03-02T10:01:05 INFO src/common.c: SRAM size: 0x5000 bytes (20 KiB), Flash: 0x10000 bytes (64 KiB) in pages of 1024 bytes
2018-03-02T10:01:05 INFO src/common.c: Attempting to write 55016 (0xd6e8) bytes to stm32 address: 134225920 (0x8002000)
Flash page at addr: 0x0800f400 erased
2018-03-02T10:01:07 INFO src/common.c: Finished erasing 54 pages of 1024 (0x400) bytes
2018-03-02T10:01:07 INFO src/common.c: Starting Flash write for VL/F0/F3 core id
2018-03-02T10:01:07 INFO src/common.c: Successfully loaded flash loader in sram
 53/53 pages written
2018-03-02T10:01:12 INFO src/common.c: Starting verification of write complete
2018-03-02T10:01:13 INFO src/common.c: Flash written and verified! jolly good!
```

現在裝置應該可以當作 /dev/ttyACMx 使用。

之後如果要經 USB 更新 MMDVM_HS 韌體本身，可以用 dfu 上傳的方式。Config.h 的設定如下：

    #define MMDVM_HS_DUAL_HAT_REV10
    #define ENABLE_ADF7021
    #define DUPLEX

    #define ADF7021_14_7456

或
    #define ADF7021_12_2880

適用於裝 12.288MHz TCXO 的板子。

    #define STM32_USB_HOST
    #define ENABLE_SCAN_MODE

選用：

    #define SEND_RSSI_DATA
    #define SERIAL_REPEATER

用「make bl」編譯韌體，然後：

```
user@host:/opt/MMDVM_HS$ sudo make dfu devser=/dev/ttyACM3
././STM32F10X_Lib/utils/linux64/upload-reset /dev/ttyACM3 750
././STM32F10X_Lib/utils/linux64/dfu-util -D bin/mmdvm_f1bl.bin -d 1eaf:0003 -a 2 -R -R
dfu-util 0.7

Copyright 2005-2008 Weston Schmidt, Harald Welte and OpenMoko Inc.
Copyright 2010-2012 Tormod Volden and Stefan Schmidt
This program is Free Software and has ABSOLUTELY NO WARRANTY
Please report bugs to dfu-util@lists.gnumonks.org

Filter on vendor = 0x1eaf product = 0x0003
Opening DFU capable USB device... ID 1eaf:0003
Run-time device DFU version 0110
Found DFU: [1eaf:0003] devnum=0, cfg=1, intf=0, alt=2, name="STM32duino bootloader v1.0  Upload to Flash 0x8002000"
Claiming USB DFU Interface...
Setting Alternate Setting #2 ...
Determining device status: state = dfuIDLE, status = 0
dfuIDLE, continuing
DFU mode device DFU version 0110
Device returned transfer size 1024
No valid DFU suffix signature
Warning: File has no DFU suffix
bytes_per_hash=1100
Copying data from PC to DFU device
Starting download: [##################################################] finished!
state(8) = dfuMANIFEST-WAIT-RESET, status(0) = No error condition is present
Done!
Resetting USB to switch back to runtime mode
```

### 手動編譯與上傳（GPIO 連接）

韌體安裝的詳細步驟請看[這份](https://github.com/juribeparada/MMDVM_HS#build-de-firmware-and-upload-to-zumspot-rpi)說明。流程和 ZumSpot Pi 的安裝類似。可以使用 MMDVM_HS 裡預先設定好的腳本。手動編輯 Config.h 的話，需要這些設定：

在 Config.h 打開下列設定：

    #define MMDVM_HS_DUAL_HAT_REV10
    #define ENABLE_ADF7021
    #define DUPLEX
    #define ADF7021_14_7456
    #define STM32_USART1_HOST
    #define ENABLE_SCAN_MODE

選用：

    #define SEND_RSSI_DATA
    #define SERIAL_REPEATER

裝 12.288MHz TCXO 的板子則用

    #define ADF7021_12_2880

取代 14_7456 選項。

編譯韌體：

    make

確認兩個 BOOT 跳線設定如下：

    BOOT0: completey removed
    BOOT1: set to BOOT 1 -

最後把韌體上傳到 MMDVM_HS_Dual_Hat：

    sudo make mmdvm_hs_dual_hat

### 在 Pi-Star 裡更新

[PiStar](http://www.pistar.uk/) 內含一個程式，可以把預先編譯好的韌體燒進 MMDVM_HS_Dual_Hat。要在 PiStar 裡更新韌體，執行下列指令：

    $ rpi-rw
    $ pistar-mmdvmhshatflash hs_dual_hat

如果板子裝的是 12.288MHz TCXO，要用下列指令燒錄對應的韌體：

    $ pistar-mmdvmhshatflash hs_dual_hat-12mhz

## 授權
本專案以 Creative Commons Attribution-NonCommercial-ShareAlike 3.0 (CC-BY-NC-SA 3.0, https://creativecommons.org/licenses/by-nc-sa/3.0/) 授權條款釋出。只要註明出處、不更改授權條款，你可以自由修改和分享。你可以替自己和朋友做任意數量的板子，甚至可以賣給他們回收成本，**但嚴格禁止把它做成商業產品！不得以營利為目的製作和販賣這些板子！**
