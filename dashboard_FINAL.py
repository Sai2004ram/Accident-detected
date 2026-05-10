#!/usr/bin/env python3
"""
Smart Accident Detection — Super Dashboard
Run : python dashboard_final.py
Pip : pip install pyserial
"""

import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import json
import time
import webbrowser
from datetime import datetime

# ── Auto-detect Arduino port ──────────────────────────────────
def find_port():
    keywords = ["Arduino", "CH340", "CH341", "USB Serial", "USB-SERIAL"]
    for p in serial.tools.list_ports.comports():
        if any(k.lower() in (p.description or "").lower() for k in keywords):
            return p.device
    all_ports = serial.tools.list_ports.comports()
    return all_ports[0].device if all_ports else "COM3"

# ── Config ────────────────────────────────────────────────────
BAUD          = 9600
TRIGGER_LEVEL = 80
ENERGY_MAX    = 300
HISTORY       = 80

# ── Colors ────────────────────────────────────────────────────
BG     = "#070D16"
CARD   = "#0C1520"
CARD2  = "#101C28"
BDR    = "#182536"
BLUE   = "#00AAFF"
GREEN  = "#00E676"
RED    = "#FF2D55"
ORG    = "#FF6B1A"
YEL    = "#FFD000"
WHT    = "#E8F0FF"
GRY    = "#3D5060"
DRK    = "#050A10"
TEAL   = "#00C9B1"

