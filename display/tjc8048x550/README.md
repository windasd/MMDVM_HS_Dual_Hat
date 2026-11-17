# TJC8048X550_011R（800 x 480）接在 MMDVM Nextion 埠的螢幕畫面設計

這是 5 吋 TJC X5 序列埠 HMI 螢幕（電阻觸控）的第一版 MMDVM 畫面。
螢幕接在數據機的 Nextion 透傳埠上，由 g4klx 的 MMDVM-Display 以 `Port=modem`、`ScreenLayout=3` 驅動。

**狀態：已設計，從未在實機上跑過。** 協定是從驅動程式的原始碼讀出來的，頁面只畫成示意圖。
這裡的東西都沒有在編輯器裡編譯過，也沒有在螢幕上顯示過。

**畫面檔本身（`.HMI`／`.tft`）不在這裡。** 它只能用 TJC 的 Windows 編輯器（USART HMI）製作，那是 GUI 程式，撰寫這份文件的電腦上沒有安裝。
這裡提供的是在那個編輯器裡手動建置所需的全部資料，不需要再決定任何版面。

| 檔案 | 內容 |
|---|---|
| `BUILD.md` | 在編輯器裡逐步建置、把畫面檔載入螢幕、MMDVM 設定、測試清單（繁體中文）。從這份開始看。 |
| `PROTOCOL.md` | 驅動程式送出的內容：頁面、元件名稱、文字、狀態碼，附原始碼出處；為什麼用 ScreenLayout 3；未解問題。 |
| `layout.json` | 設計本體：每個頁面與元件（名稱、類型、位置、字型、以 RGB565 十進位表示的顏色、事件程式碼）、字型、圖片。一切以這個檔案為準。 |
| `render_mockups.py` | 把 `layout.json` 畫出來（只需要 Pillow）並做檢查：放不下的文字、元件重疊、欄位顏色與下方圖片是否相符。 |
| `resources/` | 要匯入編輯器的九張 800 x 480 頁面背景，依圖片 id 排序。自動產生。 |
| `mockups/` | 每一頁填入範例值後應有的樣子。自動產生。 |

改了 `layout.json` 之後：

```
python render_mockups.py            # redraw resources/ and mockups/, run the checks
python render_mockups.py --tables   # print the per-page tables to paste into BUILD.md section 5
```

頁面：`MMDVM`（待機）、`DStar`、`DMR`（兩個時槽）、`YSF`、`P25`、`NXDN`、`POCSAG`、`FM`，以及本設計自己的一頁 `System`（螢幕鮑率、觸控校正）。
沒有 M17 頁：MMDVM-Display 不會送出這一頁。

這一版已知的限制：只能顯示拉丁字母（專案編碼是 iso-8859-1，選它是為了讓溫度的度數符號顯示得出來）；亮度由 MMDVM-Display 控制，不能在螢幕上調；RSSI 與 BER 以文字顯示。

搭配 Pi-Star 移植版（`software/bubblegum96/pistar/`）使用：它跑的是內建 Nextion 驅動程式的舊版 MMDVMHost，而不是 MMDVM-Display。
已把它的 `Nextion.cpp`（commit 05b10ac5）和 MMDVM-Display 的比對過：舊驅動程式用到的每一個頁面、每一個元件，這個版面都有；MMDVM-Display 只多了 `FM` 頁和 `t21`、`t22`、`t31`、`cpuload` 這幾個元件，而舊驅動程式從來不會寫入它們。
所以同一個畫面檔兩邊都能用。比對的方式是從兩份原始碼擷取指令字串，不是在螢幕上實測。
