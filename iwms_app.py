#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IWMS - Inventory & Warehouse Management System
=================================================
ONE FILE. NO PIP INSTALL. Just Python 3 (built in on most PCs, or download
free from https://www.python.org/downloads/ -- tick "Add Python to PATH").

HOW TO RUN
  Windows : double-click this file (if .py is associated with Python), or
            open Command Prompt here and run:  python iwms_app.py
  Mac/Linux: open Terminal here and run:       python3 iwms_app.py

What happens when you run it:
  1. Creates a real SQLite database file "iwms.db" next to this script
     (only the first time -- your data persists after that).
  2. Starts a small built-in web server at http://127.0.0.1:5000
  3. Opens that address in your default browser automatically.
  4. Sign in with access code:  iwms2026

Keep the black terminal window open while you use the app -- closing it
stops the server. Press Ctrl+C in that window to stop it yourself.

Everything (backend + database logic + the web page) lives in this single
file so there is nothing else to download or install besides Python.
"""
import os, re, json, sqlite3, threading, webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "iwms.db")
PORT = 5000

SCHEMA_SQL = r"""-- IWMS relational schema (SQLite) -- matches the ER diagram from the project slides

CREATE TABLE CATEGORY (
  CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT NOT NULL
);

CREATE TABLE SUPPLIER (
  SupplierID INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT NOT NULL,
  Phone TEXT,
  Address TEXT
);

CREATE TABLE PRODUCT (
  ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
  SKU TEXT UNIQUE NOT NULL,
  Name TEXT NOT NULL,
  CategoryID INTEGER,
  SupplierID INTEGER,
  Price REAL NOT NULL,
  FOREIGN KEY (CategoryID) REFERENCES CATEGORY(CategoryID),
  FOREIGN KEY (SupplierID) REFERENCES SUPPLIER(SupplierID)
);

CREATE TABLE WAREHOUSE (
  WarehouseID INTEGER PRIMARY KEY AUTOINCREMENT,
  Location TEXT NOT NULL,
  Capacity INTEGER NOT NULL
);

CREATE TABLE STOCK (
  StockID INTEGER PRIMARY KEY AUTOINCREMENT,
  ProductID INTEGER,
  WarehouseID INTEGER,
  Quantity INTEGER NOT NULL DEFAULT 0,
  ReorderLevel INTEGER NOT NULL DEFAULT 10,
  FOREIGN KEY (ProductID) REFERENCES PRODUCT(ProductID),
  FOREIGN KEY (WarehouseID) REFERENCES WAREHOUSE(WarehouseID)
);

CREATE TABLE CUSTOMER (
  CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT NOT NULL,
  Phone TEXT
);

CREATE TABLE ORDERS (
  OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
  Type TEXT NOT NULL,          -- 'Purchase' or 'Sale'
  PartyID INTEGER NOT NULL,    -- SupplierID or CustomerID depending on PartyKind
  PartyKind TEXT NOT NULL,     -- 'Supplier' or 'Customer'
  Date TEXT NOT NULL,
  Status TEXT NOT NULL
);

CREATE TABLE ORDER_ITEMS (
  OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
  OrderID INTEGER,
  ProductID INTEGER,
  WarehouseID INTEGER,
  Quantity INTEGER NOT NULL,
  UnitPrice REAL NOT NULL,
  FOREIGN KEY (OrderID) REFERENCES ORDERS(OrderID),
  FOREIGN KEY (ProductID) REFERENCES PRODUCT(ProductID),
  FOREIGN KEY (WarehouseID) REFERENCES WAREHOUSE(WarehouseID)
);

CREATE TABLE STOCK_MOVEMENT (
  MovementID INTEGER PRIMARY KEY AUTOINCREMENT,
  Date TEXT NOT NULL,
  ProductID INTEGER,
  WarehouseID INTEGER,
  Type TEXT NOT NULL,   -- 'IN' or 'OUT'
  Quantity INTEGER NOT NULL,
  Note TEXT,
  FOREIGN KEY (ProductID) REFERENCES PRODUCT(ProductID),
  FOREIGN KEY (WarehouseID) REFERENCES WAREHOUSE(WarehouseID)
);

-- ===================== SEED DATA =====================

INSERT INTO CATEGORY (CategoryID, Name) VALUES
 (1,'Electronics'), (2,'Stationery'), (3,'Packaging Materials'), (4,'Tools & Hardware'), (5,'Furniture');

INSERT INTO SUPPLIER (SupplierID, Name, Phone, Address) VALUES
 (1,'Bharat Electro Supplies','+91 98450 11234','Bengaluru, KA'),
 (2,'Sri Lakshmi Traders','+91 90000 22345','Hyderabad, TS'),
 (3,'Om Packaging Co.','+91 63000 33456','Chennai, TN'),
 (4,'Novatech Distributors','+91 88700 44567','Pune, MH');

INSERT INTO PRODUCT (ProductID, SKU, Name, CategoryID, SupplierID, Price) VALUES
 (1,'ELC-1001','Wireless Mouse',1,1,450),
 (2,'ELC-1002','USB-C Cable 1m',1,1,150),
 (3,'ELC-1003','LED Desk Lamp',1,1,720),
 (4,'STA-2001','A4 Copier Paper (Ream)',2,2,280),
 (5,'STA-2002','Ball Pen (Box of 50)',2,2,320),
 (6,'PKG-3001','Corrugated Box (Medium)',3,3,25),
 (7,'PKG-3002','Bubble Wrap Roll',3,3,480),
 (8,'PKG-3003','Packing Tape Roll',3,3,60),
 (9,'TLS-4001','Cordless Drill',4,4,2600),
 (10,'TLS-4002','Claw Hammer',4,4,350),
 (11,'FUR-5001','Steel Shelving Unit',5,4,4200),
 (12,'FUR-5002','Office Chair',5,4,3600);

INSERT INTO WAREHOUSE (WarehouseID, Location, Capacity) VALUES
 (1,'Warehouse A — Balanagar, Hyderabad',5000),
 (2,'Warehouse B — Kukatpally, Hyderabad',3000);

INSERT INTO STOCK (StockID, ProductID, WarehouseID, Quantity, ReorderLevel) VALUES
 (1,1,1,45,10), (2,1,2,6,10), (3,2,1,120,20), (4,3,1,3,10),
 (5,4,1,80,15), (6,5,1,4,10), (7,6,2,200,30), (8,7,2,15,10),
 (9,8,1,8,10), (10,9,1,12,5), (11,10,1,30,8), (12,11,2,5,6), (13,12,2,18,5);

INSERT INTO CUSTOMER (CustomerID, Name, Phone) VALUES
 (1,'Ramesh Retail Store','+91 90100 11111'),
 (2,'Green Mart Supermarket','+91 90100 22222'),
 (3,'City Electronics Hub','+91 90100 33333');

INSERT INTO ORDERS (OrderID, Type, PartyID, PartyKind, Date, Status) VALUES
 (1,'Purchase',1,'Supplier','2026-09-02','Received'),
 (2,'Sale',1,'Customer','2026-09-05','Fulfilled'),
 (3,'Purchase',4,'Supplier','2026-09-10','Received'),
 (4,'Sale',3,'Customer','2026-09-14','Fulfilled');

INSERT INTO ORDER_ITEMS (OrderItemID, OrderID, ProductID, WarehouseID, Quantity, UnitPrice) VALUES
 (1,1,1,1,20,430), (2,2,1,1,5,450), (3,3,9,1,6,2500), (4,4,3,1,2,720);

INSERT INTO STOCK_MOVEMENT (MovementID, Date, ProductID, WarehouseID, Type, Quantity, Note) VALUES
 (1,'2026-09-02 10:14',1,1,'IN',20,'Purchase order #1 received'),
 (2,'2026-09-05 15:40',1,1,'OUT',5,'Sales order #2 dispatched'),
 (3,'2026-09-10 09:05',9,1,'IN',6,'Purchase order #3 received'),
 (4,'2026-09-14 13:22',3,1,'OUT',2,'Sales order #4 dispatched');
"""

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IWMS — Inventory &amp; Warehouse Management System</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg: #eeece4;
  --panel: #fbfaf6;
  --panel-2: #f3f1e9;
  --ink: #23241f;
  --ink-soft: #5c5c53;
  --line: #d9d5c8;
  --primary: #2b4735;
  --primary-ink: #eef1ec;
  --accent: #c4661f;
  --accent-soft: #f3e1cf;
  --steel: #3e6b92;
  --steel-soft: #dfe8ee;
  --ok: #3c7a4f;
  --ok-soft: #dfeee2;
  --danger: #a3392b;
  --danger-soft: #f5e0dc;
  --radius: 3px;
  --font-ui: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', 'SFMono-Regular', monospace;
}
:root:not([data-theme="light"]) {
  @media (prefers-color-scheme: dark) {
    --bg: #1a1c17;
    --panel: #23261f;
    --panel-2: #2a2d24;
    --ink: #e9e7dd;
    --ink-soft: #a9a89b;
    --line: #3a3d33;
    --primary: #3f6449;
    --primary-ink: #eef1ec;
    --accent: #d97a34;
    --accent-soft: #3a2c1c;
    --steel: #6b9bc4;
    --steel-soft: #1f2c34;
    --ok: #5ca873;
    --ok-soft: #1e2f22;
    --danger: #c96a5a;
    --danger-soft: #34211d;
  }
}
:root[data-theme="dark"] {
  --bg: #1a1c17;
  --panel: #23261f;
  --panel-2: #2a2d24;
  --ink: #e9e7dd;
  --ink-soft: #a9a89b;
  --line: #3a3d33;
  --primary: #3f6449;
  --primary-ink: #eef1ec;
  --accent: #d97a34;
  --accent-soft: #3a2c1c;
  --steel: #6b9bc4;
  --steel-soft: #1f2c34;
  --ok: #5ca873;
  --ok-soft: #1e2f22;
  --danger: #c96a5a;
  --danger-soft: #34211d;
}

*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{
  background:var(--bg);
  color:var(--ink);
  font-family:var(--font-ui);
  font-size:14px;
  line-height:1.5;
  min-height:100vh;
}
h1,h2,h3,h4{font-family:var(--font-ui); font-weight:600; margin:0 0 4px 0; letter-spacing:-0.01em;}
p{margin:0 0 10px 0; color:var(--ink-soft);}
.mono{font-family:var(--font-mono);}
button{font-family:var(--font-ui); cursor:pointer;}
input,select,textarea{font-family:var(--font-ui); font-size:14px;}
a{color:inherit;}
::-webkit-scrollbar{height:8px;width:8px;}
::-webkit-scrollbar-thumb{background:var(--line);border-radius:4px;}

/* ---------- LOGIN ---------- */
#loginScreen{
  min-height:100vh; display:flex; align-items:center; justify-content:center;
  background:
    radial-gradient(ellipse 900px 500px at 50% -10%, var(--panel-2) 0%, var(--bg) 70%);
  padding:24px;
}
.login-card{
  width:100%; max-width:400px;
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:6px;
  padding:32px 30px 28px;
}
.login-mark{
  display:flex; align-items:center; gap:10px; margin-bottom:22px;
}
.login-mark .crate{width:30px;height:30px;flex-shrink:0;}
.login-mark .name{font-weight:700; font-size:15px; letter-spacing:0.02em;}
.login-mark .sub{font-size:11px; color:var(--ink-soft); font-family:var(--font-mono);}
.login-card h2{font-size:19px; margin-bottom:6px;}
.login-card > p{font-size:13px; margin-bottom:20px;}
.field{margin-bottom:14px;}
.field label{display:block; font-size:12px; color:var(--ink-soft); margin-bottom:5px;}
.field input, .field select{
  width:100%; padding:9px 10px; border:1px solid var(--line); border-radius:var(--radius);
  background:var(--panel-2); color:var(--ink);
}
.field input:focus, .field select:focus, .field textarea:focus, button:focus-visible{
  outline:2px solid var(--steel); outline-offset:1px;
}
.role-pick{display:flex; gap:8px;}
.role-pick label{
  flex:1; border:1px solid var(--line); border-radius:var(--radius); padding:10px 8px;
  text-align:center; font-size:13px; cursor:pointer; background:var(--panel-2); color:var(--ink-soft);
}
.role-pick input{display:none;}
.role-pick input:checked + span{color:var(--ink); font-weight:600;}
.role-pick label:has(input:checked){border-color:var(--primary); background:var(--ok-soft); color:var(--ink);}
.btn-primary{
  width:100%; padding:11px; background:var(--primary); color:var(--primary-ink);
  border:none; border-radius:var(--radius); font-weight:600; font-size:14px; margin-top:6px;
}
.btn-primary:hover{filter:brightness(1.08);}
.login-hint{margin-top:16px; font-size:11.5px; color:var(--ink-soft); border-top:1px dashed var(--line); padding-top:12px;}

/* ---------- APP SHELL ---------- */
#app{display:none; min-height:100vh;}
#app.active{display:flex;}

.sidebar{
  width:220px; flex-shrink:0; background:var(--primary); color:var(--primary-ink);
  display:flex; flex-direction:column; position:sticky; top:0; height:100vh;
}
.side-brand{padding:18px 18px 14px; display:flex; gap:10px; align-items:center; border-bottom:1px solid rgba(255,255,255,0.12);}
.side-brand .crate{width:26px; height:26px; flex-shrink:0;}
.side-brand .name{font-weight:700; font-size:14px; line-height:1.25;}
.side-brand .sub{font-size:10px; opacity:0.65; font-family:var(--font-mono); letter-spacing:0.03em;}
.side-nav{flex:1; padding:10px 8px; overflow-y:auto;}
.side-nav .grp-label{font-size:10.5px; opacity:0.55; text-transform:uppercase; letter-spacing:0.06em; padding:12px 10px 6px;}
.nav-item{
  display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:var(--radius);
  color:rgba(255,255,255,0.82); font-size:13.5px; cursor:pointer; margin-bottom:2px; border:1px solid transparent;
}
.nav-item svg{width:16px;height:16px; flex-shrink:0; opacity:0.85;}
.nav-item:hover{background:rgba(255,255,255,0.08); color:#fff;}
.nav-item.active{background:rgba(255,255,255,0.14); color:#fff; border-color:rgba(255,255,255,0.15);}
.nav-item .badge{margin-left:auto; background:var(--accent); color:#fff; font-size:10.5px; font-family:var(--font-mono); padding:1px 6px; border-radius:8px;}
.side-foot{padding:12px; border-top:1px solid rgba(255,255,255,0.12); font-size:12px;}
.side-foot .who{font-weight:600;}
.side-foot .role-tag{opacity:0.65; font-family:var(--font-mono); font-size:10.5px;}
.side-foot button{background:none; border:1px solid rgba(255,255,255,0.25); color:rgba(255,255,255,0.85); font-size:11.5px; padding:5px 8px; border-radius:var(--radius); margin-top:8px; width:100%;}
.side-foot button:hover{background:rgba(255,255,255,0.1);}

.main{flex:1; min-width:0; display:flex; flex-direction:column;}
.topbar{
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 26px; border-bottom:1px solid var(--line); background:var(--panel);
  position:sticky; top:0; z-index:5;
}
.topbar h1{font-size:17px;}
.topbar .crumb{font-size:11.5px; color:var(--ink-soft); font-family:var(--font-mono);}
.topbar-right{display:flex; align-items:center; gap:12px;}
.clock{font-family:var(--font-mono); font-size:12px; color:var(--ink-soft);}
.menu-toggle{display:none; background:none; border:1px solid var(--line); border-radius:var(--radius); padding:6px 9px;}

.content{padding:22px 26px 60px; flex:1;}
.view{display:none; animation:fadein .25s ease;}
.view.active{display:block;}
@keyframes fadein{from{opacity:0; transform:translateY(4px);} to{opacity:1; transform:translateY(0);}}
@media (prefers-reduced-motion: reduce){ .view{animation:none;} }

/* ---------- COMPONENTS ---------- */
.stat-row{display:grid; grid-template-columns:repeat(auto-fit, minmax(170px,1fr)); gap:12px; margin-bottom:22px;}
.stat-card{background:var(--panel); border:1px solid var(--line); border-radius:5px; padding:14px 16px;}
.stat-card .k{font-size:11.5px; color:var(--ink-soft); margin-bottom:6px;}
.stat-card .v{font-size:26px; font-weight:600; font-family:var(--font-mono);}
.stat-card .v.alert{color:var(--accent);}
.stat-card .t{font-size:11px; color:var(--ink-soft); margin-top:3px;}

.panel{background:var(--panel); border:1px solid var(--line); border-radius:5px; margin-bottom:20px;}
.panel-head{display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid var(--line); flex-wrap:wrap; gap:10px;}
.panel-head h3{font-size:14.5px;}
.panel-head .desc{font-size:12px; color:var(--ink-soft); margin-top:2px;}
.panel-body{padding:16px;}
.panel-body.flush{padding:0;}

.btn{border:1px solid var(--line); background:var(--panel-2); color:var(--ink); padding:7px 12px; border-radius:var(--radius); font-size:12.5px; font-weight:500;}
.btn:hover{border-color:var(--ink-soft);}
.btn.primary{background:var(--primary); color:var(--primary-ink); border-color:var(--primary);}
.btn.primary:hover{filter:brightness(1.1);}
.btn.accent{background:var(--accent); color:#fff; border-color:var(--accent);}
.btn.ghost{background:transparent; border-color:transparent;}
.btn.small{padding:4px 8px; font-size:11.5px;}
.btn.danger-outline{color:var(--danger); border-color:var(--danger-soft); background:var(--danger-soft);}
.btn:disabled{opacity:0.4; cursor:not-allowed;}

table{width:100%; border-collapse:collapse; font-size:13px;}
thead th{
  text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.04em;
  color:var(--ink-soft); font-weight:600; padding:9px 14px; border-bottom:1px solid var(--line);
  background:var(--panel-2); white-space:nowrap;
}
tbody td{padding:10px 14px; border-bottom:1px solid var(--line); vertical-align:middle;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover{background:var(--panel-2);}
.tbl-wrap{overflow-x:auto;}
td.num, th.num{text-align:right; font-family:var(--font-mono);}
td.id{font-family:var(--font-mono); color:var(--ink-soft); font-size:12px;}

.tag{display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; font-family:var(--font-mono);}
.tag.ok{background:var(--ok-soft); color:var(--ok);}
.tag.low{background:var(--accent-soft); color:var(--accent);}
.tag.out{background:var(--danger-soft); color:var(--danger);}
.tag.steel{background:var(--steel-soft); color:var(--steel);}
.tag.neutral{background:var(--panel-2); color:var(--ink-soft); border:1px solid var(--line);}

.actions-cell{display:flex; gap:6px; justify-content:flex-end;}

.empty{padding:34px 16px; text-align:center; color:var(--ink-soft); font-size:13px;}
.empty b{display:block; color:var(--ink); font-size:14px; margin-bottom:4px;}

.tabs{display:flex; gap:4px; border-bottom:1px solid var(--line); padding:0 16px;}
.tab-btn{padding:10px 4px; margin-right:16px; background:none; border:none; border-bottom:2px solid transparent; color:var(--ink-soft); font-size:13px; font-weight:500;}
.tab-btn.active{color:var(--ink); border-bottom-color:var(--accent); font-weight:600;}

.toast-wrap{position:fixed; bottom:20px; right:20px; z-index:80; display:flex; flex-direction:column; gap:8px;}
.toast{background:var(--ink); color:var(--bg); padding:10px 16px; border-radius:var(--radius); font-size:13px; box-shadow:0 4px 14px rgba(0,0,0,0.2); max-width:320px; animation:slidein .2s ease;}
.toast.err{background:var(--danger);}
@keyframes slidein{from{transform:translateY(8px); opacity:0;} to{transform:translateY(0); opacity:1);}}

/* modal */
.modal-back{position:fixed; inset:0; background:rgba(20,20,15,0.45); display:none; align-items:flex-start; justify-content:center; z-index:60; padding:40px 16px; overflow-y:auto;}
.modal-back.active{display:flex;}
.modal{background:var(--panel); border-radius:6px; width:100%; max-width:480px; border:1px solid var(--line);}
.modal-head{display:flex; justify-content:space-between; align-items:center; padding:16px 18px; border-bottom:1px solid var(--line);}
.modal-head h3{font-size:15px;}
.modal-head button{background:none; border:none; font-size:18px; color:var(--ink-soft); line-height:1;}
.modal-body{padding:18px;}
.modal-foot{padding:14px 18px; border-top:1px solid var(--line); display:flex; justify-content:flex-end; gap:8px;}
.form-row{margin-bottom:13px;}
.form-row label{display:block; font-size:12px; color:var(--ink-soft); margin-bottom:5px;}
.form-row input, .form-row select, .form-row textarea{
  width:100%; padding:8px 10px; border:1px solid var(--line); border-radius:var(--radius); background:var(--panel-2); color:var(--ink);
}
.form-grid{display:grid; grid-template-columns:1fr 1fr; gap:0 12px;}
.form-note{font-size:11.5px; color:var(--ink-soft); background:var(--panel-2); padding:8px 10px; border-radius:var(--radius); border:1px solid var(--line);}
.error-text{color:var(--danger); font-size:12px; margin-top:6px;}

/* sql box */
.sql-box{
  background:var(--ink); color:#dfe6da; font-family:var(--font-mono); font-size:12.5px;
  padding:12px 14px; border-radius:var(--radius); overflow-x:auto; white-space:pre; margin-bottom:14px;
}
:root[data-theme="dark"] .sql-box, :root:not([data-theme="light"]) .sql-box{ }
.sql-box .kw{color:#e8a86a;}

.schema-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px;}
.schema-tbl{border:1px solid var(--line); border-radius:5px; overflow:hidden;}
.schema-tbl .t-head{background:var(--primary); color:var(--primary-ink); padding:8px 12px; font-weight:600; font-size:12.5px; font-family:var(--font-mono);}
.schema-tbl .t-row{padding:6px 12px; font-size:12px; font-family:var(--font-mono); border-top:1px solid var(--line); display:flex; justify-content:space-between; color:var(--ink-soft);}
.schema-tbl .t-row.pk{color:var(--ink); font-weight:600;}
.schema-tbl .t-row .k{color:var(--steel); font-size:10px; margin-left:6px;}

.kv-note{font-size:12px; color:var(--ink-soft); margin-top:14px; display:flex; gap:18px; flex-wrap:wrap;}
.kv-note span{display:inline-flex; align-items:center; gap:5px;}
.dot{width:8px; height:8px; border-radius:50%; display:inline-block;}

@media (max-width: 880px){
  .sidebar{position:fixed; left:-240px; z-index:50; transition:left .2s ease; box-shadow:4px 0 18px rgba(0,0,0,0.2);}
  .sidebar.open{left:0;}
  .menu-toggle{display:inline-block;}
  .content{padding:16px 14px 50px;}
  .topbar{padding:12px 14px;}
  .form-grid{grid-template-columns:1fr;}
}
</style>
</head>
<body>

<!-- ============ LOGIN ============ -->
<div id="loginScreen">
  <div class="login-card">
    <div class="login-mark">
      <svg class="crate" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 10L16 4L28 10V22L16 28L4 22V10Z" stroke="#2b4735" stroke-width="2" stroke-linejoin="round"/>
        <path d="M4 10L16 16M16 16L28 10M16 16V28" stroke="#2b4735" stroke-width="2" stroke-linejoin="round"/>
      </svg>
      <div>
        <div class="name">IWMS</div>
        <div class="sub">WAREHOUSE OPS TERMINAL</div>
      </div>
    </div>
    <h2>Sign in to continue</h2>
    <p>Inventory &amp; Warehouse Management System — internal access only.</p>
    <form id="loginForm">
      <div class="field">
        <label for="loginName">Your name</label>
        <input type="text" id="loginName" placeholder="e.g. Varalakshmi K" required>
      </div>
      <div class="field">
        <label>Sign in as</label>
        <div class="role-pick">
          <label><input type="radio" name="role" value="Admin" checked><span>Admin</span></label>
          <label><input type="radio" name="role" value="Staff"><span>Staff</span></label>
        </div>
      </div>
      <div class="field">
        <label for="loginPass">Access code</label>
        <input type="password" id="loginPass" placeholder="iwms2026" required>
      </div>
      <div id="loginError" class="error-text" style="display:none;">Incorrect access code. Try iwms2026.</div>
      <button type="submit" class="btn-primary">Enter warehouse system</button>
    </form>
    <div class="login-hint">Demo access code: <b class="mono">iwms2026</b> · Admin can edit suppliers &amp; delete records, Staff has view + stock/order entry only.</div>
  </div>
</div>

<!-- ============ APP ============ -->
<div id="app">
  <aside class="sidebar" id="sidebar">
    <div class="side-brand">
      <svg class="crate" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 10L16 4L28 10V22L16 28L4 22V10Z" stroke="#eef1ec" stroke-width="2" stroke-linejoin="round"/>
        <path d="M4 10L16 16M16 16L28 10M16 16V28" stroke="#eef1ec" stroke-width="2" stroke-linejoin="round"/>
      </svg>
      <div>
        <div class="name">IWMS</div>
        <div class="sub">v2.0 · Flask + SQLite</div>
      </div>
    </div>
    <nav class="side-nav" id="sideNav"></nav>
    <div class="side-foot">
      <div class="who" id="whoName">—</div>
      <div class="role-tag" id="whoRole">—</div>
      <button id="logoutBtn">Sign out</button>
    </div>
  </aside>

  <div class="main">
    <div class="topbar">
      <div style="display:flex; align-items:center; gap:10px;">
        <button class="menu-toggle" id="menuToggle">☰</button>
        <div>
          <h1 id="pageTitle">Dashboard</h1>
          <div class="crumb" id="pageCrumb">warehouse_db → overview</div>
        </div>
      </div>
      <div class="topbar-right">
        <div class="clock" id="clock">—</div>
      </div>
    </div>

    <div class="content" id="content">
      <!-- ===== DASHBOARD ===== -->
      <section class="view" id="view-dashboard">
        <div class="stat-row" id="dashStats"></div>
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Recent stock movements</h3>
              <div class="desc">Latest stock-in / stock-out transactions across all warehouses.</div>
            </div>
            <button class="btn" data-nav="warehouses">Go to Warehouses →</button>
          </div>
          <div class="panel-body flush tbl-wrap" id="dashMovements"></div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Products below reorder level</h3>
              <div class="desc">Same alert used on the Reports page — flags stock that needs restocking soon.</div>
            </div>
            <button class="btn" data-nav="reports">View full report →</button>
          </div>
          <div class="panel-body flush tbl-wrap" id="dashLowStock"></div>
        </div>
      </section>

      <!-- ===== PRODUCTS ===== -->
      <section class="view" id="view-products">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Product catalogue</h3>
              <div class="desc">Every item tracked in the warehouse, linked to a category and a supplier.</div>
            </div>
            <button class="btn primary" id="addProductBtn">+ Add product</button>
          </div>
          <div class="panel-body flush tbl-wrap" id="productsTable"></div>
        </div>
      </section>

      <!-- ===== SUPPLIERS ===== -->
      <section class="view" id="view-suppliers">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Suppliers</h3>
              <div class="desc">Vendors who supply stock. Each product links back to exactly one supplier.</div>
            </div>
            <button class="btn primary" id="addSupplierBtn">+ Add supplier</button>
          </div>
          <div class="panel-body flush tbl-wrap" id="suppliersTable"></div>
        </div>
      </section>

      <!-- ===== WAREHOUSES / STOCK ===== -->
      <section class="view" id="view-warehouses">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Warehouses</h3>
              <div class="desc">Physical storage locations. Each holds its own stock levels per product.</div>
            </div>
            <button class="btn primary" id="addWarehouseBtn">+ Add warehouse</button>
          </div>
          <div class="panel-body flush tbl-wrap" id="warehousesTable"></div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Stock levels</h3>
              <div class="desc">Filter by warehouse, then record a stock-in or stock-out transaction.</div>
            </div>
            <select id="stockWarehouseFilter" class="btn small"></select>
          </div>
          <div class="panel-body flush tbl-wrap" id="stockTable"></div>
        </div>
      </section>

      <!-- ===== ORDERS ===== -->
      <section class="view" id="view-orders">
        <div class="panel">
          <div class="tabs">
            <button class="tab-btn active" data-tab="purchase">Purchase orders (stock in)</button>
            <button class="tab-btn" data-tab="sale">Sales orders (stock out)</button>
          </div>
          <div class="panel-head">
            <div class="desc" id="ordersDesc">Orders placed with a supplier to bring new stock into a warehouse.</div>
            <button class="btn primary" id="addOrderBtn">+ New purchase order</button>
          </div>
          <div class="panel-body flush tbl-wrap" id="ordersTable"></div>
        </div>
      </section>

      <!-- ===== REPORTS ===== -->
      <section class="view" id="view-reports">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Low-stock alert</h3>
              <div class="desc">Flags every product/warehouse pair where quantity has dropped below its reorder level.</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="sql-box" id="sqlLowStock"></div>
          </div>
          <div class="panel-body flush tbl-wrap" id="reportLowStock"></div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Stock summary by warehouse</h3>
              <div class="desc">Total units and total value currently held in each warehouse.</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="sql-box" id="sqlWarehouseSummary"></div>
          </div>
          <div class="panel-body flush tbl-wrap" id="reportWarehouse"></div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Order history</h3>
              <div class="desc">Every purchase and sales order recorded in the system, most recent first.</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="sql-box" id="sqlOrderHistory"></div>
          </div>
          <div class="panel-body flush tbl-wrap" id="reportOrders"></div>
        </div>
      </section>

      <!-- ===== SCHEMA ===== -->
      <section class="view" id="view-schema">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Entity-relationship schema</h3>
              <div class="desc">Normalised to 3NF — primary keys (PK) uniquely identify rows, foreign keys (FK) link related tables.</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="schema-grid" id="schemaGrid"></div>
            <div class="kv-note">
              <span><span class="dot" style="background:var(--ink);"></span> Primary key</span>
              <span><span class="dot" style="background:var(--steel);"></span> Foreign key</span>
            </div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>Settings</h3>
              <div class="desc">Data is stored in a real SQLite database (iwms.db) on the Flask server running on this machine — not in the browser.</div>
            </div>
          </div>
          <div class="panel-body" style="display:flex; gap:10px; flex-wrap:wrap;">
            <button class="btn" id="exportBtn">Export data as JSON</button>
            <button class="btn danger-outline" id="resetBtn">Reset to seed data</button>
          </div>
        </div>
      </section>
    </div>
  </div>
</div>

<div class="modal-back" id="modalBack">
  <div class="modal">
    <div class="modal-head">
      <h3 id="modalTitle">Title</h3>
      <button id="modalClose">✕</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
    <div class="modal-foot" id="modalFoot"></div>
  </div>
</div>

<div class="toast-wrap" id="toastWrap"></div>

<script>
(function(){
"use strict";

/* ============================================================
   DATA LAYER
   The dataset lives in a real SQLite database (iwms.db) on the
   Flask server. This client never touches localStorage for the
   inventory data — every read is a fetch to /api/data, and every
   add/edit/delete/stock-move/order is a real SQL INSERT/UPDATE/
   DELETE executed server-side (see app.py). DB below is only an
   in-memory cache of the last server response, used for rendering.
   ============================================================ */
const ACCESS_CODE = "iwms2026";

let DB = null;

async function apiGet(url){
  const res = await fetch(url);
  if(!res.ok) throw new Error("Request failed: " + url);
  return res.json();
}
async function apiSend(url, method, body){
  const res = await fetch(url, {
    method,
    headers: {"Content-Type":"application/json"},
    body: body!==undefined ? JSON.stringify(body) : undefined
  });
  let data = null;
  try{ data = await res.json(); }catch(e){ /* no body */ }
  if(!res.ok){
    const msg = (data && data.error) ? data.error : ("Server error (" + res.status + ")");
    throw new Error(msg);
  }
  return data;
}

async function fetchAll(){
  DB = await apiGet("/api/data");
}
async function resetDB(){
  await apiSend("/api/reset", "POST");
  await fetchAll();
}

/* ---------- lookup helpers ---------- */
const byId = (arr, key) => { const m={}; arr.forEach(r=>m[r[key]]=r); return m; };
function categoryName(id){ const c = DB.categories.find(x=>x.CategoryID===id); return c? c.Name : "—"; }
function supplierName(id){ const s = DB.suppliers.find(x=>x.SupplierID===id); return s? s.Name : "—"; }
function warehouseName(id){ const w = DB.warehouses.find(x=>x.WarehouseID===id); return w? w.Location : "—"; }
function productRow(id){ return DB.products.find(x=>x.ProductID===id); }
function productName(id){ const p = productRow(id); return p? p.Name : "—"; }
function customerName(id){ const c = DB.customers.find(x=>x.CustomerID===id); return c? c.Name : "—"; }
function fmtMoney(n){ return "₹" + Number(n).toLocaleString("en-IN"); }
function esc(s){ return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

function totalStockForProduct(pid){
  return DB.stock.filter(s=>s.ProductID===pid).reduce((a,b)=>a+b.Quantity,0);
}
function lowStockRows(){
  return DB.stock.filter(s => s.Quantity < s.ReorderLevel).map(s=>({
    ...s,
    ProductName: productName(s.ProductID),
    SKU: (productRow(s.ProductID)||{}).SKU || "—",
    WarehouseName: warehouseName(s.WarehouseID)
  })).sort((a,b)=>a.Quantity-b.Quantity);
}

/* ============================================================
   SESSION / AUTH (demo-only, not real security)
   ============================================================ */
let SESSION = null; // {name, role}

/* ============================================================
   NAV CONFIG
   ============================================================ */
const NAV = [
  {id:"dashboard",  label:"Dashboard",        group:"Overview", icon:iconGrid()},
  {id:"products",   label:"Products",         group:"Catalogue", icon:iconBox()},
  {id:"suppliers",  label:"Suppliers",        group:"Catalogue", icon:iconTruck()},
  {id:"warehouses", label:"Warehouses & Stock", group:"Operations", icon:iconWarehouse()},
  {id:"orders",     label:"Orders",           group:"Operations", icon:iconClipboard()},
  {id:"reports",    label:"Reports",          group:"Insights", icon:iconChart()},
  {id:"schema",     label:"Database Schema",  group:"Insights", icon:iconLayers()}
];
const CRUMB = {
  dashboard:"warehouse_db → overview", products:"warehouse_db → product", suppliers:"warehouse_db → supplier",
  warehouses:"warehouse_db → warehouse, stock", orders:"warehouse_db → orders, order_items",
  reports:"warehouse_db → queries", schema:"warehouse_db → information_schema"
};

function iconGrid(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/></svg>`;}
function iconBox(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 8l9-5 9 5v8l-9 5-9-5V8z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>`;}
function iconTruck(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="1.5" y="6.5" width="12" height="9" rx="1"/><path d="M13.5 10h4l3 3.5v2h-7z"/><circle cx="6" cy="18" r="1.7"/><circle cx="16.5" cy="18" r="1.7"/></svg>`;}
function iconWarehouse(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 10.5L12 4l9 6.5"/><path d="M5 9.5V20h14V9.5"/><path d="M9 20v-6h6v6"/></svg>`;}
function iconClipboard(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="5" y="4" width="14" height="17" rx="1.5"/><path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1"/><path d="M8.5 11h7M8.5 15h7M8.5 19h4"/></svg>`;}
function iconChart(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 19V9M11 19V4M18 19v-6"/><path d="M2.5 19.5h19"/></svg>`;}
function iconLayers(){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l9 4.5-9 4.5-9-4.5L12 3z"/><path d="M3 12l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5"/></svg>`;}

let currentView = "dashboard";
let currentOrderTab = "purchase";

/* ============================================================
   RENDER: SIDEBAR NAV
   ============================================================ */
function renderNav(){
  const groups = {};
  NAV.forEach(item=>{ (groups[item.group] = groups[item.group]||[]).push(item); });
  let html = "";
  Object.keys(groups).forEach(g=>{
    html += `<div class="grp-label">${g}</div>`;
    groups[g].forEach(item=>{
      let badge = "";
      if(item.id==="warehouses"){
        const n = lowStockRows().length;
        if(n>0) badge = `<span class="badge">${n}</span>`;
      }
      html += `<div class="nav-item ${item.id===currentView?'active':''}" data-nav="${item.id}">${item.icon}<span>${item.label}</span>${badge}</div>`;
    });
  });
  document.getElementById("sideNav").innerHTML = html;
  document.querySelectorAll("[data-nav]").forEach(el=>{
    el.addEventListener("click", ()=> goTo(el.getAttribute("data-nav")));
  });
}

function goTo(view){
  currentView = view;
  document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));
  document.getElementById("view-"+view).classList.add("active");
  const navItem = NAV.find(n=>n.id===view);
  document.getElementById("pageTitle").textContent = navItem ? navItem.label : view;
  document.getElementById("pageCrumb").textContent = CRUMB[view] || "";
  renderNav();
  document.getElementById("sidebar").classList.remove("open");
  renderCurrentView();
}

function renderCurrentView(){
  if(currentView==="dashboard") renderDashboard();
  if(currentView==="products") renderProducts();
  if(currentView==="suppliers") renderSuppliers();
  if(currentView==="warehouses") renderWarehouses();
  if(currentView==="orders") renderOrders();
  if(currentView==="reports") renderReports();
  if(currentView==="schema") renderSchema();
}

/* ============================================================
   DASHBOARD
   ============================================================ */
function renderDashboard(){
  const totalUnits = DB.stock.reduce((a,b)=>a+b.Quantity,0);
  const low = lowStockRows();
  const stats = [
    {k:"Products tracked", v:DB.products.length, t:DB.categories.length+" categories"},
    {k:"Suppliers", v:DB.suppliers.length, t:"active vendor accounts"},
    {k:"Warehouses", v:DB.warehouses.length, t:totalUnits.toLocaleString("en-IN")+" units on hand"},
    {k:"Below reorder level", v:low.length, t:"needs restocking", alert:low.length>0}
  ];
  document.getElementById("dashStats").innerHTML = stats.map(s=>`
    <div class="stat-card">
      <div class="k">${s.k}</div>
      <div class="v ${s.alert?'alert':''}">${s.v}</div>
      <div class="t">${s.t}</div>
    </div>`).join("");

  const moves = [...DB.movements].sort((a,b)=> b.MovementID - a.MovementID).slice(0,6);
  document.getElementById("dashMovements").innerHTML = tableOrEmpty(moves, "No stock movements recorded yet.", `
    <table><thead><tr><th>Date</th><th>Product</th><th>Warehouse</th><th>Type</th><th class="num">Qty</th><th>Note</th></tr></thead>
    <tbody>${moves.map(m=>`
      <tr>
        <td class="mono">${esc(m.Date)}</td>
        <td>${esc(productName(m.ProductID))}</td>
        <td>${esc(warehouseName(m.WarehouseID))}</td>
        <td><span class="tag ${m.Type==='IN'?'ok':'steel'}">${m.Type}</span></td>
        <td class="num">${m.Quantity}</td>
        <td style="color:var(--ink-soft)">${esc(m.Note)}</td>
      </tr>`).join("")}</tbody></table>`);

  document.getElementById("dashLowStock").innerHTML = tableOrEmpty(low, "Nothing below its reorder level right now — stock is healthy.", `
    <table><thead><tr><th>SKU</th><th>Product</th><th>Warehouse</th><th class="num">Qty</th><th class="num">Reorder at</th></tr></thead>
    <tbody>${low.slice(0,6).map(r=>`
      <tr>
        <td class="id">${esc(r.SKU)}</td>
        <td>${esc(r.ProductName)}</td>
        <td>${esc(r.WarehouseName)}</td>
        <td class="num"><span class="tag low">${r.Quantity}</span></td>
        <td class="num">${r.ReorderLevel}</td>
      </tr>`).join("")}</tbody></table>`);
}

function tableOrEmpty(rows, emptyMsg, html){
  if(!rows || rows.length===0) return `<div class="empty">${emptyMsg}</div>`;
  return html;
}

/* ============================================================
   PRODUCTS
   ============================================================ */
function renderProducts(){
  const rows = DB.products;
  const canEdit = SESSION.role === "Admin";
  document.getElementById("productsTable").innerHTML = tableOrEmpty(rows, "No products yet. Add your first product.", `
    <table><thead><tr>
      <th>SKU</th><th>Name</th><th>Category</th><th>Supplier</th><th class="num">Price</th><th class="num">Total stock</th><th></th>
    </tr></thead>
    <tbody>${rows.map(p=>{
      const stock = totalStockForProduct(p.ProductID);
      return `<tr>
        <td class="id">${esc(p.SKU)}</td>
        <td>${esc(p.Name)}</td>
        <td><span class="tag neutral">${esc(categoryName(p.CategoryID))}</span></td>
        <td>${esc(supplierName(p.SupplierID))}</td>
        <td class="num">${fmtMoney(p.Price)}</td>
        <td class="num">${stock}</td>
        <td class="actions-cell">
          <button class="btn small" data-edit-product="${p.ProductID}">Edit</button>
          ${canEdit? `<button class="btn small danger-outline" data-del-product="${p.ProductID}">Delete</button>` : ""}
        </td>
      </tr>`;
    }).join("")}</tbody></table>`);

  document.querySelectorAll("[data-edit-product]").forEach(b=>b.addEventListener("click", ()=>openProductForm(Number(b.dataset.editProduct))));
  document.querySelectorAll("[data-del-product]").forEach(b=>b.addEventListener("click", ()=>{
    const id = Number(b.dataset.delProduct);
    confirmAction(`Delete product "${esc(productName(id))}"? This also removes its stock records.`, async ()=>{
      try{
        await apiSend("/api/products/" + id, "DELETE");
        await fetchAll(); renderCurrentView(); toast("Product deleted.");
      }catch(e){ toast(e.message, true); }
    });
  }));
}

function openProductForm(editId){
  const editing = editId != null;
  const p = editing ? productRow(editId) : {SKU:"", Name:"", CategoryID:DB.categories[0].CategoryID, SupplierID:DB.suppliers[0].SupplierID, Price:""};
  const catOpts = DB.categories.map(c=>`<option value="${c.CategoryID}" ${c.CategoryID===p.CategoryID?"selected":""}>${esc(c.Name)}</option>`).join("");
  const supOpts = DB.suppliers.map(s=>`<option value="${s.SupplierID}" ${s.SupplierID===p.SupplierID?"selected":""}>${esc(s.Name)}</option>`).join("");
  openModal(editing?"Edit product":"Add product", `
    <form id="productForm">
      <div class="form-row"><label>Product name</label><input required id="f_name" value="${esc(p.Name)}" placeholder="e.g. Wireless Mouse"></div>
      <div class="form-grid">
        <div class="form-row"><label>SKU code</label><input required id="f_sku" value="${esc(p.SKU)}" placeholder="e.g. ELC-1004"></div>
        <div class="form-row"><label>Price (₹)</label><input required type="number" min="0" step="0.01" id="f_price" value="${p.Price}"></div>
      </div>
      <div class="form-grid">
        <div class="form-row"><label>Category</label><select id="f_cat">${catOpts}</select></div>
        <div class="form-row"><label>Supplier</label><select id="f_sup">${supOpts}</select></div>
      </div>
    </form>`,
    [
      {label:"Cancel", cls:"btn", action:closeModal},
      {label: editing?"Save changes":"Add product", cls:"btn primary", action: async ()=>{
        const name = document.getElementById("f_name").value.trim();
        const sku = document.getElementById("f_sku").value.trim();
        const price = parseFloat(document.getElementById("f_price").value);
        const cat = Number(document.getElementById("f_cat").value);
        const sup = Number(document.getElementById("f_sup").value);
        if(!name || !sku || isNaN(price)){ toast("Please fill every field.", true); return; }
        try{
          const payload = {Name:name, SKU:sku, Price:price, CategoryID:cat, SupplierID:sup};
          if(editing){
            await apiSend("/api/products/" + editId, "PUT", payload);
            toast("Product updated.");
          }else{
            await apiSend("/api/products", "POST", payload);
            toast("Product added.");
          }
          await fetchAll(); closeModal(); renderCurrentView();
        }catch(e){ toast(e.message, true); }
      }}
    ]
  );
}

/* ============================================================
   SUPPLIERS
   ============================================================ */
function renderSuppliers(){
  const rows = DB.suppliers;
  const canEdit = SESSION.role === "Admin";
  document.getElementById("suppliersTable").innerHTML = tableOrEmpty(rows, "No suppliers yet.", `
    <table><thead><tr><th>Name</th><th>Phone</th><th>Address</th><th class="num">Products supplied</th><th></th></tr></thead>
    <tbody>${rows.map(s=>{
      const count = DB.products.filter(p=>p.SupplierID===s.SupplierID).length;
      return `<tr>
        <td>${esc(s.Name)}</td>
        <td class="mono">${esc(s.Phone)}</td>
        <td style="color:var(--ink-soft)">${esc(s.Address)}</td>
        <td class="num">${count}</td>
        <td class="actions-cell">
          ${canEdit? `<button class="btn small" data-edit-sup="${s.SupplierID}">Edit</button>
          <button class="btn small danger-outline" data-del-sup="${s.SupplierID}" ${count>0?"disabled title='Has linked products'":""}>Delete</button>` : `<span style="color:var(--ink-soft); font-size:11.5px;">View only</span>`}
        </td>
      </tr>`;
    }).join("")}</tbody></table>`);

  document.querySelectorAll("[data-edit-sup]").forEach(b=>b.addEventListener("click", ()=>openSupplierForm(Number(b.dataset.editSup))));
  document.querySelectorAll("[data-del-sup]").forEach(b=>b.addEventListener("click", ()=>{
    const id = Number(b.dataset.delSup);
    confirmAction("Delete this supplier?", async ()=>{
      try{
        await apiSend("/api/suppliers/" + id, "DELETE");
        await fetchAll(); renderCurrentView(); toast("Supplier deleted.");
      }catch(e){ toast(e.message, true); }
    });
  }));
}

function openSupplierForm(editId){
  const editing = editId != null;
  const s = editing ? DB.suppliers.find(x=>x.SupplierID===editId) : {Name:"",Phone:"",Address:""};
  openModal(editing?"Edit supplier":"Add supplier", `
    <form id="supplierForm">
      <div class="form-row"><label>Supplier name</label><input required id="f_sname" value="${esc(s.Name)}" placeholder="e.g. Om Packaging Co."></div>
      <div class="form-row"><label>Phone</label><input required id="f_sphone" value="${esc(s.Phone)}" placeholder="+91 ..."></div>
      <div class="form-row"><label>Address</label><input required id="f_saddr" value="${esc(s.Address)}" placeholder="City, State"></div>
    </form>`,
    [
      {label:"Cancel", cls:"btn", action:closeModal},
      {label: editing?"Save changes":"Add supplier", cls:"btn primary", action: async ()=>{
        const name = document.getElementById("f_sname").value.trim();
        const phone = document.getElementById("f_sphone").value.trim();
        const addr = document.getElementById("f_saddr").value.trim();
        if(!name||!phone||!addr){ toast("Please fill every field.", true); return; }
        try{
          const payload = {Name:name, Phone:phone, Address:addr};
          if(editing){ await apiSend("/api/suppliers/" + editId, "PUT", payload); toast("Supplier updated."); }
          else{ await apiSend("/api/suppliers", "POST", payload); toast("Supplier added."); }
          await fetchAll(); closeModal(); renderCurrentView();
        }catch(e){ toast(e.message, true); }
      }}
    ]
  );
}

/* ============================================================
   WAREHOUSES & STOCK
   ============================================================ */
let stockFilterWH = "all";

function renderWarehouses(){
  const canEdit = SESSION.role === "Admin";
  document.getElementById("warehousesTable").innerHTML = tableOrEmpty(DB.warehouses, "No warehouses yet.", `
    <table><thead><tr><th>Location</th><th class="num">Capacity</th><th class="num">Units stored</th><th class="num">Utilisation</th><th></th></tr></thead>
    <tbody>${DB.warehouses.map(w=>{
      const used = DB.stock.filter(s=>s.WarehouseID===w.WarehouseID).reduce((a,b)=>a+b.Quantity,0);
      const pct = Math.min(100, Math.round((used/w.Capacity)*100));
      return `<tr>
        <td>${esc(w.Location)}</td>
        <td class="num">${w.Capacity.toLocaleString("en-IN")}</td>
        <td class="num">${used.toLocaleString("en-IN")}</td>
        <td class="num"><span class="tag ${pct>85?'low':'steel'}">${pct}%</span></td>
        <td class="actions-cell">${canEdit? `<button class="btn small danger-outline" data-del-wh="${w.WarehouseID}">Delete</button>`:""}</td>
      </tr>`;
    }).join("")}</tbody></table>`);

  document.querySelectorAll("[data-del-wh]").forEach(b=>b.addEventListener("click", ()=>{
    const id = Number(b.dataset.delWh);
    const hasStock = DB.stock.some(s=>s.WarehouseID===id);
    if(hasStock){ toast("Can't delete a warehouse that still holds stock.", true); return; }
    confirmAction("Delete this warehouse?", async ()=>{
      try{
        await apiSend("/api/warehouses/" + id, "DELETE");
        await fetchAll(); renderCurrentView(); toast("Warehouse deleted.");
      }catch(e){ toast(e.message, true); }
    });
  }));

  const sel = document.getElementById("stockWarehouseFilter");
  sel.innerHTML = `<option value="all">All warehouses</option>` + DB.warehouses.map(w=>`<option value="${w.WarehouseID}" ${stockFilterWH==String(w.WarehouseID)?"selected":""}>${esc(w.Location)}</option>`).join("");
  sel.value = stockFilterWH;
  sel.onchange = ()=>{ stockFilterWH = sel.value; renderStockTable(); };
  renderStockTable();
}

function renderStockTable(){
  let rows = DB.stock;
  if(stockFilterWH!=="all") rows = rows.filter(s=>String(s.WarehouseID)===stockFilterWH);
  document.getElementById("stockTable").innerHTML = tableOrEmpty(rows, "No stock records for this warehouse.", `
    <table><thead><tr><th>SKU</th><th>Product</th><th>Warehouse</th><th class="num">Qty</th><th class="num">Reorder at</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(s=>{
      const p = productRow(s.ProductID);
      const status = s.Quantity===0?["out","Out of stock"]:(s.Quantity<s.ReorderLevel?["low","Low stock"]:["ok","In stock"]);
      return `<tr>
        <td class="id">${esc(p?p.SKU:"—")}</td>
        <td>${esc(productName(s.ProductID))}</td>
        <td style="color:var(--ink-soft)">${esc(warehouseName(s.WarehouseID))}</td>
        <td class="num">${s.Quantity}</td>
        <td class="num">${s.ReorderLevel}</td>
        <td><span class="tag ${status[0]}">${status[1]}</span></td>
        <td class="actions-cell">
          <button class="btn small" data-stock-in="${s.StockID}">+ Stock in</button>
          <button class="btn small" data-stock-out="${s.StockID}">− Stock out</button>
        </td>
      </tr>`;
    }).join("")}</tbody></table>`);

  document.querySelectorAll("[data-stock-in]").forEach(b=>b.addEventListener("click", ()=>openStockMoveForm(Number(b.dataset.stockIn), "IN")));
  document.querySelectorAll("[data-stock-out]").forEach(b=>b.addEventListener("click", ()=>openStockMoveForm(Number(b.dataset.stockOut), "OUT")));
}

function openStockMoveForm(stockId, type){
  const s = DB.stock.find(x=>x.StockID===stockId);
  const p = productRow(s.ProductID);
  openModal(`${type==='IN'?'Stock in':'Stock out'} — ${esc(p.Name)}`, `
    <form id="moveForm">
      <div class="form-note">Currently <b>${s.Quantity}</b> units of <span class="mono">${esc(p.SKU)}</span> at ${esc(warehouseName(s.WarehouseID))}.</div>
      <div class="form-row" style="margin-top:12px;"><label>Quantity to ${type==='IN'?'add':'remove'}</label><input required type="number" min="1" id="f_qty" value="1"></div>
      <div class="form-row"><label>Note</label><input id="f_note" placeholder="${type==='IN'?'e.g. Received from supplier':'e.g. Dispatched to customer'}"></div>
    </form>`,
    [
      {label:"Cancel", cls:"btn", action:closeModal},
      {label: type==='IN'?"Record stock in":"Record stock out", cls:"btn primary", action: async ()=>{
        const qty = parseInt(document.getElementById("f_qty").value,10);
        const note = document.getElementById("f_note").value.trim() || (type==='IN'?"Manual stock-in":"Manual stock-out");
        if(!qty || qty<1){ toast("Enter a valid quantity.", true); return; }
        try{
          await apiSend("/api/stock/move", "POST", {StockID:stockId, Type:type, Quantity:qty, Note:note});
          await fetchAll(); closeModal(); renderCurrentView();
          toast(`${type==='IN'?'Stock in':'Stock out'} recorded.`);
        }catch(e){ toast(e.message, true); }
      }}
    ]
  );
}

function nowStr(){
  const d = new Date();
  const pad = n=>String(n).padStart(2,"0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ============================================================
   ORDERS
   ============================================================ */
function renderOrders(){
  const type = currentOrderTab === "purchase" ? "Purchase" : "Sale";
  document.getElementById("ordersDesc").textContent = type==="Purchase"
    ? "Orders placed with a supplier to bring new stock into a warehouse."
    : "Orders placed by a customer that dispatch stock out of a warehouse.";
  document.getElementById("addOrderBtn").textContent = "+ New " + type.toLowerCase() + " order";

  const rows = DB.orders.filter(o=>o.Type===type).sort((a,b)=>b.OrderID-a.OrderID);
  document.getElementById("ordersTable").innerHTML = tableOrEmpty(rows, `No ${type.toLowerCase()} orders yet.`, `
    <table><thead><tr><th>Order</th><th>Date</th><th>${type==="Purchase"?"Supplier":"Customer"}</th><th>Items</th><th class="num">Order value</th><th>Status</th></tr></thead>
    <tbody>${rows.map(o=>{
      const items = DB.orderItems.filter(i=>i.OrderID===o.OrderID);
      const value = items.reduce((a,b)=>a+b.Quantity*b.UnitPrice,0);
      const party = o.PartyKind==="Supplier" ? supplierName(o.PartyID) : customerName(o.PartyID);
      return `<tr>
        <td class="id">#${o.OrderID}</td>
        <td class="mono">${esc(o.Date)}</td>
        <td>${esc(party)}</td>
        <td style="color:var(--ink-soft)">${items.map(i=>esc(productName(i.ProductID))+" ×"+i.Quantity).join(", ")}</td>
        <td class="num">${fmtMoney(value)}</td>
        <td><span class="tag ${o.Status==='Fulfilled'||o.Status==='Received'?'ok':'steel'}">${esc(o.Status)}</span></td>
      </tr>`;
    }).join("")}</tbody></table>`);
}

function openOrderForm(){
  const type = currentOrderTab === "purchase" ? "Purchase" : "Sale";
  const partyOpts = type==="Purchase"
    ? DB.suppliers.map(s=>`<option value="${s.SupplierID}">${esc(s.Name)}</option>`).join("")
    : DB.customers.map(c=>`<option value="${c.CustomerID}">${esc(c.Name)}</option>`).join("");
  const prodOpts = DB.products.map(p=>`<option value="${p.ProductID}">${esc(p.Name)} (${esc(p.SKU)})</option>`).join("");
  const whOpts = DB.warehouses.map(w=>`<option value="${w.WarehouseID}">${esc(w.Location)}</option>`).join("");

  openModal(`New ${type.toLowerCase()} order`, `
    <form id="orderForm">
      <div class="form-row"><label>${type==="Purchase"?"Supplier":"Customer"}</label><select id="f_party">${partyOpts}</select></div>
      <div class="form-grid">
        <div class="form-row"><label>Product</label><select id="f_oprod">${prodOpts}</select></div>
        <div class="form-row"><label>Warehouse</label><select id="f_owh">${whOpts}</select></div>
      </div>
      <div class="form-grid">
        <div class="form-row"><label>Quantity</label><input required type="number" min="1" id="f_oqty" value="1"></div>
        <div class="form-row"><label>Unit price (₹)</label><input required type="number" min="0" step="0.01" id="f_oprice" value=""></div>
      </div>
      <div class="form-note" id="orderNote">${type==="Sale" ? "Stock will be checked and reduced automatically on submit." : "Stock will be increased automatically on submit."}</div>
    </form>`,
    [
      {label:"Cancel", cls:"btn", action:closeModal},
      {label:"Create order", cls:"btn primary", action: async ()=>{
        const partyId = Number(document.getElementById("f_party").value);
        const prodId = Number(document.getElementById("f_oprod").value);
        const whId = Number(document.getElementById("f_owh").value);
        const qty = parseInt(document.getElementById("f_oqty").value,10);
        const price = parseFloat(document.getElementById("f_oprice").value);
        if(!qty||qty<1||isNaN(price)){ toast("Fill in a valid quantity and price.", true); return; }
        try{
          const res = await apiSend("/api/orders", "POST", {
            Type: type, PartyID: partyId, PartyKind: type==="Purchase"?"Supplier":"Customer",
            ProductID: prodId, WarehouseID: whId, Quantity: qty, UnitPrice: price
          });
          await fetchAll(); closeModal(); renderCurrentView();
          toast(`${type} order #${res.OrderID} created.`);
        }catch(e){ toast(e.message, true); }
      }}
    ]
  );
}

/* ============================================================
   REPORTS
   ============================================================ */
function renderReports(){
  document.getElementById("sqlLowStock").innerHTML =
`<span class="kw">SELECT</span> p.Name, s.Quantity, s.ReorderLevel, w.Location
<span class="kw">FROM</span> PRODUCT p
<span class="kw">JOIN</span> STOCK s <span class="kw">ON</span> p.ProductID = s.ProductID
<span class="kw">JOIN</span> WAREHOUSE w <span class="kw">ON</span> s.WarehouseID = w.WarehouseID
<span class="kw">WHERE</span> s.Quantity < s.ReorderLevel
<span class="kw">ORDER BY</span> s.Quantity <span class="kw">ASC</span>;`;

  // These three panels fetch straight from dedicated Flask endpoints that
  // run a real SQL query against iwms.db on every call — not cached data.
  apiGet("/api/reports/low-stock").then(low=>{
    document.getElementById("reportLowStock").innerHTML = tableOrEmpty(low, "No products are currently below their reorder level.", `
      <table><thead><tr><th>SKU</th><th>Product</th><th>Warehouse</th><th class="num">Qty</th><th class="num">Reorder at</th></tr></thead>
      <tbody>${low.map(r=>`<tr><td class="id">${esc(r.SKU)}</td><td>${esc(r.ProductName)}</td><td>${esc(r.WarehouseName)}</td><td class="num"><span class="tag low">${r.Quantity}</span></td><td class="num">${r.ReorderLevel}</td></tr>`).join("")}</tbody></table>`);
  }).catch(()=>{ document.getElementById("reportLowStock").innerHTML = `<div class="empty">Could not reach the server for this report.</div>`; });

  document.getElementById("sqlWarehouseSummary").innerHTML =
`<span class="kw">SELECT</span> w.Location, SUM(s.Quantity) <span class="kw">AS</span> total_units,
       SUM(s.Quantity * p.Price) <span class="kw">AS</span> total_value
<span class="kw">FROM</span> STOCK s
<span class="kw">JOIN</span> WAREHOUSE w <span class="kw">ON</span> s.WarehouseID = w.WarehouseID
<span class="kw">JOIN</span> PRODUCT p <span class="kw">ON</span> s.ProductID = p.ProductID
<span class="kw">GROUP BY</span> w.Location;`;

  apiGet("/api/reports/warehouse-summary").then(whSummary=>{
    document.getElementById("reportWarehouse").innerHTML = tableOrEmpty(whSummary, "No stock recorded yet.", `
      <table><thead><tr><th>Warehouse</th><th class="num">Total units</th><th class="num">Total value</th></tr></thead>
      <tbody>${whSummary.map(w=>`<tr><td>${esc(w.Location)}</td><td class="num">${Number(w.units).toLocaleString("en-IN")}</td><td class="num">${fmtMoney(w.value)}</td></tr>`).join("")}</tbody></table>`);
  }).catch(()=>{ document.getElementById("reportWarehouse").innerHTML = `<div class="empty">Could not reach the server for this report.</div>`; });

  document.getElementById("sqlOrderHistory").innerHTML =
`<span class="kw">SELECT</span> o.OrderID, o.Type, o.Date, oi.ProductID, oi.Quantity, oi.UnitPrice
<span class="kw">FROM</span> ORDERS o
<span class="kw">JOIN</span> ORDER_ITEMS oi <span class="kw">ON</span> o.OrderID = oi.OrderID
<span class="kw">ORDER BY</span> o.OrderID <span class="kw">DESC</span>;`;

  apiGet("/api/reports/order-history").then(allOrders=>{
    document.getElementById("reportOrders").innerHTML = tableOrEmpty(allOrders, "No orders recorded yet.", `
      <table><thead><tr><th>Order</th><th>Type</th><th>Date</th><th>Party</th><th class="num">Value</th><th>Status</th></tr></thead>
      <tbody>${allOrders.map(o=>{
        const items = o.items || [];
        const value = items.reduce((a,b)=>a+b.Quantity*b.UnitPrice,0);
        const party = o.PartyKind==="Supplier" ? supplierName(o.PartyID) : customerName(o.PartyID);
        return `<tr><td class="id">#${o.OrderID}</td><td><span class="tag ${o.Type==='Purchase'?'ok':'steel'}">${o.Type}</span></td><td class="mono">${esc(o.Date)}</td><td>${esc(party)}</td><td class="num">${fmtMoney(value)}</td><td>${esc(o.Status)}</td></tr>`;
      }).join("")}</tbody></table>`);
  }).catch(()=>{ document.getElementById("reportOrders").innerHTML = `<div class="empty">Could not reach the server for this report.</div>`; });
}

/* ============================================================
   SCHEMA VIEW
   ============================================================ */
function renderSchema(){
  const tables = [
    {name:"CATEGORY", rows:[["CategoryID","PK"],["Name",""]]},
    {name:"SUPPLIER", rows:[["SupplierID","PK"],["Name",""],["Phone",""],["Address",""]]},
    {name:"PRODUCT", rows:[["ProductID","PK"],["SKU",""],["Name",""],["CategoryID","FK"],["SupplierID","FK"],["Price",""]]},
    {name:"WAREHOUSE", rows:[["WarehouseID","PK"],["Location",""],["Capacity",""]]},
    {name:"STOCK", rows:[["StockID","PK"],["ProductID","FK"],["WarehouseID","FK"],["Quantity",""],["ReorderLevel",""]]},
    {name:"CUSTOMER", rows:[["CustomerID","PK"],["Name",""],["Phone",""]]},
    {name:"ORDERS", rows:[["OrderID","PK"],["Type",""],["PartyID","FK"],["Date",""],["Status",""]]},
    {name:"ORDER_ITEMS", rows:[["OrderItemID","PK"],["OrderID","FK"],["ProductID","FK"],["Quantity",""],["UnitPrice",""]]}
  ];
  document.getElementById("schemaGrid").innerHTML = tables.map(t=>`
    <div class="schema-tbl">
      <div class="t-head">${t.name}</div>
      ${t.rows.map(r=>`<div class="t-row ${r[1]==='PK'?'pk':''}">${r[0]}${r[1]?`<span class="k">${r[1]}</span>`:""}</div>`).join("")}
    </div>`).join("");
}

/* ============================================================
   MODAL / TOAST HELPERS
   ============================================================ */
function openModal(title, bodyHtml, buttons){
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalBody").innerHTML = bodyHtml;
  document.getElementById("modalFoot").innerHTML = "";
  buttons.forEach(b=>{
    const el = document.createElement("button");
    el.className = b.cls; el.textContent = b.label;
    el.addEventListener("click", b.action);
    document.getElementById("modalFoot").appendChild(el);
  });
  document.getElementById("modalBack").classList.add("active");
}
function closeModal(){ document.getElementById("modalBack").classList.remove("active"); }
function confirmAction(msg, onYes){
  openModal("Please confirm", `<p style="margin:0;">${msg}</p>`, [
    {label:"Cancel", cls:"btn", action:closeModal},
    {label:"Yes, continue", cls:"btn danger-outline", action:()=>{ closeModal(); onYes(); }}
  ]);
}
function toast(msg, isErr){
  const t = document.createElement("div");
  t.className = "toast" + (isErr? " err":"");
  t.textContent = msg;
  document.getElementById("toastWrap").appendChild(t);
  setTimeout(()=>{ t.remove(); }, 3200);
}

/* ============================================================
   BOOTSTRAP
   ============================================================ */
function initAppShell(){
  renderNav();
  goTo("dashboard");

  document.getElementById("addProductBtn").addEventListener("click", ()=>openProductForm(null));
  document.getElementById("addSupplierBtn").addEventListener("click", ()=>{
    if(SESSION.role!=="Admin"){ toast("Only an Admin can add suppliers.", true); return; }
    openSupplierForm(null);
  });
  document.getElementById("addWarehouseBtn").addEventListener("click", ()=>{
    if(SESSION.role!=="Admin"){ toast("Only an Admin can add warehouses.", true); return; }
    openModal("Add warehouse", `
      <form id="whForm">
        <div class="form-row"><label>Location</label><input required id="f_whloc" placeholder="e.g. Warehouse C — Genome Valley"></div>
        <div class="form-row"><label>Capacity (units)</label><input required type="number" min="1" id="f_whcap" value="1000"></div>
      </form>`, [
        {label:"Cancel", cls:"btn", action:closeModal},
        {label:"Add warehouse", cls:"btn primary", action: async ()=>{
          const loc = document.getElementById("f_whloc").value.trim();
          const cap = parseInt(document.getElementById("f_whcap").value,10);
          if(!loc||!cap){ toast("Fill in every field.", true); return; }
          try{
            await apiSend("/api/warehouses", "POST", {Location:loc, Capacity:cap});
            await fetchAll(); closeModal(); renderCurrentView(); toast("Warehouse added.");
          }catch(e){ toast(e.message, true); }
        }}
      ]);
  });
  document.getElementById("addOrderBtn").addEventListener("click", openOrderForm);

  document.querySelectorAll(".tab-btn").forEach(b=>b.addEventListener("click", ()=>{
    document.querySelectorAll(".tab-btn").forEach(x=>x.classList.remove("active"));
    b.classList.add("active");
    currentOrderTab = b.dataset.tab;
    renderOrders();
  }));

  document.getElementById("modalClose").addEventListener("click", closeModal);
  document.getElementById("modalBack").addEventListener("click", (e)=>{ if(e.target.id==="modalBack") closeModal(); });

  document.getElementById("menuToggle").addEventListener("click", ()=> document.getElementById("sidebar").classList.toggle("open"));
  document.getElementById("logoutBtn").addEventListener("click", ()=>{
    SESSION = null;
    document.getElementById("app").classList.remove("active");
    document.getElementById("loginScreen").style.display = "flex";
  });

  document.getElementById("exportBtn").addEventListener("click", ()=>{
    const blob = new Blob([JSON.stringify(DB,null,2)], {type:"application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "iwms_data_export.json"; a.click();
  });
  document.getElementById("resetBtn").addEventListener("click", ()=>{
    confirmAction("Reset all data back to the original seed dataset? Your changes will be lost.", async ()=>{
      try{
        await resetDB(); renderCurrentView(); toast("Data reset to seed dataset.");
      }catch(e){ toast(e.message, true); }
    });
  });

  setInterval(updateClock, 1000); updateClock();
}

function updateClock(){
  const d = new Date();
  document.getElementById("clock").textContent = d.toLocaleString("en-IN", {weekday:"short", day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit"});
}

/* login */
document.getElementById("loginForm").addEventListener("submit", async function(e){
  e.preventDefault();
  const pass = document.getElementById("loginPass").value;
  if(pass !== ACCESS_CODE){
    document.getElementById("loginError").style.display = "block";
    return;
  }
  document.getElementById("loginError").style.display = "none";

  const submitBtn = e.target.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = "Connecting to server…";

  try{
    await fetchAll(); // real fetch to Flask -> SQLite
  }catch(err){
    submitBtn.disabled = false;
    submitBtn.textContent = "Enter warehouse system";
    document.getElementById("loginError").style.display = "block";
    document.getElementById("loginError").textContent =
      "Couldn't reach the backend server. Make sure you ran \"python app.py\" in the project folder, then try again.";
    return;
  }

  const name = document.getElementById("loginName").value.trim() || "Guest";
  const role = document.querySelector('input[name="role"]:checked').value;
  SESSION = {name, role};
  document.getElementById("whoName").textContent = name;
  document.getElementById("whoRole").textContent = role + " access";
  document.getElementById("loginScreen").style.display = "none";
  document.getElementById("app").classList.add("active");
  initAppShell();
});

})();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(force=False):
    if force and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()


def rows(cursor):
    return [dict(r) for r in cursor.fetchall()]


def now_dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def now_d():
    return datetime.now().strftime("%Y-%m-%d")


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


# ---------------------------------------------------------------------------
# Routing -- tiny hand-rolled router (method, regex pattern, handler)
# ---------------------------------------------------------------------------
ROUTES = []


def route(method, pattern):
    regex = re.compile("^" + pattern + "$")

    def deco(fn):
        ROUTES.append((method, regex, fn))
        return fn

    return deco


# ----- bulk read ------------------------------------------------------------
@route("GET", r"/api/data")
def h_data(m, body):
    conn = get_conn()
    data = {
        "categories": rows(conn.execute("SELECT * FROM CATEGORY")),
        "suppliers": rows(conn.execute("SELECT * FROM SUPPLIER")),
        "products": rows(conn.execute("SELECT * FROM PRODUCT")),
        "warehouses": rows(conn.execute("SELECT * FROM WAREHOUSE")),
        "stock": rows(conn.execute("SELECT * FROM STOCK")),
        "customers": rows(conn.execute("SELECT * FROM CUSTOMER")),
        "orders": rows(conn.execute("SELECT * FROM ORDERS")),
        "orderItems": rows(conn.execute("SELECT * FROM ORDER_ITEMS")),
        "movements": rows(conn.execute(
            "SELECT * FROM STOCK_MOVEMENT ORDER BY MovementID DESC LIMIT 100")),
    }
    conn.close()
    return 200, data


# ----- products --------------------------------------------------------------
@route("POST", r"/api/products")
def h_add_product(m, body):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO PRODUCT (SKU, Name, CategoryID, SupplierID, Price) VALUES (?,?,?,?,?)",
        (body["SKU"], body["Name"], body["CategoryID"], body["SupplierID"], body["Price"]),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return 200, {"ProductID": pid}


@route("PUT", r"/api/products/(?P<id>\d+)")
def h_edit_product(m, body):
    pid = int(m.group("id"))
    conn = get_conn()
    conn.execute(
        "UPDATE PRODUCT SET SKU=?, Name=?, CategoryID=?, SupplierID=?, Price=? WHERE ProductID=?",
        (body["SKU"], body["Name"], body["CategoryID"], body["SupplierID"], body["Price"], pid),
    )
    conn.commit()
    conn.close()
    return 200, {"ok": True}


@route("DELETE", r"/api/products/(?P<id>\d+)")
def h_del_product(m, body):
    pid = int(m.group("id"))
    conn = get_conn()
    conn.execute("DELETE FROM STOCK WHERE ProductID=?", (pid,))
    conn.execute("DELETE FROM PRODUCT WHERE ProductID=?", (pid,))
    conn.commit()
    conn.close()
    return 200, {"ok": True}


# ----- suppliers --------------------------------------------------------------
@route("POST", r"/api/suppliers")
def h_add_supplier(m, body):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO SUPPLIER (Name, Phone, Address) VALUES (?,?,?)",
        (body["Name"], body["Phone"], body["Address"]),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return 200, {"SupplierID": sid}


@route("PUT", r"/api/suppliers/(?P<id>\d+)")
def h_edit_supplier(m, body):
    sid = int(m.group("id"))
    conn = get_conn()
    conn.execute(
        "UPDATE SUPPLIER SET Name=?, Phone=?, Address=? WHERE SupplierID=?",
        (body["Name"], body["Phone"], body["Address"], sid),
    )
    conn.commit()
    conn.close()
    return 200, {"ok": True}


@route("DELETE", r"/api/suppliers/(?P<id>\d+)")
def h_del_supplier(m, body):
    sid = int(m.group("id"))
    conn = get_conn()
    linked = conn.execute("SELECT COUNT(*) AS n FROM PRODUCT WHERE SupplierID=?", (sid,)).fetchone()["n"]
    if linked > 0:
        conn.close()
        raise ApiError("Supplier still has linked products.")
    conn.execute("DELETE FROM SUPPLIER WHERE SupplierID=?", (sid,))
    conn.commit()
    conn.close()
    return 200, {"ok": True}


# ----- warehouses --------------------------------------------------------------
@route("POST", r"/api/warehouses")
def h_add_warehouse(m, body):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO WAREHOUSE (Location, Capacity) VALUES (?,?)",
        (body["Location"], body["Capacity"]),
    )
    conn.commit()
    wid = cur.lastrowid
    conn.close()
    return 200, {"WarehouseID": wid}


@route("DELETE", r"/api/warehouses/(?P<id>\d+)")
def h_del_warehouse(m, body):
    wid = int(m.group("id"))
    conn = get_conn()
    linked = conn.execute("SELECT COUNT(*) AS n FROM STOCK WHERE WarehouseID=?", (wid,)).fetchone()["n"]
    if linked > 0:
        conn.close()
        raise ApiError("Warehouse still holds stock.")
    conn.execute("DELETE FROM WAREHOUSE WHERE WarehouseID=?", (wid,))
    conn.commit()
    conn.close()
    return 200, {"ok": True}


# ----- stock movements --------------------------------------------------------
@route("POST", r"/api/stock/move")
def h_stock_move(m, body):
    conn = get_conn()
    stock = conn.execute("SELECT * FROM STOCK WHERE StockID=?", (body["StockID"],)).fetchone()
    if stock is None:
        conn.close()
        raise ApiError("Stock row not found.", 404)

    qty = int(body["Quantity"])
    move_type = body["Type"]

    if move_type == "OUT" and stock["Quantity"] < qty:
        conn.close()
        raise ApiError("Not enough stock to remove that much.")

    new_qty = stock["Quantity"] + qty if move_type == "IN" else stock["Quantity"] - qty
    conn.execute("UPDATE STOCK SET Quantity=? WHERE StockID=?", (new_qty, body["StockID"]))
    conn.execute(
        "INSERT INTO STOCK_MOVEMENT (Date, ProductID, WarehouseID, Type, Quantity, Note) VALUES (?,?,?,?,?,?)",
        (now_dt(), stock["ProductID"], stock["WarehouseID"], move_type, qty, body.get("Note", "")),
    )
    conn.commit()
    conn.close()
    return 200, {"ok": True, "NewQuantity": new_qty}


# ----- orders -------------------------------------------------------------------
@route("POST", r"/api/orders")
def h_create_order(m, body):
    conn = get_conn()
    order_type = body["Type"]
    party_id = body["PartyID"]
    party_kind = body["PartyKind"]
    product_id = body["ProductID"]
    warehouse_id = body["WarehouseID"]
    qty = int(body["Quantity"])
    unit_price = float(body["UnitPrice"])

    stock = conn.execute(
        "SELECT * FROM STOCK WHERE ProductID=? AND WarehouseID=?", (product_id, warehouse_id)
    ).fetchone()

    if order_type == "Sale":
        if stock is None or stock["Quantity"] < qty:
            conn.close()
            raise ApiError("Not enough stock in that warehouse for this sale.")
        conn.execute("UPDATE STOCK SET Quantity = Quantity - ? WHERE StockID=?", (qty, stock["StockID"]))
    else:
        if stock is None:
            conn.execute(
                "INSERT INTO STOCK (ProductID, WarehouseID, Quantity, ReorderLevel) VALUES (?,?,?,10)",
                (product_id, warehouse_id, qty),
            )
        else:
            conn.execute("UPDATE STOCK SET Quantity = Quantity + ? WHERE StockID=?", (qty, stock["StockID"]))

    status = "Received" if order_type == "Purchase" else "Fulfilled"
    cur = conn.execute(
        "INSERT INTO ORDERS (Type, PartyID, PartyKind, Date, Status) VALUES (?,?,?,?,?)",
        (order_type, party_id, party_kind, now_d(), status),
    )
    order_id = cur.lastrowid
    conn.execute(
        "INSERT INTO ORDER_ITEMS (OrderID, ProductID, WarehouseID, Quantity, UnitPrice) VALUES (?,?,?,?,?)",
        (order_id, product_id, warehouse_id, qty, unit_price),
    )
    conn.execute(
        "INSERT INTO STOCK_MOVEMENT (Date, ProductID, WarehouseID, Type, Quantity, Note) VALUES (?,?,?,?,?,?)",
        (now_dt(), product_id, warehouse_id, "IN" if order_type == "Purchase" else "OUT", qty,
         "{} order #{}".format(order_type, order_id)),
    )
    conn.commit()
    conn.close()
    return 200, {"OrderID": order_id}


# ----- reports (live SQL JOIN / GROUP BY queries) -------------------------------
@route("GET", r"/api/reports/low-stock")
def h_report_low_stock(m, body):
    conn = get_conn()
    result = rows(conn.execute("""
        SELECT p.SKU AS SKU, p.Name AS ProductName, s.Quantity AS Quantity,
               s.ReorderLevel AS ReorderLevel, w.Location AS WarehouseName
        FROM PRODUCT p
        JOIN STOCK s ON p.ProductID = s.ProductID
        JOIN WAREHOUSE w ON s.WarehouseID = w.WarehouseID
        WHERE s.Quantity < s.ReorderLevel
        ORDER BY s.Quantity ASC
    """))
    conn.close()
    return 200, result


@route("GET", r"/api/reports/warehouse-summary")
def h_report_warehouse_summary(m, body):
    conn = get_conn()
    result = rows(conn.execute("""
        SELECT w.Location AS Location,
               COALESCE(SUM(s.Quantity), 0) AS units,
               COALESCE(SUM(s.Quantity * p.Price), 0) AS value
        FROM WAREHOUSE w
        LEFT JOIN STOCK s ON s.WarehouseID = w.WarehouseID
        LEFT JOIN PRODUCT p ON p.ProductID = s.ProductID
        GROUP BY w.WarehouseID, w.Location
    """))
    conn.close()
    return 200, result


@route("GET", r"/api/reports/order-history")
def h_report_order_history(m, body):
    conn = get_conn()
    orders = rows(conn.execute("SELECT * FROM ORDERS ORDER BY OrderID DESC"))
    for o in orders:
        o["items"] = rows(conn.execute("SELECT * FROM ORDER_ITEMS WHERE OrderID=?", (o["OrderID"],)))
    conn.close()
    return 200, orders


# ----- reset ----------------------------------------------------------------------
@route("POST", r"/api/reset")
def h_reset(m, body):
    init_db(force=True)
    return 200, {"ok": True}


# ---------------------------------------------------------------------------
# HTTP server (standard library only -- no Flask, no pip install needed)
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_text):
        payload = html_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _dispatch(self, method):
        path = self.path.split("?", 1)[0]
        if method == "GET" and path == "/":
            self._send_html(INDEX_HTML)
            return

        body = self._read_json_body() if method in ("POST", "PUT", "DELETE") else {}

        for route_method, regex, fn in ROUTES:
            if route_method != method:
                continue
            match = regex.match(path)
            if match:
                try:
                    status, result = fn(match, body)
                except ApiError as e:
                    status, result = e.status, {"error": e.message}
                except KeyError as e:
                    status, result = 400, {"error": "Missing field: {}".format(e)}
                except (ValueError, TypeError) as e:
                    status, result = 400, {"error": str(e)}
                self._send_json(status, result)
                return

        self._send_json(404, {"error": "Not found"})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def log_message(self, fmt, *args):
        pass  # keep the terminal window quiet


def main():
    init_db()
    url = "http://127.0.0.1:{}".format(PORT)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("=" * 60)
    print(" IWMS is running at:", url)
    print(" Access code: iwms2026")
    print(" Press Ctrl+C in this window to stop the server.")
    print("=" * 60)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping IWMS server...")


if __name__ == "__main__":
    main()