# ═════════════════════════════════════════════════════════════
class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚨 Smart Accident Detection Dashboard")
        self.geometry("1100x720")
        self.configure(bg=BG)
        self.resizable(True, True)

        # Data
        self.energy_history = [0] * HISTORY
        self.acc_count      = 0
        self.map_url        = ""
        self.serial_conn    = None

        # Tk vars
        self.v_energy  = tk.IntVar(value=0)
        self.v_x       = tk.StringVar(value="0")
        self.v_y       = tk.StringVar(value="0")
        self.v_z       = tk.StringVar(value="0")
        self.v_lat     = tk.StringVar(value="Waiting...")
        self.v_lon     = tk.StringVar(value="Waiting...")
        self.v_gps     = tk.StringVar(value="SEARCHING")
        self.v_count   = tk.StringVar(value="0")
        self.v_conn    = tk.StringVar(value="● Connecting...")
        self.v_port    = tk.StringVar(value=find_port())
        self.v_status  = tk.StringVar(value="MONITORING")

        self._build()
        self._start_serial()
        self._tick()

    # ══════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════
    def _build(self):

        # ── TOP HEADER ────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(14, 4))

        tk.Label(hdr, text="🚨",
                 font=("Segoe UI Emoji", 22),
                 bg=BG, fg=RED).pack(side="left")

        tk.Label(hdr, text="  SMART ACCIDENT DETECTION SYSTEM",
                 font=("Consolas", 17, "bold"),
                 bg=BG, fg=WHT).pack(side="left")

        self.lbl_clock = tk.Label(hdr, text="",
                                   font=("Consolas", 11),
                                   bg=BG, fg=BLUE)
        self.lbl_clock.pack(side="right")

        # ── CONNECTION BAR ────────────────────────────────────
        cbar = tk.Frame(self, bg=CARD2, pady=0)
        cbar.pack(fill="x", padx=20, pady=4)

        self.dot = tk.Label(cbar, text="●",
                             font=("Consolas", 14),
                             bg=CARD2, fg=YEL)
        self.dot.pack(side="left", padx=(12, 4), pady=6)

        self.lbl_conn = tk.Label(cbar, textvariable=self.v_conn,
                                  font=("Consolas", 10, "bold"),
                                  bg=CARD2, fg=YEL)
        self.lbl_conn.pack(side="left", pady=6)

        # Port selector
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb = ttk.Combobox(cbar, textvariable=self.v_port,
                                     values=ports, width=9,
                                     font=("Consolas", 9))
        self.port_cb.pack(side="right", padx=8, pady=6)

        tk.Label(cbar, text="Port:", bg=CARD2, fg=GRY,
                 font=("Consolas", 9)).pack(side="right")

        tk.Button(cbar, text="⟳  RECONNECT",
                  command=self._reconnect,
                  font=("Consolas", 9, "bold"),
                  bg=BLUE, fg=BG, relief="flat",
                  padx=10, pady=3,
                  cursor="hand2").pack(side="right", padx=8, pady=6)

        # ── STAT CARDS ROW ────────────────────────────────────
        r1 = tk.Frame(self, bg=BG)
        r1.pack(fill="x", padx=20, pady=(8, 4))
        for i in range(4): r1.columnconfigure(i, weight=1)

        self._card(r1, "⚡ SHAKE ENERGY", self.v_energy,  "",  ORG,   0)
        self._card(r1, "🛰  GPS STATUS",   self.v_gps,    "",  GREEN, 1)
        self._card(r1, "🔔 ACCIDENTS",     self.v_count,  "",  RED,   2)
        self._card(r1, "📡 SYSTEM",        self.v_status, "",  TEAL,  3)

        # ── MAIN AREA ─────────────────────────────────────────
        mid = tk.Frame(self, bg=BG)
        mid.pack(fill="both", expand=True, padx=20, pady=4)
        mid.columnconfigure(0, weight=5)
        mid.columnconfigure(1, weight=3)
        mid.rowconfigure(0, weight=1)

        # ── ENERGY GRAPH (left) ───────────────────────────────
        gc = tk.Frame(mid, bg=CARD,
                       highlightbackground=BDR, highlightthickness=1)
        gc.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ghead = tk.Frame(gc, bg=CARD)
        ghead.pack(fill="x", padx=14, pady=(10, 4))

        tk.Label(ghead, text="📊  REAL-TIME SHAKE ENERGY",
                 font=("Consolas", 10, "bold"),
                 bg=CARD, fg=ORG).pack(side="left")

        self.lbl_live_e = tk.Label(ghead, text="Energy: 0",
                                    font=("Consolas", 10),
                                    bg=CARD, fg=YEL)
        self.lbl_live_e.pack(side="right")

        # Energy bar
        bar_frame = tk.Frame(gc, bg=CARD)
        bar_frame.pack(fill="x", padx=14, pady=(0, 6))

        tk.Label(bar_frame, text="0",
                 font=("Consolas", 8), bg=CARD, fg=GRY).pack(side="left")
        tk.Label(bar_frame, text=str(TRIGGER_LEVEL),
                 font=("Consolas", 8), bg=CARD, fg=RED).pack(side="right")

        self.ebar_bg = tk.Frame(gc, bg=BDR, height=12)
        self.ebar_bg.pack(fill="x", padx=14, pady=(0, 8))
        self.ebar_fill = tk.Frame(self.ebar_bg, bg=ORG, height=12)
        self.ebar_fill.place(x=0, y=0, relheight=1, width=0)

        # Canvas graph
        self.canvas = tk.Canvas(gc, bg=DRK, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.canvas.bind("<Configure>", lambda e: self._draw_graph())

        # X Y Z row
        xyz_row = tk.Frame(gc, bg=CARD)
        xyz_row.pack(fill="x", padx=14, pady=(0, 10))
        for i in range(3): xyz_row.columnconfigure(i, weight=1)

        for i, (lbl, var, col) in enumerate([
            ("X Axis", self.v_x, "#FF6060"),
            ("Y Axis", self.v_y, "#60FF90"),
            ("Z Axis", self.v_z, "#60C0FF"),
        ]):
            f = tk.Frame(xyz_row, bg=CARD2,
                          highlightbackground=BDR, highlightthickness=1)
            f.grid(row=0, column=i, sticky="nsew", padx=3, ipady=4)
            tk.Label(f, text=lbl, font=("Consolas", 8),
                     bg=CARD2, fg=GRY).pack(anchor="w", padx=8, pady=(4,0))
            tk.Label(f, textvariable=var,
                     font=("Consolas", 16, "bold"),
                     bg=CARD2, fg=col).pack(anchor="w", padx=8)

        # ── RIGHT PANEL ───────────────────────────────────────
        rp = tk.Frame(mid, bg=BG)
        rp.grid(row=0, column=1, sticky="nsew")
        rp.rowconfigure(0, weight=1)
        rp.rowconfigure(1, weight=1)
        rp.columnconfigure(0, weight=1)

        # Location card
        lc = tk.Frame(rp, bg=CARD,
                       highlightbackground=BDR, highlightthickness=1)
        lc.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        tk.Label(lc, text="📍  GPS LOCATION",
                 font=("Consolas", 10, "bold"),
                 bg=CARD, fg=BLUE).pack(anchor="w", padx=14, pady=(10, 6))

        for lbl, var in [("Latitude",  self.v_lat),
                          ("Longitude", self.v_lon)]:
            tk.Label(lc, text=lbl, font=("Consolas", 8),
                     bg=CARD, fg=GRY).pack(anchor="w", padx=14)
            tk.Label(lc, textvariable=var,
                     font=("Consolas", 11, "bold"),
                     bg=CARD, fg=WHT,
                     wraplength=280).pack(anchor="w", padx=14, pady=(0, 8))

        tk.Frame(lc, bg=BDR, height=1).pack(fill="x", padx=14, pady=4)

        self.btn_map = tk.Button(lc, text="🗺   OPEN GOOGLE MAPS",
                                  command=self._open_map,
                                  font=("Consolas", 9, "bold"),
                                  bg=BLUE, fg=BG, relief="flat",
                                  pady=8, cursor="hand2",
                                  state="disabled")
        self.btn_map.pack(fill="x", padx=14, pady=6)

        # Last accident card
        ac = tk.Frame(rp, bg=CARD,
                       highlightbackground=BDR, highlightthickness=1)
        ac.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        tk.Label(ac, text="🚨  LAST ACCIDENT",
                 font=("Consolas", 10, "bold"),
                 bg=CARD, fg=RED).pack(anchor="w", padx=14, pady=(10, 6))

        self.lbl_acc_time = tk.Label(ac, text="No accident yet",
                                      font=("Consolas", 10),
                                      bg=CARD, fg=GRY)
        self.lbl_acc_time.pack(anchor="w", padx=14)

        self.lbl_acc_energy = tk.Label(ac, text="",
                                        font=("Consolas", 10),
                                        bg=CARD, fg=YEL)
        self.lbl_acc_energy.pack(anchor="w", padx=14, pady=2)

        self.lbl_acc_gps = tk.Label(ac, text="",
                                     font=("Consolas", 9),
                                     bg=CARD, fg=GRY,
                                     wraplength=280, justify="left")
        self.lbl_acc_gps.pack(anchor="w", padx=14, pady=2)

        tk.Frame(ac, bg=BDR, height=1).pack(fill="x", padx=14, pady=6)

        # Reset button
        tk.Button(ac, text="🔄  RESET SYSTEM",
                  command=self._reset,
                  font=("Consolas", 9, "bold"),
                  bg=CARD2, fg=GRY, relief="flat",
                  pady=6, cursor="hand2").pack(fill="x", padx=14, pady=(0, 10))

        # ── ALERT BANNER (hidden) ─────────────────────────────
        self.alert_frame = tk.Frame(self, bg=RED)
        self.alert_lbl   = tk.Label(self.alert_frame,
                                     text="", bg=RED, fg=WHT,
                                     font=("Consolas", 11, "bold"), pady=7)
        self.alert_lbl.pack(side="left", padx=14)
        tk.Button(self.alert_frame, text="🗺 VIEW MAP",
                  command=self._open_map,
                  bg=WHT, fg=RED,
                  font=("Consolas", 9, "bold"),
                  relief="flat", padx=10).pack(side="right", padx=10)

        # ── LOG ───────────────────────────────────────────────
        lf = tk.Frame(self, bg=CARD,
                       highlightbackground=BDR, highlightthickness=1)
        lf.pack(fill="x", padx=20, pady=(4, 14))

        tk.Label(lf, text="📋  LOG",
                 font=("Consolas", 9, "bold"),
                 bg=CARD, fg=BLUE).pack(anchor="w", padx=14, pady=(6, 2))

        self.log = tk.Text(lf, height=4, bg=DRK, fg=WHT,
                            font=("Consolas", 8),
                            relief="flat", state="disabled")
        self.log.pack(fill="x", padx=14, pady=(0, 8))
        self.log.tag_config("red",    foreground=RED)
        self.log.tag_config("green",  foreground=GREEN)
        self.log.tag_config("yellow", foreground=YEL)
        self.log.tag_config("blue",   foreground=BLUE)
        self.log.tag_config("orange", foreground=ORG)

        self._log(f"Dashboard started — port: {self.v_port.get()}", "blue")

    # ── Stat card ─────────────────────────────────────────────
    def _card(self, parent, title, var, unit, color, col):
        c = tk.Frame(parent, bg=CARD,
                      highlightbackground=BDR, highlightthickness=1)
        c.grid(row=0, column=col, sticky="nsew", padx=4, ipady=6)
        tk.Label(c, text=title,
                 font=("Consolas", 8, "bold"),
                 bg=CARD, fg=GRY).pack(anchor="w", padx=12, pady=(8, 0))
        tk.Label(c, textvariable=var,
                 font=("Consolas", 20, "bold"),
                 bg=CARD, fg=color).pack(anchor="w", padx=12, pady=2)

    # ══════════════════════════════════════════════════════════
    #  GRAPH
    # ══════════════════════════════════════════════════════════
    def _draw_graph(self):
        cv = self.canvas
        cv.delete("all")
        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 20 or h < 20:
            return

        # Grid
        for i in range(1, 5):
            y = int(h - h * i / 4)
            cv.create_line(0, y, w, y, fill="#0C1A25", dash=(3, 5))
            val = int(ENERGY_MAX * i / 4)
            cv.create_text(6, y - 8, text=str(val),
                           fill=GRY, font=("Consolas", 7), anchor="w")

        # Trigger line
        ty = int(h - h * TRIGGER_LEVEL / ENERGY_MAX)
        cv.create_line(0, ty, w, ty, fill=RED, dash=(6, 3), width=1)
        cv.create_text(w - 8, ty - 9, text="TRIGGER",
                       fill=RED, font=("Consolas", 7), anchor="e")

        # Plot
        n   = len(self.energy_history)
        pts = [(int(w * i / (n - 1)),
                int(h - h * min(v, ENERGY_MAX) / ENERGY_MAX))
               for i, v in enumerate(self.energy_history)]

        if len(pts) > 1:
            poly = [(pts[0][0], h)] + pts + [(pts[-1][0], h)]
            cv.create_polygon([v for p in poly for v in p],
                               fill="#0A1C10", outline="")
            cv.create_line(*[v for p in pts for v in p],
                           fill=ORG, width=2, smooth=True)

            lx, ly  = pts[-1]
            cur     = self.energy_history[-1]
            dot_col = RED if cur >= TRIGGER_LEVEL else ORG
            cv.create_oval(lx - 5, ly - 5, lx + 5, ly + 5,
                           fill=dot_col, outline=WHT, width=1)

    # ── Energy bar ────────────────────────────────────────────
    def _update_ebar(self, energy):
        self.ebar_bg.update_idletasks()
        total  = self.ebar_bg.winfo_width()
        pct    = min(energy / ENERGY_MAX, 1.0)
        fw     = int(total * pct)
        color  = RED if energy >= TRIGGER_LEVEL else (YEL if energy > 40 else ORG)
        self.ebar_fill.config(bg=color)
        self.ebar_fill.place(x=0, y=0, width=fw, relheight=1)

    # ══════════════════════════════════════════════════════════
    #  SERIAL
    # ══════════════════════════════════════════════════════════
    def _start_serial(self):
        threading.Thread(target=self._serial_loop, daemon=True).start()

    def _serial_loop(self):
        while True:
            try:
                port = self.v_port.get()
                conn = serial.Serial(port, BAUD, timeout=1)
                self.serial_conn = conn
                self.after(0, self._on_connected)
                self._log(f"Connected → {port}", "green")

                buf = ""
                while True:
                    ch = conn.read(1).decode("utf-8", errors="ignore")
                    if ch == "\n":
                        line = buf.strip()
                        buf  = ""
                        if line.startswith("{"):
                            self.after(0, lambda l=line: self._handle(l))
                    else:
                        buf += ch

            except serial.SerialException:
                self.after(0, self._on_disconnected)
                time.sleep(3)
            except Exception as e:
                self._log(f"Error: {e}", "red")
                time.sleep(3)

    def _on_connected(self):
        self.v_conn.set(f"● CONNECTED  {self.v_port.get()}")
        self.lbl_conn.config(fg=GREEN)
        self.dot.config(fg=GREEN)

    def _on_disconnected(self):
        self.v_conn.set("● DISCONNECTED — retrying...")
        self.lbl_conn.config(fg=RED)
        self.dot.config(fg=RED)

    # ══════════════════════════════════════════════════════════
    #  HANDLE JSON
    # ══════════════════════════════════════════════════════════
    def _handle(self, raw):
        try:
            d = json.loads(raw)
        except:
            return

        t = d.get("type", "")

        # ── STATUS ────────────────────────────────────────────
        if t == "STATUS":
            msg = d.get("msg", "")
            if msg == "READY":
                self.v_status.set("ACTIVE")
                self._log("Arduino ready!", "green")
            elif msg == "GPS_FIXED":
                self.v_gps.set("FIXED ✓")
                self._log("GPS Fixed!", "green")
            elif msg == "GPS_NO_FIX":
                self.v_gps.set("NO FIX")
                self._log("GPS not fixed", "yellow")
            return

        # ── LIVE DATA ─────────────────────────────────────────
        if t == "LIVE":
            energy = int(d.get("energy", 0))
            x      = int(d.get("x", 0))
            y      = int(d.get("y", 0))
            z      = int(d.get("z", 0))

            self.v_energy.set(energy)
            self.v_x.set(str(x))
            self.v_y.set(str(y))
            self.v_z.set(str(z))
            self.lbl_live_e.config(text=f"Energy: {energy}")

            # Graph
            self.energy_history.append(energy)
            self.energy_history = self.energy_history[-HISTORY:]
            self._draw_graph()
            self._update_ebar(energy)

            # Status color
            if energy >= TRIGGER_LEVEL:
                self.v_conn.set(f"⚠  HIGH ENERGY: {energy}")
                self.lbl_conn.config(fg=RED)
                self.dot.config(fg=RED)
            else:
                self.v_conn.set(f"● MONITORING  |  {self.v_port.get()}")
                self.lbl_conn.config(fg=GREEN)
                self.dot.config(fg=GREEN)

        # ── ACCIDENT ──────────────────────────────────────────
        elif t == "ACCIDENT":
            self._on_accident(d)

    # ══════════════════════════════════════════════════════════
    #  ACCIDENT
    # ══════════════════════════════════════════════════════════
    def _on_accident(self, d):
        self.acc_count += 1
        self.v_count.set(str(self.acc_count))

        energy    = int(d.get("energy",    0))
        lat       = d.get("lat",       "")
        lon       = d.get("lon",       "")
        gps_fixed = d.get("gps_fixed", False)
        ts        = datetime.now().strftime("%d-%m-%Y  %H:%M:%S")

        if gps_fixed and lat:
            self.map_url = f"https://www.google.com/maps?q={lat},{lon}"
            self.btn_map.config(state="normal")
            loc_txt  = f"{lat}, {lon}"
            gps_disp = f"📍 {lat}\n    {lon}"
        else:
            loc_txt  = "GPS not fixed"
            gps_disp = "❌ GPS not fixed"

        # Update last accident panel
        self.lbl_acc_time.config(text=f"🕐 {ts}", fg=WHT)
        self.lbl_acc_energy.config(text=f"⚡ Energy: {energy}")
        self.lbl_acc_gps.config(text=gps_disp, fg=TEAL if gps_fixed else GRY)

        # Red alert banner
        self.alert_lbl.config(
            text=f"🚨  ACCIDENT #{self.acc_count}  |  Energy={energy}  |  {loc_txt}"
        )
        self.alert_frame.pack(fill="x", padx=20, pady=2,
                               before=self.log.master)

        # Log
        self._log(f"🚨 ACCIDENT #{self.acc_count}  energy={energy}", "red")
        if gps_fixed:
            self._log(f"   📍 {lat}, {lon}", "yellow")
            self._log(f"   🗺 {self.map_url}", "orange")
            self.after(500, self._open_map)
        else:
            self._log("   ❌ GPS not fixed", "yellow")

    # ══════════════════════════════════════════════════════════
    def _open_map(self):
        if self.map_url:
            webbrowser.open(self.map_url)
        else:
            self._log("No GPS location available", "yellow")

    def _reset(self):
        """Reset triggered flag on Arduino side by reconnecting."""
        self._log("Resetting — reconnecting serial...", "blue")
        self.alert_frame.pack_forget()
        if self.serial_conn:
            try: self.serial_conn.close()
            except: pass
        self.lbl_acc_time.config(text="No accident yet", fg=GRY)
        self.lbl_acc_energy.config(text="")
        self.lbl_acc_gps.config(text="")

    def _reconnect(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if self.serial_conn:
            try: self.serial_conn.close()
            except: pass
        self._log(f"Reconnecting → {self.v_port.get()}", "blue")

    def _log(self, msg, tag=""):
        self.log.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _tick(self):
        self.lbl_clock.config(
            text=datetime.now().strftime("%d-%m-%Y   %H:%M:%S"))
        self.after(1000, self._tick)

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()
