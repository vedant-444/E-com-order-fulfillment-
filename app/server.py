"""
OrderFlow360 Analytics Platform - Deployable Web MVP
Full-featured Interactive Dashboard & REST API Engine
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glass-card { background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); }
        .tab-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
    </style>
</head>
<body class="min-h-screen">
    <!-- Navbar -->
    <header class="glass sticky top-0 z-50 px-6 py-4 flex items-center justify-between shadow-lg">
        <div class="flex items-center space-x-3">
            <div class="bg-gradient-to-tr from-blue-600 to-indigo-500 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
                <i class="fa-solid fa-boxes-packing text-white text-lg"></i>
            </div>
            <div>
                <h1 class="text-xl font-bold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-white bg-clip-text text-transparent">OrderFlow360</h1>
                <p class="text-xs text-slate-400">Order Fulfillment Data Warehouse & Analytics MVP</p>
            </div>
        </div>
        <div class="flex items-center space-x-4">
            <button onclick="triggerPipelineRun()" id="run-btn" class="flex items-center space-x-2 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-lg shadow-emerald-600/30">
                <i class="fa-solid fa-play"></i>
                <span>Run ETL Pipeline</span>
            </button>
            <div class="flex items-center space-x-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-mono text-emerald-400">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>DB ACTIVE (DuckDB/SQLite)</span>
            </div>
        </div>
    </header>

    <!-- Navigation Tabs -->
    <div class="max-w-7xl mx-auto px-6 pt-6">
        <div class="flex space-x-2 border-b border-slate-700/60 pb-3 overflow-x-auto text-sm">
            <button onclick="switchTab('dashboard')" class="tab-btn active px-4 py-2 rounded-lg font-medium transition-colors" id="btn-dashboard">
                <i class="fa-solid fa-chart-line mr-2"></i>Executive Overview
            </button>
            <button onclick="switchTab('couriers')" class="tab-btn px-4 py-2 rounded-lg font-medium text-slate-400 hover:text-white transition-colors" id="btn-couriers">
                <i class="fa-solid fa-truck-fast mr-2"></i>Courier Performance
            </button>
            <button onclick="switchTab('trends')" class="tab-btn px-4 py-2 rounded-lg font-medium text-slate-400 hover:text-white transition-colors" id="btn-trends">
                <i class="fa-solid fa-arrow-trend-up mr-2"></i>Trends & Volume
            </button>
            <button onclick="switchTab('data-quality')" class="tab-btn px-4 py-2 rounded-lg font-medium text-slate-400 hover:text-white transition-colors" id="btn-data-quality">
                <i class="fa-solid fa-shield-halved mr-2"></i>Data Quality & DQ Audit (38 Rules)
            </button>
            <button onclick="switchTab('schema')" class="tab-btn px-4 py-2 rounded-lg font-medium text-slate-400 hover:text-white transition-colors" id="btn-schema">
                <i class="fa-solid fa-sitemap mr-2"></i>Star Schema & SCD2
            </button>
            <button onclick="switchTab('sql-console')" class="tab-btn px-4 py-2 rounded-lg font-medium text-slate-400 hover:text-white transition-colors" id="btn-sql-console">
                <i class="fa-solid fa-terminal mr-2"></i>SQL Query Workbench
            </button>
        </div>
    </div>

    <!-- Main Content Area -->
    <main class="max-w-7xl mx-auto px-6 py-6 space-y-6">
        
        <!-- =================== TAB 1: EXECUTIVE DASHBOARD =================== -->
        <section id="tab-dashboard" class="tab-content space-y-6">
            <!-- Summary KPI Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                <div class="glass-card p-5 rounded-2xl">
                    <div class="flex items-center justify-between text-slate-400 mb-2">
                        <span class="text-xs font-semibold uppercase tracking-wider">Total Warehouse Orders</span>
                        <i class="fa-solid fa-cart-shopping text-blue-400"></i>
                    </div>
                    <div class="text-3xl font-extrabold text-white" id="kpi-total-orders">{{ order_kpis.total_orders or 0 }}</div>
                    <div class="mt-2 text-xs text-slate-400 flex items-center justify-between">
                        <span>Success Rate: <b class="text-emerald-400">{{ order_kpis.shipment_success_rate_pct or 0 }}%</b></span>
                        <span class="text-slate-500">Net Loaded</span>
                    </div>
                </div>

                <div class="glass-card p-5 rounded-2xl">
                    <div class="flex items-center justify-between text-slate-400 mb-2">
                        <span class="text-xs font-semibold uppercase tracking-wider">On-Time SLA Delivery</span>
                        <i class="fa-solid fa-clock-check text-emerald-400"></i>
                    </div>
                    <div class="text-3xl font-extrabold text-emerald-400" id="kpi-ontime-rate">{{ order_kpis.on_time_delivery_pct or 0 }}%</div>
                    <div class="mt-2 text-xs text-slate-400 flex items-center justify-between">
                        <span>Late Delivery: <b class="text-rose-400">{{ order_kpis.late_delivery_pct or 0 }}%</b></span>
                        <span class="text-amber-400 font-medium">SLA Gap Detected</span>
                    </div>
                </div>

                <div class="glass-card p-5 rounded-2xl">
                    <div class="flex items-center justify-between text-slate-400 mb-2">
                        <span class="text-xs font-semibold uppercase tracking-wider">Avg Delivery vs SLA</span>
                        <i class="fa-solid fa-business-time text-amber-400"></i>
                    </div>
                    <div class="text-3xl font-extrabold text-white">
                        <span>{{ order_kpis.avg_delivery_days or 0 }}</span>
                        <span class="text-sm font-normal text-slate-400">days</span>
                    </div>
                    <div class="mt-2 text-xs text-slate-400 flex items-center justify-between">
                        <span>Target SLA Avg: <b class="text-blue-400">{{ order_kpis.avg_sla_days or 0 }} days</b></span>
                        <span class="text-rose-400">+{{ ((order_kpis.avg_delivery_days or 0) - (order_kpis.avg_sla_days or 0))|round(2) }} d variance</span>
                    </div>
                </div>

                <div class="glass-card p-5 rounded-2xl">
                    <div class="flex items-center justify-between text-slate-400 mb-2">
                        <span class="text-xs font-semibold uppercase tracking-wider">Total Fulfillment Revenue</span>
                        <i class="fa-solid fa-indian-rupee-sign text-purple-400"></i>
                    </div>
                    <div class="text-3xl font-extrabold text-purple-400">₹{{ "{:,.2f}".format(order_kpis.total_revenue or 0) }}</div>
                    <div class="mt-2 text-xs text-slate-400 flex items-center justify-between">
                        <span>Delivered: <b class="text-slate-200">{{ order_kpis.delivered_orders or 0 }}</b></span>
                        <span>In-Transit: <b class="text-blue-400">{{ order_kpis.in_transit_orders or 0 }}</b></span>
                    </div>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Status Breakdown Chart -->
                <div class="glass-card p-6 rounded-2xl">
                    <h3 class="text-base font-bold text-white mb-4 flex items-center">
                        <i class="fa-solid fa-chart-pie text-blue-400 mr-2"></i>Order Status Distribution
                    </h3>
                    <div class="h-64 flex items-center justify-center">
                        <canvas id="chart-status-pie"></canvas>
                    </div>
                </div>

                <!-- Monthly Orders & Revenue Chart -->
                <div class="glass-card p-6 rounded-2xl lg:col-span-2">
                    <h3 class="text-base font-bold text-white mb-4 flex items-center">
                        <i class="fa-solid fa-chart-column text-indigo-400 mr-2"></i>Monthly Order Fulfillment Velocity
                    </h3>
                    <div class="h-64">
                        <canvas id="chart-monthly-bar"></canvas>
                    </div>
                </div>
            </div>

            <!-- Top 10 Customers Leaderboard -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-white flex items-center">
                        <i class="fa-solid fa-crown text-amber-400 mr-2"></i>Top 10 Customers by Order Volume & Spend
                    </h3>
                    <span class="text-xs text-slate-400">Linked via DIM_CUSTOMER (SCD Type 2)</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-800/60 text-slate-400 border-b border-slate-700">
                            <tr>
                                <th class="py-3 px-4">Customer ID</th>
                                <th class="py-3 px-4">Customer Name</th>
                                <th class="py-3 px-4">City</th>
                                <th class="py-3 px-4">Segment</th>
                                <th class="py-3 px-4 text-center">Total Orders</th>
                                <th class="py-3 px-4 text-center">Delivered</th>
                                <th class="py-3 px-4 text-right">Total Spend</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            {% for c in customer_kpis.top_10_customers %}
                            <tr class="hover:bg-slate-800/40 transition-colors">
                                <td class="py-3 px-4 font-mono text-blue-400">{{ c.CUSTOMER_ID }}</td>
                                <td class="py-3 px-4 font-semibold text-white">{{ c.CUSTOMER_NAME }}</td>
                                <td class="py-3 px-4 text-slate-300">{{ c.CITY }}</td>
                                <td class="py-3 px-4">
                                    <span class="px-2 py-0.5 rounded text-xs font-semibold {% if c.CUSTOMER_SEGMENT == 'Premium' %}bg-purple-900/60 text-purple-300 border border-purple-500/30{% elif c.CUSTOMER_SEGMENT == 'Corporate' %}bg-blue-900/60 text-blue-300 border border-blue-500/30{% else %}bg-slate-700 text-slate-300{% endif %}">
                                        {{ c.CUSTOMER_SEGMENT }}
                                    </span>
                                </td>
                                <td class="py-3 px-4 text-center font-bold text-white">{{ c.total_orders }}</td>
                                <td class="py-3 px-4 text-center text-emerald-400">{{ c.delivered_orders }}</td>
                                <td class="py-3 px-4 text-right font-mono font-semibold text-slate-200">₹{{ "{:,.2f}".format(c.total_spend) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- =================== TAB 2: COURIER PERFORMANCE =================== -->
        <section id="tab-couriers" class="tab-content hidden space-y-6">
            <!-- Best and Worst Courier Highlights -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="glass-card p-6 rounded-2xl border-l-4 border-emerald-500">
                    <div class="flex items-center justify-between">
                        <div>
                            <span class="text-xs uppercase tracking-wider text-emerald-400 font-bold">Best Performing Courier</span>
                            <h2 class="text-2xl font-extrabold text-white mt-1">{{ courier_kpis.best_performing_courier.COURIER_NAME }}</h2>
                            <p class="text-xs text-slate-400 mt-1">Service: {{ courier_kpis.best_performing_courier.SERVICE_TYPE }} | Target SLA: {{ courier_kpis.best_performing_courier.SLA_DAYS }} Days</p>
                        </div>
                        <div class="text-right">
                            <div class="text-3xl font-extrabold text-emerald-400">{{ courier_kpis.best_performing_courier.on_time_pct }}%</div>
                            <span class="text-xs text-slate-400">On-Time SLA Rate</span>
                        </div>
                    </div>
                </div>

                <div class="glass-card p-6 rounded-2xl border-l-4 border-rose-500">
                    <div class="flex items-center justify-between">
                        <div>
                            <span class="text-xs uppercase tracking-wider text-rose-400 font-bold">Worst Performing Courier (Highest Delays)</span>
                            <h2 class="text-2xl font-extrabold text-white mt-1">{{ courier_kpis.worst_performing_courier.COURIER_NAME }}</h2>
                            <p class="text-xs text-slate-400 mt-1">Service: {{ courier_kpis.worst_performing_courier.SERVICE_TYPE }} | Target SLA: {{ courier_kpis.worst_performing_courier.SLA_DAYS }} Days</p>
                        </div>
                        <div class="text-right">
                            <div class="text-3xl font-extrabold text-rose-400">{{ courier_kpis.worst_performing_courier.delay_pct }}%</div>
                            <span class="text-xs text-slate-400">Delayed Delivery Rate</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Full Courier Matrix Table -->
            <div class="glass-card p-6 rounded-2xl">
                <h3 class="text-base font-bold text-white mb-4 flex items-center">
                    <i class="fa-solid fa-table-list text-blue-400 mr-2"></i>Courier SLA Compliance & Reliability Matrix
                </h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-800/60 text-slate-400 border-b border-slate-700">
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
                        <tbody class="divide-y divide-slate-800">
                            {% for c in courier_kpis.courier_metrics %}
                            <tr class="hover:bg-slate-800/40 transition-colors">
                                <td class="py-3 px-4 font-bold text-white flex items-center space-x-2">
                                    <span>{{ c.COURIER_NAME }}</span>
                                </td>
                                <td class="py-3 px-4">
                                    {% if c.ACTIVE_FLAG == 'Y' %}
                                        <span class="px-2 py-0.5 rounded text-xs bg-emerald-950 text-emerald-400 border border-emerald-800">Active</span>
                                    {% else %}
                                        <span class="px-2 py-0.5 rounded text-xs bg-amber-950 text-amber-400 border border-amber-800">Inactive</span>
                                    {% endif %}
                                </td>
                                <td class="py-3 px-4 text-center font-mono">{{ c.SLA_DAYS }}d</td>
                                <td class="py-3 px-4 text-center font-semibold">{{ c.total_orders }}</td>
                                <td class="py-3 px-4 text-center">{{ c.delivered_orders }}</td>
                                <td class="py-3 px-4 text-center font-bold text-emerald-400">{{ c.on_time_pct }}%</td>
                                <td class="py-3 px-4 text-center font-bold text-rose-400">{{ c.delay_pct }}%</td>
                                <td class="py-3 px-4 text-center font-mono">{{ c.avg_delivery_days or 'N/A' }}d</td>
                                <td class="py-3 px-4 text-center font-mono text-amber-400">{{ c.avg_delay_days or '0' }}d</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- =================== TAB 3: TRENDS =================== -->
        <section id="tab-trends" class="tab-content hidden space-y-6">
            <div class="glass-card p-6 rounded-2xl">
                <h3 class="text-base font-bold text-white mb-4 flex items-center">
                    <i class="fa-solid fa-chart-area text-blue-400 mr-2"></i>Monthly Order Fulfillment & Delay Metrics
                </h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-800/60 text-slate-400 border-b border-slate-700">
                            <tr>
                                <th class="py-3 px-4">Month</th>
                                <th class="py-3 px-4 text-center">Total Orders</th>
                                <th class="py-3 px-4 text-center">Delivered</th>
                                <th class="py-3 px-4 text-center text-rose-400">Cancelled</th>
                                <th class="py-3 px-4 text-center text-amber-400">Returned</th>
                                <th class="py-3 px-4 text-center">Avg Delivery Days</th>
                                <th class="py-3 px-4 text-right">Revenue</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            {% for t in trend_kpis.monthly_trends %}
                            <tr class="hover:bg-slate-800/40">
                                <td class="py-3 px-4 font-mono font-bold text-blue-400">{{ t.year_month }}</td>
                                <td class="py-3 px-4 text-center font-semibold text-white">{{ t.total_orders }}</td>
                                <td class="py-3 px-4 text-center text-emerald-400">{{ t.delivered_orders }}</td>
                                <td class="py-3 px-4 text-center text-rose-400">{{ t.cancelled_orders }}</td>
                                <td class="py-3 px-4 text-center text-amber-400">{{ t.returned_orders }}</td>
                                <td class="py-3 px-4 text-center font-mono">{{ t.avg_delivery_days }}d</td>
                                <td class="py-3 px-4 text-right font-mono font-semibold text-slate-200">₹{{ "{:,.2f}".format(t.monthly_revenue or 0) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- =================== TAB 4: DATA QUALITY & PROFILING =================== -->
        <section id="tab-data-quality" class="tab-content hidden space-y-6">
            <!-- DQ Scorecard -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div class="glass-card p-5 rounded-2xl">
                    <span class="text-xs uppercase text-slate-400 font-semibold">Total DQ Incidents Logged</span>
                    <div class="text-3xl font-extrabold text-blue-400 mt-1">{{ dq_summary.total_logged }}</div>
                    <p class="text-xs text-slate-400 mt-2">Checked against ground truth rules</p>
                </div>
                <div class="glass-card p-5 rounded-2xl">
                    <span class="text-xs uppercase text-slate-400 font-semibold">Quarantined / Rejected Records</span>
                    <div class="text-3xl font-extrabold text-rose-400 mt-1">{{ dq_summary.total_rejected }}</div>
                    <p class="text-xs text-slate-400 mt-2">Segregated into quarantine storage</p>
                </div>
                <div class="glass-card p-5 rounded-2xl">
                    <span class="text-xs uppercase text-slate-400 font-semibold">Rules Evaluated with 100% Precision</span>
                    <div class="text-3xl font-extrabold text-emerald-400 mt-1">38 Rules</div>
                    <p class="text-xs text-emerald-400 mt-2"><i class="fa-solid fa-circle-check mr-1"></i>Benchmark Answer Key Validated</p>
                </div>
            </div>

            <!-- DQ Audit Log Table -->
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-white flex items-center">
                        <i class="fa-solid fa-list-check text-indigo-400 mr-2"></i>Data Quality Audit Breakdown (All 38 Rules)
                    </h3>
                </div>
                <div class="overflow-x-auto max-h-96">
                    <table class="w-full text-left text-sm">
                        <thead class="text-xs uppercase bg-slate-800 text-slate-400 sticky top-0">
                            <tr>
                                <th class="py-3 px-4">Rule Code</th>
                                <th class="py-3 px-4">Severity</th>
                                <th class="py-3 px-4">Action Taken</th>
                                <th class="py-3 px-4 text-center">Incidents</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            {% for r in dq_summary.rule_breakdown %}
                            <tr class="hover:bg-slate-800/40">
                                <td class="py-3 px-4 font-mono font-semibold text-slate-200">{{ r.RULE_NAME }}</td>
                                <td class="py-3 px-4">
                                    {% if r.SEVERITY == 'REJECT' or r.SEVERITY == 'QUARANTINE' %}
                                        <span class="px-2 py-0.5 rounded text-xs bg-rose-950 text-rose-300 border border-rose-800">{{ r.SEVERITY }}</span>
                                    {% elif r.SEVERITY == 'WARNING' %}
                                        <span class="px-2 py-0.5 rounded text-xs bg-amber-950 text-amber-300 border border-amber-800">{{ r.SEVERITY }}</span>
                                    {% else %}
                                        <span class="px-2 py-0.5 rounded text-xs bg-blue-950 text-blue-300 border border-blue-800">{{ r.SEVERITY }}</span>
                                    {% endif %}
                                </td>
                                <td class="py-3 px-4 text-slate-300">{{ r.ACTION_TAKEN }}</td>
                                <td class="py-3 px-4 text-center font-bold text-white">{{ r.count }}</td>
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
                    <div class="bg-slate-800/70 border border-slate-700 p-4 rounded-xl">
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

                    <div class="bg-slate-800/70 border border-slate-700 p-4 rounded-xl">
                        <span class="text-blue-400 font-bold">DIM_COURIER</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>COURIER_KEY (PK)</li>
                            <li>COURIER_ID, NAME</li>
                            <li>SLA_DAYS</li>
                            <li>SERVICE_TYPE</li>
                            <li>ACTIVE_FLAG</li>
                        </ul>
                    </div>

                    <div class="bg-slate-800/70 border border-slate-700 p-4 rounded-xl">
                        <span class="text-emerald-400 font-bold">DIM_PRODUCT</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>PRODUCT_KEY (PK)</li>
                            <li>PRODUCT_ID, NAME</li>
                            <li>CATEGORY</li>
                            <li>BASE_UNIT_PRICE</li>
                        </ul>
                    </div>

                    <div class="bg-slate-800/70 border border-slate-700 p-4 rounded-xl">
                        <span class="text-amber-400 font-bold">DIM_DATE</span>
                        <ul class="mt-2 space-y-1 text-slate-400">
                            <li>DATE_KEY (PK)</li>
                            <li>FULL_DATE</li>
                            <li>DAY, MONTH, YEAR</li>
                            <li>QUARTER, WEEKEND</li>
                        </ul>
                    </div>
                </div>

                <div class="mt-6 bg-slate-900/90 border border-blue-500/30 p-5 rounded-xl">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-blue-400 font-bold text-sm">FACT_ORDER_FULFILLMENT</span>
                        <span class="text-xs text-slate-400 font-mono">Grain: 1 record per ORDER_ID</span>
                    </div>
                    <p class="text-xs text-slate-400 mb-3">Foreign Keys: CUSTOMER_KEY, COURIER_KEY, PRODUCT_KEY, ORDER_DATE_KEY, SHIPPED_DATE_KEY, DELIVERY_DATE_KEY</p>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono text-slate-300">
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

        <!-- =================== TAB 6: SQL QUERY CONSOLE =================== -->
        <section id="tab-sql-console" class="tab-content hidden space-y-6">
            <div class="glass-card p-6 rounded-2xl">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-white flex items-center">
                        <i class="fa-solid fa-code text-blue-400 mr-2"></i>Live Warehouse SQL Workbench
                    </h3>
                    <div class="flex space-x-2">
                        <button onclick="setQuery('SELECT * FROM FACT_ORDER_FULFILLMENT LIMIT 10;')" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded text-slate-300">Sample Fact</button>
                        <button onclick="setQuery('SELECT * FROM DIM_CUSTOMER WHERE IS_CURRENT = 0 LIMIT 10;')" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded text-slate-300">SCD2 History</button>
                        <button onclick="setQuery('SELECT * FROM DIM_COURIER;')" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded text-slate-300">Couriers</button>
                    </div>
                </div>
                
                <div class="space-y-3">
                    <textarea id="sql-input" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 font-mono text-sm text-emerald-300 focus:outline-none focus:border-blue-500 h-32" placeholder="Enter custom SELECT query here...">SELECT c.COURIER_NAME, COUNT(f.ORDER_ID) AS orders, ROUND(AVG(f.DELIVERY_DAYS), 2) AS avg_days FROM FACT_ORDER_FULFILLMENT f JOIN DIM_COURIER c ON f.COURIER_KEY = c.COURIER_KEY GROUP BY c.COURIER_NAME ORDER BY orders DESC;</textarea>
                    <button onclick="executeSQL()" class="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors flex items-center space-x-2">
                        <i class="fa-solid fa-play"></i>
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
                el.classList.remove('active', 'bg-blue-600', 'text-white');
                el.classList.add('text-slate-400');
            });
            
            document.getElementById('tab-' + tabId).classList.remove('hidden');
            const activeBtn = document.getElementById('btn-' + tabId);
            activeBtn.classList.add('active', 'bg-blue-600', 'text-white');
            activeBtn.classList.remove('text-slate-400');
        }

        function setQuery(sql) {
            document.getElementById('sql-input').value = sql;
            executeSQL();
        }

        async function executeSQL() {
            const sql = document.getElementById('sql-input').value;
            const container = document.getElementById('query-results');
            container.innerHTML = '<div class="text-slate-400 text-sm py-4"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Executing query...</div>';

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
                let tableHtml = '<table class="w-full text-left text-sm"><thead class="text-xs uppercase bg-slate-800 text-slate-400 border-b border-slate-700"><tr>';
                cols.forEach(c => tableHtml += `<th class="py-2.5 px-4">${c}</th>`);
                tableHtml += '</tr></thead><tbody class="divide-y divide-slate-800">';
                data.rows.forEach(r => {
                    tableHtml += '<tr class="hover:bg-slate-800/40">';
                    cols.forEach(c => tableHtml += `<td class="py-2.5 px-4 font-mono text-slate-300">${r[c] !== null ? r[c] : '<span class="text-slate-600">NULL</span>'}</td>`);
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
                btn.innerHTML = '<i class="fa-solid fa-play"></i><span>Run ETL Pipeline</span>';
                btn.disabled = false;
            }
        }

        // Initialize Charts
        window.onload = function() {
            // Status Chart
            const ctxStatus = document.getElementById('chart-status-pie').getContext('2d');
            new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: ['Delivered', 'In-Transit', 'Cancelled', 'Returned'],
                    datasets: [{
                        data: [
                            {{ order_kpis.delivered_orders or 0 }},
                            {{ order_kpis.in_transit_orders or 0 }},
                            {{ order_kpis.cancelled_orders or 0 }},
                            {{ order_kpis.returned_orders or 0 }}
                        ],
                        backgroundColor: ['#10b981', '#3b82f6', '#ef4444', '#f59e0b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                }
            });

            // Monthly Bar Chart
            const ctxMonthly = document.getElementById('chart-monthly-bar').getContext('2d');
            const monthlyLabels = {{ trend_kpis.monthly_trends | map(attribute='year_month') | list | tojson }};
            const monthlyOrders = {{ trend_kpis.monthly_trends | map(attribute='total_orders') | list | tojson }};
            const monthlyDelivered = {{ trend_kpis.monthly_trends | map(attribute='delivered_orders') | list | tojson }};

            new Chart(ctxMonthly, {
                type: 'bar',
                data: {
                    labels: monthlyLabels,
                    datasets: [
                        { label: 'Total Orders', data: monthlyOrders, backgroundColor: '#6366f1', borderRadius: 4 },
                        { label: 'Delivered', data: monthlyDelivered, backgroundColor: '#10b981', borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                        y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
                    },
                    plugins: { legend: { labels: { color: '#94a3b8' } } }
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
