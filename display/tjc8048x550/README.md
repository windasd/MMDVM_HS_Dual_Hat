# Screen design for the TJC8048X550_011R (800 x 480) on the MMDVM Nextion port

A first version of the MMDVM screen for the 5-inch TJC X5 serial HMI display
(resistive touch) that hangs on the modem's Nextion pass-through port and is
driven by g4klx MMDVM-Display with `Port=modem`, `ScreenLayout=3`.

**State: designed, never run on hardware.** The protocol was read from the driver
source and the pages were only rendered as mock-ups. Nothing here has been
compiled in the editor or shown on the display.

**The screen file itself (`.HMI` / `.tft`) is not here.** It can only be made
with TJC's Windows editor (USART HMI), which is a GUI program and was not
installed on the machine this was written on. What is here is everything needed
to build it by hand in that editor, with no layout decisions left to make.

| File | What it is |
|---|---|
| `BUILD.md` | Step-by-step build in the editor, loading the display, MMDVM settings, test checklist (Traditional Chinese). Start here. |
| `PROTOCOL.md` | What the driver sends: pages, object names, texts, status codes, with source references; why ScreenLayout 3; open points. |
| `layout.json` | The design: every page and component (name, type, position, font, colours as RGB565 decimal, event code), fonts, pictures. The source of truth. |
| `render_mockups.py` | Renders `layout.json` (Pillow only) and checks it: text that does not fit, overlaps, field colour against the picture under it. |
| `resources/` | The nine 800 x 480 page backgrounds to import into the editor, in picture-id order. Generated. |
| `mockups/` | Each page with sample values, as it should look. Generated. |

After changing `layout.json`:

```
python render_mockups.py            # redraw resources/ and mockups/, run the checks
python render_mockups.py --tables   # print the per-page tables to paste into BUILD.md section 5
```

Pages: `MMDVM` (idle), `DStar`, `DMR` (both slots), `YSF`, `P25`, `NXDN`,
`POCSAG`, `FM`, and one page of its own, `System` (display baud rate, touch
calibration). There is no M17 page: MMDVM-Display does not send one.

Known limits of this version: Latin text only (the project encoding is
iso-8859-1, chosen so the temperature's degree sign shows); brightness is
controlled by MMDVM-Display, not from the screen; RSSI and BER are shown as text.
