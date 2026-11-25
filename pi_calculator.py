#!/usr/bin/python3
# Calculator for Raspberry Pi, styled after the Windows 11 Calculator (dark).
import os
import sys
import re
import json
import math
import time
import shutil
import signal
import threading
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, Gio, GObject  # noqa: E402,F401
import cairo  # noqa: E402

HOME = os.path.expanduser("~")
C_ACCENT = "#4CC2FF"
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def _rr(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _line(cr, *pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()


def draw_glyph(cr, name, s, col):
    """Monochrome line icons for buttons."""
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    cr.set_source_rgba(*col)
    cr.set_line_width(1.15)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    pi = math.pi
    L = lambda *p: _line(cr, *p)  # noqa: E731
    if name == "back":
        L((13.5, 8), (2.5, 8))
        L((7, 3.5), (2.5, 8), (7, 12.5))
    elif name == "forward":
        L((2.5, 8), (13.5, 8))
        L((9, 3.5), (13.5, 8), (9, 12.5))
    elif name == "up":
        L((8, 13.5), (8, 2.5))
        L((3.5, 7), (8, 2.5), (12.5, 7))
    elif name == "refresh":
        cr.arc(8, 8, 5.5, -pi * 0.35, pi * 1.55)
        cr.stroke()
        L((12.9, 1.8), (12.6, 4.9), (9.6, 4.6))
    elif name == "plus":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "new":
        cr.set_source_rgba(*hexc(C_ACCENT))
        cr.arc(8, 8, 6.5, 0, 2 * pi)
        cr.stroke()
        L((8, 4.8), (8, 11.2))
        L((4.8, 8), (11.2, 8))
    elif name == "cut":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(11.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        L((5.8, 10.5), (11, 1.8))
        L((10.2, 10.5), (5, 1.8))
    elif name == "copy":
        _rr(cr, 5, 1.5, 9, 10.5, 1.5)
        cr.stroke()
        cr.move_to(3, 4.5)
        cr.line_to(3, 13)
        cr.arc_negative(4.5, 13, 1.5, pi, pi / 2)
        cr.line_to(11, 14.5)
        cr.stroke()
    elif name == "paste":
        _rr(cr, 2.5, 3, 11, 11.5, 1.5)
        cr.stroke()
        _rr(cr, 5.5, 1.5, 5, 3, 1)
        cr.stroke()
        L((5.5, 8), (10.5, 8))
        L((5.5, 11), (9, 11))
    elif name == "rename":
        _rr(cr, 1.5, 4.5, 13, 7, 1.3)
        cr.stroke()
        L((4, 8), (8, 8))
        L((10.5, 2.5), (10.5, 13.5))
        L((9, 2.5), (12, 2.5))
        L((9, 13.5), (12, 13.5))
    elif name == "delete" or name == "trash":
        L((2.5, 4), (13.5, 4))
        L((6, 4), (6.5, 2), (9.5, 2), (10, 4))
        cr.move_to(4, 4)
        cr.line_to(4.8, 14)
        cr.line_to(11.2, 14)
        cr.line_to(12, 4)
        cr.stroke()
        L((6.8, 6.8), (7, 11.5))
        L((9.2, 6.8), (9, 11.5))
    elif name == "sort":
        L((4.5, 2.5), (4.5, 13.5))
        L((2, 5), (4.5, 2.5), (7, 5))
        L((11.5, 2.5), (11.5, 13.5))
        L((9, 11), (11.5, 13.5), (14, 11))
    elif name == "view":
        for y in (3, 8, 13):
            L((2, y), (14, y))
    elif name == "more":
        for x in (3, 8, 13):
            cr.arc(x, 8, 1.1, 0, 2 * pi)
            cr.fill()
    elif name == "chevdown":
        L((4, 6), (8, 10), (12, 6))
    elif name == "chevright":
        L((6, 4), (10, 8), (6, 12))
    elif name == "close":
        L((3.5, 3.5), (12.5, 12.5))
        L((12.5, 3.5), (3.5, 12.5))
    elif name == "min":
        L((3, 8), (13, 8))
    elif name == "max":
        _rr(cr, 3, 3, 10, 10, 1.2)
        cr.stroke()
    elif name == "restore":
        _rr(cr, 3, 5, 8, 8, 1.2)
        cr.stroke()
        L((5, 3), (12, 3), (13, 4), (13, 11))
    elif name == "search":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
    elif name == "pane":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((10, 2.5), (10, 13.5))
    elif name == "terminal":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((4, 6), (6.5, 8), (4, 10))
        L((8, 10.5), (11.5, 10.5))
    elif name == "properties":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (5, 8, 11):
            cr.arc(5.2, y, 0.8, 0, 2 * pi)
            cr.fill()
            L((7.2, y), (11, y))
    elif name == "pin":
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "pin-fill":
        cr.set_line_width(1.0)
        cr.translate(8, 8)
        cr.rotate(pi / 4)
        cr.translate(-8, -8)
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    elif name == "file":
        cr.move_to(3.5, 1.5)
        cr.line_to(9.5, 1.5)
        cr.line_to(12.5, 4.5)
        cr.line_to(12.5, 14.5)
        cr.line_to(3.5, 14.5)
        cr.close_path()
        cr.stroke()
        L((9.5, 1.5), (9.5, 4.5), (12.5, 4.5))
    elif name == "zip":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (3, 5, 7):
            L((7, y), (9, y))
        _rr(cr, 6.5, 9, 3, 3.5, 0.6)
        cr.stroke()
    elif name == "extract":
        _rr(cr, 2.5, 6.5, 11, 8, 1.5)
        cr.stroke()
        L((8, 1.5), (8, 10))
        L((5.5, 7.5), (8, 10), (10.5, 7.5))
    elif name == "restoreitem":
        cr.arc(8.5, 8.5, 5, -pi * 0.9, pi * 0.6)
        cr.stroke()
        L((2, 3.5), (3.6, 6.6), (6.6, 5.4))
    elif name == "open":
        _rr(cr, 1.5, 1.5, 13, 13, 2)
        cr.stroke()
        L((7, 9), (12.5, 3.5))
        L((8.5, 3.5), (12.5, 3.5), (12.5, 7.5))
    elif name == "newtab":
        _rr(cr, 1.5, 3.5, 13, 10, 1.5)
        cr.stroke()
        L((1.5, 6), (8, 6))
        L((8, 3.5), (8, 6))
    elif name == "check":
        L((3, 8.5), (6.5, 12), (13, 4.5))
    elif name == "eject":
        cr.move_to(8, 3)
        cr.line_to(13, 9)
        cr.line_to(3, 9)
        cr.close_path()
        cr.stroke()
        L((3, 12.5), (13, 12.5))
    elif name == "details-view":
        for y in (3.5, 8, 12.5):
            _rr(cr, 1.5, y - 1.2, 2.4, 2.4, 0.5)
            cr.stroke()
            L((6, y), (14.5, y))
    elif name == "icons-view":
        for x in (2, 9):
            for y in (2, 9):
                _rr(cr, x, y, 5, 5, 1.2)
                cr.stroke()
    elif name == "selectall":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        L((5, 8), (7.2, 10.2), (11, 6))
    elif name == "info":
        cr.arc(8, 8, 6, 0, 2 * pi)
        cr.stroke()
        L((8, 7), (8, 11.5))
        cr.arc(8, 4.8, 0.9, 0, 2 * pi)
        cr.fill()
    elif name == "share":
        cr.arc(4, 8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 3.8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 12.2, 1.8, 0, 2 * pi)
        cr.stroke()
        L((5.6, 7.1), (10.4, 4.7))
        L((5.6, 8.9), (10.4, 11.3))
    elif name == "network":
        _rr(cr, 5, 1.5, 6, 4.5, 1)
        cr.stroke()
        L((8, 6), (8, 9))
        L((3, 9), (13, 9))
        L((3, 9), (3, 11))
        L((13, 9), (13, 11))
        _rr(cr, 1, 11, 4, 3.5, 0.8)
        cr.stroke()
        _rr(cr, 11, 11, 4, 3.5, 0.8)
        cr.stroke()
    elif name == "link":
        cr.arc(5.5, 10.5, 3, pi * 0.25, pi * 1.75)
        cr.stroke()
        cr.arc(10.5, 5.5, 3, pi * 1.25, pi * 0.75)
        cr.stroke()
        L((6.5, 9.5), (9.5, 6.5))
    else:
        draw_glyph_extra(cr, name, L, pi)
    cr.restore()




# ----------------------------------------------------------------------------
# Shared Windows 11 dark style
# ----------------------------------------------------------------------------
BASE_CSS = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", "Selawik", "Open Sans", "Noto Sans", sans-serif; }
window.fx, window.fx-dialog { background-color: #202020; color: #ffffff; font-size: 12px; }
.fx label { color: #ffffff; }
headerbar.fx-title { background: #202020; border: none; box-shadow: none; min-height: 40px; padding: 0; margin: 0; }
headerbar.fx-title:backdrop { background: #202020; }
.app-title { font-size: 12px; color: #ffffff; margin-left: 4px; }
.app-title:backdrop { color: rgba(255,255,255,0.55); }
button.wc { background: transparent; border: none; border-radius: 0; min-width: 46px; min-height: 32px; padding: 0; box-shadow: none; }
button.wc:hover { background-color: rgba(255,255,255,0.06); }
button.wc.close:hover { background-color: #C42B1C; }
.tabstrip { margin-top: 6px; margin-left: 6px; }
button.tab { outline-color: transparent; background: transparent; border: none; border-radius: 8px 8px 0 0; min-height: 34px;
   padding: 0 6px 0 12px; box-shadow: none; margin-right: 1px; }
button.tab:hover { background-color: rgba(255,255,255,0.04); }
button.tab.active { background-color: #2C2C2C; }
button.tab label { font-size: 12px; }
button.tab-x { background: transparent; border: none; border-radius: 4px; min-width: 24px; min-height: 24px; padding: 0; box-shadow: none; }
button.tab-x:hover { background-color: rgba(255,255,255,0.08); }
button.tab-new { background: transparent; border: none; border-radius: 4px; min-width: 32px; min-height: 28px; padding: 0;
   box-shadow: none; margin-top: 4px; margin-left: 2px; }
button.tab-new:hover { background-color: rgba(255,255,255,0.06); }
.bar { background-color: #2C2C2C; padding: 4px 8px; }
.bar-bottom { border-bottom: 1px solid rgba(255,255,255,0.06); }
button.tb, button.nb { background: transparent; border: none; border-radius: 4px; min-height: 32px; padding: 0 9px; box-shadow: none; color: #ffffff; }
button.nb { min-width: 34px; padding: 0; }
button.tb:hover, button.nb:hover { background-color: rgba(255,255,255,0.06); }
button.tb:active, button.nb:active { background-color: rgba(255,255,255,0.04); }
button.tb:disabled label { color: rgba(255,255,255,0.36); }
button.tb label { font-size: 12px; }
button.tb.on, button.nb.on { background-color: rgba(255,255,255,0.09); }
.vsep { background-color: rgba(255,255,255,0.08); min-width: 1px; margin: 6px 6px; }
.status { background-color: #202020; padding: 4px 12px; border-top: 1px solid rgba(255,255,255,0.06); }
.status label { font-size: 12px; color: rgba(255,255,255,0.786); }
.sec { color: rgba(255,255,255,0.786); }
.ter { color: rgba(255,255,255,0.545); }
.big-title { font-size: 20px; font-weight: 600; }
.sect-title { font-size: 14px; font-weight: 600; }
entry.field, entry.fx-search { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07);
   border-bottom: 1px solid rgba(255,255,255,0.54); border-radius: 4px; min-height: 30px; padding: 0 10px; box-shadow: none;
   font-size: 12px; caret-color: #ffffff; }
entry.field:focus, entry.fx-search:focus { background-color: #1c1c1c; border-bottom: 2px solid #4CC2FF; }
entry selection, textview text selection, entry selection:focus, textview text selection:focus { background-color: #0078D4; color: #ffffff; }
scrollbar { background: transparent; border: none; }
scrollbar slider { background-color: rgba(255,255,255,0.45); border-radius: 6px; min-width: 3px; min-height: 3px; border: none; }
scrollbar:hover slider { min-width: 6px; min-height: 6px; background-color: rgba(255,255,255,0.55); }
scrollbar trough { background: transparent; border: none; }
scale trough { background-color: rgba(255,255,255,0.3); border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale highlight { background-color: #4CC2FF; border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale slider { background-color: #4CC2FF; border: 5px solid #454545; border-radius: 50%; min-width: 12px; min-height: 12px; box-shadow: none; }
scale slider:hover { border-width: 4px; }
menu, .menu, .context-menu { background-color: #2C2C2C; color: #ffffff; border: 1px solid rgba(0,0,0,0.45); border-radius: 8px; padding: 4px; }
menu menuitem { padding: 6px 12px; border-radius: 4px; color: #ffffff; min-height: 18px; }
menu menuitem:hover { background-color: rgba(255,255,255,0.06); }
menu menuitem:disabled label { color: rgba(255,255,255,0.36); }
menu menuitem label { color: #ffffff; font-size: 12px; }
menu menuitem arrow { color: rgba(255,255,255,0.786); }
menu separator { background-color: rgba(255,255,255,0.08); margin: 4px 0; min-height: 1px; }
window.fx button, window.fx-dialog button { background-image: none; text-shadow: none; -gtk-icon-shadow: none; }
button.primary { background-color: #4CC2FF; color: #000000; border: none; border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.primary label { color: #000000; }
button.primary:hover { background-color: #48B1E8; }
button.secondary { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.09); border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.secondary:hover { background-color: rgba(255,255,255,0.09); }
.dlg-body { background-color: #2B2B2B; padding: 24px; }
.dlg-foot { background-color: #202020; padding: 22px 24px; border-top: 1px solid rgba(0,0,0,0.3); }
.dlg-title { font-size: 20px; font-weight: 600; }
.fx-dialog label { color: #ffffff; }
.fx-dialog label.sec { color: rgba(255,255,255,0.786); }
.fx-dialog label.ter { color: rgba(255,255,255,0.545); }
checkbutton check { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 4px; min-width: 18px; min-height: 18px; -gtk-icon-source: none; color: #000000; }
checkbutton check:checked { background-color: #4CC2FF; border-color: #4CC2FF; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
checkbutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
radiobutton radio { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 50%; min-width: 18px; min-height: 18px; -gtk-icon-source: none; }
radiobutton radio:checked { background-color: #000000; border: 5px solid #4CC2FF; }
radiobutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
switch { background-color: transparent; border: 1px solid rgba(255,255,255,0.6); border-radius: 12px; min-width: 40px; min-height: 18px; }
switch:checked { background-color: #4CC2FF; border-color: #4CC2FF; }
switch slider { background-color: rgba(255,255,255,0.8); border-radius: 50%; min-width: 12px; min-height: 12px; margin: 3px; border: none; box-shadow: none; }
switch:checked slider { background-color: #000000; }
switch image { color: transparent; }
combobox button, combobox box { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; min-height: 30px; }
combobox button cellview, combobox button label, combobox arrow { color: #ffffff; }
spinbutton { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; }
spinbutton entry { background: transparent; border: none; box-shadow: none; color: #ffffff; }
spinbutton button { background: transparent; border: none; box-shadow: none; color: #ffffff; }
tooltip, tooltip.background { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.4); border-radius: 4px; }
tooltip label { color: #ffffff; font-size: 12px; }
.set-group { background-color: rgba(255,255,255,0.05); border-radius: 4px; border: 1px solid rgba(0,0,0,0.2); padding: 12px 16px; }
.set-head { font-size: 13px; }
.set-desc { font-size: 12px; color: rgba(255,255,255,0.6); }
"""


def apply_css(extra=""):
    prov = Gtk.CssProvider()
    prov.load_from_data((BASE_CSS + extra).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)


def draw_glyph_extra(cr, name, L, pi):
    if name == "save":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        _rr(cr, 4.5, 2, 6, 4, 0.5)
        cr.stroke()
        _rr(cr, 4.5, 9, 7, 5, 0.5)
        cr.stroke()
    elif name == "undo":
        cr.move_to(3, 7)
        cr.curve_to(6, 3.5, 13, 4.5, 13, 10)
        cr.stroke()
        L((3, 3), (3, 7), (7, 7))
    elif name == "redo":
        cr.move_to(13, 7)
        cr.curve_to(10, 3.5, 3, 4.5, 3, 10)
        cr.stroke()
        L((13, 3), (13, 7), (9, 7))
    elif name == "replace":
        L((2, 5), (10, 5))
        L((7.5, 2.5), (10, 5), (7.5, 7.5))
        L((14, 11), (6, 11))
        L((8.5, 8.5), (6, 11), (8.5, 13.5))
    elif name == "zoomin":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
        L((6.6, 4.6), (6.6, 8.6))
    elif name == "zoomout":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
    elif name == "fit":
        L((2, 5.5), (2, 2), (5.5, 2))
        L((10.5, 2), (14, 2), (14, 5.5))
        L((14, 10.5), (14, 14), (10.5, 14))
        L((5.5, 14), (2, 14), (2, 10.5))
    elif name == "wrap":
        L((2, 3), (14, 3))
        cr.move_to(2, 8)
        cr.line_to(11.5, 8)
        cr.curve_to(15, 8, 15, 13, 11.5, 13)
        cr.line_to(8, 13)
        cr.stroke()
        L((9.5, 11.3), (8, 13), (9.5, 14.7))
        L((2, 13), (5, 13))
    elif name == "play":
        cr.move_to(4.5, 2.5)
        cr.line_to(13, 8)
        cr.line_to(4.5, 13.5)
        cr.close_path()
        cr.fill()
    elif name == "pause":
        _rr(cr, 3.5, 2.5, 3, 11, 0.8)
        cr.fill()
        _rr(cr, 9.5, 2.5, 3, 11, 0.8)
        cr.fill()
    elif name in ("next", "prev"):
        if name == "prev":
            cr.translate(16, 0)
            cr.scale(-1, 1)
        cr.move_to(3, 3)
        cr.line_to(10.5, 8)
        cr.line_to(3, 13)
        cr.close_path()
        cr.fill()
        _rr(cr, 11, 3, 2, 10, 0.6)
        cr.fill()
    elif name == "shuffle":
        L((2, 4), (5, 4), (11, 12), (14, 12))
        L((2, 12), (5, 12), (11, 4), (14, 4))
        L((12, 2), (14, 4), (12, 6))
        L((12, 10), (14, 12), (12, 14))
    elif name in ("repeat", "repeat1"):
        cr.move_to(3, 9)
        cr.line_to(3, 6)
        cr.arc(5, 6, 2, pi, 1.5 * pi)
        cr.line_to(13, 4)
        cr.stroke()
        L((11, 2), (13, 4), (11, 6))
        cr.move_to(13, 7)
        cr.line_to(13, 10)
        cr.arc(11, 10, 2, 0, 0.5 * pi)
        cr.line_to(3, 12)
        cr.stroke()
        L((5, 10), (3, 12), (5, 14))
        if name == "repeat1":
            cr.set_font_size(5)
            cr.move_to(6.8, 9.8)
            cr.show_text("1")
    elif name in ("volume", "mute"):
        cr.move_to(1.5, 6)
        cr.line_to(4.5, 6)
        cr.line_to(8, 2.5)
        cr.line_to(8, 13.5)
        cr.line_to(4.5, 10)
        cr.line_to(1.5, 10)
        cr.close_path()
        cr.stroke()
        if name == "mute":
            L((10.5, 6), (14.5, 10))
            L((14.5, 6), (10.5, 10))
        else:
            cr.arc(8, 8, 3.5, -pi / 3.5, pi / 3.5)
            cr.stroke()
            cr.arc(8, 8, 6.2, -pi / 3.5, pi / 3.5)
            cr.stroke()
    elif name == "fullscreen":
        L((2, 6), (2, 2), (6, 2))
        L((10, 2), (14, 2), (14, 6))
        L((14, 10), (14, 14), (10, 14))
        L((6, 14), (2, 14), (2, 10))
        L((2, 2), (6, 6))
        L((14, 14), (10, 10))
    elif name == "unfullscreen":
        L((6, 2), (6, 6), (2, 6))
        L((10, 2), (10, 6), (14, 6))
        L((10, 14), (10, 10), (14, 10))
        L((6, 14), (6, 10), (2, 10))
    elif name == "rotate":
        cr.arc(8, 9, 5, pi * 1.15, pi * 2.85)
        cr.stroke()
        L((2.5, 2.5), (3.4, 6.4), (7.2, 5.4))
    elif name == "heart":
        cr.move_to(8, 13.5)
        cr.curve_to(1, 8, 1.5, 2.5, 5, 2.5)
        cr.curve_to(6.5, 2.5, 7.5, 3.5, 8, 4.5)
        cr.curve_to(8.5, 3.5, 9.5, 2.5, 11, 2.5)
        cr.curve_to(14.5, 2.5, 15, 8, 8, 13.5)
        cr.stroke()
    elif name == "pen":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
        L((9.5, 4.2), (11.8, 6.5))
    elif name == "highlighter":
        L((3, 13.5), (13, 13.5))
        cr.move_to(5, 11)
        cr.line_to(11, 3)
        cr.line_to(13.5, 5)
        cr.line_to(7.5, 12.5)
        cr.line_to(5, 12.5)
        cr.close_path()
        cr.stroke()
    elif name == "eraser":
        cr.move_to(2.5, 10)
        cr.line_to(9, 3.5)
        cr.line_to(13.5, 8)
        cr.line_to(8, 13.5)
        cr.line_to(5.5, 13.5)
        cr.close_path()
        cr.stroke()
        L((6, 6.5), (10.5, 11))
        L((8, 13.5), (14, 13.5))
    elif name == "crop":
        L((4.5, 1.5), (4.5, 11.5), (14.5, 11.5))
        L((1.5, 4.5), (11.5, 4.5), (11.5, 14.5))
    elif name == "camera":
        _rr(cr, 1.5, 4, 13, 9.5, 1.6)
        cr.stroke()
        L((5, 4), (6, 2.5), (10, 2.5), (11, 4))
        cr.arc(8, 8.8, 2.6, 0, 2 * pi)
        cr.stroke()
    elif name == "timer":
        cr.arc(8, 9, 5.5, 0, 2 * pi)
        cr.stroke()
        L((8, 9), (8, 5.8))
        L((6.3, 1.8), (9.7, 1.8))
    elif name == "settings":
        n = 8
        cr.new_path()
        for i in range(n * 2):
            a = i * pi / n
            r = 6.6 if i % 2 == 0 else 5.0
            a1, a2 = a - pi / (n * 2.4), a + pi / (n * 2.4)
            cr.line_to(8 + r * math.cos(a1), 8 + r * math.sin(a1))
            cr.line_to(8 + r * math.cos(a2), 8 + r * math.sin(a2))
        cr.close_path()
        cr.stroke()
        cr.arc(8, 8, 2.2, 0, 2 * pi)
        cr.stroke()
    elif name == "history":
        cr.arc(8, 8, 6, pi * 1.05, pi * 2.85)
        cr.stroke()
        L((1.2, 6.2), (2.3, 8.6), (4.6, 7.3))
        L((8, 4.6), (8, 8.2), (10.5, 9.7))
    elif name == "image":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((1.5, 11), (5.5, 7), (9, 10.5), (11, 8.5), (14.5, 12))
        cr.arc(10.5, 5.5, 1.2, 0, 2 * pi)
        cr.stroke()
    elif name == "music":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 10.5, 2, 0, 2 * pi)
        cr.stroke()
        L((6.5, 12), (6.5, 3.5), (14, 2), (14, 10.5))
    elif name == "video":
        _rr(cr, 1.5, 3.5, 9.5, 9, 1.5)
        cr.stroke()
        L((11, 6.5), (14.5, 4.5), (14.5, 11.5), (11, 9.5))
    elif name == "queue":
        for y in (3, 7):
            L((2, y), (14, y))
        L((2, 11), (8, 11))
        cr.move_to(10.5, 9)
        cr.line_to(14, 11.5)
        cr.line_to(10.5, 14)
        cr.close_path()
        cr.fill()
    elif name == "edit":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
    elif name == "slideshow":
        _rr(cr, 1.5, 2.5, 13, 9, 1.5)
        cr.stroke()
        cr.move_to(6.5, 5)
        cr.line_to(10, 7)
        cr.line_to(6.5, 9)
        cr.close_path()
        cr.fill()
        L((5, 14), (11, 14))
    elif name == "print":
        _rr(cr, 1.5, 6, 13, 6, 1.2)
        cr.stroke()
        L((4.5, 6), (4.5, 1.5), (11.5, 1.5), (11.5, 6))
        _rr(cr, 4.5, 9.5, 7, 5, 0.5)
        cr.stroke()
    elif name == "wallpaper":
        _rr(cr, 1.5, 2.5, 13, 9, 1.2)
        cr.stroke()
        L((1.5, 9.5), (5, 6), (8, 9), (10, 7), (14.5, 10.5))
        L((5.5, 14), (10.5, 14))
        L((8, 11.5), (8, 14))
    elif name == "list":
        for y in (3.5, 8, 12.5):
            cr.arc(2.5, y, 0.9, 0, 2 * pi)
            cr.fill()
            L((5.5, y), (14, y))
    elif name == "add":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "split":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((8, 2.5), (8, 13.5))
    elif name == "keyboard":
        _rr(cr, 1, 3.5, 14, 9, 1.5)
        cr.stroke()
        for x in (4, 6.7, 9.3, 12):
            cr.rectangle(x - 0.5, 6, 1, 1)
        cr.fill()
        L((4.5, 10), (11.5, 10))


class Icon(Gtk.DrawingArea):
    """Monochrome glyph icon."""

    def __init__(self, name, size=16, color=None):
        super().__init__()
        self.name = name
        self.size = size
        self.color = color
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    def set_icon(self, name):
        self.name = name
        self.queue_draw()

    def _draw(self, w, cr):
        col = self.color or (1, 1, 1, 1)
        p = self.get_parent()
        if not self.is_sensitive() or (p and not p.is_sensitive()):
            col = (1, 1, 1, 0.36)
        draw_glyph(cr, self.name, self.size, col)


class WinTitlebar(Gtk.HeaderBar):
    """Title bar with Windows 11 caption buttons. Pack your own widgets with pack_start()."""

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.get_style_context().add_class("fx-title")
        self.set_show_close_button(False)
        self.set_custom_title(Gtk.Box())
        wc = Gtk.Box(spacing=0)
        wc.set_valign(Gtk.Align.START)
        for name, cb, extra in (("min", lambda *_: window.iconify(), ""),
                                ("max", lambda *_: self.toggle_max(), ""),
                                ("close", lambda *_: window.close(), "close")):
            b = Gtk.Button()
            b.get_style_context().add_class("wc")
            if extra:
                b.get_style_context().add_class(extra)
            ic = Icon(name, 10)
            b.add(ic)
            b.connect("clicked", cb)
            if name == "max":
                self.max_icon = ic
            wc.pack_start(b, False, False, 0)
        self.pack_end(wc)
        window.connect("window-state-event", self._wstate)
        window.set_titlebar(self)

    def toggle_max(self):
        if self.win.is_maximized():
            self.win.unmaximize()
        else:
            self.win.maximize()

    def _wstate(self, w, ev):
        maxed = bool(ev.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.max_icon.set_icon("restore" if maxed else "max")
        return False


def app_title(text, logo_draw):
    """Little logo + app name for the left of the title bar."""
    box = Gtk.Box(spacing=8)
    box.set_margin_start(14)
    da = Gtk.DrawingArea()
    da.set_size_request(16, 16)
    da.set_valign(Gtk.Align.CENTER)
    da.connect("draw", lambda w, cr: logo_draw(cr, 16))
    box.pack_start(da, False, False, 0)
    lb = Gtk.Label(label=text)
    lb.get_style_context().add_class("app-title")
    box.pack_start(lb, False, False, 0)
    return box, lb


class JsonSettings(dict):
    def __init__(self, app_dir, defaults):
        super().__init__(defaults)
        self.dir = os.path.join(HOME, ".config", app_dir)
        self.file = os.path.join(self.dir, "settings.json")
        try:
            with open(self.file) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self.file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self, f, indent=1)
            os.replace(tmp, self.file)
        except OSError:
            pass


def vsep():
    s = Gtk.Box()
    s.get_style_context().add_class("vsep")
    return s


def logo_pixbuf(draw, size):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw(cairo.Context(surf), size)
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, size, size)
def label(text="", cls=None, xalign=0.0, ellipsize=False, wrap=False, markup=False):
    lb = Gtk.Label()
    if markup:
        lb.set_markup(text)
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    if cls:
        for c in cls.split():
            lb.get_style_context().add_class(c)
    if ellipsize:
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    if wrap:
        lb.set_line_wrap(True)
        lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    return lb


def add_cls(w, *cls):
    ctx = w.get_style_context()
    for c in cls:
        ctx.add_class(c)
    return w


def tb_button(icon, text, cb=None, chev=False, tip=None):
    b = Gtk.Button()
    add_cls(b, "tb")
    box = Gtk.Box(spacing=7)
    if icon:
        box.pack_start(Icon(icon), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    if chev:
        box.pack_start(Icon("chevdown", 10), False, False, 0)
    b.add(box)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_tooltip_text(tip or text or None)
    if cb:
        b.connect("clicked", lambda w: cb(w))
    return b


def icon_button(icon, cb, cls="nb", tip=None, size=16):
    b = Gtk.Button()
    add_cls(b, cls)
    b.add(Icon(icon, size))
    b.set_relief(Gtk.ReliefStyle.NONE)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb(w))
    return b


def build_menu(spec):
    """spec: list of None (separator) or dicts: label, cb, icon, place, accel, sensitive, checked, sub."""
    menu = Gtk.Menu()
    add_cls(menu, "context-menu")
    for it in spec:
        if it is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue
        mi = Gtk.MenuItem()
        box = Gtk.Box(spacing=12)
        ic = None
        if it.get("checked"):
            ic = Icon("check", 16)
        elif it.get("pixbuf") is not None:
            ic = Gtk.Image.new_from_pixbuf(it["pixbuf"])
        elif it.get("icon"):
            ic = Icon(it["icon"], 16)
        if ic is None:
            ic = Gtk.Box()
            ic.set_size_request(16, 16)
        box.pack_start(ic, False, False, 0)
        lb = Gtk.Label(label=it["label"])
        lb.set_xalign(0)
        box.pack_start(lb, True, True, 0)
        if it.get("accel"):
            al = Gtk.Label(label=it["accel"])
            al.get_style_context().add_class("dim-label")
            al.set_opacity(0.55)
            al.set_margin_start(24)
            box.pack_end(al, False, False, 0)
        mi.add(box)
        mi.set_sensitive(it.get("sensitive", True))
        if it.get("sub") is not None:
            mi.set_submenu(build_menu(it["sub"]))
        elif it.get("cb"):
            cb = it["cb"]
            mi.connect("activate", lambda w, cb=cb: GLib.idle_add(cb))
        menu.append(mi)
    menu.show_all()
    return menu


def popup_menu(menu, widget, event=None):
    menu.attach_to_widget(widget, None)
    if event is not None:
        menu.popup_at_pointer(event)
    else:
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)


# ----------------------------------------------------------------------------
# Windows 11 style dialogs
# ----------------------------------------------------------------------------
class WinDialog(Gtk.Window):
    def __init__(self, parent, title, body=None, primary="OK", secondary="Cancel", width=440, extra=None,
                 markup=False):
        super().__init__(transient_for=parent, modal=True)
        add_cls(self, "fx-dialog")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(width, -1)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_title(title)
        self.cb = None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(self.body, "dlg-body")
        self.body.pack_start(label(title, "dlg-title"), False, False, 0)
        if body:
            lb = label(body, wrap=True, markup=markup)
            lb.set_max_width_chars(60)
            self.body.pack_start(lb, False, False, 0)
        if extra:
            self.body.pack_start(extra, False, False, 0)
        outer.pack_start(self.body, True, True, 0)
        self.foot = Gtk.Box(spacing=8, homogeneous=True)
        add_cls(self.foot, "dlg-foot")
        self.primary_btn = None
        if primary:
            pb = Gtk.Button(label=primary)
            add_cls(pb, "primary")
            pb.connect("clicked", lambda *_: self.done(True))
            self.foot.pack_start(pb, True, True, 0)
            pb.set_can_default(True)
            self.set_default(pb)
            self.primary_btn = pb
        if secondary:
            sb = Gtk.Button(label=secondary)
            add_cls(sb, "secondary")
            sb.connect("clicked", lambda *_: self.done(False))
            self.foot.pack_start(sb, True, True, 0)
        if primary or secondary:
            outer.pack_start(self.foot, False, False, 0)
        self.add(outer)
        self.connect("key-press-event", self._key)

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.done(False)
            return True
        return False

    def done(self, ok):
        cb = self.cb
        self.cb = None
        self.hide()
        if cb:
            cb(ok)
        self.destroy()

    def ask(self, cb=None):
        self.cb = cb
        self.show_all()
        if self.primary_btn:
            self.primary_btn.grab_focus()


def info_dialog(parent, title, body):
    WinDialog(parent, title, body, primary="OK", secondary=None).ask()


def confirm(parent, title, body, yes, cb, no="Cancel"):
    WinDialog(parent, title, body, primary=yes, secondary=no).ask(cb)


def error_list_dialog(parent, title, errors):
    lines = []
    for p, msg in errors[:12]:
        lines.append(f"{os.path.basename(p) or p}: {msg}" if p else msg)
    if len(errors) > 12:
        lines.append(f"...and {len(errors) - 12} more")
    info_dialog(parent, title, "\n".join(lines))




# ----------------------------------------------------------------------------
# Calculator
# ----------------------------------------------------------------------------
import ast  # noqa: E402
import datetime  # noqa: E402
import operator  # noqa: E402

APP_ID = "io.github.picalculator"
DEFAULTS = {"width": 340, "height": 560, "mode": "standard", "angle": "deg", "history": [], "memory": [],
            "prog_base": "DEC"}

CSS = """
window.fx.calc { background-color: #202020; }
.disp-expr { font-size: 13px; color: rgba(255,255,255,0.6); }
.disp-main { font-size: 44px; font-weight: 600; color: #ffffff; }
.disp-main.small { font-size: 32px; }
.disp-main.tiny { font-size: 24px; }
.mode-title { font-size: 20px; font-weight: 600; }
button.key { background-color: #3B3B3B; border: 1px solid rgba(255,255,255,0.04); border-radius: 4px; min-height: 44px;
   min-width: 40px; padding: 0; box-shadow: none; color: #ffffff; margin: 1px; }
button.key:hover { background-color: #323232; }
button.key:active { background-color: #2A2A2A; }
button.key label { font-size: 16px; color: #ffffff; }
button.key.op { background-color: #323232; }
button.key.op:hover { background-color: #3B3B3B; }
button.key.num label { font-size: 18px; font-weight: 600; }
button.key.eq { background-color: #4CC2FF; border-color: #4CC2FF; }
button.key.eq:hover { background-color: #48B1E8; }
button.key.eq label { color: #000000; font-size: 20px; }
button.key:disabled { background-color: #2B2B2B; }
button.key:disabled label { color: rgba(255,255,255,0.3); }
button.key.on { background-color: rgba(76,194,255,0.25); }
button.mem { background: transparent; border: none; border-radius: 4px; min-height: 30px; min-width: 36px; padding: 0; box-shadow: none; }
button.mem:hover { background-color: rgba(255,255,255,0.06); }
button.mem label { font-size: 12px; font-weight: 600; }
button.mem:disabled label { color: rgba(255,255,255,0.3); }
button.navitem { background: transparent; border: none; border-radius: 4px; min-height: 36px; padding: 0 12px; box-shadow: none; }
button.navitem:hover { background-color: rgba(255,255,255,0.06); }
button.navitem.selected { background-color: rgba(255,255,255,0.08); }
button.navitem label { font-size: 13px; }
.navhead { font-size: 13px; font-weight: 600; padding: 10px 12px 4px 12px; }
.navpanel { background-color: #2B2B2B; border-right: 1px solid rgba(0,0,0,0.4); }
.histpanel { background-color: #202020; }
button.histrow { background: transparent; border: none; border-radius: 4px; padding: 8px 12px; box-shadow: none; }
button.histrow:hover { background-color: rgba(255,255,255,0.06); }
.hist-expr { font-size: 12px; color: rgba(255,255,255,0.6); }
.hist-val { font-size: 20px; font-weight: 600; }
button.htab { background: transparent; border: none; border-radius: 0; min-height: 34px; padding: 0 10px; box-shadow: none; }
button.htab label { font-size: 13px; color: rgba(255,255,255,0.7); }
button.htab.on { box-shadow: inset 0 -2px #4CC2FF; }
button.htab.on label { color: #ffffff; font-weight: 600; }
button.base { background: transparent; border: none; border-radius: 4px; padding: 3px 8px; box-shadow: none; }
button.base:hover { background-color: rgba(255,255,255,0.06); }
button.base.on { box-shadow: inset 3px 0 #4CC2FF; background-color: rgba(255,255,255,0.05); }
.base-name { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.7); }
.base-val { font-size: 12px; }
.conv-val { font-size: 34px; font-weight: 600; }
.conv-val.active { color: #ffffff; }
.conv-val.inactive { color: rgba(255,255,255,0.75); font-weight: 400; }
.conv-note { font-size: 12px; color: rgba(255,255,255,0.6); }
"""


def draw_logo(cr, s):
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    cr.set_source_rgba(*hexc("#3A3A3A"))
    _rr(cr, 2, 1, 12, 14, 2.2)
    cr.fill()
    g = cairo.LinearGradient(0, 2, 0, 6)
    g.add_color_stop_rgb(0, 0.33, 0.73, 0.98)
    g.add_color_stop_rgb(1, 0.13, 0.45, 0.86)
    cr.set_source(g)
    _rr(cr, 3.5, 2.5, 9, 3.5, 0.8)
    cr.fill()
    for i in range(3):
        for j in range(3):
            if i == 2 and j == 2:
                cr.set_source_rgba(*hexc("#4CC2FF"))
            else:
                cr.set_source_rgba(1, 1, 1, 0.85)
            _rr(cr, 3.6 + j * 3.1, 7.2 + i * 2.5, 2.4, 1.8, 0.4)
            cr.fill()
    cr.restore()


# ---------------------------------------------------------------- number format
def fmt_num(v, maxlen=15):
    if isinstance(v, str):
        return v
    if v != v:
        return "Result is undefined"
    if v in (float("inf"), float("-inf")):
        return "Overflow"
    if v == 0:
        return "0"
    s = f"{v:.{maxlen}g}"
    if "e" in s:
        mant, exp = s.split("e")
        if "." in mant:
            mant = mant.rstrip("0").rstrip(".")
        return f"{mant}e{'+' if int(exp) >= 0 else '-'}{abs(int(exp))}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def group(s):
    """Add thousands separators to a plain number string."""
    if "e" in s or not re.match(r"^-?\d", s):
        return s
    neg = s.startswith("-")
    s = s.lstrip("-")
    ip, dot, fp = s.partition(".")
    ip = f"{int(ip):,}" if ip else "0"
    return ("-" if neg else "") + ip + dot + fp


# ---------------------------------------------------------------- safe evaluator
class Evaluator:
    def __init__(self, angle="deg"):
        self.angle = angle

    def _trig(self, f):
        def g(x):
            if self.angle == "deg":
                x = math.radians(x)
            elif self.angle == "grad":
                x = x * math.pi / 200
            r = f(x)
            return 0.0 if abs(r) < 1e-15 else r
        return g

    def _atrig(self, f):
        def g(x):
            r = f(x)
            if self.angle == "deg":
                return math.degrees(r)
            if self.angle == "grad":
                return r * 200 / math.pi
            return r
        return g

    def funcs(self):
        def fact(x):
            if x < 0 or x != int(x):
                return math.gamma(x + 1)
            if x > 170:
                raise OverflowError
            return float(math.factorial(int(x)))
        return {
            "sin": self._trig(math.sin), "cos": self._trig(math.cos), "tan": self._trig(math.tan),
            "asin": self._atrig(math.asin), "acos": self._atrig(math.acos), "atan": self._atrig(math.atan),
            "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
            "log": math.log10, "ln": math.log, "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
            "abs": abs, "fact": fact, "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
            "pi": math.pi, "e": math.e,
        }

    OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
           ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos}

    def eval(self, expr):
        tree = ast.parse(expr, mode="eval")
        f = self.funcs()

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return float(n.value)
            if isinstance(n, ast.BinOp) and type(n.op) in self.OPS:
                a, b = ev(n.left), ev(n.right)
                if isinstance(n.op, ast.Pow) and abs(b) > 10000:
                    raise OverflowError
                return self.OPS[type(n.op)](a, b)
            if isinstance(n, ast.UnaryOp) and type(n.op) in self.OPS:
                return self.OPS[type(n.op)](ev(n.operand))
            if isinstance(n, ast.Name) and n.id in ("pi", "e"):
                return f[n.id]
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in f and len(n.args) == 1:
                return float(f[n.func.id](ev(n.args[0])))
            raise ValueError("bad expression")
        return ev(tree)


# ---------------------------------------------------------------- unit converters
UNITS = {
    "Length": [("Nanometers", 1e-9), ("Micrometers", 1e-6), ("Millimeters", 1e-3), ("Centimeters", 1e-2),
               ("Meters", 1), ("Kilometers", 1e3), ("Inches", 0.0254), ("Feet", 0.3048), ("Yards", 0.9144),
               ("Miles", 1609.344), ("Nautical miles", 1852)],
    "Weight and mass": [("Milligrams", 1e-6), ("Grams", 1e-3), ("Kilograms", 1), ("Metric tonnes", 1000),
                        ("Ounces", 0.028349523125), ("Pounds", 0.45359237), ("Stone", 6.35029318),
                        ("Short tons (US)", 907.18474)],
    "Volume": [("Milliliters", 1e-3), ("Liters", 1), ("Cubic centimeters", 1e-3), ("Cubic meters", 1000),
               ("Teaspoons (US)", 0.00492892159), ("Tablespoons (US)", 0.0147867648),
               ("Fluid ounces (US)", 0.0295735296), ("Cups (US)", 0.2365882365), ("Pints (US)", 0.473176473),
               ("Quarts (US)", 0.946352946), ("Gallons (US)", 3.785411784), ("Cubic inches", 0.016387064),
               ("Cubic feet", 28.316846592)],
    "Temperature": [("Celsius", None), ("Fahrenheit", None), ("Kelvin", None)],
    "Area": [("Square millimeters", 1e-6), ("Square centimeters", 1e-4), ("Square meters", 1), ("Hectares", 1e4),
             ("Square kilometers", 1e6), ("Square inches", 0.00064516), ("Square feet", 0.09290304),
             ("Square yards", 0.83612736), ("Acres", 4046.8564224), ("Square miles", 2589988.110336)],
    "Speed": [("Meters per second", 1), ("Kilometers per hour", 1 / 3.6), ("Miles per hour", 0.44704),
              ("Feet per second", 0.3048), ("Knots", 0.514444444)],
    "Time": [("Microseconds", 1e-6), ("Milliseconds", 1e-3), ("Seconds", 1), ("Minutes", 60), ("Hours", 3600),
             ("Days", 86400), ("Weeks", 604800), ("Years", 31557600)],
    "Energy": [("Joules", 1), ("Kilojoules", 1000), ("Calories", 4.184), ("Kilocalories", 4184),
               ("Watt hours", 3600), ("Kilowatt hours", 3.6e6), ("Milliamp hours at 3.7 V", 13.32),
               ("British thermal units", 1055.05585)],
    "Power": [("Watts", 1), ("Kilowatts", 1000), ("Horsepower (US)", 745.69987158),
              ("Foot-pounds/minute", 0.0225969658), ("BTUs/minute", 17.5842642)],
    "Data": [("Bits", 1 / 8), ("Bytes", 1), ("Kilobytes", 1e3), ("Megabytes", 1e6), ("Gigabytes", 1e9),
             ("Terabytes", 1e12), ("Kibibytes", 1024), ("Mebibytes", 1024 ** 2), ("Gibibytes", 1024 ** 3),
             ("Tebibytes", 1024 ** 4)],
    "Pressure": [("Pascals", 1), ("Kilopascals", 1000), ("Bars", 1e5), ("Atmospheres", 101325),
                 ("Pounds per square inch", 6894.757293), ("Millimeters of mercury", 133.322387)],
    "Angle": [("Degrees", math.pi / 180), ("Radians", 1), ("Gradians", math.pi / 200)],
}
UNIT_DEFAULTS = {"Length": ("Millimeters", "Inches"), "Weight and mass": ("Grams", "Ounces"),
                 "Volume": ("Milliliters", "Fluid ounces (US)"), "Temperature": ("Celsius", "Fahrenheit"),
                 "Area": ("Square meters", "Square feet"), "Speed": ("Kilometers per hour", "Miles per hour"),
                 "Time": ("Hours", "Minutes"), "Energy": ("Watt hours", "Milliamp hours at 3.7 V"),
                 "Power": ("Watts", "Horsepower (US)"), "Data": ("Gigabytes", "Megabytes"),
                 "Pressure": ("Pounds per square inch", "Bars"), "Angle": ("Degrees", "Radians")}


def convert(cat, v, a, b):
    if cat == "Temperature":
        c = {"Celsius": v, "Fahrenheit": (v - 32) * 5 / 9, "Kelvin": v - 273.15}[a]
        return {"Celsius": c, "Fahrenheit": c * 9 / 5 + 32, "Kelvin": c + 273.15}[b]
    fa = dict(UNITS[cat])[a]
    fb = dict(UNITS[cat])[b]
    return v * fa / fb


# ---------------------------------------------------------------- UI helpers
def key(text, cb, cls="op", tip=None):
    b = Gtk.Button()
    b.get_style_context().add_class("key")
    for c in cls.split():
        b.get_style_context().add_class(c)
    lb = Gtk.Label()
    lb.set_markup(text)
    b.add(lb)
    b.set_hexpand(True)
    b.set_vexpand(True)
    b.set_can_focus(False)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb())
    return b


def grid(rows):
    g = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, row_spacing=1, column_spacing=1)
    g.set_margin_start(4)
    g.set_margin_end(4)
    g.set_margin_bottom(4)
    for r, row in enumerate(rows):
        for c, w in enumerate(row):
            if w is not None:
                g.attach(w, c, r, 1, 1)
    return g


SUP = {"2": "²", "3": "³", "x": "ˣ", "y": "ʸ"}


# ---------------------------------------------------------------- Standard mode (left to right, like Windows)
class StandardCalc(Gtk.Box):
    title = "Standard"

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.reset()
        self.expr_lbl = label("", "disp-expr", xalign=1.0, ellipsize=True)
        self.expr_lbl.set_margin_end(14)
        self.main_lbl = label("0", "disp-main", xalign=1.0, ellipsize=True)
        self.main_lbl.set_margin_end(14)
        self.main_lbl.set_selectable(True)
        self.pack_start(self.expr_lbl, False, False, 4)
        self.pack_start(self.main_lbl, False, False, 0)
        self.pack_start(self.win.memory_row(self), False, False, 4)
        D = lambda d: key(d, lambda: self.digit(d), "num")  # noqa: E731
        O = lambda t, cb, tip=None: key(t, cb, "op", tip)  # noqa: E731
        self.pack_start(grid([
            [O("%", self.percent, "Percent"), O("CE", self.clear_entry, "Clear entry (Delete)"),
             O("C", self.clear, "Clear (Esc)"), O("⌫", self.backspace, "Backspace")],
            [O("¹⁄ₓ", lambda: self.unary("recip"), "Reciprocal (R)"),
             O("x²", lambda: self.unary("sqr"), "Square (Q)"),
             O("²√x", lambda: self.unary("sqrt"), "Square root (@)"),
             O("÷", lambda: self.op("/"), "Divide (/)")],
            [D("7"), D("8"), D("9"), O("×", lambda: self.op("*"), "Multiply (*)")],
            [D("4"), D("5"), D("6"), O("−", lambda: self.op("-"), "Subtract (-)")],
            [D("1"), D("2"), D("3"), O("+", lambda: self.op("+"), "Add (+)")],
            [O("+/−", self.negate, "Negate (F9)"), D("0"), O(".", self.dot, "Decimal separator"),
             key("=", self.equals, "eq", "Equals (Enter)")],
        ]), True, True, 0)
        self.refresh()

    def reset(self):
        self.acc = None
        self.pending = None
        self.entry = "0"
        self.new_entry = True
        self.expr = ""
        self.last_op = None
        self.error = False
        self.just_eq = False

    # --- value helpers
    def cur(self):
        try:
            return float(self.entry)
        except ValueError:
            return 0.0

    def set_value(self, v):
        self.entry = fmt_num(v)
        self.new_entry = True

    def refresh(self):
        txt = self.entry if self.error else group(self.entry)
        self.main_lbl.set_text(txt)
        ctx = self.main_lbl.get_style_context()
        ctx.remove_class("small")
        ctx.remove_class("tiny")
        if len(txt) > 18:
            ctx.add_class("tiny")
        elif len(txt) > 12:
            ctx.add_class("small")
        sym = {"+": "+", "-": "−", "*": "×", "/": "÷"}
        self.expr_lbl.set_text(re.sub(r"[*/\-+](?= |$)", lambda m: sym[m.group(0)], self.expr))

    def _guard(self):
        if self.error:
            self.reset()

    # --- input
    def digit(self, d):
        self._guard()
        if self.just_eq:
            self.expr = ""
            self.acc = None
            self.just_eq = False
        if self.new_entry:
            self.entry = d
            self.new_entry = False
        elif len(self.entry.replace("-", "").replace(".", "")) < 16:
            self.entry = d if self.entry == "0" else self.entry + d
        self.refresh()

    def dot(self):
        self._guard()
        if self.just_eq:
            self.expr = ""
            self.acc = None
            self.just_eq = False
        if self.new_entry:
            self.entry = "0."
            self.new_entry = False
        elif "." not in self.entry:
            self.entry += "."
        self.refresh()

    def backspace(self):
        if self.error:
            self.reset()
        elif self.just_eq:
            self.expr = ""
        elif not self.new_entry:
            self.entry = self.entry[:-1]
            if self.entry in ("", "-"):
                self.entry = "0"
        self.refresh()

    def clear_entry(self):
        if self.error or self.just_eq:
            self.reset()
        self.entry = "0"
        self.new_entry = True
        self.refresh()

    def clear(self):
        self.reset()
        self.refresh()

    def negate(self):
        self._guard()
        if self.entry != "0":
            self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry
        self.refresh()

    def _apply(self, a, op, b):
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise ZeroDivisionError
            return a / b
        return b

    def _fail(self, msg):
        self.error = True
        self.entry = msg
        self.new_entry = True
        self.refresh()

    def op(self, o):
        self._guard()
        v = self.cur()
        if self.just_eq:
            self.acc = v
            self.just_eq = False
        elif self.pending and not self.new_entry:
            try:
                self.acc = self._apply(self.acc, self.pending, v)
            except ZeroDivisionError:
                return self._fail("Cannot divide by zero")
            self.set_value(self.acc)
        elif self.acc is None or not self.pending:
            self.acc = v
        self.pending = o
        self.new_entry = True
        self.expr = f"{fmt_num(self.acc)} {o} "
        self.refresh()

    def equals(self):
        self._guard()
        v = self.cur()
        if self.just_eq and self.last_op:
            op, b = self.last_op
            a = v
        elif self.pending:
            op, b, a = self.pending, v, self.acc
        else:
            self.expr = f"{fmt_num(v)} ="
            self.just_eq = True
            self.refresh()
            return
        try:
            r = self._apply(a, op, b)
        except ZeroDivisionError:
            return self._fail("Cannot divide by zero")
        except OverflowError:
            return self._fail("Overflow")
        self.expr = f"{fmt_num(a)} {op} {fmt_num(b)} ="
        self.last_op = (op, b)
        self.pending = None
        self.acc = r
        self.set_value(r)
        self.just_eq = True
        self.refresh()
        self.win.add_history(self.expr_lbl.get_text(), self.entry)

    def unary(self, kind):
        self._guard()
        v = self.cur()
        try:
            if kind == "recip":
                if v == 0:
                    raise ZeroDivisionError
                r, t = 1 / v, f"1/({fmt_num(v)})"
            elif kind == "sqr":
                r, t = v * v, f"sqr({fmt_num(v)})"
            else:
                if v < 0:
                    return self._fail("Invalid input")
                r, t = math.sqrt(v), f"√({fmt_num(v)})"
        except ZeroDivisionError:
            return self._fail("Cannot divide by zero")
        except OverflowError:
            return self._fail("Overflow")
        base = f"{fmt_num(self.acc)} {self.pending} " if self.pending and not self.just_eq else ""
        self.expr = base + t
        self.set_value(r)
        if self.just_eq:
            self.acc = r
        self.refresh()

    def percent(self):
        self._guard()
        v = self.cur()
        if self.pending in ("+", "-") and self.acc is not None:
            r = self.acc * v / 100
        else:
            r = v / 100
        self.set_value(r)
        self.expr = (f"{fmt_num(self.acc)} {self.pending} " if self.pending else "") + fmt_num(r)
        self.refresh()

    def set_entry_value(self, s):
        self.reset() if self.error else None
        self.entry = s
        self.new_entry = True
        self.refresh()

    def display_value(self):
        return self.entry

    def key(self, ev):
        k = ev.keyval
        ch = chr(Gdk.keyval_to_unicode(k)) if Gdk.keyval_to_unicode(k) else "\x00"
        if ch.isdigit():
            self.digit(ch)
        elif ch in ".,":
            self.dot()
        elif ch in "+-*/":
            self.op(ch)
        elif ch == "x" or ch == "X":
            self.op("*")
        elif ch == "%":
            self.percent()
        elif ch in ("=",) or k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.equals()
        elif k == Gdk.KEY_BackSpace:
            self.backspace()
        elif k == Gdk.KEY_Escape:
            self.clear()
        elif k == Gdk.KEY_Delete:
            self.clear_entry()
        elif k == Gdk.KEY_F9:
            self.negate()
        elif ch in "rR":
            self.unary("recip")
        elif ch in "qQ":
            self.unary("sqr")
        elif ch == "@":
            self.unary("sqrt")
        else:
            return False
        return True


# ---------------------------------------------------------------- Scientific mode (full expressions)
class ScientificCalc(Gtk.Box):
    title = "Scientific"

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.ev = Evaluator(win.app.settings["angle"])
        self.tokens = []     # committed expression pieces (python syntax, display text)
        self.entry = "0"
        self.new_entry = True
        self.just_eq = False
        self.second = False
        self.hyp = False
        self.fe = False
        self.error = False
        self.expr_lbl = label("", "disp-expr", xalign=1.0, ellipsize=True)
        self.expr_lbl.set_margin_end(14)
        self.main_lbl = label("0", "disp-main", xalign=1.0, ellipsize=True)
        self.main_lbl.set_margin_end(14)
        self.main_lbl.set_selectable(True)
        self.pack_start(self.expr_lbl, False, False, 4)
        self.pack_start(self.main_lbl, False, False, 0)
        row = Gtk.Box(spacing=2)
        row.set_margin_start(6)
        self.angle_btn = Gtk.Button(label="DEG")
        self.angle_btn.get_style_context().add_class("mem")
        self.angle_btn.connect("clicked", lambda w: self.cycle_angle())
        self.angle_btn.set_can_focus(False)
        self.fe_btn = Gtk.Button(label="F-E")
        self.fe_btn.get_style_context().add_class("mem")
        self.fe_btn.set_can_focus(False)
        self.fe_btn.connect("clicked", lambda w: self.toggle_fe())
        row.pack_start(self.angle_btn, False, False, 0)
        row.pack_start(self.fe_btn, False, False, 0)
        self.pack_start(row, False, False, 0)
        self.pack_start(self.win.memory_row(self), False, False, 2)
        self._update_angle()
        self.grid_box = Gtk.Box()
        self.pack_start(self.grid_box, True, True, 0)
        self._build_keys()
        self.refresh()

    def _build_keys(self):
        for c in self.grid_box.get_children():
            c.destroy()
        D = lambda d: key(d, lambda: self.digit(d), "num")  # noqa: E731
        O = lambda t, cb, tip=None: key(t, cb, "op", tip)  # noqa: E731
        s = self.second
        h = "h" if self.hyp else ""
        inv = "\u207b\u00b9"
        trig = []
        for nm in ("sin", "cos", "tan"):
            lbl_ = (nm + inv if s else nm) + h
            fn = ("a" + nm) if s else nm + h
            trig.append(O(lbl_, lambda fn=fn: self.func(fn)))
        second = O("2<sup>nd</sup>", self.toggle_second, "Second functions")
        if s:
            second.get_style_context().add_class("on")
        hyp = O("hyp", self.toggle_hyp, "Hyperbolic")
        if self.hyp:
            hyp.get_style_context().add_class("on")
        rows = [
            trig + [hyp, O("F-E", self.toggle_fe, "Scientific notation")],
            [second, O("π", lambda: self.const("pi", "π")), O("e", lambda: self.const("e", "e")),
             O("C", self.clear, "Clear (Esc)"), O("⌫", self.backspace, "Backspace")],
            [O("x³" if s else "x²", lambda: self.power(3 if s else 2)),
             O("¹⁄ₓ", lambda: self.recip()), O("|x|", lambda: self.func("abs")),
             O("exp", lambda: self.func("exp")), O("mod", lambda: self.binop("%", "mod"))],
            [O("³√x" if s else "²√x", lambda: self.func("cbrt" if s else "sqrt")),
             O("(", lambda: self.paren("(")), O(")", lambda: self.paren(")")), O("n!", lambda: self.func("fact")),
             O("÷", lambda: self.binop("/", "÷"))],
            [O("ʸ√x" if s else "xʸ", (lambda: self.binop("**(1/", "yroot")) if s else
               (lambda: self.binop("**", "^"))), D("7"), D("8"), D("9"), O("×", lambda: self.binop("*", "×"))],
            [O("2ˣ" if s else "10ˣ", lambda: self.pow_of(2 if s else 10)), D("4"), D("5"), D("6"),
             O("−", lambda: self.binop("-", "−"))],
            [O("log₂x" if s else "log", lambda: self.func("log2" if s else "log")), D("1"), D("2"), D("3"),
             O("+", lambda: self.binop("+", "+"))],
            [O("eˣ" if s else "ln", lambda: self.func("exp" if s else "ln")), O("+/−", self.negate),
             D("0"), O(".", self.dot), key("=", self.equals, "eq")],
        ]
        g = grid(rows)
        self.grid_box.pack_start(g, True, True, 0)
        g.show_all()

    def cycle_angle(self):
        order = ["deg", "rad", "grad"]
        a = order[(order.index(self.ev.angle) + 1) % 3]
        self.ev.angle = a
        self.win.app.settings["angle"] = a
        self._update_angle()

    def _update_angle(self):
        self.angle_btn.set_label(self.ev.angle.upper())

    def toggle_second(self):
        self.second = not self.second
        self._build_keys()

    def toggle_hyp(self):
        self.hyp = not self.hyp
        self._build_keys()

    def toggle_fe(self):
        self.fe = not self.fe
        self.refresh()

    # --- state
    def reset(self):
        self.tokens = []
        self.entry = "0"
        self.new_entry = True
        self.just_eq = False
        self.error = False

    def clear(self):
        self.reset()
        self.refresh()

    def _guard(self):
        if self.error:
            self.reset()

    def _fresh(self):
        if self.just_eq:
            self.tokens = []
            self.just_eq = False

    def refresh(self):
        txt = self.entry
        if not self.error:
            try:
                v = float(self.entry)
                txt = f"{v:.10e}".replace("e+", "e+").rstrip("0") if self.fe and not self.entry.endswith(".") \
                    else group(self.entry)
                if self.fe:
                    m, e_ = f"{v:.12e}".split("e")
                    txt = f"{m.rstrip('0').rstrip('.')}e{'+' if int(e_) >= 0 else '-'}{abs(int(e_))}"
            except ValueError:
                txt = self.entry
        self.main_lbl.set_text(txt)
        ctx = self.main_lbl.get_style_context()
        ctx.remove_class("small")
        ctx.remove_class("tiny")
        if len(txt) > 18:
            ctx.add_class("tiny")
        elif len(txt) > 12:
            ctx.add_class("small")
        self.expr_lbl.set_text(" ".join(d for _, d in self.tokens))

    def _last_is_value(self):
        return self.tokens and (self.tokens[-1][0].endswith(")") or re.match(r".*[\d.e]$", self.tokens[-1][0])
                                or self.tokens[-1][0] in ("pi", "e"))

    def digit(self, d):
        self._guard()
        self._fresh()
        if self.new_entry:
            self.entry = d
            self.new_entry = False
        elif len(self.entry.replace("-", "").replace(".", "")) < 32:
            self.entry = d if self.entry == "0" else self.entry + d
        self.refresh()

    def dot(self):
        self._guard()
        self._fresh()
        if self.new_entry:
            self.entry = "0."
            self.new_entry = False
        elif "." not in self.entry:
            self.entry += "."
        self.refresh()

    def backspace(self):
        if self.error:
            self.reset()
        elif not self.new_entry:
            self.entry = self.entry[:-1] or "0"
            if self.entry == "-":
                self.entry = "0"
        self.refresh()

    def negate(self):
        self._guard()
        if self.entry != "0":
            self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry
        self.refresh()

    def _commit_entry(self):
        """Push the current entry as a value token if the expression needs one."""
        if not self._last_is_value():
            v = self.entry
            self.tokens.append((f"({v})" if v.startswith("-") else v, v))
        self.new_entry = True

    def binop(self, py, disp):
        self._guard()
        if self.just_eq:
            self.tokens = []
            self.just_eq = False
        self._commit_entry()
        self.tokens.append((py, disp))
        self.refresh()

    def paren(self, p):
        self._guard()
        self._fresh()
        if p == "(":
            if self._last_is_value():
                self.tokens.append(("*", "×"))
            self.tokens.append(("(", "("))
        else:
            opens = sum(1 for t, _ in self.tokens if t.endswith("(")) - sum(1 for t, _ in self.tokens if t == ")")
            if opens <= 0:
                return
            self._commit_entry()
            self.tokens.append((")", ")"))
        self.refresh()

    def const(self, name, disp):
        self._guard()
        self._fresh()
        self.entry = fmt_num(math.pi if name == "pi" else math.e)
        self.new_entry = True
        self.refresh()

    def _value_now(self):
        """The value a function key applies to: the last value in the expression, or the entry."""
        if self.new_entry and self._last_is_value():
            if self.tokens[-1][0] == ")":
                depth = 0
                for i in range(len(self.tokens) - 1, -1, -1):
                    t = self.tokens[i][0]
                    if t == ")":
                        depth += 1
                    elif t.endswith("("):
                        depth -= 1
                        if depth == 0:
                            grp = self.tokens[i:]
                            self.tokens = self.tokens[:i]
                            return "".join(t for t, _ in grp), " ".join(d for _, d in grp)
            return self.tokens.pop()
        v = self.entry
        return (f"({v})" if v.startswith("-") else v), v

    def _apply_unary(self, py_wrap, disp_wrap):
        self._guard()
        if self.just_eq:
            self.tokens = []
            self.just_eq = False
        py, disp = self._value_now()
        expr_py, expr_disp = py_wrap(py), disp_wrap(disp)
        try:
            v = self.ev.eval(expr_py)
        except (ValueError, ZeroDivisionError, OverflowError, SyntaxError, TypeError):
            return self._fail("Invalid input")
        self.tokens.append((expr_py, expr_disp))
        self.entry = fmt_num(v)
        self.new_entry = True
        self.refresh()

    def func(self, name):
        names = {"log2": ("log2", "log₂"), "sinh": ("sinh", "sinh"), "cosh": ("cosh", "cosh"),
                 "tanh": ("tanh", "tanh"), "cbrt": ("cbrt", "cube√"), "sqrt": ("sqrt", "√"),
                 "fact": ("fact", "fact"), "abs": ("abs", "abs")}
        py, disp = names.get(name, (name, name))
        if name == "log2":
            return self._apply_unary(lambda x: f"(ln({x})/ln(2))", lambda d: f"log₂({d})")
        self._apply_unary(lambda x: f"{py}({x})", lambda d: f"{disp}({d})")

    def power(self, n):
        self._apply_unary(lambda x: f"({x})**{n}", lambda d: f"({d}){SUP[str(n)]}")

    def recip(self):
        self._apply_unary(lambda x: f"1/({x})", lambda d: f"1/({d})")

    def pow_of(self, b):
        self._apply_unary(lambda x: f"{b}**({x})", lambda d: f"{b}^({d})")

    def _fail(self, msg):
        self.error = True
        self.entry = msg
        self.new_entry = True
        self.refresh()

    def equals(self):
        self._guard()
        if self.just_eq:
            return
        self._commit_entry()
        py = "".join(t for t, _ in self.tokens)
        disp = " ".join(d for _, d in self.tokens)
        opens = py.count("(") - py.count(")")
        py += ")" * max(0, opens)
        disp += " )" * max(0, opens)
        try:
            v = self.ev.eval(py)
        except ZeroDivisionError:
            return self._fail("Cannot divide by zero")
        except OverflowError:
            return self._fail("Overflow")
        except (ValueError, SyntaxError, TypeError):
            return self._fail("Invalid input")
        self.tokens = [(py, disp + " =")]
        self.entry = fmt_num(v)
        self.just_eq = True
        self.refresh()
        self.win.add_history(self.expr_lbl.get_text(), self.entry)
        self.tokens = [(fmt_num(v), disp + " =")]
        self.tokens = []
        self.expr_lbl.set_text(disp + " =")

    def set_entry_value(self, s):
        self.reset()
        self.entry = s
        self.refresh()

    def display_value(self):
        return self.entry

    def key(self, ev):
        k = ev.keyval
        ch = chr(Gdk.keyval_to_unicode(k)) if Gdk.keyval_to_unicode(k) else "\x00"
        if ch.isdigit():
            self.digit(ch)
        elif ch in ".,":
            self.dot()
        elif ch in "+-*/":
            self.binop(ch, {"+": "+", "-": "−", "*": "×", "/": "÷"}[ch])
        elif ch == "^":
            self.binop("**", "^")
        elif ch == "%":
            self.binop("%", "mod")
        elif ch in "()":
            self.paren(ch)
        elif ch == "!":
            self.func("fact")
        elif ch == "p":
            self.const("pi", "π")
        elif ch == "=" or k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.equals()
        elif k == Gdk.KEY_BackSpace:
            self.backspace()
        elif k in (Gdk.KEY_Escape, Gdk.KEY_Delete):
            self.clear()
        elif k == Gdk.KEY_F9:
            self.negate()
        elif ch == "s":
            self.func("sin")
        elif ch == "o":
            self.func("cos")
        elif ch == "t":
            self.func("tan")
        elif ch == "l":
            self.func("log")
        elif ch == "n":
            self.func("ln")
        elif ch == "@":
            self.func("sqrt")
        elif ch == "q":
            self.power(2)
        else:
            return False
        return True


# ---------------------------------------------------------------- Programmer mode
class ProgrammerCalc(Gtk.Box):
    title = "Programmer"
    BITS = 64

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.base = win.app.settings.get("prog_base", "DEC")
        self.tokens = []
        self.entry = 0
        self.new_entry = True
        self.just_eq = False
        self.error = None
        self.expr_lbl = label("", "disp-expr", xalign=1.0, ellipsize=True)
        self.expr_lbl.set_margin_end(14)
        self.main_lbl = label("0", "disp-main", xalign=1.0, ellipsize=True)
        self.main_lbl.set_margin_end(14)
        self.main_lbl.set_selectable(True)
        self.pack_start(self.expr_lbl, False, False, 4)
        self.pack_start(self.main_lbl, False, False, 0)
        self.base_btns = {}
        self.base_vals = {}
        bb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bb.set_margin_start(6)
        bb.set_margin_end(6)
        for b in ("HEX", "DEC", "OCT", "BIN"):
            btn = Gtk.Button()
            btn.get_style_context().add_class("base")
            btn.set_can_focus(False)
            row = Gtk.Box(spacing=12)
            row.pack_start(label(b, "base-name"), False, False, 0)
            v = label("0", "base-val", ellipsize=True)
            row.pack_start(v, True, True, 0)
            btn.add(row)
            btn.connect("clicked", lambda w, b=b: self.set_base(b))
            bb.pack_start(btn, False, False, 0)
            self.base_btns[b] = btn
            self.base_vals[b] = v
        self.pack_start(bb, False, False, 4)
        D = lambda d: key(d, lambda: self.digit(d), "num")  # noqa: E731
        O = lambda t, cb, tip=None: key(t, cb, "op", tip)  # noqa: E731
        nodot = O(".", lambda: None)
        nodot.set_sensitive(False)
        self.digit_keys = {d: D(d) for d in "0123456789ABCDEF"}
        k = self.digit_keys
        self.pack_start(grid([
            [O("AND", lambda: self.binop("&", "AND")), O("OR", lambda: self.binop("|", "OR")),
             O("XOR", lambda: self.binop("^", "XOR")), O("NOT", self.bnot), O("NAND", lambda: self.binop("nand", "NAND"))],
            [k["A"], O("&lt;&lt;", lambda: self.binop("<<", "Lsh")), O("&gt;&gt;", lambda: self.binop(">>", "Rsh")),
             O("C", self.clear, "Clear (Esc)"), O("⌫", self.backspace)],
            [k["B"], O("(", lambda: self.paren("(")), O(")", lambda: self.paren(")")), O("%", lambda: self.binop("%", "%")),
             O("÷", lambda: self.binop("//", "÷"))],
            [k["C"], k["7"], k["8"], k["9"], O("×", lambda: self.binop("*", "×"))],
            [k["D"], k["4"], k["5"], k["6"], O("−", lambda: self.binop("-", "−"))],
            [k["E"], k["1"], k["2"], k["3"], O("+", lambda: self.binop("+", "+"))],
            [k["F"], O("+/−", self.negate), k["0"], O(".", lambda: None), key("=", self.equals, "eq")],
        ]), True, True, 0)
        self.set_base(self.base)

    RADIX = {"HEX": 16, "DEC": 10, "OCT": 8, "BIN": 2}

    def mask(self, v):
        v &= (1 << self.BITS) - 1
        if v >= 1 << (self.BITS - 1):
            v -= 1 << self.BITS
        return v

    def fmt(self, v, base):
        if base == "DEC":
            return f"{v:,}"
        u = v & ((1 << self.BITS) - 1)
        s = {"HEX": f"{u:X}", "OCT": f"{u:o}", "BIN": f"{u:b}"}[base]
        if base == "BIN":
            s = s.zfill((len(s) + 3) // 4 * 4)
            s = " ".join(s[i:i + 4] for i in range(0, len(s), 4))
        elif base == "HEX":
            s = " ".join([s[max(0, i - 4):i] for i in range(len(s), 0, -4)][::-1])
        return s

    def set_base(self, b):
        self.base = b
        self.win.app.settings["prog_base"] = b
        for name, btn in self.base_btns.items():
            ctx = btn.get_style_context()
            (ctx.add_class if name == b else ctx.remove_class)("on")
        r = self.RADIX[b]
        for d, w in self.digit_keys.items():
            w.set_sensitive(int(d, 16) < r)
        self.new_entry = True
        self.refresh()

    def refresh(self):
        if self.error:
            self.main_lbl.set_text(self.error)
        else:
            self.main_lbl.set_text(self.fmt(self.entry, self.base))
        for b, lbl in self.base_vals.items():
            lbl.set_text("" if self.error else self.fmt(self.entry, b))
        self.expr_lbl.set_text(" ".join(d for _, d in self.tokens))
        ctx = self.main_lbl.get_style_context()
        ctx.remove_class("small")
        ctx.remove_class("tiny")
        n = len(self.main_lbl.get_text())
        if n > 20:
            ctx.add_class("tiny")
        elif n > 12:
            ctx.add_class("small")

    def _guard(self):
        if self.error:
            self.clear()

    def _fresh(self):
        if self.just_eq:
            self.tokens = []
            self.just_eq = False

    def digit(self, d):
        self._guard()
        self._fresh()
        r = self.RADIX[self.base]
        if int(d, 16) >= r:
            return
        if self.new_entry:
            self.entry = int(d, 16)
            self.new_entry = False
        else:
            nv = self.entry * r + (int(d, 16) if self.entry >= 0 else -int(d, 16))
            if nv.bit_length() < self.BITS:
                self.entry = nv
        self.refresh()

    def backspace(self):
        if self.error:
            return self.clear()
        if not self.new_entry:
            r = self.RADIX[self.base]
            self.entry = int(self.entry / r)
        self.refresh()

    def clear(self):
        self.tokens = []
        self.entry = 0
        self.new_entry = True
        self.just_eq = False
        self.error = None
        self.refresh()

    def negate(self):
        self._guard()
        self.entry = self.mask(-self.entry)
        self.refresh()

    def bnot(self):
        self._guard()
        self.entry = self.mask(~self.entry)
        self.new_entry = True
        self.refresh()

    def _last_is_value(self):
        return self.tokens and (self.tokens[-1][0] == ")" or re.match(r"^\(?-?\d+\)?$", self.tokens[-1][0]))

    def binop(self, py, disp):
        self._guard()
        if self.just_eq:
            self.tokens = []
            self.just_eq = False
        if not self._last_is_value():
            self.tokens.append((f"({self.entry})", self.fmt(self.entry, self.base)))
        self.tokens.append((py, disp))
        self.new_entry = True
        self.refresh()

    def paren(self, p):
        self._guard()
        self._fresh()
        if p == "(":
            self.tokens.append(("(", "("))
        else:
            if "".join(t for t, _ in self.tokens).count("(") <= "".join(t for t, _ in self.tokens).count(")"):
                return
            if not self._last_is_value():
                self.tokens.append((f"({self.entry})", self.fmt(self.entry, self.base)))
            self.tokens.append((")", ")"))
            self.new_entry = True
        self.refresh()

    def _eval(self, toks):
        py = "".join(t for t, _ in toks)
        py += ")" * max(0, py.count("(") - py.count(")"))
        py = re.sub(r"\(([^()]*?)\)nand\(([^()]*?)\)", r"~((\1)&(\2))", py)
        tree = ast.parse(py.replace("nand", "&"), mode="eval")
        ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: None,
               ast.Mod: None, ast.BitAnd: operator.and_, ast.BitOr: operator.or_, ast.BitXor: operator.xor,
               ast.LShift: operator.lshift, ast.RShift: operator.rshift}

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, int):
                return n.value
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.Invert, ast.UAdd)):
                v = ev(n.operand)
                return -v if isinstance(n.op, ast.USub) else (~v if isinstance(n.op, ast.Invert) else v)
            if isinstance(n, ast.BinOp) and type(n.op) in ops:
                a, b = ev(n.left), ev(n.right)
                if isinstance(n.op, (ast.FloorDiv, ast.Mod)):
                    if b == 0:
                        raise ZeroDivisionError
                    q = abs(a) // abs(b) * (1 if (a >= 0) == (b >= 0) else -1)
                    return q if isinstance(n.op, ast.FloorDiv) else a - q * b
                if isinstance(n.op, ast.LShift) and b > 64:
                    b = 64
                return self.mask(ops[type(n.op)](a, b))
            raise ValueError
        return self.mask(ev(tree))

    def equals(self):
        self._guard()
        if self.just_eq:
            return
        if not self._last_is_value():
            self.tokens.append((f"({self.entry})", self.fmt(self.entry, self.base)))
        disp = " ".join(d for _, d in self.tokens)
        try:
            v = self._eval(self.tokens)
        except ZeroDivisionError:
            self.error = "Cannot divide by zero"
            return self.refresh()
        except (ValueError, SyntaxError):
            self.error = "Invalid input"
            return self.refresh()
        self.tokens = []
        self.entry = v
        self.new_entry = True
        self.just_eq = True
        self.refresh()
        self.expr_lbl.set_text(disp + " =")
        self.win.add_history(disp + " =", self.fmt(v, self.base))

    def set_entry_value(self, s):
        try:
            self.entry = self.mask(int(float(s.replace(",", "").replace(" ", ""))))
        except ValueError:
            return
        self.new_entry = True
        self.refresh()

    def display_value(self):
        return self.fmt(self.entry, self.base).replace(" ", "").replace(",", "")

    def key(self, ev):
        k = ev.keyval
        ch = chr(Gdk.keyval_to_unicode(k)) if Gdk.keyval_to_unicode(k) else "\x00"
        if ch.upper() in "0123456789ABCDEF":
            self.digit(ch.upper())
        elif ch in "+-*":
            self.binop(ch, {"+": "+", "-": "−", "*": "×"}[ch])
        elif ch == "/":
            self.binop("//", "÷")
        elif ch == "%":
            self.binop("%", "%")
        elif ch == "&":
            self.binop("&", "AND")
        elif ch == "|":
            self.binop("|", "OR")
        elif ch == "^":
            self.binop("^", "XOR")
        elif ch == "~":
            self.bnot()
        elif ch == "<":
            self.binop("<<", "Lsh")
        elif ch == ">":
            self.binop(">>", "Rsh")
        elif ch in "()":
            self.paren(ch)
        elif ch == "=" or k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.equals()
        elif k == Gdk.KEY_BackSpace:
            self.backspace()
        elif k in (Gdk.KEY_Escape, Gdk.KEY_Delete):
            self.clear()
        elif k == Gdk.KEY_F9:
            self.negate()
        else:
            return False
        return True


# ---------------------------------------------------------------- Converter mode
class ConverterCalc(Gtk.Box):
    def __init__(self, win, cat):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.cat = cat
        self.title = cat
        self.entry = "0"
        self.active = 0
        units = [u for u, _ in UNITS[cat]]
        a, b = UNIT_DEFAULTS.get(cat, (units[0], units[1]))
        self.vals = []
        self.combos = []
        for i, u in enumerate((a, b)):
            ev = Gtk.EventBox()
            v = label("0", "conv-val", ellipsize=True)
            v.set_margin_start(16)
            ev.add(v)
            ev.connect("button-press-event", lambda w, e, i=i: self.set_active(i))
            cb = Gtk.ComboBoxText()
            for uu in units:
                cb.append(uu, uu)
            cb.set_active_id(u)
            cb.set_halign(Gtk.Align.START)
            cb.set_margin_start(16)
            cb.connect("changed", lambda *x: self.recalc())
            self.pack_start(ev, False, False, 6 if i == 0 else 2)
            self.pack_start(cb, False, False, 0)
            self.vals.append(v)
            self.combos.append(cb)
        self.note = label("", "conv-note", wrap=True)
        self.note.set_margin_start(16)
        self.note.set_margin_top(8)
        self.pack_start(self.note, False, False, 0)
        D = lambda d: key(d, lambda: self.digit(d), "num")  # noqa: E731
        O = lambda t, cb: key(t, cb, "op")  # noqa: E731
        self.pack_end(grid([
            [None, O("CE", self.clear), O("⌫", self.backspace)],
            [D("7"), D("8"), D("9")],
            [D("4"), D("5"), D("6")],
            [D("1"), D("2"), D("3")],
            [O("+/−", self.negate), D("0"), O(".", self.dot)],
        ]), True, True, 0)
        self.set_active(0)

    def set_active(self, i):
        self.active = i
        for j, v in enumerate(self.vals):
            ctx = v.get_style_context()
            ctx.remove_class("active")
            ctx.remove_class("inactive")
            ctx.add_class("active" if j == i else "inactive")
        self.entry = self.vals[i].get_text().replace(",", "")
        try:
            float(self.entry)
        except ValueError:
            self.entry = "0"
        self.fresh = True
        self.recalc()
        return True

    def digit(self, d):
        if getattr(self, "fresh", False) or self.entry == "0":
            self.entry = d
        elif len(self.entry) < 16:
            self.entry += d
        self.fresh = False
        self.recalc()

    def dot(self):
        if getattr(self, "fresh", False):
            self.entry = "0."
        elif "." not in self.entry:
            self.entry += "."
        self.fresh = False
        self.recalc()

    def backspace(self):
        self.entry = self.entry[:-1] or "0"
        if self.entry == "-":
            self.entry = "0"
        self.fresh = False
        self.recalc()

    def clear(self):
        self.entry = "0"
        self.recalc()

    def negate(self):
        if self.cat != "Temperature" and False:
            return
        if self.entry != "0":
            self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry
        self.recalc()

    def recalc(self):
        a = self.combos[self.active].get_active_id()
        b = self.combos[1 - self.active].get_active_id()
        try:
            v = float(self.entry)
        except ValueError:
            v = 0.0
        r = convert(self.cat, v, a, b)
        self.vals[self.active].set_text(group(self.entry))
        self.vals[1 - self.active].set_text(group(fmt_num(r, 12)))
        ua, ub = self.combos[0].get_active_id(), self.combos[1].get_active_id()
        one = convert(self.cat, 1, ua, ub)
        self.note.set_text(f"About equal to\n1 {ua} = {group(fmt_num(one, 10))} {ub}")

    def set_entry_value(self, s):
        self.entry = s.replace(",", "")
        self.recalc()

    def display_value(self):
        return self.vals[1 - self.active].get_text().replace(",", "")

    def key(self, ev):
        k = ev.keyval
        ch = chr(Gdk.keyval_to_unicode(k)) if Gdk.keyval_to_unicode(k) else "\x00"
        if ch.isdigit():
            self.digit(ch)
        elif ch in ".,":
            self.dot()
        elif k == Gdk.KEY_BackSpace:
            self.backspace()
        elif k in (Gdk.KEY_Escape, Gdk.KEY_Delete):
            self.clear()
        elif k == Gdk.KEY_F9 or ch == "-":
            self.negate()
        elif k in (Gdk.KEY_Tab, Gdk.KEY_Up, Gdk.KEY_Down):
            self.set_active(1 - self.active)
        else:
            return False
        return True


# ---------------------------------------------------------------- Date calculation
class DateCalc(Gtk.Box):
    title = "Date calculation"

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.win = win
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.pack_start(label("Difference between dates", "sect-title"), False, False, 8)
        self.cals = []
        for t in ("From", "To"):
            self.pack_start(label(t, "sec"), False, False, 0)
            c = Gtk.Calendar()
            c.connect("day-selected", lambda *a: self.recalc())
            self.pack_start(c, False, False, 0)
            self.cals.append(c)
        self.pack_start(label("Difference", "sec"), False, False, 4)
        self.res = label("", "hist-val", wrap=True)
        self.pack_start(self.res, False, False, 0)
        self.res2 = label("", "sec")
        self.pack_start(self.res2, False, False, 0)
        self.recalc()

    def recalc(self):
        ds = []
        for c in self.cals:
            y, m, d = c.get_date()
            ds.append(datetime.date(y, m + 1, d))
        a, b = sorted(ds)
        days = (b - a).days
        if days == 0:
            self.res.set_text("Same dates")
            self.res2.set_text("")
            return
        y, m = b.year - a.year, b.month - a.month
        d = b.day - a.day
        if d < 0:
            m -= 1
            prev = (b.replace(day=1) - datetime.timedelta(days=1))
            d += prev.day
        if m < 0:
            y -= 1
            m += 12
        parts = [f"{n} {w}{'s' if n != 1 else ''}" for n, w in ((y, "year"), (m, "month"), (d, "day")) if n]
        self.res.set_text(", ".join(parts))
        self.res2.set_text(f"{days:,} days  ({days // 7} weeks, {days % 7} days)")

    def set_entry_value(self, s):
        pass

    def display_value(self):
        return self.res.get_text()

    def key(self, ev):
        return False


# ---------------------------------------------------------------- Window
MODES = [("standard", "Standard", StandardCalc), ("scientific", "Scientific", ScientificCalc),
         ("programmer", "Programmer", ProgrammerCalc), ("date", "Date calculation", DateCalc)]


class CalcWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        st = app.settings
        self.st = st
        self._menu = None
        self.set_title("Calculator")
        self.set_icon_name("pi-calculator")
        self.get_style_context().add_class("fx")
        self.get_style_context().add_class("calc")
        self.set_default_size(st["width"], st["height"])
        self.set_size_request(320, 500)
        self.connect("key-press-event", self._key)
        self.connect("configure-event", self._configure)
        self.connect("size-allocate", lambda *a: self._layout())
        self.connect("delete-event", lambda *a: (self.st.save(), False)[1])
        tb = WinTitlebar(self)
        t, _ = app_title("Calculator", draw_logo)
        tb.pack_start(t)
        tb.show_all()

        self.overlay = Gtk.Overlay()
        main = Gtk.Box()
        self.left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        top = Gtk.Box(spacing=4)
        top.set_margin_start(4)
        top.set_margin_top(2)
        top.pack_start(icon_button("view", lambda w: self.toggle_nav(), tip="Open Navigation"), False, False, 0)
        self.mode_lbl = label("Standard", "mode-title")
        top.pack_start(self.mode_lbl, False, False, 4)
        self.hist_btn = icon_button("history", lambda w: self.toggle_history_popup(), tip="History (Ctrl+H)")
        top.pack_end(self.hist_btn, False, False, 4)
        self.left.pack_start(top, False, False, 0)
        self.mode_box = Gtk.Box()
        self.left.pack_start(self.mode_box, True, True, 0)
        main.pack_start(self.left, True, True, 0)
        self.hist = self._build_history()
        main.pack_start(self.hist, False, False, 0)
        self.overlay.add(main)
        self.nav = self._build_nav()
        self.overlay.add_overlay(self.nav)
        self.add(self.overlay)
        self.overlay.show_all()
        self.nav.hide()
        self.view = None
        self.set_mode(st.get("mode", "standard"))
        self._layout()

    # ---------------- navigation
    def _build_nav(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.get_style_context().add_class("navpanel")
        sw.set_size_request(250, -1)
        sw.set_halign(Gtk.Align.START)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.pack_start(icon_button("view", lambda w: self.toggle_nav(), tip="Close Navigation"), False, False, 4)
        box.pack_start(label("Calculator", "navhead"), False, False, 0)
        self.nav_items = {}

        def item(key_, text):
            b = Gtk.Button()
            b.get_style_context().add_class("navitem")
            b.add(label(text))
            b.connect("clicked", lambda w: (self.set_mode(key_), self.toggle_nav()))
            box.pack_start(b, False, False, 0)
            self.nav_items[key_] = b
        for k, n, _ in MODES:
            item(k, n)
        box.pack_start(label("Converter", "navhead"), False, False, 0)
        for cat in UNITS:
            item("conv:" + cat, cat)
        sw.add(box)
        return sw

    def toggle_nav(self):
        if self.nav.get_visible():
            self.nav.hide()
        else:
            self.nav.show_all()

    def set_mode(self, mode):
        for c in self.mode_box.get_children():
            c.destroy()
        if mode.startswith("conv:") and mode[5:] in UNITS:
            v = ConverterCalc(self, mode[5:])
        else:
            cls = {k: c for k, _, c in MODES}.get(mode, StandardCalc)
            v = cls(self)
            mode = [k for k, _, c in MODES if c is cls][0]
        self.view = v
        self.st["mode"] = mode
        self.mode_lbl.set_text(v.title)
        self.mode_box.pack_start(v, True, True, 0)
        v.show_all()
        for k, b in self.nav_items.items():
            ctx = b.get_style_context()
            (ctx.add_class if k == mode else ctx.remove_class)("selected")
        is_conv = mode.startswith("conv:") or mode == "date"
        self.hist_btn.set_visible(not is_conv)
        self._layout()

    # ---------------- memory
    def memory_row(self, view):
        row = Gtk.Box(spacing=2, homogeneous=True)
        row.set_margin_start(6)
        row.set_margin_end(6)
        btns = {}

        def mk(t, cb, tip):
            b = Gtk.Button(label=t)
            b.get_style_context().add_class("mem")
            b.set_can_focus(False)
            b.set_tooltip_text(tip)
            b.connect("clicked", lambda w: (cb(view), self._mem_sens(btns)))
            row.pack_start(b, True, True, 0)
            btns[t] = b
        mk("MC", lambda v: self.st.__setitem__("memory", []), "Clear all memory (Ctrl+L)")
        mk("MR", lambda v: self.st["memory"] and v.set_entry_value(self.st["memory"][0]), "Memory recall (Ctrl+R)")
        mk("M+", lambda v: self._mem_add(v, 1), "Memory add (Ctrl+P)")
        mk("M−", lambda v: self._mem_add(v, -1), "Memory subtract (Ctrl+Q)")
        mk("MS", lambda v: self._mem_store(v), "Memory store (Ctrl+M)")
        self._mem_sens(btns)
        self._mem_btns = btns
        return row

    def _mem_sens(self, btns):
        has = bool(self.st["memory"])
        btns["MC"].set_sensitive(has)
        btns["MR"].set_sensitive(has)
        self._refresh_mem_list()

    def _mem_store(self, v):
        self.st["memory"].insert(0, v.display_value().replace(",", ""))

    def _mem_add(self, v, sign):
        try:
            cur = float(v.display_value().replace(",", ""))
        except ValueError:
            return
        if not self.st["memory"]:
            self.st["memory"].insert(0, "0")
        try:
            m = float(self.st["memory"][0])
        except ValueError:
            m = 0.0
        self.st["memory"][0] = fmt_num(m + sign * cur)

    # ---------------- history / memory panel
    def _build_history(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("histpanel")
        box.set_size_request(260, -1)
        tabs = Gtk.Box()
        tabs.set_margin_start(8)
        self.htabs = {}
        for t in ("History", "Memory"):
            b = Gtk.Button(label=t)
            b.get_style_context().add_class("htab")
            b.connect("clicked", lambda w, t=t: self._htab(t))
            tabs.pack_start(b, False, False, 0)
            self.htabs[t] = b
        box.pack_start(tabs, False, False, 4)
        self.hstack = Gtk.Stack()
        self.hist_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mem_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for name, lst in (("History", self.hist_list), ("Memory", self.mem_list)):
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.add(lst)
            self.hstack.add_named(sw, name)
        box.pack_start(self.hstack, True, True, 0)
        clr = icon_button("trash", lambda w: self._clear_panel(), tip="Clear")
        clr.set_halign(Gtk.Align.END)
        clr.set_margin_end(8)
        clr.set_margin_bottom(6)
        box.pack_start(clr, False, False, 0)
        self._htab("History")
        self._refresh_history()
        return box

    def _htab(self, t):
        self.hstack.set_visible_child_name(t)
        for n, b in self.htabs.items():
            ctx = b.get_style_context()
            (ctx.add_class if n == t else ctx.remove_class)("on")

    def _clear_panel(self):
        if self.hstack.get_visible_child_name() == "History":
            self.st["history"] = []
            self._refresh_history()
        else:
            self.st["memory"] = []
            if hasattr(self, "_mem_btns"):
                self._mem_sens(self._mem_btns)

    def add_history(self, expr, result):
        self.st["history"].insert(0, [expr, result])
        del self.st["history"][100:]
        self._refresh_history()

    def _refresh_history(self):
        for c in self.hist_list.get_children():
            c.destroy()
        if not self.st["history"]:
            lb = label("There's no history yet", "sec")
            lb.set_margin_start(16)
            lb.set_margin_top(10)
            self.hist_list.pack_start(lb, False, False, 0)
        for expr, res in self.st["history"]:
            b = Gtk.Button()
            b.get_style_context().add_class("histrow")
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.pack_start(label(expr, "hist-expr", xalign=1.0, ellipsize=True), False, False, 0)
            col.pack_start(label(group(res) if re.match(r"^-?[\d.]+$", res) else res, "hist-val", xalign=1.0,
                                 ellipsize=True), False, False, 0)
            b.add(col)
            b.connect("clicked", lambda w, r=res: self.view.set_entry_value(r))
            self.hist_list.pack_start(b, False, False, 0)
        self.hist_list.show_all()

    def _refresh_mem_list(self):
        if not hasattr(self, "mem_list"):
            return
        for c in self.mem_list.get_children():
            c.destroy()
        if not self.st["memory"]:
            lb = label("There's nothing saved in memory", "sec")
            lb.set_margin_start(16)
            lb.set_margin_top(10)
            self.mem_list.pack_start(lb, False, False, 0)
        for i, v in enumerate(self.st["memory"]):
            b = Gtk.Button()
            b.get_style_context().add_class("histrow")
            b.add(label(group(v), "hist-val", xalign=1.0))
            b.connect("clicked", lambda w, v=v: self.view.set_entry_value(v))
            self.mem_list.pack_start(b, False, False, 0)
        self.mem_list.show_all()

    def toggle_history_popup(self):
        if self.get_allocated_width() >= 600:
            return
        # narrow window: show the panel as a popover
        pop = Gtk.Popover()
        pop.set_relative_to(self.hist_btn)
        pop.get_style_context().add_class("fx-pop")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_size_request(280, 360)
        sw = Gtk.ScrolledWindow()
        lst = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if not self.st["history"]:
            lst.pack_start(label("There's no history yet", "sec"), False, False, 10)
        for expr, res in self.st["history"]:
            b = Gtk.Button()
            b.get_style_context().add_class("histrow")
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            col.pack_start(label(expr, "hist-expr", xalign=1.0, ellipsize=True), False, False, 0)
            col.pack_start(label(res, "hist-val", xalign=1.0, ellipsize=True), False, False, 0)
            b.add(col)
            b.connect("clicked", lambda w, r=res: (self.view.set_entry_value(r), pop.popdown()))
            lst.pack_start(b, False, False, 0)
        sw.add(lst)
        box.pack_start(sw, True, True, 0)
        pop.add(box)
        pop.show_all()
        pop.popup()

    def _layout(self):
        w = self.get_allocated_width() or self.st["width"]
        wide = w >= 600 and not (self.st["mode"].startswith("conv:") or self.st["mode"] == "date")
        if self.hist.get_visible() != wide:
            self.hist.set_visible(wide)

    def _configure(self, w, ev):
        if not self.is_maximized():
            self.st["width"], self.st["height"] = self.get_size()
        GLib.idle_add(lambda: self._layout() and False)
        return False

    # ---------------- keyboard
    def _key(self, w, ev):
        ctrl = bool(ev.state & Gdk.ModifierType.CONTROL_MASK)
        alt = bool(ev.state & Gdk.ModifierType.MOD1_MASK)
        k = Gdk.keyval_to_lower(ev.keyval)
        if isinstance(self.get_focus(), (Gtk.Entry, Gtk.Calendar)):
            return False
        if alt and Gdk.KEY_1 <= k <= Gdk.KEY_4:
            self.set_mode(MODES[k - Gdk.KEY_1][0])
            return True
        if ctrl and k == Gdk.KEY_c:
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.view.display_value().replace(",", ""), -1)
            return True
        if ctrl and k == Gdk.KEY_v:
            t = (Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text() or "").strip().replace(",", "")
            try:
                float(t)
                self.view.set_entry_value(t)
            except ValueError:
                pass
            return True
        if ctrl and k == Gdk.KEY_h:
            self.toggle_history_popup()
            return True
        if ctrl and k in (Gdk.KEY_m, Gdk.KEY_r, Gdk.KEY_p, Gdk.KEY_q, Gdk.KEY_l) and hasattr(self, "_mem_btns"):
            name = {Gdk.KEY_m: "MS", Gdk.KEY_r: "MR", Gdk.KEY_p: "M+", Gdk.KEY_q: "M−", Gdk.KEY_l: "MC"}[k]
            b = self._mem_btns.get(name)
            if b and b.get_sensitive():
                b.clicked()
            return True
        if ctrl:
            return False
        if k == Gdk.KEY_Escape and self.nav.get_visible():
            self.nav.hide()
            return True
        return bool(self.view and self.view.key(ev))


class CalcApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.settings = JsonSettings("pi-calculator", DEFAULTS)
        apply_css(CSS)
        GLib.timeout_add_seconds(5, lambda: self.settings.save() or True)

    def do_activate(self):
        w = self.get_active_window()
        if w:
            w.present()
            return
        CalcWindow(self).present()


def main():
    GLib.set_prgname("pi-calculator")
    GLib.set_application_name("Calculator")
    app = CalcApp()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
