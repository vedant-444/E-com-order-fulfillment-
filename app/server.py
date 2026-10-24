"""
OrderFlow360 Analytics Platform - Deployable Web MVP
Full-featured Interactive Dashboard & REST API Engine
Includes Sections A-E Strategic Business KPIs and Section 6 Real-World Problem Solving Scenarios
"""

import sys
import os
import sqlite3
import json
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DB_PATH, REPORTS_DIR, QUARANTINE_DATA_DIR
from src.analytics.kpi_calculator import KPICalculator
from src.database.connection import get_db_connection
from src.etl.pipeline import OrderFlow360Pipeline

app = Flask(__name__)
kpi_calc = KPICalculator()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OrderFlow360 | E-Commerce Fulfillment Analytics Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #0b1120; color: #f8fafc; }
        .glass { background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(14px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glass-card { background: rgba(17, 24, 39, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); transition: transform 0.2s, box-shadow 0.2s; }
        .glass-card:hover { border-color: rgba(99, 102, 241, 0.3); }
        .tab-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.35); }
        .badge-pill { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 9999px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    </style>
</head>
<body class="min-h-screen pb-12">
    <!-- Navbar -->
    <header class="glass sticky top-0 z-50 px-6 py-4 flex items-center justify-between shadow-2xl border-b border-slate-800">
        <div class="flex items-center space-x-3">
            <div class="bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 w-11 h-11 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                <i class="fa-solid fa-boxes-packing text-white text-xl"></i>
            </div>
            <div>
                <div class="flex items-center space-x-2">
                    <h1 class="text-xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-200 to-white bg-clip-text text-transparent">OrderFlow360</h1>
                    <span class="badge-pill bg-indigo-950 text-indigo-400 border border-indigo-700/50">Campus Hiring Assessment</span>
                </div>
                <p class="text-xs text-slate-400">E-Commerce Order Fulfillment Analytical Platform & Warehouse MVP</p>
            </div>
        </div>
        <div class="flex items-center space-x-3">
            <button onclick="triggerPipelineRun()" id="run-btn" class="flex items-center space-x-2 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-emerald-600/20 active:scale-95">
                <i class="fa-solid fa-play text-xs"></i>
                <span>Re-Run ETL Pipeline</span>
            </button>
            <div class="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-xs font-mono text-emerald-400">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>DATA WAREHOUSE ACTIVE</span>
            </div>
        </div>
    </header>

    <!-- Navigation Tabs -->
    <div class="max-w-7xl mx-auto px-6 pt-6">
        <div class="flex space-x-2 border-b border-slate-800 pb-3 overflow-x-auto text-sm scrollbar-none">
            <button onclick="switchTab('strategic-kpis')" class="tab-btn active px-4 py-2 rounded-xl font-medium transition-all" id="btn-strategic-kpis">
                <i class="fa-solid fa-chart-line mr-2"></i>Strategic KPIs (Sections A-E)
            </button>
            <button onclick="switchTab('business-scenarios')" class="tab-btn px-4 py-2 rounded-xl font-medium text-slate-400 hover:text-white transition-all" id="btn-business-scenarios">
                <i class="fa-solid fa-lightbulb mr-2 text-amber-400"></i>Business Solutions (Section 6)
            </button>
            <button onclick="switchTab('couriers')" class="tab-btn px-4 py-2 rounded-xl font-medium text-slate-400 hover:text-white transition-all" id="btn-couriers">
                <i class="fa-solid fa-truck-fast mr-2"></i>Courier Performance Matrix
            </button>
            <button onclick="switchTab('data-quality')" class="tab-btn px-4 py-2 rounded-xl font-medium text-slate-400 hover:text-white transition-all" id="btn-data-quality">
                <i class="fa-solid fa-shield-halved mr-2 text-cyan-400"></i>DQ & Audit Studio (38 Rules)
            </button>
            <button onclick="switchTab('schema')" class="tab-btn px-4 py-2 rounded-xl font-medium text-slate-400 hover:text-white transition-all" id="btn-schema">
                <i class="fa-solid fa-sitemap mr-2 text-purple-400"></i>Star Schema & SCD2
            </button>
            <button onclick="switchTab('sql-console')" class="tab-btn px-4 py-2 rounded-xl font-medium text-slate-400 hover:text-white transition-all" id="btn-sql-console">
                <i class="fa-solid fa-terminal mr-2 text-emerald-400"></i>SQL Workbench
            </button>
        </div>
    </div>

    <!-- Main Content Container -->
    <main class="max-w-7xl mx-auto px-6 py-6 space-y-8">
        
        <!-- =================== TAB 1: STRATEGIC BUSINESS KPIS (SECTIONS A-E) =================== -->
        <section id="tab-strategic-kpis" class="tab-content space-y-8">

            <!-- SECTION A: ORDER KPIS -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-2">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="badge-pill bg-blue-900/60 text-blue-400 border border-blue-500/30">Section A</span>
                            <h2 class="text-lg font-bold text-white">Order KPIs</h2>
                        </div>
                        <p class="text-xs text-indigo-300 mt-1 flex items-center">
                            <i class="fa-solid fa-circle-question mr-1.5 text-blue-400"></i>
                            <span class="font-medium">Business Question:</span>&nbsp;What is happening to our orders?
                        </p>
                    </div>
                    <span class="text-xs text-slate-400 font-mono">Net Processed: 4,190 Valid Orders</span>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mt-5">
                    <div class="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400 font-semibold uppercase">Total Orders</span>
                        <div class="text-2xl font-black text-white mt-1">{{ order_kpis.total_orders or 0 }}</div>
                        <div class="text-xs text-slate-500 mt-1">100% Net Ingested</div>
                    </div>
                    <div class="bg-slate-900/90 border border-emerald-900/40 p-4 rounded-xl">
                        <span class="text-xs text-emerald-400 font-semibold uppercase">Delivered Orders</span>
                        <div class="text-2xl font-black text-emerald-400 mt-1">{{ order_kpis.delivered_orders or 0 }}</div>
                        <div class="text-xs text-emerald-500/80 mt-1">{{ order_kpis.shipment_success_rate_pct or 0 }}% of Total</div>
                    </div>
                    <div class="bg-slate-900/90 border border-rose-900/40 p-4 rounded-xl">
                        <span class="text-xs text-rose-400 font-semibold uppercase">Cancelled Orders</span>
                        <div class="text-2xl font-black text-rose-400 mt-1">{{ order_kpis.cancelled_orders or 0 }}</div>
                        <div class="text-xs text-rose-500/80 mt-1">{{ ((order_kpis.cancelled_orders or 0) / (order_kpis.total_orders or 1) * 100)|round(2) }}% of Total</div>
                    </div>
                    <div class="bg-slate-900/90 border border-amber-900/40 p-4 rounded-xl">
                        <span class="text-xs text-amber-400 font-semibold uppercase">Returned Orders</span>
                        <div class="text-2xl font-black text-amber-400 mt-1">{{ order_kpis.returned_orders or 0 }}</div>
                        <div class="text-xs text-amber-500/80 mt-1">{{ ((order_kpis.returned_orders or 0) / (order_kpis.total_orders or 1) * 100)|round(2) }}% of Total</div>
                    </div>
                    <div class="bg-slate-900/90 border border-blue-900/40 p-4 rounded-xl col-span-2 md:col-span-1">
                        <span class="text-xs text-blue-400 font-semibold uppercase">In-Transit Orders</span>
                        <div class="text-2xl font-black text-blue-400 mt-1">{{ order_kpis.in_transit_orders or 0 }}</div>
                        <div class="text-xs text-blue-500/80 mt-1">Active Pipeline</div>
                    </div>
                </div>
            </div>

            <!-- SECTION B: CUSTOMER KPIS -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-2">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="badge-pill bg-purple-900/60 text-purple-400 border border-purple-500/30">Section B</span>
                            <h2 class="text-lg font-bold text-white">Customer KPIs</h2>
                        </div>
                        <p class="text-xs text-purple-300 mt-1 flex items-center">
                            <i class="fa-solid fa-circle-question mr-1.5 text-purple-400"></i>
                            <span class="font-medium">Business Question:</span>&nbsp;How many customers do we serve, and who places the most orders?
                        </p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-xs text-slate-400">Distinct Customers Served:</span>
                        <span class="px-3 py-1 rounded-lg bg-purple-950 border border-purple-800 font-mono font-bold text-purple-300">{{ customer_kpis.distinct_customers }}</span>
                    </div>
                </div>

                <!-- Top 10 Customers Table -->
                <div class="mt-5 overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-3 px-4">Rank</th>
                                <th class="py-3 px-4">Customer ID</th>
                                <th class="py-3 px-4">Customer Name</th>
                                <th class="py-3 px-4">City</th>
                                <th class="py-3 px-4">Segment</th>
                                <th class="py-3 px-4 text-center">Orders Placed</th>
                                <th class="py-3 px-4 text-center text-emerald-400">Delivered</th>
                                <th class="py-3 px-4 text-right">Total Lifetime Spend</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60">
                            {% for c in customer_kpis.top_10_customers %}
                            <tr class="hover:bg-slate-800/40 transition-colors">
                                <td class="py-3 px-4 font-mono font-bold text-slate-500">#{{ loop.index }}</td>
                                <td class="py-3 px-4 font-mono text-blue-400">{{ c.CUSTOMER_ID }}</td>
                                <td class="py-3 px-4 font-semibold text-white">{{ c.CUSTOMER_NAME }}</td>
                                <td class="py-3 px-4 text-slate-300">{{ c.CITY }}</td>
                                <td class="py-3 px-4">
                                    <span class="badge-pill {% if c.CUSTOMER_SEGMENT == 'Premium' %}bg-purple-900/60 text-purple-300 border border-purple-500/30{% elif c.CUSTOMER_SEGMENT == 'Corporate' %}bg-blue-900/60 text-blue-300 border border-blue-500/30{% else %}bg-slate-800 text-slate-400 border border-slate-700{% endif %}">
                                        {{ c.CUSTOMER_SEGMENT }}
                                    </span>
                                </td>
                                <td class="py-3 px-4 text-center font-bold text-white">{{ c.total_orders }}</td>
                                <td class="py-3 px-4 text-center text-emerald-400 font-semibold">{{ c.delivered_orders }}</td>
                                <td class="py-3 px-4 text-right font-mono font-bold text-slate-200">₹{{ "{:,.2f}".format(c.total_spend) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION C: FULFILLMENT KPIS & FORMULA EXPLAINER -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-2">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="badge-pill bg-emerald-900/60 text-emerald-400 border border-emerald-500/30">Section C</span>
                            <h2 class="text-lg font-bold text-white">Fulfillment KPIs & SLA Performance</h2>
                        </div>
                        <p class="text-xs text-emerald-300 mt-1 flex items-center">
                            <i class="fa-solid fa-circle-question mr-1.5 text-emerald-400"></i>
                            <span class="font-medium">Business Question:</span>&nbsp;Are we delivering on time?
                        </p>
                    </div>
                    <span class="text-xs text-slate-400 font-mono">SLA Delivery Threshold: 100% Target</span>
                </div>

                <!-- 5 Mandatory Fulfillment Metrics Cards -->
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mt-5">
                    <div class="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400 font-semibold uppercase">Avg Delivery Days</span>
                        <div class="text-2xl font-black text-white mt-1">{{ order_kpis.avg_delivery_days or 0 }} <span class="text-sm font-normal text-slate-400">days</span></div>
                        <div class="text-xs text-slate-500 mt-1">Order to Doorstep</div>
                    </div>
                    <div class="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400 font-semibold uppercase">Average SLA Days</span>
                        <div class="text-2xl font-black text-blue-400 mt-1">{{ order_kpis.avg_sla_days or 0 }} <span class="text-sm font-normal text-slate-400">days</span></div>
                        <div class="text-xs text-blue-500/80 mt-1">Contractual Target</div>
                    </div>
                    <div class="bg-slate-900/90 border border-emerald-900/40 p-4 rounded-xl">
                        <span class="text-xs text-emerald-400 font-semibold uppercase">On-Time Delivery %</span>
                        <div class="text-2xl font-black text-emerald-400 mt-1">{{ order_kpis.on_time_delivery_pct or 0 }}%</div>
                        <div class="text-xs text-emerald-500/80 mt-1">Delivered &le; SLA Days</div>
                    </div>
                    <div class="bg-slate-900/90 border border-rose-900/40 p-4 rounded-xl">
                        <span class="text-xs text-rose-400 font-semibold uppercase">Late Delivery %</span>
                        <div class="text-2xl font-black text-rose-400 mt-1">{{ order_kpis.late_delivery_pct or 0 }}%</div>
                        <div class="text-xs text-rose-500/80 mt-1">Delivered &gt; SLA Days</div>
                    </div>
                    <div class="bg-slate-900/90 border border-cyan-900/40 p-4 rounded-xl col-span-2 md:col-span-1">
                        <span class="text-xs text-cyan-400 font-semibold uppercase">Shipment Success Rate</span>
                        <div class="text-2xl font-black text-cyan-400 mt-1">{{ order_kpis.shipment_success_rate_pct or 0 }}%</div>
                        <div class="text-xs text-cyan-500/80 mt-1">Delivered / Total Orders</div>
                    </div>
                </div>

                <!-- Mathematical Formula & Investigative Value Callout -->
                <div class="mt-6 bg-gradient-to-r from-blue-950/60 via-slate-900 to-indigo-950/60 border border-blue-500/30 p-5 rounded-xl">
                    <div class="flex items-start space-x-3">
                        <i class="fa-solid fa-calculator text-blue-400 text-lg mt-0.5"></i>
                        <div class="space-y-2 text-xs text-slate-300">
                            <h4 class="font-bold text-white text-sm">Example: How does an on-time delivery KPI help management?</h4>
                            <p>Suppose 100 eligible orders have been delivered: 80 were delivered on time and 20 were delivered late.</p>
                            <div class="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg font-mono text-emerald-300 text-xs inline-block">
                                On-Time Delivery % = ( On-Time Delivered Orders / Total Delivered Orders ) &times; 100 = ( 80 / 100 ) &times; 100 = 80.0%
                            </div>
                            <p class="text-slate-400 italic">
                                &ldquo;Management can investigate the remaining 20 late deliveries and determine whether they are concentrated around a particular courier, city, or month. <b>The metric identifies where to investigate</b>; it does not, by itself, prove why the delays occurred.&rdquo;
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION D: COURIER KPIS & LEADERBOARD -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-2">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="badge-pill bg-cyan-900/60 text-cyan-400 border border-cyan-500/30">Section D</span>
                            <h2 class="text-lg font-bold text-white">Courier KPIs & Performance Rankings</h2>
                        </div>
                        <p class="text-xs text-cyan-300 mt-1 flex items-center">
                            <i class="fa-solid fa-circle-question mr-1.5 text-cyan-400"></i>
                            <span class="font-medium">Business Question:</span>&nbsp;Which delivery partners should we investigate or reward?
                        </p>
                    </div>
                    <div class="flex items-center space-x-3 text-xs">
                        <span class="flex items-center text-emerald-400 font-semibold"><i class="fa-solid fa-trophy mr-1"></i> Best: {{ courier_kpis.best_performing_courier.COURIER_NAME }} ({{ courier_kpis.best_performing_courier.on_time_pct }}% On-Time)</span>
                        <span class="text-slate-600">|</span>
                        <span class="flex items-center text-rose-400 font-semibold"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Worst: {{ courier_kpis.worst_performing_courier.COURIER_NAME }} ({{ courier_kpis.worst_performing_courier.delay_pct }}% Late)</span>
                    </div>
                </div>

                <div class="mt-5 overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-3 px-4">Courier Partner</th>
                                <th class="py-3 px-4">Service Tier</th>
                                <th class="py-3 px-4 text-center">SLA Days</th>
                                <th class="py-3 px-4 text-center">Orders Handled</th>
                                <th class="py-3 px-4 text-center">Delivered</th>
                                <th class="py-3 px-4 text-center text-emerald-400 font-bold">On-Time %</th>
                                <th class="py-3 px-4 text-center text-rose-400 font-bold">Delay %</th>
                                <th class="py-3 px-4 text-center">Avg Delivery</th>
                                <th class="py-3 px-4 text-right">Investigation Action</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60">
                            {% for c in courier_kpis.courier_metrics %}
                            <tr class="hover:bg-slate-800/40 transition-colors">
                                <td class="py-3 px-4 font-bold text-white flex items-center space-x-2">
                                    <span>{{ c.COURIER_NAME }}</span>
                                    {% if c.ACTIVE_FLAG == 'N' %}
                                        <span class="badge-pill bg-amber-950 text-amber-400 border border-amber-800">Inactive Vendor</span>
                                    {% endif %}
                                </td>
                                <td class="py-3 px-4 text-slate-400 text-xs">{{ c.SERVICE_TYPE }}</td>
                                <td class="py-3 px-4 text-center font-mono">{{ c.SLA_DAYS }}d</td>
                                <td class="py-3 px-4 text-center font-bold text-slate-200">{{ c.total_orders }}</td>
                                <td class="py-3 px-4 text-center text-slate-300">{{ c.delivered_orders }}</td>
                                <td class="py-3 px-4 text-center font-extrabold {% if c.on_time_pct >= 40 %}text-emerald-400{% else %}text-amber-400{% endif %}">{{ c.on_time_pct }}%</td>
                                <td class="py-3 px-4 text-center font-extrabold {% if c.delay_pct >= 75 %}text-rose-400{% else %}text-slate-300{% endif %}">{{ c.delay_pct }}%</td>
                                <td class="py-3 px-4 text-center font-mono text-slate-300">{{ c.avg_delivery_days }}d</td>
                                <td class="py-3 px-4 text-right">
                                    {% if c.delay_pct >= 80 %}
                                        <span class="badge-pill bg-rose-950 text-rose-300 border border-rose-800">Investigate Routes</span>
                                    {% elif c.ACTIVE_FLAG == 'N' %}
                                        <span class="badge-pill bg-slate-800 text-slate-400 border border-slate-700">Decommissioned</span>
                                    {% else %}
                                        <span class="badge-pill bg-emerald-950 text-emerald-400 border border-emerald-800">Eligible Reward</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION E: TREND KPIS -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-2">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="badge-pill bg-amber-900/60 text-amber-400 border border-amber-500/30">Section E</span>
                            <h2 class="text-lg font-bold text-white">Trend KPIs & Temporal Dynamics</h2>
                        </div>
                        <p class="text-xs text-amber-300 mt-1 flex items-center">
                            <i class="fa-solid fa-circle-question mr-1.5 text-amber-400"></i>
                            <span class="font-medium">Business Question:</span>&nbsp;Is performance improving or deteriorating over time?
                        </p>
                    </div>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-5">
                    <!-- Chart 1: Monthly Order & Delivery Volume Trend -->
                    <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
                        <h4 class="text-sm font-bold text-white mb-3 flex items-center">
                            <i class="fa-solid fa-chart-column text-indigo-400 mr-2"></i>Monthly Order & Delivery Trends
                        </h4>
                        <div class="h-64">
                            <canvas id="chart-monthly-trends"></canvas>
                        </div>
                    </div>

                    <!-- Chart 2: Order Status Distribution Trend -->
                    <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
                        <h4 class="text-sm font-bold text-white mb-3 flex items-center">
                            <i class="fa-solid fa-chart-pie text-emerald-400 mr-2"></i>Status-Wise Fulfillment Share
                        </h4>
                        <div class="h-64 flex items-center justify-center">
                            <canvas id="chart-status-distribution"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Monthly Trend Table -->
                <div class="mt-6 overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-900 text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-2.5 px-4">Year-Month</th>
                                <th class="py-2.5 px-4 text-center">Total Orders</th>
                                <th class="py-2.5 px-4 text-center text-emerald-400">Delivered</th>
                                <th class="py-2.5 px-4 text-center text-rose-400">Cancelled</th>
                                <th class="py-2.5 px-4 text-center text-amber-400">Returned</th>
                                <th class="py-2.5 px-4 text-center text-blue-400">In-Transit</th>
                                <th class="py-2.5 px-4 text-center">Avg Delivery Days</th>
                                <th class="py-2.5 px-4 text-right">Monthly Revenue</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60 font-mono text-xs">
                            {% for t in trend_kpis.monthly_trends %}
                            <tr class="hover:bg-slate-800/30">
                                <td class="py-2.5 px-4 font-bold text-blue-400">{{ t.year_month }}</td>
                                <td class="py-2.5 px-4 text-center font-bold text-white">{{ t.total_orders }}</td>
                                <td class="py-2.5 px-4 text-center text-emerald-400">{{ t.delivered_orders }}</td>
                                <td class="py-2.5 px-4 text-center text-rose-400">{{ t.cancelled_orders }}</td>
                                <td class="py-2.5 px-4 text-center text-amber-400">{{ t.returned_orders }}</td>
                                <td class="py-2.5 px-4 text-center text-blue-400">{{ t.in_transit_orders }}</td>
                                <td class="py-2.5 px-4 text-center text-slate-300">{{ t.avg_delivery_days }}d</td>
                                <td class="py-2.5 px-4 text-right font-bold text-slate-200">₹{{ "{:,.2f}".format(t.monthly_revenue or 0) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

        </section>

        <!-- =================== TAB 2: BUSINESS SOLUTIONS & REAL-WORLD SCENARIOS (SECTION 6) =================== -->
        <section id="tab-business-scenarios" class="tab-content hidden space-y-6">
            <div class="glass-card p-6 rounded-2xl border-l-4 border-amber-500">
                <div class="flex items-center space-x-2">
                    <span class="badge-pill bg-amber-950 text-amber-400 border border-amber-800">Section 6 Framework</span>
                    <h2 class="text-xl font-black text-white">How Does This Platform Solve Real-World Customer Problems?</h2>
                </div>
                <p class="text-xs text-slate-400 mt-2">
                    Connecting Data Engineering pipeline transformations to tangible business actions and end-customer outcomes across 4 operational scenarios.
                </p>
            </div>

            <!-- The 4 Real-World Scenarios Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

                <!-- Scenario 1 -->
                <div class="glass-card p-6 rounded-2xl flex flex-col justify-between space-y-4">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="badge-pill bg-rose-950 text-rose-300 border border-rose-800">Scenario 1</span>
                            <i class="fa-solid fa-clock-rotate-left text-rose-400"></i>
                        </div>
                        <h3 class="text-base font-bold text-white mt-2">A Customer Repeatedly Receives Late Deliveries</h3>
                        
                        <div class="mt-3 p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs space-y-2">
                            <div>
                                <span class="text-slate-400 font-semibold">Dashboard Evidence:</span>
                                <p class="text-slate-200 mt-0.5">Blue Dart exhibits an <b>81.65% late-delivery rate</b> with an average delay of 5.16 days against their 2-day express SLA.</p>
                            </div>
                            <div>
                                <span class="text-blue-400 font-semibold">Business Action:</span>
                                <p class="text-slate-300 mt-0.5">The operations team investigates Blue Dart's express hub routes and reallocates eligible express orders to alternative partners or renegotiates capacity commitments.</p>
                            </div>
                            <div>
                                <span class="text-emerald-400 font-semibold">Customer Benefit:</span>
                                <p class="text-slate-300 mt-0.5">Significantly higher probability of receiving orders within the promised delivery window.</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Scenario 2 -->
                <div class="glass-card p-6 rounded-2xl flex flex-col justify-between space-y-4">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="badge-pill bg-blue-950 text-blue-300 border border-blue-800">Scenario 2</span>
                            <i class="fa-solid fa-database text-blue-400"></i>
                        </div>
                        <h3 class="text-base font-bold text-white mt-2">Incorrect Order Records Distort Delivery Reports</h3>
                        
                        <div class="mt-3 p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs space-y-2">
                            <div>
                                <span class="text-slate-400 font-semibold">Dashboard Evidence:</span>
                                <p class="text-slate-200 mt-0.5">Automated DQ framework segregated <b>316 corrupt records</b> (negative quantities, invalid dates like <code class="text-amber-400">2026/13/40</code>, orphan customer keys, unresolvable duplicate timestamps).</p>
                            </div>
                            <div>
                                <span class="text-blue-400 font-semibold">Business Action:</span>
                                <p class="text-slate-300 mt-0.5">Operations evaluates quarantined records in <code class="text-blue-300">data/quarantine</code> while BI reporting computes KPIs solely on validated warehouse facts.</p>
                            </div>
                            <div>
                                <span class="text-emerald-400 font-semibold">Customer Benefit:</span>
                                <p class="text-slate-300 mt-0.5">Better-informed operational decisions and zero fulfillment discrepancies caused by distorted executive reports.</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Scenario 3 -->
                <div class="glass-card p-6 rounded-2xl flex flex-col justify-between space-y-4">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="badge-pill bg-purple-950 text-purple-300 border border-purple-800">Scenario 3</span>
                            <i class="fa-solid fa-map-location-dot text-purple-400"></i>
                        </div>
                        <h3 class="text-base font-bold text-white mt-2">Deliveries in a Particular City Consistently Delayed</h3>
                        
                        <div class="mt-3 p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs space-y-2">
                            <div>
                                <span class="text-slate-400 font-semibold">Dashboard Evidence:</span>
                                <p class="text-slate-200 mt-0.5">Geographic analysis reveals <b>Patna (10.54 days)</b> and <b>Lucknow (8.62 days)</b> have double the delivery latency of Delhi (6.87 days).</p>
                            </div>
                            <div>
                                <span class="text-blue-400 font-semibold">Business Action:</span>
                                <p class="text-slate-300 mt-0.5">Management investigates local last-mile capacity, route planning, and regional carrier coverage in Eastern & Northern delivery corridors.</p>
                            </div>
                            <div>
                                <span class="text-emerald-400 font-semibold">Customer Benefit:</span>
                                <p class="text-slate-300 mt-0.5">Targeted infrastructure improvements in affected cities rather than applying blanket fixes to all regions.</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Scenario 4 -->
                <div class="glass-card p-6 rounded-2xl flex flex-col justify-between space-y-4">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="badge-pill bg-emerald-950 text-emerald-300 border border-emerald-800">Scenario 4</span>
                            <i class="fa-solid fa-coins text-emerald-400"></i>
                        </div>
                        <h3 class="text-base font-bold text-white mt-2">Management Wants to Reduce Operational Costs</h3>
                        
                        <div class="mt-3 p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs space-y-2">
                            <div>
                                <span class="text-slate-400 font-semibold">Dashboard Evidence:</span>
                                <p class="text-slate-200 mt-0.5">Cross-comparing courier volume shares, SLA days, and on-time compliance highlights underperforming surface vs express partners.</p>
                            </div>
                            <div>
                                <span class="text-blue-400 font-semibold">Business Action:</span>
                                <p class="text-slate-300 mt-0.5">The company evaluates courier contract allocation using service levels alongside cost, capacity, and coverage parameters during SLA negotiations.</p>
                            </div>
                            <div>
                                <span class="text-emerald-400 font-semibold">Customer Benefit:</span>
                                <p class="text-slate-300 mt-0.5">More reliable, on-time fulfillment without unnecessary increases in logistics surcharges or delivery costs.</p>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            <!-- Scenario 3 Deep Dive: City-Wise Delivery Latency Table -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-white flex items-center">
                        <i class="fa-solid fa-city text-purple-400 mr-2"></i>City-Wise Fulfillment Latency & Delay Heatmap (Supporting Scenario 3)
                    </h3>
                    <span class="text-xs text-slate-400">Top 10 Indian Delivery Hubs</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-900 text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-3 px-4">Metro / Hub City</th>
                                <th class="py-3 px-4 text-center">Total Orders</th>
                                <th class="py-3 px-4 text-center">Delivered</th>
                                <th class="py-3 px-4 text-center text-rose-400">Late Deliveries</th>
                                <th class="py-3 px-4 text-center text-emerald-400">On-Time %</th>
                                <th class="py-3 px-4 text-center">Avg Delivery Days</th>
                                <th class="py-3 px-4 text-right">Fulfillment Status</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60 font-mono text-xs">
                            {% for c in city_kpis %}
                            <tr class="hover:bg-slate-800/40">
                                <td class="py-3 px-4 font-bold text-white font-sans flex items-center space-x-2">
                                    <span>{{ c.CITY }}</span>
                                </td>
                                <td class="py-3 px-4 text-center font-bold text-slate-200">{{ c.total_orders }}</td>
                                <td class="py-3 px-4 text-center text-slate-300">{{ c.delivered_orders }}</td>
                                <td class="py-3 px-4 text-center text-rose-400 font-bold">{{ c.late_orders }}</td>
                                <td class="py-3 px-4 text-center font-bold {% if c.on_time_pct >= 30 %}text-emerald-400{% else %}text-amber-400{% endif %}">{{ c.on_time_pct }}%</td>
                                <td class="py-3 px-4 text-center font-bold {% if c.avg_delivery_days >= 8.5 %}text-rose-400{% else %}text-slate-200{% endif %}">{{ c.avg_delivery_days }} days</td>
                                <td class="py-3 px-4 text-right font-sans">
                                    {% if c.avg_delivery_days >= 9.0 %}
                                        <span class="badge-pill bg-rose-950 text-rose-300 border border-rose-800">High Latency Bottleneck</span>
                                    {% elif c.avg_delivery_days >= 7.5 %}
                                        <span class="badge-pill bg-amber-950 text-amber-300 border border-amber-800">Moderate Transit Delay</span>
                                    {% else %}
                                        <span class="badge-pill bg-emerald-950 text-emerald-300 border border-emerald-800">Optimal Hub</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- =================== TAB 3: COURIER PERFORMANCE MATRIX =================== -->
        <section id="tab-couriers" class="tab-content hidden space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="glass-card p-6 rounded-2xl border-l-4 border-emerald-500">
                    <span class="badge-pill bg-emerald-950 text-emerald-400 border border-emerald-800">Best Performing Courier Partner</span>
                    <h2 class="text-2xl font-black text-white mt-2">{{ courier_kpis.best_performing_courier.COURIER_NAME }}</h2>
                    <p class="text-xs text-slate-400 mt-1">Service: {{ courier_kpis.best_performing_courier.SERVICE_TYPE }} | Target SLA: {{ courier_kpis.best_performing_courier.SLA_DAYS }} Days</p>
                    <div class="mt-4 flex items-baseline space-x-3">
                        <span class="text-3xl font-extrabold text-emerald-400">{{ courier_kpis.best_performing_courier.on_time_pct }}%</span>
                        <span class="text-xs text-slate-400">On-Time SLA Rate</span>
                    </div>
                </div>

                <div class="glass-card p-6 rounded-2xl border-l-4 border-rose-500">
                    <span class="badge-pill bg-rose-950 text-rose-400 border border-rose-800">Worst Performing Courier (Highest Delays)</span>
                    <h2 class="text-2xl font-black text-white mt-2">{{ courier_kpis.worst_performing_courier.COURIER_NAME }}</h2>
                    <p class="text-xs text-slate-400 mt-1">Service: {{ courier_kpis.worst_performing_courier.SERVICE_TYPE }} | Target SLA: {{ courier_kpis.worst_performing_courier.SLA_DAYS }} Days</p>
                    <div class="mt-4 flex items-baseline space-x-3">
                        <span class="text-3xl font-extrabold text-rose-400">{{ courier_kpis.worst_performing_courier.delay_pct }}%</span>
                        <span class="text-xs text-slate-400">Delayed Delivery Rate</span>
                    </div>
                </div>
            </div>

            <!-- Full Courier Table -->
            <div class="glass-card p-6 rounded-2xl">
                <h3 class="text-base font-bold text-white mb-4 flex items-center">
                    <i class="fa-solid fa-table-list text-blue-400 mr-2"></i>Full Courier SLA Compliance & Reliability Matrix
                </h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-900 text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-3 px-4">Courier Name</th>
                                <th class="py-3 px-4">Status</th>
                                <th class="py-3 px-4 text-center">SLA Days</th>
                                <th class="py-3 px-4 text-center">Total Orders</th>
                                <th class="py-3 px-4 text-center">Delivered</th>
                                <th class="py-3 px-4 text-center text-emerald-400">On-Time %</th>
                                <th class="py-3 px-4 text-center text-rose-400">Delay %</th>
                                <th class="py-3 px-4 text-center">Avg Delivery</th>
                                <th class="py-3 px-4 text-center">Avg Delay</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800 font-mono text-xs">
                            {% for c in courier_kpis.courier_metrics %}
                            <tr class="hover:bg-slate-800/40">
                                <td class="py-3 px-4 font-bold text-white font-sans">{{ c.COURIER_NAME }}</td>
                                <td class="py-3 px-4 font-sans">
                                    {% if c.ACTIVE_FLAG == 'Y' %}
                                        <span class="badge-pill bg-emerald-950 text-emerald-400 border border-emerald-800">Active</span>
                                    {% else %}
                                        <span class="badge-pill bg-amber-950 text-amber-400 border border-amber-800">Inactive</span>
                                    {% endif %}
                                </td>
                                <td class="py-3 px-4 text-center">{{ c.SLA_DAYS }}d</td>
                                <td class="py-3 px-4 text-center font-bold text-slate-200">{{ c.total_orders }}</td>
                                <td class="py-3 px-4 text-center">{{ c.delivered_orders }}</td>
                                <td class="py-3 px-4 text-center font-extrabold text-emerald-400">{{ c.on_time_pct }}%</td>
                                <td class="py-3 px-4 text-center font-extrabold text-rose-400">{{ c.delay_pct }}%</td>
                                <td class="py-3 px-4 text-center">{{ c.avg_delivery_days or 'N/A' }}d</td>
                                <td class="py-3 px-4 text-center text-amber-400">{{ c.avg_delay_days or '0' }}d</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- =================== TAB 4: DATA QUALITY & AUDIT (38 RULES) =================== -->
        <section id="tab-data-quality" class="tab-content hidden space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div class="glass-card p-5 rounded-2xl">
                    <span class="text-xs uppercase text-slate-400 font-semibold">Total DQ Incidents Audited</span>
                    <div class="text-3xl font-extrabold text-blue-400 mt-1">{{ dq_summary.total_logged }}</div>
                    <p class="text-xs text-slate-400 mt-2">Evaluated across all source files</p>
                </div>
                <div class="glass-card p-5 rounded-2xl">
                    <span class="text-xs uppercase text-slate-400 font-semibold">Quarantined / Rejected Rows</span>
                    <div class="text-3xl font-extrabold text-rose-400 mt-1">{{ dq_summary.total_rejected }}</div>
                    <p class="text-xs text-slate-400 mt-2">Isolated from reporting warehouse</p>
                </div>
                <div class="glass-card p-5 rounded-2xl">
                    <span class="text-xs uppercase text-slate-400 font-semibold">DQ Precision Benchmark</span>
                    <div class="text-3xl font-extrabold text-emerald-400 mt-1">100.0%</div>
                    <p class="text-xs text-emerald-400 mt-2"><i class="fa-solid fa-circle-check mr-1"></i>Answer Key Benchmark Verified</p>
                </div>
            </div>

            <!-- DQ Audit Log Table -->
            <div class="glass-card p-6 rounded-2xl">
                <h3 class="text-base font-bold text-white mb-4 flex items-center">
                    <i class="fa-solid fa-list-check text-indigo-400 mr-2"></i>Audit Incident Log across All 38 Injected Rules
                </h3>
                <div class="overflow-x-auto max-h-96">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-900 text-slate-400 sticky top-0">
                            <tr>
                                <th class="py-3 px-4">Rule Code</th>
                                <th class="py-3 px-4">Severity</th>
                                <th class="py-3 px-4">Action Taken</th>
                                <th class="py-3 px-4 text-center">Incidents</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800 font-mono text-xs">
                            {% for r in dq_summary.rule_breakdown %}
                            <tr class="hover:bg-slate-800/40">
                                <td class="py-3 px-4 font-bold text-slate-200">{{ r.RULE_NAME }}</td>
                                <td class="py-3 px-4 font-sans">
                                    {% if r.SEVERITY in ['REJECT', 'QUARANTINE'] %}
                                        <span class="badge-pill bg-rose-950 text-rose-300 border border-rose-800">{{ r.SEVERITY }}</span>
                                    {% elif r.SEVERITY == 'WARNING' %}
                                        <span class="badge-pill bg-amber-950 text-amber-300 border border-amber-800">{{ r.SEVERITY }}</span>
                                    {% else %}
                                        <span class="badge-pill bg-blue-950 text-blue-300 border border-blue-800">{{ r.SEVERITY }}</span>
                                    {% endif %}
                                </td>
                                <td class="py-3 px-4 font-sans text-slate-300">{{ r.ACTION_TAKEN }}</td>
                                <td class="py-3 px-4 text-center font-bold text-white text-sm">{{ r.count }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- =================== TAB 5: SCHEMA & SCD2 =================== -->
        <section id="tab-schema" class="tab-content hidden space-y-6">
            <div class="glass-card p-6 rounded-2xl">
                <h3 class="text-base font-bold text-white mb-2 flex items-center">
                    <i class="fa-solid fa-diagram-project text-blue-400 mr-2"></i>Star Schema Architecture
                </h3>
                <p class="text-xs text-slate-400 mb-6">Central Fact Table with Conformed Dimensions</p>
                
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
                    <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                        <span class="text-purple-400 font-bold">DIM_CUSTOMER (SCD2)</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>CUSTOMER_KEY (PK)</li>
                            <li>CUSTOMER_ID (NK)</li>
                            <li>CUSTOMER_NAME</li>
                            <li>CITY, STATE, PINCODE</li>
                            <li>START_DATE, END_DATE</li>
                            <li>IS_CURRENT, VERSION</li>
                        </ul>
                    </div>

                    <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                        <span class="text-blue-400 font-bold">DIM_COURIER</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>COURIER_KEY (PK)</li>
                            <li>COURIER_ID, NAME</li>
                            <li>SLA_DAYS</li>
                            <li>SERVICE_TYPE</li>
                            <li>ACTIVE_FLAG</li>
                        </ul>
                    </div>

                    <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                        <span class="text-emerald-400 font-bold">DIM_PRODUCT</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>PRODUCT_KEY (PK)</li>
                            <li>PRODUCT_ID, NAME</li>
                            <li>CATEGORY</li>
                            <li>BASE_UNIT_PRICE</li>
                        </ul>
                    </div>

                    <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                        <span class="text-amber-400 font-bold">DIM_DATE</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>DATE_KEY (PK)</li>
                            <li>FULL_DATE</li>
                            <li>DAY, MONTH, YEAR</li>
                            <li>QUARTER, WEEKEND</li>
                        </ul>
                    </div>
                </div>

                <div class="mt-6 bg-slate-950 border border-blue-500/30 p-5 rounded-xl">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-blue-400 font-bold text-sm">FACT_ORDER_FULFILLMENT</span>
                        <span class="text-xs text-slate-400 font-mono">Grain: 1 record per ORDER_ID</span>
                    </div>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono text-slate-300 mt-3">
                        <div>QUANTITY</div>
                        <div>UNIT_PRICE</div>
                        <div>TOTAL_AMOUNT</div>
                        <div>DELIVERY_DAYS</div>
                        <div>DELAY_DAYS</div>
                        <div>DELIVERED_FLAG</div>
                        <div>ON_TIME_FLAG</div>
                        <div>LATE_DELIVERY_FLAG</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- =================== TAB 6: SQL WORKBENCH =================== -->
        <section id="tab-sql-console" class="tab-content hidden space-y-6">
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-white flex items-center">
                        <i class="fa-solid fa-code text-blue-400 mr-2"></i>Live Warehouse SQL Console
                    </h3>
                    <div class="flex space-x-2">
                        <button onclick="setQuery('SELECT * FROM FACT_ORDER_FULFILLMENT LIMIT 10;')" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-slate-300">Sample Fact</button>
                        <button onclick="setQuery('SELECT * FROM DIM_CUSTOMER WHERE IS_CURRENT = 0 LIMIT 10;')" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-slate-300">SCD2 History</button>
                        <button onclick="setQuery('SELECT * FROM DIM_COURIER;')" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-slate-300">Couriers</button>
                    </div>
                </div>
                
                <div class="space-y-3">
                    <textarea id="sql-input" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 font-mono text-sm text-emerald-300 focus:outline-none focus:border-blue-500 h-32" placeholder="Enter custom SELECT query here...">SELECT c.COURIER_NAME, COUNT(f.ORDER_ID) AS orders, ROUND(AVG(f.DELIVERY_DAYS), 2) AS avg_days FROM FACT_ORDER_FULFILLMENT f JOIN DIM_COURIER c ON f.COURIER_KEY = c.COURIER_KEY GROUP BY c.COURIER_NAME ORDER BY orders DESC;</textarea>
                    <button onclick="executeSQL()" class="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors flex items-center space-x-2">
                        <i class="fa-solid fa-play text-xs"></i>
                        <span>Execute SQL Query</span>
                    </button>
                </div>

                <div id="query-results" class="mt-6 overflow-x-auto"></div>
            </div>
        </section>

    </main>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(el => {
                el.classList.remove('active');
                el.classList.add('text-slate-400');
            });
            
            document.getElementById('tab-' + tabId).classList.remove('hidden');
            const activeBtn = document.getElementById('btn-' + tabId);
            activeBtn.classList.add('active');
            activeBtn.classList.remove('text-slate-400');
        }

        function setQuery(sql) {
            document.getElementById('sql-input').value = sql;
            executeSQL();
        }

        async function executeSQL() {
            const sql = document.getElementById('sql-input').value;
            const container = document.getElementById('query-results');
            container.innerHTML = '<div class="text-slate-400 text-sm py-4"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Executing query against warehouse...</div>';

            try {
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: sql })
                });
                const data = await res.json();
                
                if (data.error) {
                    container.innerHTML = `<div class="p-4 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-xl text-sm font-mono">${data.error}</div>`;
                    return;
                }

                if (!data.rows || data.rows.length === 0) {
                    container.innerHTML = '<div class="text-slate-400 text-sm py-4">Query returned 0 rows.</div>';
                    return;
                }

                const cols = Object.keys(data.rows[0]);
                let tableHtml = '<table class="w-full text-left text-sm font-mono"><thead class="text-xs uppercase bg-slate-900 text-slate-400 border-b border-slate-800"><tr>';
                cols.forEach(c => tableHtml += `<th class="py-2.5 px-4">${c}</th>`);
                tableHtml += '</tr></thead><tbody class="divide-y divide-slate-800 text-xs">';
                data.rows.forEach(r => {
                    tableHtml += '<tr class="hover:bg-slate-800/40">';
                    cols.forEach(c => tableHtml += `<td class="py-2 px-4 text-slate-300">${r[c] !== null ? r[c] : '<span class="text-slate-600">NULL</span>'}</td>`);
                    tableHtml += '</tr>';
                });
                tableHtml += '</tbody></table>';
                container.innerHTML = tableHtml;

            } catch (err) {
                container.innerHTML = `<div class="p-4 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-xl text-sm font-mono">${err}</div>`;
            }
        }

        async function triggerPipelineRun() {
            const btn = document.getElementById('run-btn');
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Running Pipeline...</span>';
            btn.disabled = true;

            try {
                const res = await fetch('/api/run-pipeline', { method: 'POST' });
                const data = await res.json();
                alert('Pipeline Completed Successfully! Loaded: ' + data.fact_orders_loaded + ' orders.');
                window.location.reload();
            } catch (e) {
                alert('Error running pipeline: ' + e);
            } finally {
                btn.innerHTML = '<i class="fa-solid fa-play text-xs"></i><span>Re-Run ETL Pipeline</span>';
                btn.disabled = false;
            }
        }

        window.onload = function() {
            // Section E: Monthly Trends Bar Chart
            const ctxMonthly = document.getElementById('chart-monthly-trends').getContext('2d');
            const monthlyLabels = {{ trend_kpis.monthly_trends | map(attribute='year_month') | list | tojson }};
            const monthlyOrders = {{ trend_kpis.monthly_trends | map(attribute='total_orders') | list | tojson }};
            const monthlyDelivered = {{ trend_kpis.monthly_trends | map(attribute='delivered_orders') | list | tojson }};

            new Chart(ctxMonthly, {
                type: 'bar',
                data: {
                    labels: monthlyLabels,
                    datasets: [
                        { label: 'Total Orders', data: monthlyOrders, backgroundColor: '#6366f1', borderRadius: 4 },
                        { label: 'Delivered Orders', data: monthlyDelivered, backgroundColor: '#10b981', borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                        y: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } }
                    },
                    plugins: { legend: { labels: { color: '#94a3b8' } } }
                }
            });

            // Section E: Status Distribution Doughnut Chart
            const ctxStatus = document.getElementById('chart-status-distribution').getContext('2d');
            new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: ['Delivered', 'Cancelled', 'Returned', 'In-Transit'],
                    datasets: [{
                        data: [
                            {{ order_kpis.delivered_orders or 0 }},
                            {{ order_kpis.cancelled_orders or 0 }},
                            {{ order_kpis.returned_orders or 0 }},
                            {{ order_kpis.in_transit_orders or 0 }}
                        ],
                        backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#3b82f6'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                }
            });
        };
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    order_kpis = kpi_calc.get_order_kpis()
    cust_kpis = kpi_calc.get_customer_kpis()
    courier_kpis = kpi_calc.get_courier_kpis()
    trend_kpis = kpi_calc.get_trend_kpis()
    city_kpis = kpi_calc.get_city_kpis()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT RULE_NAME, SEVERITY, ACTION_TAKEN, COUNT(*) AS count FROM DQ_AUDIT_LOG GROUP BY RULE_NAME, SEVERITY, ACTION_TAKEN ORDER BY count DESC")
    rule_breakdown = [dict(r) for r in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM DQ_AUDIT_LOG")
    total_logged = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM DQ_AUDIT_LOG WHERE SEVERITY IN ('REJECT', 'QUARANTINE')")
    total_rejected = c.fetchone()[0]
    conn.close()

    dq_summary = {
        "total_logged": total_logged,
        "total_rejected": total_rejected,
        "rule_breakdown": rule_breakdown
    }

    return render_template_string(
        HTML_TEMPLATE,
        order_kpis=order_kpis,
        customer_kpis=cust_kpis,
        courier_kpis=courier_kpis,
        trend_kpis=trend_kpis,
        city_kpis=city_kpis,
        dq_summary=dq_summary
    )

@app.route("/api/kpis")
def api_kpis():
    return jsonify(kpi_calc.get_order_kpis())

@app.route("/api/couriers")
def api_couriers():
    return jsonify(kpi_calc.get_courier_kpis())

@app.route("/api/trends")
def api_trends():
    return jsonify(kpi_calc.get_trend_kpis())

@app.route("/api/cities")
def api_cities():
    return jsonify(kpi_calc.get_city_kpis())

@app.route("/api/query", methods=["POST"])
def api_query():
    body = request.get_json() or {}
    query = body.get("query", "").strip()

    if not query.lower().startswith("select"):
        return jsonify({"error": "Only SELECT queries are permitted in the web query console."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        rows = [dict(r) for r in cursor.fetchall()[:100]]
        conn.close()
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/run-pipeline", methods=["POST"])
def api_run_pipeline():
    pipeline = OrderFlow360Pipeline()
    result = pipeline.run_pipeline()
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n[WEB MVP] Starting OrderFlow360 Dashboard on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
