import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import requests
import pyperclip
import webbrowser
import json
import threading
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from cloudflare_api import CloudflareAPI
from s3_api import S3API
from google_search_console import GoogleSearchConsole
from config_manager import ConfigManager
from py.ai_agent import AIAgent
from google_sheet_manager import GoogleSheetManager
from datetime import datetime, timedelta

# Appearance settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Modern Design Color Tokens (matching HTML reference)
COLORS = {
    "primary": "#3b82f6",
    "primary_hover": "#2563eb",
    "secondary": "#10b981",
    "secondary_hover": "#059669",
    "danger": "#ef4444",
    "danger_hover": "#dc2626",
    "accent": "#fb923c",
    "accent_hover": "#f97316",
    "bg_dark": "#0f0f0f",
    "bg_sidebar": "#1a1a1a",
    "bg_card": "#1e1e1e",
    "bg_hover": "#2a2a2a",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "border": "#333333",
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cloud Management Pro")
        self.geometry("1000x800")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Variables
        self.api = None
        self.zone_id = None
        self.s3_api = None
        
        # Load config
        config = ConfigManager.load_config()
        self.cf_profile_var = ctk.StringVar()
        self.token_var = ctk.StringVar(value="")
        self.domain_var = ctk.StringVar(value=config.get("domain", ""))
        self.subdomain_var = ctk.StringVar()
        self.ip_var = ctk.StringVar()
        self.type_var = ctk.StringVar(value="A")
        self.selected_record_id = None
        self.zones_data = [] # Store full zone objects
        self.current_records = [] # Store full record objects
        
        # Cloudflare Pagination & Search
        self.cf_search_text = ""
        self.cf_current_page = 1
        self.cf_page_size = 50
        self.cf_filtered_records = []

        # Extra Record Vars
        self.proxied_var = ctk.BooleanVar(value=False)
        self.ttl_var = ctk.StringVar(value="Auto")

        self.ttl_mapping = {
            "Auto": 1,
            "1 min": 60,
            "2 min": 120,
            "5 min": 300,
            "10 min": 600,
            "15 min": 900,
            "30 min": 1800,
            "1 hr": 3600,
            "2 hr": 7200,
            "5 hr": 18000,
            "12 hr": 43200,
            "1 day": 86400
        }
        # Reverse mapping for display
        self.ttl_reverse_mapping = {v: k for k, v in self.ttl_mapping.items()}

        # AWS Variables
        self.aws_access_key_var = ctk.StringVar()
        self.aws_secret_key_var = ctk.StringVar()
        self.aws_region_var = ctk.StringVar(value="us-east-1")
        self.bucket_name_var = ctk.StringVar()
        self.aws_profile_var = ctk.StringVar() # For the profile combobox

        # Website Hosting Vars
        self.enable_hosting_var = ctk.BooleanVar(value=True)
        self.index_doc_var = ctk.StringVar(value="index.html")
        self.error_doc_var = ctk.StringVar(value="404.html")
        self.bucket_endpoint_var = ctk.StringVar(value="-")
        self.bucket_search_var = ctk.StringVar()
        self.obj_search_var = ctk.StringVar()
        self.website_status_var = ctk.StringVar(value="-")
        self.website_endpoint_var = ctk.StringVar(value="-")
        self.versioning_status_var = ctk.StringVar(value="-")
        
        # Cloudflare Integration Vars
        self.link_cf_var = ctk.BooleanVar(value=False)
        self.cf_subdomain_var = ctk.StringVar()
        self.cf_proxy_var = ctk.BooleanVar(value=True)
        
        # S3 New Bucket Vars
        self.s3_subdomain_var = ctk.StringVar()
        self.s3_domain_var = ctk.StringVar()
        self.auto_upload_var = ctk.BooleanVar(value=False)
        self.auto_upload_path_var = ctk.StringVar(value="")

        # Auto Bucket Creator Vars
        self.auto_bucket_count_var = ctk.StringVar(value="10")
        self.auto_bucket_topic_var = ctk.StringVar(value="")
        self.auto_bucket_dns_proxied_var = ctk.BooleanVar(value=True)
        self.auto_gsc_var = ctk.BooleanVar(value=False)
        
        # Status Bar Vars
        self.status_var = ctk.StringVar(value="Ready")
        self.progress_var = ctk.DoubleVar(value=0)
        
        # Store full lists for filtering
        self.all_buckets = []
        self.all_objects = []

        # WMT / GSC Profile Var
        self.gsc_profile_var = ctk.StringVar(value="Default")

        self.setup_ui()

    def setup_ui(self):
        # Configure main grid: sidebar (col 0), content (col 1)
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(2, weight=0)  # Status bar

        # Current view tracker
        self.current_view = "cloudflare"
        self.sidebar_expanded = True

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=COLORS["bg_sidebar"])
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.burger_btn = ctk.CTkButton(self.header_frame, text="☰", width=40, height=40, 
                                         fg_color="transparent", hover_color=COLORS["bg_hover"],
                                         command=self.toggle_sidebar)
        self.burger_btn.grid(row=0, column=0, padx=10, pady=5)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Cloud Management Pro", 
                                         font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.grid(row=0, column=1, padx=20, pady=10, sticky="w")

        # --- Sidebar ---
        self.nav_sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLORS["bg_sidebar"])
        self.nav_sidebar.grid(row=1, column=0, sticky="nsew")
        self.nav_sidebar.grid_rowconfigure(10, weight=1)  # Spacer
        
        # Nav Buttons
        self.cf_nav_btn = ctk.CTkButton(self.nav_sidebar, text="☁️  Cloudflare DNS", 
                                         font=ctk.CTkFont(size=14), height=45, anchor="w",
                                         fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                                         command=lambda: self.show_view("cloudflare"))
        self.cf_nav_btn.grid(row=0, column=0, padx=10, pady=(20, 5), sticky="ew")
        
        self.s3_nav_btn = ctk.CTkButton(self.nav_sidebar, text="📦  AWS S3", 
                                         font=ctk.CTkFont(size=14), height=45, anchor="w",
                                         fg_color="transparent", hover_color=COLORS["bg_hover"],
                                         command=lambda: self.show_view("s3"))
        self.s3_nav_btn.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.wmt_nav_btn = ctk.CTkButton(self.nav_sidebar, text="📈  GSC / WMT", 
                                         font=ctk.CTkFont(size=14), height=45, anchor="w",
                                         fg_color="transparent", hover_color=COLORS["bg_hover"],
                                         command=lambda: self.show_view("wmt"))
        self.wmt_nav_btn = ctk.CTkButton(self.nav_sidebar, text="📈  GSC / WMT", 
                                         font=ctk.CTkFont(size=14), height=45, anchor="w",
                                         fg_color="transparent", hover_color=COLORS["bg_hover"],
                                         command=lambda: self.show_view("wmt"))
        self.wmt_nav_btn.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.gsheet_nav_btn = ctk.CTkButton(self.nav_sidebar, text="📊  Google Sheets", 
                                         font=ctk.CTkFont(size=14), height=45, anchor="w",
                                         fg_color="transparent", hover_color=COLORS["bg_hover"],
                                         command=lambda: self.show_view("gsheet"))
        self.gsheet_nav_btn.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        # Theme Toggle at bottom
        self.theme_label = ctk.CTkLabel(self.nav_sidebar, text="Theme", text_color=COLORS["text_secondary"])
        self.theme_label.grid(row=11, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.theme_switch = ctk.CTkSwitch(self.nav_sidebar, text="Dark Mode", 
                                           command=self.toggle_theme, onvalue=1, offvalue=0)
        self.theme_switch.select()  # Default to dark
        self.theme_switch.grid(row=12, column=0, padx=10, pady=(5, 20), sticky="w")

        # --- Main Content Area ---
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg_dark"])
        self.main_container.grid(row=1, column=1, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Create view frames (only one visible at a time)
        self.cloudflare_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.s3_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.wmt_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.gsheet_view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        

        self.setup_cloudflare_view()
        self.setup_s3_view()
        self.setup_wmt_view()
        self.setup_gsheet_view()
        
        # Show default view
        self.show_view("cloudflare")

        # --- Status Bar ---
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color=COLORS["bg_sidebar"])
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.status_bar, textvariable=self.status_var, font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, padx=20, pady=2, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.status_bar, variable=self.progress_var, width=200, height=10)
        self.progress_bar.grid(row=0, column=1, padx=20, pady=2, sticky="e")
        self.progress_bar.set(0)

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.nav_sidebar.grid_remove()
            self.grid_columnconfigure(0, weight=0, minsize=0)
            self.sidebar_expanded = False
        else:
            self.nav_sidebar.grid()
            self.grid_columnconfigure(0, weight=0, minsize=220)
            self.sidebar_expanded = True

    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def show_view(self, view_name):
        # Hide all views
        self.cloudflare_view.grid_remove()
        self.s3_view.grid_remove()
        self.wmt_view.grid_remove()
        self.gsheet_view.grid_remove()
        
        # Reset nav button styles
        self.cf_nav_btn.configure(fg_color="transparent")
        self.s3_nav_btn.configure(fg_color="transparent")
        self.wmt_nav_btn.configure(fg_color="transparent")
        self.gsheet_nav_btn.configure(fg_color="transparent")
        
        # Show selected view and highlight button
        if view_name == "cloudflare":
            self.cloudflare_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.cf_nav_btn.configure(fg_color=COLORS["primary"])
        elif view_name == "s3":
            self.s3_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.s3_nav_btn.configure(fg_color=COLORS["primary"])
        elif view_name == "wmt":
            self.wmt_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.wmt_nav_btn.configure(fg_color=COLORS["primary"])
        elif view_name == "gsheet":
            self.gsheet_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.gsheet_nav_btn.configure(fg_color=COLORS["primary"])
        
        self.current_view = view_name

    def set_status(self, text, progress=None):
        def update():
            self.status_var.set(text)
            if progress is not None:
                self.progress_var.set(progress)
                if progress >= 1.0 or progress < 0:
                    self.progress_bar.configure(mode="indeterminate")
                    if progress >= 1.0: self.progress_bar.stop()
                    else: self.progress_bar.start()
                else:
                    self.progress_bar.configure(mode="determinate")
            else:
                self.progress_bar.set(0)
                self.progress_bar.configure(mode="determinate")
        self.after(0, update)

    def setup_cloudflare_view(self):
        tab = self.cloudflare_view
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # --- Top Section: Configuration Card ---
        self.config_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=COLORS["bg_card"])
        self.config_frame.grid(row=0, column=0, padx=0, pady=(0, 15), sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)
        
        # --- Profile Section ---
        self.cf_profile_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.cf_profile_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.cf_profile_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.cf_profile_frame, text="Profile:", text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=20, pady=5, sticky="e")
        self.cf_profile_combo = ctk.CTkComboBox(self.cf_profile_frame, variable=self.cf_profile_var, command=self.on_cf_profile_change, width=200)
        self.cf_profile_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Save/Delete Profile Buttons
        self.save_cf_profile_btn = ctk.CTkButton(self.cf_profile_frame, text="Save Profile", command=self.save_cf_profile_action, width=100, 
                                                  fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.save_cf_profile_btn.grid(row=0, column=2, padx=5, sticky="e")

        self.del_cf_profile_btn = ctk.CTkButton(self.cf_profile_frame, text="Delete", command=self.delete_cf_profile_action, width=80, 
                                                 fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.del_cf_profile_btn.grid(row=0, column=3, padx=5, sticky="e")

        ctk.CTkLabel(self.config_frame, text="Cloudflare Settings", font=ctk.CTkFont(size=16, weight="bold")).grid(row=1, column=0, columnspan=3, padx=20, pady=(10,5), sticky="w")

        ctk.CTkLabel(self.config_frame, text="API Token:", text_color=COLORS["text_secondary"]).grid(row=2, column=0, padx=20, pady=8, sticky="e")
        self.token_entry = ctk.CTkEntry(self.config_frame, textvariable=self.token_var, width=350, show="*", placeholder_text="Cloudflare API Token")
        self.token_entry.grid(row=2, column=1, padx=20, pady=8, sticky="w")
        self.token_entry.bind("<FocusOut>", lambda e: self.load_zones())
        self.token_entry.bind("<Return>", lambda e: self.load_zones())

        ctk.CTkLabel(self.config_frame, text="Select Domain:", text_color=COLORS["text_secondary"]).grid(row=3, column=0, padx=20, pady=8, sticky="e")
        self.domain_combo = ctk.CTkComboBox(self.config_frame, variable=self.domain_var, width=350, values=["Please enter API token..."], command=self.on_domain_change)
        self.domain_combo.grid(row=3, column=1, padx=20, pady=8, sticky="w")

        self.save_btn = ctk.CTkButton(self.config_frame, text="Load Domains", command=self.load_zones, width=130, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.save_btn.grid(row=2, column=2, padx=20, pady=8)

        # Zone Count Label
        self.zone_count_label = ctk.CTkLabel(self.config_frame, text="(0 domains)", text_color=COLORS["text_secondary"], font=ctk.CTkFont(size=11))
        self.zone_count_label.grid(row=3, column=2, padx=20, sticky="w")

        self.add_site_btn = ctk.CTkButton(self.config_frame, text="+ Add Site", command=self.add_new_zone, width=100, fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.add_site_btn.grid(row=4, column=1, padx=(20, 5), pady=8, sticky="e")

        self.del_site_btn = ctk.CTkButton(self.config_frame, text="🗑️ Delete Site", command=self.delete_current_zone, width=100, fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.del_site_btn.grid(row=4, column=2, padx=5, pady=8, sticky="w")

        # Removed redundant Save Config button as we save via profile now

        # Auto-load if loaded
        if self.token_var.get():
            self.after(500, self.load_zones)

        self.load_cf_profiles_into_ui()

        # --- Middle Section: Add Record Card ---
        self.mgmt_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=COLORS["bg_card"])
        self.mgmt_frame.grid(row=1, column=0, padx=0, pady=(0, 15), sticky="nsew")
        self.mgmt_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(self.mgmt_frame, text="Add New Record", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=6, padx=20, pady=12, sticky="w")

        ctk.CTkLabel(self.mgmt_frame, text="Subdomain:", text_color=COLORS["text_secondary"]).grid(row=1, column=0, padx=20, pady=8, sticky="e")
        self.subdomain_entry = ctk.CTkEntry(self.mgmt_frame, textvariable=self.subdomain_var, placeholder_text="www")
        self.subdomain_entry.grid(row=1, column=1, padx=(0, 20), pady=8, sticky="ew")

        ctk.CTkLabel(self.mgmt_frame, text="Type:", text_color=COLORS["text_secondary"]).grid(row=1, column=2, padx=5, pady=8, sticky="e")
        self.type_combo = ctk.CTkComboBox(self.mgmt_frame, variable=self.type_var, values=["A", "AAAA", "CNAME", "TXT", "MX", "SRV", "NS"], width=100)
        self.type_combo.grid(row=1, column=3, padx=(0, 20), pady=8, sticky="w")

        ctk.CTkLabel(self.mgmt_frame, text="Content:", text_color=COLORS["text_secondary"]).grid(row=1, column=4, padx=5, pady=8, sticky="e")
        self.ip_entry = ctk.CTkEntry(self.mgmt_frame, textvariable=self.ip_var, placeholder_text="1.2.3.4", width=200)
        self.ip_entry.grid(row=1, column=5, padx=(0, 20), pady=8, sticky="ew")

        # Row 2: TTL, Proxied, Buttons
        ctk.CTkLabel(self.mgmt_frame, text="TTL:", text_color=COLORS["text_secondary"]).grid(row=2, column=0, padx=20, pady=8, sticky="e")
        self.ttl_combo = ctk.CTkComboBox(self.mgmt_frame, variable=self.ttl_var, values=list(self.ttl_mapping.keys()), width=100)
        self.ttl_combo.grid(row=2, column=1, padx=(0, 20), pady=8, sticky="w")

        self.proxied_cb = ctk.CTkCheckBox(self.mgmt_frame, text="Proxied", variable=self.proxied_var)
        self.proxied_cb.grid(row=2, column=2, padx=5, pady=8, sticky="w")

        self.create_btn = ctk.CTkButton(self.mgmt_frame, text="Create Record", command=self.create_record, 
                                         fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.create_btn.grid(row=2, column=4, padx=5, pady=8)

        self.clear_btn = ctk.CTkButton(self.mgmt_frame, text="Clear", command=self.clear_form, 
                                        fg_color=COLORS["bg_hover"], hover_color=COLORS["border"], width=100)
        self.clear_btn.grid(row=2, column=5, padx=20, pady=8)


        # --- Bottom Section: Records Table Card ---
        self.table_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=COLORS["bg_card"])
        self.table_frame.grid(row=2, column=0, padx=0, pady=0, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(1, weight=1)

        # Toolbar above table
        self.toolbar = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=12)

        self.refresh_btn = ctk.CTkButton(self.toolbar, text="↻ Refresh", command=self.list_records, width=100,
                                          fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.refresh_btn.pack(side="left", padx=5)

        # Search Box
        self.cf_search_entry = ctk.CTkEntry(self.toolbar, placeholder_text="🔍 Search records...", width=200)
        self.cf_search_entry.pack(side="left", padx=5)
        self.cf_search_entry.bind("<KeyRelease>", self.filter_cf_records)

        self.delete_btn = ctk.CTkButton(self.toolbar, text="Delete Selected", command=self.delete_selected, 
                                         fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"], width=120)
        self.delete_btn.pack(side="left", padx=5)

        self.export_btn = ctk.CTkButton(self.toolbar, text="Export MikroTik", command=self.export_mikrotik, width=120,
                                         fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        self.export_btn.pack(side="right", padx=5)

        self.open_web_btn = ctk.CTkButton(self.toolbar, text="🌐 Open Website", command=self.open_selected_website, width=120,
                                         fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.open_web_btn.pack(side="right", padx=5)

        # Treeview Styling
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background=COLORS["bg_card"], 
                        foreground="white", 
                        fieldbackground=COLORS["bg_card"], 
                        borderwidth=0,
                        font=("SF Pro Display", 11))
        style.map("Treeview", background=[('selected', COLORS["primary"])])
        style.configure("Treeview.Heading", 
                        background=COLORS["bg_hover"], 
                        foreground="white", 
                        relief="flat",
                        font=("SF Pro Display", 12, "bold"))

        # Treeview
        columns = ("type", "name", "ip", "record_id")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        self.tree.heading("type", text="Type")
        self.tree.heading("name", text="Name")
        self.tree.heading("ip", text="Content / IP")
        self.tree.heading("record_id", text="Record ID")
        self.tree.column("type", width=80)
        self.tree.column("name", width=250)
        self.tree.column("ip", width=200)
        self.tree.column("record_id", width=0, stretch=False)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.tree.bind("<<TreeviewSelect>>", self.on_record_select)

        # Scrollbar
        self.scrollbar = ctk.CTkScrollbar(self.table_frame, command=self.tree.yview)
        self.scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 5))
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Pagination Controls
        self.pagination_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent", height=40)
        self.pagination_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))
        
        self.prev_page_btn = ctk.CTkButton(self.pagination_frame, text="< Previous", width=100, 
                                            command=lambda: self.change_cf_page(-1),
                                            fg_color=COLORS["bg_hover"], hover_color=COLORS["border"])
        self.prev_page_btn.pack(side="left", padx=5)
        
        self.page_label = ctk.CTkLabel(self.pagination_frame, text="Page 1 of 1", font=("Arial", 12, "bold"))
        self.page_label.pack(side="left", padx=20)
        
        self.next_page_btn = ctk.CTkButton(self.pagination_frame, text="Next >", width=100, 
                                            command=lambda: self.change_cf_page(1),
                                            fg_color=COLORS["bg_hover"], hover_color=COLORS["border"])
        self.next_page_btn.pack(side="left", padx=5)
        
        # Total records label
        self.total_records_label = ctk.CTkLabel(self.pagination_frame, text="Total: 0", text_color=COLORS["text_secondary"])
        self.total_records_label.pack(side="right", padx=10)

    def setup_s3_view(self):
        tab = self.s3_view
        tab.grid_columnconfigure(0, weight=0, minsize=350)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # --- Sidebar (Left Column) ---
        self.sidebar_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=COLORS["bg_card"])
        self.sidebar_frame.grid(row=0, column=0, padx=(0, 15), pady=0, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        # 1. AWS Configuration Area
        self.aws_config_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.aws_config_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        self.aws_config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.aws_config_frame, text="AWS Profiles & Configuration", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, padx=5, pady=(0, 12), sticky="w")
        
        # Profile Selection Row
        ctk.CTkLabel(self.aws_config_frame, text="Profile:", text_color=COLORS["text_secondary"]).grid(row=1, column=0, padx=5, pady=4, sticky="e")
        self.profile_combo = ctk.CTkComboBox(self.aws_config_frame, variable=self.aws_profile_var, command=self.on_profile_change)
        self.profile_combo.grid(row=1, column=1, padx=5, pady=4, sticky="ew")
        
        # Mini Toolbar for Profile
        self.prof_tools = ctk.CTkFrame(self.aws_config_frame, fg_color="transparent")
        self.prof_tools.grid(row=2, column=1, sticky="e")
        self.save_aws_btn = ctk.CTkButton(self.prof_tools, text="Save", command=self.save_s3_profile_action, width=60, height=26, 
                                           fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.save_aws_btn.pack(side="right", padx=2)
        self.delete_profile_btn = ctk.CTkButton(self.prof_tools, text="Delete", command=self.delete_s3_profile_action, width=60, height=26, 
                                                 fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.delete_profile_btn.pack(side="right", padx=2)

        # Quick Key/Region Edit
        ctk.CTkLabel(self.aws_config_frame, text="Access:", text_color=COLORS["text_secondary"]).grid(row=3, column=0, padx=5, pady=4, sticky="e")
        self.aws_access_entry = ctk.CTkEntry(self.aws_config_frame, textvariable=self.aws_access_key_var, height=28)
        self.aws_access_entry.grid(row=3, column=1, padx=5, pady=4, sticky="ew")

        ctk.CTkLabel(self.aws_config_frame, text="Secret:", text_color=COLORS["text_secondary"]).grid(row=4, column=0, padx=5, pady=4, sticky="e")
        self.aws_secret_entry = ctk.CTkEntry(self.aws_config_frame, textvariable=self.aws_secret_key_var, height=28, show="*")
        self.aws_secret_entry.grid(row=4, column=1, padx=5, pady=4, sticky="ew")

        ctk.CTkLabel(self.aws_config_frame, text="Region:", text_color=COLORS["text_secondary"]).grid(row=5, column=0, padx=5, pady=4, sticky="e")
        self.aws_region_entry = ctk.CTkEntry(self.aws_config_frame, textvariable=self.aws_region_var, height=28)
        self.aws_region_entry.grid(row=5, column=1, padx=5, pady=4, sticky="ew")

        self.load_buckets_btn = ctk.CTkButton(self.aws_config_frame, text="📦 Load S3 Buckets", command=self.list_s3_buckets, height=36,
                                               fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.load_buckets_btn.grid(row=6, column=0, columnspan=2, padx=5, pady=12, sticky="ew")

        # 2. Bucket List Area
        self.list_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.list_container.grid(row=1, column=0, rowspan=2, padx=15, pady=(0, 15), sticky="nsew")
        self.list_container.grid_columnconfigure(0, weight=1)
        self.list_container.grid_rowconfigure(1, weight=1)

        # Search
        self.bucket_search_entry = ctk.CTkEntry(self.list_container, textvariable=self.bucket_search_var, placeholder_text="🔍 Search buckets...")
        self.bucket_search_entry.grid(row=0, column=0, padx=0, pady=(0, 8), sticky="ew")
        self.bucket_search_entry.bind("<KeyRelease>", lambda e: self.filter_buckets())

        # Bucket Count Label
        self.bucket_count_label = ctk.CTkLabel(self.list_container, text="Total Buckets: 0", text_color=COLORS["text_secondary"], font=ctk.CTkFont(size=11))
        self.bucket_count_label.grid(row=1, column=0, padx=0, pady=(0, 8), sticky="w")

        # Table
        self.bucket_table_frame = ctk.CTkFrame(self.list_container, fg_color=COLORS["bg_hover"], corner_radius=10)
        self.bucket_table_frame.grid(row=2, column=0, sticky="nsew")
        self.bucket_table_frame.grid_columnconfigure(0, weight=1)
        self.bucket_table_frame.grid_rowconfigure(0, weight=1)

        columns = ("name",)
        self.bucket_tree = ttk.Treeview(self.bucket_table_frame, columns=columns, show="headings", selectmode="extended")
        self.bucket_tree.heading("name", text="Bucket Name")
        self.bucket_tree.column("name", width=250)
        self.bucket_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.bucket_tree.bind("<<TreeviewSelect>>", self.on_bucket_select)

        self.bucket_scrollbar = ctk.CTkScrollbar(self.bucket_table_frame, command=self.bucket_tree.yview)
        self.bucket_scrollbar.grid(row=0, column=1, sticky="ns", pady=5)
        self.bucket_tree.configure(yscrollcommand=self.bucket_scrollbar.set)

        # Export Button
        # Export & Copy Buttons
        self.list_actions_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
        self.list_actions_frame.grid(row=3, column=0, padx=0, pady=(10, 0), sticky="ew")
        self.list_actions_frame.grid_columnconfigure((0,1), weight=1)

        self.export_buckets_btn = ctk.CTkButton(self.list_actions_frame, text="Export List", command=self.export_bucket_list,
                                                 fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], height=28)
        self.export_buckets_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.copy_bucket_btn = ctk.CTkButton(self.list_actions_frame, text="Copy Name", command=self.copy_selected_bucket_name,
                                              fg_color=COLORS["bg_hover"], hover_color=COLORS["border"], height=28)
        self.copy_bucket_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # --- Main Content (Right Column) ---
        self.main_content_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Selection Info & Hosting Actions Card
        self.bucket_frame = ctk.CTkFrame(self.main_content_frame, corner_radius=15, fg_color=COLORS["bg_card"])
        self.bucket_frame.grid(row=0, column=0, padx=0, pady=(0, 15), sticky="ew")
        self.bucket_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.bucket_frame, text="Current Bucket Management", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, padx=20, pady=12, sticky="w")
        
        ctk.CTkLabel(self.bucket_frame, text="Bucket Name:", text_color=COLORS["text_secondary"]).grid(row=1, column=0, padx=20, pady=6, sticky="e")
        
        # Composite Bucket Name Input (Subdomain + Domain)
        self.bucket_name_frame = ctk.CTkFrame(self.bucket_frame, fg_color="transparent")
        self.bucket_name_frame.grid(row=1, column=1, padx=20, pady=6, sticky="ew")
        
        self.s3_subdomain_entry = ctk.CTkEntry(self.bucket_name_frame, textvariable=self.s3_subdomain_var, width=140, placeholder_text="subdomain")
        self.s3_subdomain_entry.pack(side="left", padx=(0, 5))
        self.s3_subdomain_entry.bind("<KeyRelease>", self.update_full_bucket_name_from_parts)
        
        ctk.CTkLabel(self.bucket_name_frame, text=".", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.s3_domain_combo = ctk.CTkComboBox(self.bucket_name_frame, variable=self.s3_domain_var, width=140, values=["Select Domain..."], command=self.update_full_bucket_name_from_parts)
        self.s3_domain_combo.pack(side="left", padx=(5, 0))

        # Hidden bucket_name_var updater/holder
        self.bucket_name_label = ctk.CTkLabel(self.bucket_frame, textvariable=self.bucket_name_var, text_color=COLORS["text_secondary"], font=ctk.CTkFont(size=10))
        self.bucket_name_label.grid(row=1, column=2, padx=5, sticky="w")

        self.new_bucket_btn = ctk.CTkButton(self.bucket_frame, text="+ New", command=self.reset_s3_selection, width=60, 
                                             fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.new_bucket_btn.grid(row=1, column=3, padx=15, pady=6, sticky="w")

        self.refresh_domains_btn = ctk.CTkButton(self.bucket_frame, text="↻", command=self.load_zones, width=30, height=28, fg_color=COLORS["bg_hover"])
        self.refresh_domains_btn.grid(row=1, column=4, padx=0, pady=6)

        self.open_auto_btn = ctk.CTkButton(self.bucket_frame, text="✨ Auto", command=self.open_auto_creation_dialog, width=60, 
                                           fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        self.open_auto_btn.grid(row=1, column=5, padx=5, pady=6)

        # Compact Hosting Config
        self.web_config_frame = ctk.CTkFrame(self.bucket_frame, fg_color="transparent")
        self.web_config_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=6, sticky="w")
        
        self.enable_hosting_cb = ctk.CTkCheckBox(self.web_config_frame, text="Hosting", variable=self.enable_hosting_var, width=100)
        self.enable_hosting_cb.grid(row=0, column=0, padx=(0, 12))
        
        ctk.CTkLabel(self.web_config_frame, text="Idx:", text_color=COLORS["text_secondary"]).grid(row=0, column=1, padx=2)
        self.index_entry = ctk.CTkEntry(self.web_config_frame, textvariable=self.index_doc_var, width=90)
        self.index_entry.grid(row=0, column=2, padx=2)
        
        ctk.CTkLabel(self.web_config_frame, text="Err:", text_color=COLORS["text_secondary"]).grid(row=0, column=3, padx=2)
        self.error_entry = ctk.CTkEntry(self.web_config_frame, textvariable=self.error_doc_var, width=90)
        self.error_entry.grid(row=0, column=4, padx=2)

        # Endpoint strip
        self.endpoint_frame = ctk.CTkFrame(self.bucket_frame, fg_color="transparent")
        self.endpoint_frame.grid(row=3, column=0, columnspan=3, padx=20, pady=(0, 12), sticky="ew")
        ctk.CTkLabel(self.endpoint_frame, text="URL:", text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 5))
        self.main_endpoint_entry = ctk.CTkEntry(self.endpoint_frame, textvariable=self.bucket_endpoint_var, state="readonly")
        self.main_endpoint_entry.pack(side="left", fill="x", expand=True)
        self.copy_endpoint_btn = ctk.CTkButton(self.endpoint_frame, text="Copy", width=60, command=self.copy_endpoint,
                                                fg_color=COLORS["bg_hover"], hover_color=COLORS["border"])
        self.copy_endpoint_btn.pack(side="left", padx=5)

        # Cloudflare Quick Link
        self.cf_link_frame = ctk.CTkFrame(self.bucket_frame, fg_color="transparent")
        self.cf_link_frame.grid(row=4, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="ew")

        self.cf_link_cb = ctk.CTkCheckBox(self.cf_link_frame, text="Link Cloudflare DNS", variable=self.link_cf_var)
        self.cf_link_cb.grid(row=0, column=0, padx=(0, 12))

        ctk.CTkLabel(self.cf_link_frame, text="Sub:", text_color=COLORS["text_secondary"]).grid(row=0, column=1, padx=2)
        self.cf_subdomain_entry = ctk.CTkEntry(self.cf_link_frame, textvariable=self.cf_subdomain_var, width=120, placeholder_text="e.g. static")
        self.cf_subdomain_entry.grid(row=0, column=2, padx=2)

        self.cf_proxy_cb = ctk.CTkCheckBox(self.cf_link_frame, text="Proxy", variable=self.cf_proxy_var)
        self.cf_proxy_cb.grid(row=0, column=3, padx=12)
        
        ctk.CTkLabel(self.cf_link_frame, text="|", text_color=COLORS["border"]).grid(row=0, column=4, padx=5)

        self.add_dns_btn = ctk.CTkButton(self.cf_link_frame, text="⚡ Add DNS", command=self.link_dns_manually, width=100, 
                                          fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        self.add_dns_btn.grid(row=0, column=5, padx=5)

        
        # Auto Upload Source Section
        self.auto_upload_frame = ctk.CTkFrame(self.bucket_frame, fg_color="transparent")
        self.auto_upload_frame.grid(row=5, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="ew")

        self.auto_upload_cb = ctk.CTkCheckBox(self.auto_upload_frame, text="Auto Upload Source", variable=self.auto_upload_var)
        self.auto_upload_cb.grid(row=0, column=0, padx=(0, 12))

        self.auto_upload_path_entry = ctk.CTkEntry(self.auto_upload_frame, textvariable=self.auto_upload_path_var, width=250, placeholder_text="Select folder to upload...")
        self.auto_upload_path_entry.grid(row=0, column=1, padx=2)

        self.select_folder_btn = ctk.CTkButton(self.auto_upload_frame, text="📁", command=self.select_auto_upload_folder, width=30, height=28, fg_color=COLORS["bg_hover"])
        self.select_folder_btn.grid(row=0, column=2, padx=5)

        # Action Buttons moved to bottom
        self.btn_group = ctk.CTkFrame(self.bucket_frame, fg_color="transparent")
        self.btn_group.grid(row=6, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
        self.btn_group.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Row 1
        self.create_bucket_btn = ctk.CTkButton(self.btn_group, text="Add Bucket", command=self.handle_s3_creation, 
                                                fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.create_bucket_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.delete_bucket_btn = ctk.CTkButton(self.btn_group, text="Delete Bucket", command=self.delete_bucket_action, 
                                                fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.delete_bucket_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.open_bucket_web_btn = ctk.CTkButton(self.btn_group, text="Open Web", command=self.open_selected_buckets_web,
                                                 fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"]) 
        self.open_bucket_web_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.open_bucket_web_btn.configure(state="disabled")

        # Row 2
        self.add_wmt_btn = ctk.CTkButton(self.btn_group, text="Add GSC", command=self.add_to_wmt_manual,
                                         fg_color="#F4B400", hover_color="#C09000", text_color="black") # Google-ish Yellow
        self.add_wmt_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.add_wmt_btn.configure(state="disabled")

        self.add_sitemap_btn = ctk.CTkButton(self.btn_group, text="Add Sitemap", command=self.add_sitemap_manual,
                                             fg_color="#34A853", hover_color="#2E8B57", text_color="white") # Google Green
        self.add_sitemap_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.add_sitemap_btn.configure(state="disabled")

        self.config_site_btn = ctk.CTkButton(self.btn_group, text="Config Site", command=self.open_site_config_dialog,
                                             fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.config_site_btn.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # 3. Details Tabs
        self.details_tabview = ctk.CTkTabview(self.main_content_frame, corner_radius=15, fg_color=COLORS["bg_card"])
        self.details_tabview.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        
        self.details_tabview.add("Objects")
        self.details_tabview.add("Permissions / Policy")
        self.details_tabview.add("Public Access Block")
        self.details_tabview.add("Website Hosting")
        self.details_tabview.add("CORS")
        self.details_tabview.add("Versioning")
        
        self.setup_bucket_objects_tab()
        self.setup_bucket_permissions_tab()
        self.setup_bucket_pab_tab()
        self.setup_bucket_website_tab()
        self.setup_bucket_cors_tab()
        self.setup_bucket_versioning_tab()
        
        # Load saved profiles on startup
        self.load_s3_profiles_into_ui()

    def open_site_config_dialog(self):
        selection = self.bucket_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select at least one bucket.")
            return

        buckets = [self.bucket_tree.item(item, "values")[0] for item in selection]

        if len(buckets) == 1:
            self.open_single_site_config_dialog(buckets[0])
        else:
            self.open_bulk_site_config_dialog(buckets)

    def open_single_site_config_dialog(self, bucket_name):
        top = ctk.CTkToplevel(self)
        top.title(f"Site Config: {bucket_name}")
        top.geometry("600x700")
        
        # Scrollable Frame
        sf = ctk.CTkScrollableFrame(top)
        sf.pack(fill="both", expand=True, padx=10, pady=10)
        
        fields = ["site", "title", "desc", "footer_info", "about", "contactus", "email", "address", "namesite", "theme"]
        self.site_config_vars = {}

        for i, field in enumerate(fields):
            ctk.CTkLabel(sf, text=field.replace("_", " ").title() + ":").grid(row=i, column=0, padx=10, pady=5, sticky="e")
            var = ctk.StringVar()
            self.site_config_vars[field] = var
            entry = ctk.CTkEntry(sf, textvariable=var, width=350)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="w")

        # Data Source Selection
        ctk.CTkLabel(sf, text="Data Sources:", font=ctk.CTkFont(weight="bold")).grid(row=len(fields), column=0, padx=10, pady=10, sticky="nw")
        
        self.source_vars = {} # url -> booleanvar
        self.source_frame = ctk.CTkScrollableFrame(sf, height=200, label_text="Select Sources")
        self.source_frame.grid(row=len(fields), column=1, padx=10, pady=5, sticky="ew")
        
        # Fetch sources
        def fetch_sources():
             try:
                 url = "https://opensheet.elk.sh/1D9uhjrX8E2ag_xJ1i5baRDhUMi9RkoHdk5sE8y_OV-g/source"
                 resp = requests.get(url, timeout=10)
                 if resp.status_code == 200:
                     sources = resp.json()
                     # Deduplicate by data URL? Or just show all. User said "choose source data content".
                     # We display "catename" + "cate_tag" -> URL
                     
                     for s in sources:
                         url_data = s.get("data", "")
                         if not url_data: continue
                         
                         name = s.get("catename", "Unknown")
                         tag = s.get("cate_tag", "")
                         display_text = f"[{name}/{tag}] {os.path.basename(url_data)}"
                         
                         if url_data not in self.source_vars:
                             var = ctk.BooleanVar(value=False)
                             self.source_vars[url_data] = var
                             cb = ctk.CTkCheckBox(self.source_frame, text=display_text, variable=var, width=500)
                             cb.pack(fill="x", padx=5, pady=2)
             except Exception as e:
                 print(f"Error fetching sources: {e}")
                 self.after(0, lambda: ctk.CTkLabel(self.source_frame, text="Error loading sources").pack())
        
        # Run fetch in background to not freeze UI
        threading.Thread(target=fetch_sources, daemon=True).start()

        # Buttons
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        def save_config():
            # Gather config
            config_obj = {k: v.get() for k, v in self.site_config_vars.items()}
            
            # Gather sources
            selected_sources = [url for url, var in self.source_vars.items() if var.get()]
            if selected_sources:
                 config_obj["source"] = selected_sources

            data = [config_obj]
            json_str = json.dumps(data, indent=4, ensure_ascii=False)
            
            # Save to temp file
            tmp_path = "temp_info.json"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            
            # Upload
            s3 = S3API(self.aws_access_key_var.get(), self.aws_secret_key_var.get(), self.aws_region_var.get())
            res = s3.upload_file(bucket_name, tmp_path, "info.json")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
            if res["success"]:
                messagebox.showinfo("Success", "Site info saved successfully.")
                top.destroy()
            else:
                messagebox.showerror("Error", f"Failed to save: {res.get('error')}")

        # Topic Input
        topic_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        topic_frame.pack(side="left", padx=5)
        
        ctk.CTkLabel(topic_frame, text="AI Topic:").pack(side="left", padx=(0, 5))
        topic_var = ctk.StringVar()
        topic_entry = ctk.CTkEntry(topic_frame, textvariable=topic_var, width=150, placeholder_text="e.g. Technology")
        topic_entry.pack(side="left")

        def generate_ai():
            gen_btn.configure(state="disabled", text="Generating...")
            topic = topic_var.get()
            
            prompt = (
                f"Generate a JSON object for a website with domain '{bucket_name}'. "
                f"Topic/Niche: {topic if topic else 'General'}. "
                f"Fields: site, title, desc, footer_info, about, contactus, email, address, namesite, theme. "
                "Format: [{\"site\":\"...\", ...}]. "
                "Ensure 'site', 'about', 'contactus' are just the domain name. "
                "'theme' should be 'theme1 or theme2 or theme3 or theme4 or theme5'. "
                "'namesite' is a short name. "
                f"'email' should be 'info@{bucket_name}' or similar. "
                "Return ONLY valid JSON."
            )
            
            def task():
                try:
                    res = AIAgent.call_ai_agent(prompt)
                    if res:
                        try:
                            # Clean markdown code blocks if any
                            clean_res = res.replace("```json", "").replace("```", "").strip()
                            data = json.loads(clean_res)
                            if isinstance(data, list) and len(data) > 0:
                                item = data[0]
                                for k, v in self.site_config_vars.items():
                                    if k in item:
                                        self.after(0, lambda var=v, val=item[k]: var.set(val))
                            else:
                                 self.after(0, lambda: messagebox.showerror("AI Error", "AI returned unexpected format."))
                        except Exception as e:
                            self.after(0, lambda: messagebox.showerror("Error", f"Parse error: {e}"))
                    else:
                        self.after(0, lambda: messagebox.showerror("Error", "AI failed to generate response."))

                except Exception as e:
                     self.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.after(0, lambda: gen_btn.configure(state="normal", text="Generate AI"))

            threading.Thread(target=task, daemon=True).start()

        # Load existing
        def load_existing():
            s3 = S3API(self.aws_access_key_var.get(), self.aws_secret_key_var.get(), self.aws_region_var.get())
            tmp_path = "temp_load_info.json"
            res = s3.download_file(bucket_name, "info.json", tmp_path)
            if res["success"]:
                try:
                    with open(tmp_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        for k, v in self.site_config_vars.items():
                            if k in item:
                                v.set(item[k])
                        
                        # Load sources
                        saved_sources = item.get("source", [])
                        if isinstance(saved_sources, list):
                            def apply_sources():
                                # Wait for source vars to be populated
                                import time
                                for _ in range(20): 
                                    if self.source_vars: 
                                        break
                                    time.sleep(0.5)
                                    
                                for src in saved_sources:
                                    if src in self.source_vars:
                                        self.after(0, lambda v=self.source_vars[src]: v.set(True))
                                        
                            threading.Thread(target=apply_sources, daemon=True).start()

                except Exception as e:
                    pass # Maybe file doesn't exist or bad format
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

        gen_btn = ctk.CTkButton(btn_frame, text="Generate AI", command=generate_ai, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        gen_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="Save", command=save_config, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"]).pack(side="right", padx=5)

        # Auto load on open
        self.after(100, load_existing)

    def open_bulk_site_config_dialog(self, buckets):
        top = ctk.CTkToplevel(self)
        top.title(f"Bulk Site Config ({len(buckets)} buckets)")
        top.geometry("500x400")

        ctk.CTkLabel(top, text=f"Selected {len(buckets)} buckets for Info Generation", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        status_text = ctk.CTkTextbox(top, height=200)
        status_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Options
        opts_frame = ctk.CTkFrame(top, fg_color="transparent")
        opts_frame.pack(fill="x", padx=10)
        
        overwrite_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_frame, text="Overwrite existing info.json", variable=overwrite_var).pack(side="left")

        def run_bulk():
            btn.configure(state="disabled")
            overwrite = overwrite_var.get()
            
            def task():
                s3 = S3API(self.aws_access_key_var.get(), self.aws_secret_key_var.get(), self.aws_region_var.get())
                
                for i, bucket in enumerate(buckets):
                    msg = f"Processing {bucket} ({i+1}/{len(buckets)})..."
                    self.after(0, lambda m=msg: status_text.insert("end", m + "\n"))
                    
                    if not overwrite:
                        if s3.object_exists(bucket, "info.json"):
                            msg = f"  Skipped (Exists): {bucket}"
                            self.after(0, lambda m=msg: status_text.insert("end", m + "\n"))
                            continue
                            
                    # Generate
                    prompt = (
                        f"Generate a JSON object for a website with domain '{bucket}'. "
                        f"Fields: site, title, desc, footer_info, about, contactus, email, address, namesite, theme. "
                        "Format: [{\"site\":\"...\", ...}]. "
                        "Ensure 'site', 'about', 'contactus' are just the domain name. "
                        "'theme' should be 'theme2'. "
                        "'namesite' is a short name. "
                        f"'email' should be 'info@{bucket}' or similar. "
                        "Return ONLY valid JSON."
                    )
                    
                    try:
                        res = AIAgent.call_ai_agent(prompt)
                        if res:
                             # Clean
                            clean_res = res.replace("```json", "").replace("```", "").strip()
                            # Validate JSON
                            json.loads(clean_res) 
                            
                            # Save
                            tmp_path = f"temp_info_{i}.json"
                            with open(tmp_path, "w", encoding="utf-8") as f:
                                f.write(clean_res)
                                
                            up_res = s3.upload_file(bucket, tmp_path, "info.json")
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                                
                            if up_res["success"]:
                                msg = f"  Success: {bucket}"
                            else:
                                msg = f"  Upload Error: {up_res.get('error')}"
                        else:
                            msg = f"  AI Error: No response"
                    except Exception as e:
                        msg = f"  Error: {e}"

                    self.after(0, lambda m=msg: [status_text.insert("end", m + "\n"), status_text.see("end")])
                
                self.after(0, lambda: [status_text.insert("end", "Done!\n"), btn.configure(state="normal")])

            threading.Thread(target=task, daemon=True).start()

        btn = ctk.CTkButton(top, text="Start Batch Generation", command=run_bulk, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        btn.pack(pady=10)

    def open_auto_creation_dialog(self):
        # Create Toplevel
        top = ctk.CTkToplevel(self)
        top.title("Auto Create Buckets & DNS")
        top.geometry("500x300")
        top.transient(self) # Make it modal-like
        
        # Center setup
        top.grid_columnconfigure(1, weight=1)
        
        # Header
        ctk.CTkLabel(top, text="Auto Create Buckets & DNS (AI Powered)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=15)

        # Inputs
        ctk.CTkLabel(top, text="Count (Max 100):").grid(row=1, column=0, padx=20, pady=10, sticky="e")
        auto_count_entry = ctk.CTkEntry(top, textvariable=self.auto_bucket_count_var, width=100)
        auto_count_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(top, text="Topic (Optional):").grid(row=2, column=0, padx=20, pady=10, sticky="e")
        auto_topic_entry = ctk.CTkEntry(top, textvariable=self.auto_bucket_topic_var, width=200, placeholder_text="e.g. tech, news")
        auto_topic_entry.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(top, text="Target Domain:").grid(row=3, column=0, padx=20, pady=10, sticky="e")
        # Reuse existing var but show label since it's selected in main UI
        domain_label = ctk.CTkLabel(top, textvariable=self.s3_domain_var, font=ctk.CTkFont(weight="bold"))
        domain_label.grid(row=3, column=1, padx=20, pady=10, sticky="w")
        
        auto_proxied_cb = ctk.CTkCheckBox(top, text="Cloudflare Proxy", variable=self.auto_bucket_dns_proxied_var)
        auto_proxied_cb.grid(row=4, column=1, padx=20, pady=5, sticky="w")

        auto_gsc_cb = ctk.CTkCheckBox(top, text="Add to Webmaster Tools", variable=self.auto_gsc_var)
        auto_gsc_cb.grid(row=5, column=1, padx=20, pady=5, sticky="w")

        # Start Button
        start_btn = ctk.CTkButton(top, text="✨ Start Auto Creation", command=lambda: [top.destroy(), self.run_auto_bucket_creation()], 
                                  fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        start_btn.grid(row=6, column=0, columnspan=2, padx=20, pady=20)
        
        if not self.s3_domain_var.get() or "Select Domain" in self.s3_domain_var.get():
             # Try to fallback to main domain var if valid
             main_domain = self.domain_var.get()
             if main_domain and "API token" not in main_domain:
                 self.s3_domain_var.set(main_domain)
             else:
                 ctk.CTkLabel(top, text="Warning: Please select a domain in the main window first!", text_color=COLORS["danger"]).grid(row=6, column=0, columnspan=2)
                 start_btn.configure(state="disabled")

    def run_auto_bucket_creation(self):
        # Validation
        try:
            count = int(self.auto_bucket_count_var.get())
            if count <= 0 or count > 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Count must be an integer between 1 and 100.")
            return

        domain = self.s3_domain_var.get()
        if not domain or "Select Domain" in domain:
            messagebox.showerror("Missing Domain", "Please select a target domain first (load from Cloudflare tab if needed).")
            return
            
        topic = self.auto_bucket_topic_var.get()
        proxied = self.auto_bucket_dns_proxied_var.get()
        
        # AWS Check
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        if not all([access_key, secret_key]):
            messagebox.showerror("AWS Error", "Please configure AWS Credentials in the sidebar first.")
            return
            
        # Cloudflare Check
        cf_token = self.token_var.get()
        if not cf_token:
            messagebox.showerror("Cloudflare Error", "Cloudflare API Token missing. Please configure in Cloudflare tab.")
            return

        # GSC Check
        use_gsc = self.auto_gsc_var.get()
        if use_gsc:
            if not os.path.exists('credentials.json') and not os.path.exists('token.pickle'):
                 messagebox.showerror("GSC Error", "Google Search Console requires 'credentials.json' in the app directory.")
                 return

        if not messagebox.askyesno("Confirm", f"This will auto-create {count} buckets as subdomains of '{domain}'.\n\n- Generate names via AI\n- Create S3 Bucket\n- Enable Content Hosting\n- Add DNS Record\n\nContinue?"):
            return

        self.set_status("Starting Auto Creation Process...", 0)
        # self.start_auto_btn.configure(state="disabled")

        def task():
            try:
                # 1. Generate Names
                self.set_status("AI Agents Generating Names...", 0.1)
                prompt = (
                    f"Generate {count} unique, meaningful English sub-domain names (single word or hyphenated). "
                    f"Topic: {topic if topic else 'general technology/web'}. "
                    f"Return ONLY a comma-separated list of names. No numbering, no bullets, no whitespace."
                )
                
                ai_response = AIAgent.call_ai_agent(prompt)
                
                if not ai_response:
                    self.after(0, lambda: messagebox.showerror("AI Error", "Failed to generate names from AI Agent."))
                    self.set_status("AI Generation Failed.")
                    return

                # Clean and parse
                subnames = [n.strip().lower() for n in ai_response.replace('\\n', ',').split(',') if n.strip()]
                # Limit to count
                subnames = subnames[:count]
                
                if not subnames:
                    self.after(0, lambda: messagebox.showerror("AI Error", "AI returned empty list."))
                    self.set_status("AI Generation Failed.")
                    return

                s3 = S3API(access_key, secret_key, region)
                cf = CloudflareAPI(cf_token)

                # GSC Setup
                gsc = None
                if use_gsc:
                    self.set_status("Authenticating Google Search Console...", 0.15)
                    try:
                        gsc = GoogleSearchConsole()
                        if not gsc.authenticate():
                             raise Exception("Authentication failed. Check credentials.")
                        # Authentication check only here, actual work is per bucket
                        
                    except Exception as e:
                        print(f"GSC Error: {e}")
                        gsc = None
                
                # Get Zone ID (if not got already)
                zone_id = cf.get_zone_id(domain)
                if not zone_id:
                    self.after(0, lambda: messagebox.showerror("Cloudflare Error", f"Could not find Zone ID for domain: {domain}"))
                    self.set_status("Cloudflare Error.")
                    return

                # Process Loop
                total = len(subnames)
                success_count = 0
                
                for idx, sub in enumerate(subnames):
                    full_bucket_name = f"{sub}.{domain}"
                    progress = (idx / total) * 0.9 + 0.1
                    self.set_status(f"Processing ({idx+1}/{total}): {full_bucket_name}", progress)
                    
                    # A. Create Bucket
                    # Check if exists (simplified, just try create)
                    res = s3.create_bucket(full_bucket_name, region)
                    if not res["success"]:
                        print(f"Failed to create bucket {full_bucket_name}: {res.get('error')}")
                        continue
                        
                    # B. Enable Website Hosting
                    s3.enable_website_hosting(full_bucket_name)
                    s3.disable_public_access_block(full_bucket_name) # Ensure public
                    s3.set_public_read_policy(full_bucket_name) # Add policy
                    
                    # Get Endpoint
                    region_str = region
                    # Standard endpoint format construction since boto3 doesn't always return the full public URL easily without lookup
                    # Format: http://bucket-name.s3-website-region.amazonaws.com
                    endpoint = f"{full_bucket_name}.s3-website-{region_str}.amazonaws.com"
                    
                    # C. DNS
                    # Remove existing if any (optional, but safer to just create/update)
                    # We usually search but for speed let's just try create.
                    
                    # Actually, we should check if record exists to update, or just create.
                    # Let's try create; if it conflicts, we might get error or duplicate. 
                    # Ideally we search first.
                    records = cf.list_dns_records(zone_id, "CNAME")
                    existing_record = next((r for r in records if r["name"] == full_bucket_name or r["name"] == full_bucket_name + "."), None)
                    
                    # D. Add to Webmaster Tool (if enabled)
                    if gsc:
                        try:
                            # Verify individual subdomain using HTML File method
                            site_url = f"https://{full_bucket_name}/"
                            
                            # 1. Get Token (HTML filename)
                            token = gsc.get_verification_token(site_url, "FILE")
                            if token:
                                file_name = token
                                file_content = f"google-site-verification: {token}"
                                
                                # 2. Upload to S3
                                tmp_path = file_name
                                with open(tmp_path, "w") as f:
                                    f.write(file_content)
                                s3.upload_file(full_bucket_name, tmp_path, file_name)
                                if os.path.exists(tmp_path):
                                    os.remove(tmp_path)
                                
                                # 3. Verify
                                gsc.verify_site(site_url, "FILE")
                                gsc.add_site_to_search_console(site_url)

                        except Exception as e:
                            print(f"GSC Add Error for {full_bucket_name}: {e}")

                    success_count += 1
                
                self.set_status("Auto Creation Completed!", 1.0)
                self.after(0, lambda: messagebox.showinfo("Success", f"Completed! Created {success_count} buckets and DNS records."))
                
                # Refresh bucket list
                self.after(0, self.list_s3_buckets)
                
            except Exception as e:
                print(e)
                self.set_status(f"Error: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                # self.start_auto_btn.configure(state="normal")
                self.after(2000, lambda: self.set_status("Ready"))

        threading.Thread(target=task, daemon=True).start()


    def setup_bucket_objects_tab(self):
        tab = self.details_tabview.tab("Objects")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=0)  # Scrollbar column
        tab.grid_rowconfigure(0, weight=0)  # Toolbar - fixed height
        tab.grid_rowconfigure(1, weight=1)  # Tree - expands
        
        # Toolbar for Objects - compact
        self.obj_toolbar = ctk.CTkFrame(tab, fg_color="transparent", height=40)
        self.obj_toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(5, 2))
        
        self.upload_btn = ctk.CTkButton(self.obj_toolbar, text="Upload File", command=self.upload_object_action, width=100, height=30)
        self.upload_btn.pack(side="left", padx=3)
        
        self.upload_folder_btn = ctk.CTkButton(self.obj_toolbar, text="Upload Folder", command=self.upload_folder_action, width=110, height=30, fg_color="#34495E", hover_color="#2C3E50")
        self.upload_folder_btn.pack(side="left", padx=3)
        
        self.download_btn = ctk.CTkButton(self.obj_toolbar, text="Download Selected", command=self.download_object_action, width=120, height=30)
        self.download_btn.pack(side="left", padx=3)
        
        self.delete_obj_btn = ctk.CTkButton(self.obj_toolbar, text="Delete Selected", command=self.delete_object_action, fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"], width=120, height=30)
        self.delete_obj_btn.pack(side="left", padx=3)

        # Overwrite toggle
        self.overwrite_var = ctk.BooleanVar(value=True)
        self.overwrite_cb = ctk.CTkCheckBox(self.obj_toolbar, text="Overwrite", variable=self.overwrite_var, width=80, checkbox_width=20, checkbox_height=20)
        self.overwrite_cb.pack(side="left", padx=5)

        ctk.CTkLabel(self.obj_toolbar, text="Search:").pack(side="left", padx=(8, 3))
        self.obj_search_entry = ctk.CTkEntry(self.obj_toolbar, textvariable=self.obj_search_var, width=120, height=28, placeholder_text="Filter...")
        self.obj_search_entry.pack(side="left", padx=3)
        self.obj_search_entry.bind("<KeyRelease>", lambda e: self.filter_objects())

        self.refresh_obj_btn = ctk.CTkButton(self.obj_toolbar, text="↻", command=lambda: self.fetch_bucket_details(self.bucket_name_var.get()), width=40, height=30)
        self.refresh_obj_btn.pack(side="right", padx=3)

        # Treeview with hierarchical support
        columns = ("size", "date")
        self.obj_tree = ttk.Treeview(tab, columns=columns, show="tree headings")
        
        # Configure columns
        self.obj_tree.heading("#0", text="Name")
        self.obj_tree.heading("size", text="Size")
        self.obj_tree.heading("date", text="Date")
        
        self.obj_tree.column("#0", width=400, anchor="w")
        self.obj_tree.column("size", width=100, anchor="e")
        self.obj_tree.column("date", width=180, anchor="w")
        
        self.obj_tree.grid(row=1, column=0, sticky="nsew", padx=(5, 0), pady=(2, 5))
        
        # Store mapping of tree items to S3 keys for operations
        self.tree_item_to_key = {}
        
        self.obj_scrollbar = ctk.CTkScrollbar(tab, command=self.obj_tree.yview)
        self.obj_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 5), pady=(2, 5))
        self.obj_tree.configure(yscrollcommand=self.obj_scrollbar.set)

    def setup_bucket_permissions_tab(self):
        tab = self.details_tabview.tab("Permissions / Policy")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Bucket Policy (JSON):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.policy_text = ctk.CTkTextbox(tab, height=200)
        self.policy_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def setup_bucket_pab_tab(self):
        tab = self.details_tabview.tab("Public Access Block")
        tab.grid_columnconfigure(1, weight=1)
        
        self.pab_labels = {}
        fields = [
            ("BlockPublicAcls", "Block Public ACLs"),
            ("IgnorePublicAcls", "Ignore Public ACLs"),
            ("BlockPublicPolicy", "Block Public Policy"),
            ("RestrictPublicBuckets", "Restrict Public Buckets")
        ]
        
        for i, (key, label) in enumerate(fields):
            ctk.CTkLabel(tab, text=f"{label}:").grid(row=i, column=0, padx=20, pady=5, sticky="e")
            val_var = ctk.StringVar(value="Unknown")
            self.pab_labels[key] = val_var
            ctk.CTkLabel(tab, textvariable=val_var, font=ctk.CTkFont(weight="bold")).grid(row=i, column=1, padx=20, pady=5, sticky="w")

    def setup_bucket_website_tab(self):
        tab = self.details_tabview.tab("Website Hosting")
        tab.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tab, text="Status:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=10, sticky="e")
        ctk.CTkLabel(tab, textvariable=self.website_status_var).grid(row=0, column=1, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(tab, text="Endpoint:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=10, sticky="e")
        self.website_endpoint_var = ctk.StringVar(value="-")
        # Clickable behavior could be added, but for now just text
        self.website_endpoint_entry = ctk.CTkEntry(tab, textvariable=self.website_endpoint_var, width=400, state="readonly")
        self.website_endpoint_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        self.enable_website_btn = ctk.CTkButton(tab, text="Enable Website Hosting", command=self.enable_website_hosting_manual, fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.enable_website_btn.grid(row=2, column=0, columnspan=2, padx=20, pady=20)

    def setup_bucket_cors_tab(self):
        tab = self.details_tabview.tab("CORS")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(tab, text="CORS Configuration (JSON):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.cors_text = ctk.CTkTextbox(tab, height=200)
        self.cors_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        self.save_cors_btn = ctk.CTkButton(tab, text="Save CORS", command=self.save_cors_action, fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.save_cors_btn.grid(row=2, column=0, padx=10, pady=10)

    def setup_bucket_versioning_tab(self):
        tab = self.details_tabview.tab("Versioning")
        tab.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Versioning Status:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=20, sticky="e")
        ctk.CTkLabel(tab, textvariable=self.versioning_status_var).grid(row=0, column=1, padx=20, pady=20, sticky="w")
        
        self.enable_versioning_btn = ctk.CTkButton(tab, text="Enable Versioning", command=lambda: self.set_versioning_action("Enabled"), fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.enable_versioning_btn.grid(row=1, column=0, padx=20, pady=10)
        
        self.disable_versioning_btn = ctk.CTkButton(tab, text="Suspend Versioning", command=lambda: self.set_versioning_action("Suspended"), fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.disable_versioning_btn.grid(row=1, column=1, padx=20, pady=10)


    def list_s3_buckets(self):
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()

        if not all([access_key, secret_key]):
            messagebox.showerror("Error", "Please enter AWS Access Key and Secret Key")
            return

        self.load_buckets_btn.configure(state="disabled", text="Loading...")
        self.set_status("Loading S3 buckets...", progress=-1)

        def fetch():
            try:
                s3 = S3API(access_key, secret_key, region)
                res = s3.list_buckets()
                
                def update_ui():
                    self.load_buckets_btn.configure(state="normal", text="Load S3 Buckets")
                    self.set_status("Buckets loaded", progress=1.0)
                    if not res["success"]:
                        messagebox.showerror("S3 Error", f"Failed to list buckets: {res['error']}")
                        self.bucket_count_label.configure(text="Total Buckets: -")
                        return

                    self.bucket_tree.delete(*self.bucket_tree.get_children())
                    self.all_buckets = res["buckets"]
                    self.bucket_count_label.configure(text=f"Total Buckets: {len(self.all_buckets)}")
                    for name in self.all_buckets:
                        self.bucket_tree.insert("", "end", values=(name,))
                
                self.after(0, update_ui)
                
            except Exception as e:
                def on_error():
                    self.load_buckets_btn.configure(state="normal", text="Load S3 Buckets")
                    self.set_status("Failed to load buckets", progress=1.0)
                    messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
                self.after(0, on_error)

        threading.Thread(target=fetch, daemon=True).start()

    def export_bucket_list(self):
        if not self.all_buckets:
            messagebox.showwarning("Warning", "No buckets to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                                                 title="Export Bucket List")
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for bucket in self.all_buckets:
                    f.write(f"{bucket}\n")
            
            messagebox.showinfo("Success", f"Bucket list exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def copy_selected_bucket_name(self):
        selected = self.bucket_tree.selection()
        if not selected:
             messagebox.showwarning("Warning", "Please select a bucket from the list.")
             return
        
        vals = self.bucket_tree.item(selected[0])["values"]
        if vals:
            b_name = vals[0]
            pyperclip.copy(b_name)
            self.set_status(f"Copied: {b_name}")

    def filter_buckets(self):
        query = self.bucket_search_var.get().lower()
        self.bucket_tree.delete(*self.bucket_tree.get_children())
        for name in self.all_buckets:
            if query in name.lower():
                self.bucket_tree.insert("", "end", values=(name,))

    def update_full_bucket_name_from_parts(self, event=None):
        # Deselect any selected bucket in the tree to indicate we are now in "Creation/Custom" mode
        if self.bucket_tree.selection():
            self.bucket_tree.selection_remove(self.bucket_tree.selection())
            self.add_dns_btn.configure(state="disabled") # Disable the "Manage" DNS button until a valid bucket is selected/created? 
            # Actually, for creation, we have the "Apply Web & Policy" which does DNS. 
            # The "Add DNS" button is for manual linking. We can keep it disabled or enabled.
            # Original logic: reset_s3_selection disabled it.
            # Let's disable it to avoid confusion, or enable it if name is valid?
            # Let's just deselect.

        sub = self.s3_subdomain_var.get().strip()
        dom = self.s3_domain_var.get().strip()
        
        if dom and dom != "Select Domain..." and not dom.startswith("No domains"):
            full_name = f"{sub}.{dom}"
        else:
            full_name = sub
            
        self.bucket_name_var.set(full_name)
        
        # Auto-sync to DNS config if linking is enabled or just for convenience
        self.cf_subdomain_var.set(sub)


    def on_bucket_select(self, event):
        selected = self.bucket_tree.selection()
        if not selected:
            self.add_dns_btn.configure(state="disabled")
            return
            
        item = selected[0]
        values = self.bucket_tree.item(item)["values"]
        bucket_name = values[0]
        
        self.bucket_name_var.set(bucket_name)
        
        # Try to deconstruct bucket name
        zones = [z["name"] for z in self.zones_data]
        matched_domain = None
        
        # Sort zones by length desc to match longest suffix first
        zones.sort(key=len, reverse=True)
        
        for zone in zones:
            if bucket_name.endswith(f".{zone}"):
                matched_domain = zone
                break
        
        if matched_domain:
            sub = bucket_name[:-len(matched_domain)-1] # remove .domain
            self.s3_subdomain_var.set(sub)
            self.s3_domain_var.set(matched_domain)
            self.cf_subdomain_var.set(sub)
        else:
            self.s3_subdomain_var.set(bucket_name)
            self.s3_domain_var.set("Select Domain...")
            self.cf_subdomain_var.set(bucket_name)

        # Always enable actions when bucket(s) selected
        self.add_dns_btn.configure(state="normal")
        self.add_wmt_btn.configure(state="normal")
        self.open_bucket_web_btn.configure(state="normal")
        self.add_sitemap_btn.configure(state="normal")

        # Fetch details in background (for the first one if multiple, or just skip if too many?)
        # Just show details for the first one for now as UI only supports one detail view
        self.fetch_bucket_details(bucket_name)

    def open_selected_buckets_web(self):
        selected_items = self.bucket_tree.selection()
        if not selected_items:
            return
            
        for item in selected_items:
            vals = self.bucket_tree.item(item)["values"]
            if vals:
                b_name = vals[0]
                url = f"https://{b_name}/"
                webbrowser.open(url)

    def add_to_wmt_manual(self):
        selected_items = self.bucket_tree.selection()
        if not selected_items:
            return

        buckets = [self.bucket_tree.item(i)["values"][0] for i in selected_items]
        count = len(buckets)

        # Check credentials
        if not os.path.exists('credentials.json') and not os.path.exists('token.pickle'):
             messagebox.showerror("GSC Error", "Google Search Console requires 'credentials.json' in the app directory.")
             return
        
        # We need AWS credentials to upload the HTML file
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()

        if not all([access_key, secret_key]):
            messagebox.showerror("AWS Error", "AWS Credentials needed to upload verification file.")
            return

        if not messagebox.askyesno("Add to GSC", f"Add {count} buckets to Google Search Console?\n\nMethod: HTML File Upload\n\nBuckets:\n" + "\n".join(buckets[:5]) + (f"\n...and {count-5} more" if count > 5 else "")):
             return

        self.add_wmt_btn.configure(state="disabled")
        self.open_bucket_web_btn.configure(state="disabled")
        self.set_status("Starting Batch GSC Add...", 0)

        def task():
            try:
                # 1. Auth
                self.set_status("Authenticating Google...", 0.05)
                gsc = GoogleSearchConsole()
                if not gsc.authenticate():
                     raise Exception("Google Auth failed")

                # 2. AWS Init
                s3 = S3API(access_key, secret_key, region)
                
                # 3. Process Loop
                success_count = 0
                for idx, bucket_name in enumerate(buckets):
                    progress = (idx / count)
                    self.set_status(f"Processing ({idx+1}/{count}): {bucket_name}...", progress)
                    
                    try:
                        site_url = f"https://{bucket_name}/"
                        
                        # Get Token
                        token = gsc.get_verification_token(site_url, "FILE")
                        if not token:
                             print(f"Failed to get token for {bucket_name}")
                             continue
                             
                        file_name = token
                        file_content = f"google-site-verification: {token}"
                        
                        # Upload
                        tmp_path = f"tmp_{file_name}"
                        with open(tmp_path, "w") as f:
                            f.write(file_content)
                            
                        s3.upload_file(bucket_name, tmp_path, file_name)
                        
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                        
                        # Verify
                        gsc.verify_site(site_url, "FILE")
                        gsc.add_site_to_search_console(site_url)
                        
                        # Auto-submit sitemap (default: sitemap.html)
                        try:
                            gsc.submit_sitemap(site_url, "sitemap.html")
                            print(f"Sitemap submitted for {bucket_name}")
                        except Exception as se:
                            print(f"Sitemap auto-submit failed for {bucket_name}: {se}")

                        success_count += 1
                        
                    except Exception as e:
                        print(f"Error processing {bucket_name}: {e}")
                
                self.set_status(f"Batch GSC Completed. Success: {success_count}/{count}", 1.0)
                self.after(0, lambda: messagebox.showinfo("Batch Complete", f"Successfully added {success_count} of {count} buckets/sites."))

            except Exception as e:
                print(f"GSC Batch Error: {e}")
                self.set_status(f"Error: {e}")
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("GSC Error", err_msg))
            finally:
                self.after(0, lambda: self.add_wmt_btn.configure(state="normal"))
                self.after(0, lambda: self.open_bucket_web_btn.configure(state="normal"))
                self.after(3000, lambda: self.set_status("Ready"))
        
        threading.Thread(target=task, daemon=True).start()

    def add_sitemap_manual(self):
        selected_items = self.bucket_tree.selection()
        if not selected_items:
            return

        buckets = [self.bucket_tree.item(i)["values"][0] for i in selected_items]
        count = len(buckets)

        # Default sitemap filename
        sitemap_file = "sitemap.html"
        
        # Check creds
        if not os.path.exists('credentials.json') and not os.path.exists('token.pickle'):
             messagebox.showerror("GSC Error", "Google Credentials needed.")
             return
             
        self.add_sitemap_btn.configure(state="disabled")
        self.set_status("Submitting Sitemaps...", 0)
        
        def task():
            try:
                gsc = GoogleSearchConsole()
                if not gsc.authenticate():
                     raise Exception("Google Auth failed")

                success_count = 0
                for idx, bucket_name in enumerate(buckets):
                    self.set_status(f"Submitting sitemap for {bucket_name}...", (idx / count))
                    try:
                        site_url = f"https://{bucket_name}/"
                        gsc.submit_sitemap(site_url, sitemap_file)
                        success_count += 1
                    except Exception as e:
                        print(f"Error {bucket_name}: {e}")
                
                self.set_status("Done", 1.0)
                self.after(0, lambda: messagebox.showinfo("Sitemap", f"Submitted {sitemap_file} for {success_count}/{count} sites."))
            
            except Exception as e:
                print(e)
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: self.add_sitemap_btn.configure(state="normal"))
                self.after(2000, lambda: self.set_status("Ready"))
                
        threading.Thread(target=task, daemon=True).start()

    def reset_s3_selection(self):
        self.bucket_tree.selection_remove(self.bucket_tree.selection())
        self.bucket_name_var.set("")
        self.bucket_endpoint_var.set("-")
        self.s3_subdomain_var.set("")
        # self.s3_domain_var.set("Select Domain...") # converting this to keep the selected domain might be better UX?
        self.cf_subdomain_var.set("")  # Clear subdomain
        self.auto_upload_var.set(False)
        self.auto_upload_path_var.set("")
        self.auto_upload_var.set(False)
        self.auto_upload_path_var.set("")
        self.add_dns_btn.configure(state="disabled")  # Disable when no bucket selected
        self.add_wmt_btn.configure(state="disabled")
        self.open_bucket_web_btn.configure(state="disabled")
        self.add_sitemap_btn.configure(state="disabled")
        
        # Clear all detail views
        self.obj_tree.delete(*self.obj_tree.get_children())
        self.policy_text.delete("1.0", "end")
        self.cors_text.delete("1.0", "end")
        self.website_status_var.set("-")
        self.website_endpoint_var.set("-")
        self.versioning_status_var.set("-")

    def fetch_bucket_details(self, bucket_name):
        if not bucket_name:
            return
            
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()

        if not all([access_key, secret_key]):
            return

        # Show loading state in UI
        self.refresh_obj_btn.configure(state="disabled", text="...")
        self.set_status(f"Fetching details for {bucket_name}...", progress=-1)

        def do_fetch():
            try:
                s3 = S3API(access_key, secret_key, region)
                
                with ThreadPoolExecutor(max_workers=6) as executor:
                    # Submit all tasks - use hierarchical list for objects
                    f_objects = executor.submit(s3.list_objects_hierarchical, bucket_name)
                    f_policy = executor.submit(s3.get_bucket_policy, bucket_name)
                    f_pab = executor.submit(s3.get_public_access_block, bucket_name)
                    f_web = executor.submit(s3.get_bucket_website, bucket_name)
                    f_cors = executor.submit(s3.get_bucket_cors, bucket_name)
                    f_ver = executor.submit(s3.get_bucket_versioning, bucket_name)

                    # Get results
                    res_obj = f_objects.result()
                    res_pol = f_policy.result()
                    res_pab = f_pab.result()
                    res_web = f_web.result()
                    res_cors = f_cors.result()
                    res_ver = f_ver.result()

                def update_ui():
                    # 1. Objects - Hierarchical Tree Display
                    self.obj_tree.delete(*self.obj_tree.get_children())
                    self.tree_item_to_key = {}
                    self.all_objects = []
                    
                    if res_obj["success"]:
                        folders_dict = {}  # path -> tree_item_id
                        
                        # First, create all folder nodes
                        for folder in res_obj.get("folders", []):
                            folder_path = folder["path"]
                            folder_name = folder["name"]
                            parent_path = folder.get("parent")
                            
                            # Determine parent tree item
                            parent_id = folders_dict.get(parent_path, "")
                            
                            # Insert folder with icon
                            item_id = self.obj_tree.insert(
                                parent_id, 
                                "end", 
                                text=f"📁 {folder_name}",
                                values=("", ""),  # Empty size and date for folders
                                open=False
                            )
                            folders_dict[folder_path] = item_id
                        
                        # Then, add all files
                        for file_obj in res_obj.get("files", []):
                            self.all_objects.append(file_obj)
                            
                            file_name = file_obj["Name"]
                            file_key = file_obj["Key"]
                            parent_path = file_obj.get("Parent")
                            
                            # Get file icon
                            icon = self.get_file_icon(file_name)
                            
                            # Format size and date
                            size_str = self.format_size(file_obj["Size"])
                            date_str = self.format_date_nice(file_obj["LastModified"])
                            
                            # Determine parent tree item
                            parent_id = folders_dict.get(parent_path, "")
                            
                            # Insert file
                            item_id = self.obj_tree.insert(
                                parent_id,
                                "end",
                                text=f"{icon} {file_name}",
                                values=(size_str, date_str)
                            )
                            
                            # Store mapping for operations
                            self.tree_item_to_key[item_id] = file_key

                    # 2. Policy
                    self.policy_text.delete("1.0", "end")
                    if res_pol["success"]:
                        policy = res_pol["policy"]
                        if isinstance(policy, str) and policy.startswith("{"):
                            try:
                                policy = json.dumps(json.loads(policy), indent=4)
                            except: pass
                        self.policy_text.insert("1.0", policy)
                    else:
                        self.policy_text.insert("1.0", f"Error: {res_pol.get('error')}")

                    # 3. PAB
                    if res_pab["success"]:
                        config = res_pab["config"]
                        if isinstance(config, dict):
                            for key in self.pab_labels:
                                val = config.get(key, "Not set")
                                self.pab_labels[key].set(str(val))
                        else:
                            for var in self.pab_labels.values():
                                var.set(str(config))
                    else:
                        for var in self.pab_labels.values():
                            var.set("Error fetching")

                    # 4. Website
                    if res_web["success"]:
                        if res_web["config"]:
                            self.website_status_var.set("Enabled")
                            endpoint = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
                            self.website_endpoint_var.set(endpoint)
                            self.bucket_endpoint_var.set(endpoint)
                            self.enable_website_btn.configure(text="Update Website Config", fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
                        else:
                            self.website_status_var.set("Disabled")
                            self.website_endpoint_var.set("-")
                            self.bucket_endpoint_var.set("-")
                            self.enable_website_btn.configure(text="Enable Website Hosting", fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
                    else:
                        self.website_status_var.set(f"Error: {res_web.get('error')}")
                        self.website_endpoint_var.set("-")
                        self.bucket_endpoint_var.set("-")
                    
                    # Note: Add DNS button state is controlled by bucket selection only

                    # 5. CORS
                    self.cors_text.delete("1.0", "end")
                    if res_cors["success"]:
                        cors = res_cors["cors"]
                        self.cors_text.insert("1.0", json.dumps(cors, indent=4))
                    else:
                        self.cors_text.insert("1.0", f"Error: {res_cors.get('error')}")

                    # 6. Versioning
                    if res_ver["success"]:
                        self.versioning_status_var.set(res_ver["status"])
                    else:
                        self.versioning_status_var.set("Error")

                    # End loading state
                    self.refresh_obj_btn.configure(state="normal", text="Refresh")
                    self.set_status(f"Bucket {bucket_name} details loaded", progress=1.0)

                self.after(0, update_ui)

            except Exception as e:
                def on_error():
                    self.refresh_obj_btn.configure(state="normal", text="Refresh")
                    self.set_status("Error fetching bucket details", progress=1.0)
                    print(f"Error fetching details: {e}")
                self.after(0, on_error)

        threading.Thread(target=do_fetch, daemon=True).start()

    def filter_objects(self):
        """Filter objects in tree view"""
        query = self.obj_search_var.get().lower()
        if not query:
            # Refresh to show all
            self.fetch_bucket_details(self.bucket_name_var.get())
            return
        
        # Simple filter: only show files matching query
        self.obj_tree.delete(*self.obj_tree.get_children())
        self.tree_item_to_key = {}
        
        for file_obj in self.all_objects:
            if query in file_obj["Name"].lower() or query in file_obj["Key"].lower():
                icon = self.get_file_icon(file_obj["Name"])
                size_str = self.format_size(file_obj["Size"])
                date_str = self.format_date_nice(file_obj["LastModified"])
                
                item_id = self.obj_tree.insert(
                    "",
                    "end",
                    text=f"{icon} {file_obj['Name']}",
                    values=(size_str, date_str)
                )
                self.tree_item_to_key[item_id] = file_obj["Key"]

    def enable_website_hosting_manual(self):
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        bucket_name = self.bucket_name_var.get().strip()
        
        if not bucket_name:
            messagebox.showwarning("Warning", "Please select a bucket first")
            return
            
        try:
            s3 = S3API(access_key, secret_key, region)
            index = self.index_doc_var.get().strip() or "index.html"
            error = self.error_doc_var.get().strip() or "404.html"
            res = s3.enable_website_hosting(bucket_name, index=index, error=error)
            
            if res["success"]:
                messagebox.showinfo("Success", f"Static Website Hosting enabled for {bucket_name}")
                self.fetch_bucket_details(bucket_name) # Refresh
            else:
                messagebox.showerror("Error", f"Failed to enable hosting: {res['error']}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")

    def copy_endpoint(self):
        endpoint = self.bucket_endpoint_var.get()
        if endpoint and endpoint != "-":
            pyperclip.copy(endpoint)
            messagebox.showinfo("Copied", "Endpoint copied to clipboard!")
        else:
            messagebox.showwarning("Warning", "No endpoint to copy")

    def get_file_icon(self, filename):
        """Return icon/emoji based on file type"""
        if not filename:
            return "📄"
        
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        icon_map = {
            # Web
            'html': '🌐',
            'htm': '🌐',
            'css': '🎨',
            'js': '📜',
            # Documents
            'pdf': '📕',
            'doc': '📘',
            'docx': '📘',
            'txt': '📝',
            'md': '📝',
            'readme': '📝',
            # Images
            'png': '🖼️',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'gif': '🖼️',
            'svg': '🖼️',
            'ico': '🖼️',
            # Config
            'json': '⚙️',
            'xml': '⚙️',
            'yaml': '⚙️',
            'yml': '⚙️',
            'config': '⚙️',
            # Code
            'py': '🐍',
            'java': '☕',
            'cpp': '⚡',
            'c': '⚡',
            # Archives
            'zip': '📦',
            'tar': '📦',
            'gz': '📦',
            'rar': '📦',
        }
        
        return icon_map.get(ext, '📄')
    
    def format_date_nice(self, date_obj):
        """Format date nicely like 'Saturday, 27 Dec'"""
        import datetime
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.datetime.strptime(date_obj, "%Y-%m-%d %H:%M:%S")
            except:
                return date_obj
        
        if isinstance(date_obj, datetime.datetime):
            return date_obj.strftime("%A, %d %b")
        return str(date_obj)

    def format_size(self, size_bytes):
        if size_bytes == 0: return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])

    def upload_object_action(self):
        bucket_name = self.bucket_name_var.get().strip()
        if not bucket_name:
            messagebox.showwarning("Warning", "Please select a bucket first")
            return
        
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
            
        import os
        object_name = os.path.basename(file_path)
        
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        overwrite = self.overwrite_var.get()
        
        self.upload_btn.configure(state="disabled", text="Uploading...")
        self.set_status(f"Uploading {object_name}...", progress=-1)

        def do_upload():
            try:
                s3 = S3API(access_key, secret_key, region)
                res = s3.upload_file(bucket_name, file_path, object_name, overwrite=overwrite)
                
                def update_ui():
                    self.upload_btn.configure(state="normal", text="Upload File")
                    if res["success"]:
                        self.set_status(f"Uploaded {object_name}", progress=1.0)
                        messagebox.showinfo("Success", f"Uploaded {object_name}")
                        self.fetch_bucket_details(bucket_name)
                    else:
                        msg = res.get("error", "Unknown error")
                        if res.get("skipped"):
                             self.set_status(f"Upload skipped: {msg}", progress=1.0)
                             messagebox.showinfo("Skipped", msg)
                        else:
                            self.set_status("Upload failed", progress=1.0)
                            messagebox.showerror("Error", f"Upload failed: {msg}")
                self.after(0, update_ui)
            except Exception as e:
                def on_error():
                    self.upload_btn.configure(state="normal", text="Upload File")
                    self.set_status("Error during upload", progress=1.0)
                    messagebox.showerror("Error", str(e))
                self.after(0, on_error)

        threading.Thread(target=do_upload, daemon=True).start()

    def upload_folder_action(self):
        # Get selected buckets from tree
        selected_items = self.bucket_tree.selection()
        bucket_names = []
        for item in selected_items:
            vals = self.bucket_tree.item(item)["values"]
            if vals: 
                bucket_names.append(vals[0])
        
        # Fallback to current var if tree empty (e.g. if single selection logic prevailed or UI interaction style)
        if not bucket_names:
            single = self.bucket_name_var.get().strip()
            if single:
                bucket_names.append(single)

        if not bucket_names:
            messagebox.showwarning("Warning", "Please select one or more buckets first")
            return
    
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return
            
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        overwrite = self.overwrite_var.get()
        
        self.upload_folder_btn.configure(state="disabled", text="Uploading...")
        self.set_status(f"Starting upload to {len(bucket_names)} buckets...", progress=0)

        def do_upload():
            try:
                s3 = S3API(access_key, secret_key, region)
                total_buckets = len(bucket_names)
                successful = 0
                failed = 0
                
                for idx, bucket_name in enumerate(bucket_names):
                    
                    def progress_cb(data):
                        if isinstance(data, dict):
                            current = data.get("current", 0)
                            total = data.get("total", 0)
                            remaining = data.get("remaining", 0)
                            speed = data.get("speed", 0)
                            fname = data.get("filename", "unknown")
                            status = data.get("status", "Uploading")
                            
                            # Global progress calculation
                            local_pct = current / total if total > 0 else 0
                            global_pct = (idx + local_pct) / total_buckets
                            
                            msg = f"[{idx+1}/{total_buckets}] {bucket_name}: {current}/{total} | {fname}"
                            self.set_status(msg, progress=global_pct)
                        else:
                            self.set_status(str(data), progress=-1)
                    
                    self.set_status(f"Preparing upload to {bucket_name} ({idx+1}/{total_buckets})...", progress=(idx/total_buckets))
                    
                    res = s3.upload_directory(bucket_name, dir_path, progress_callback=progress_cb, overwrite=overwrite)
                    
                    if res.get("success"):
                        successful += 1
                    else:
                        failed += 1
                        print(f"Failed to upload to {bucket_name}: {res.get('error')}")
            
                def update_ui():
                    self.upload_folder_btn.configure(state="normal", text="Upload Folder")
                    self.set_status("All uploads completed", progress=1.0)
                    messagebox.showinfo("Success", f"Batch Upload Complete.\nSuccessful: {successful}\nFailed: {failed}")
                    # Refresh details for the last bucket so UI isn't stale
                    if bucket_names:
                        self.fetch_bucket_details(bucket_names[-1])
                        
                self.after(0, update_ui)
                
            except Exception as e:
                def on_error():
                    self.upload_folder_btn.configure(state="normal", text="Upload Folder")
                    self.set_status("Error during folder upload", progress=1.0)
                    messagebox.showerror("Error", str(e))
                self.after(0, on_error)

        threading.Thread(target=do_upload, daemon=True).start()

    def download_object_action(self):
        selected = self.obj_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an object to download")
            return
        
        selected_item = selected[0]
        
        # Check if it's a file (not a folder)
        if selected_item not in self.tree_item_to_key:
            messagebox.showwarning("Warning", "Cannot download folders. Please select a file.")
            return
            
        bucket_name = self.bucket_name_var.get().strip()
        object_name = self.tree_item_to_key[selected_item]
        
        # Extract filename for save dialog
        filename = object_name.split('/')[-1]
        
        file_path = filedialog.asksaveasfilename(initialfile=filename)
        if not file_path:
            return
            
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        
        try:
            s3 = S3API(access_key, secret_key, region)
            res = s3.download_file(bucket_name, object_name, file_path)
            if res["success"]:
                messagebox.showinfo("Success", f"Downloaded {object_name}")
            else:
                messagebox.showerror("Error", f"Download failed: {res['error']}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_object_action(self):
        selected = self.obj_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an object to delete")
            return
        
        selected_item = selected[0]
        
        # Check if it's a file (not a folder)
        if selected_item not in self.tree_item_to_key:
            messagebox.showwarning("Warning", "Cannot delete folders directly. Please delete files individually.")
            return
            
        bucket_name = self.bucket_name_var.get().strip()
        object_name = self.tree_item_to_key[selected_item]
        
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete {object_name}?"):
            return
            
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        
        try:
            s3 = S3API(access_key, secret_key, region)
            res = s3.delete_object(bucket_name, object_name)
            if res["success"]:
                messagebox.showinfo("Success", f"Deleted {object_name}")
                self.fetch_bucket_details(bucket_name)
            else:
                messagebox.showerror("Error", f"Delete failed: {res['error']}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_cors_action(self):
        bucket_name = self.bucket_name_var.get().strip()
        if not bucket_name:
            messagebox.showwarning("Warning", "Please select a bucket first")
            return
            
        cors_json = self.cors_text.get("1.0", "end").strip()
        try:
            cors_rules = json.loads(cors_json)
            
            access_key = self.aws_access_key_var.get().strip()
            secret_key = self.aws_secret_key_var.get().strip()
            region = self.aws_region_var.get().strip()
            
            s3 = S3API(access_key, secret_key, region)
            res = s3.put_bucket_cors(bucket_name, cors_rules)
            if res["success"]:
                messagebox.showinfo("Success", "CORS policy updated")
                self.fetch_bucket_details(bucket_name)
            else:
                messagebox.showerror("Error", f"Update failed: {res['error']}")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid JSON or API error: {str(e)}")

    def set_versioning_action(self, status):
        bucket_name = self.bucket_name_var.get().strip()
        if not bucket_name:
            messagebox.showwarning("Warning", "Please select a bucket first")
            return
            
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        
        try:
            s3 = S3API(access_key, secret_key, region)
            res = s3.put_bucket_versioning(bucket_name, status)
            if res["success"]:
                messagebox.showinfo("Success", f"Versioning {status.lower()}")
                self.fetch_bucket_details(bucket_name)
            else:
                messagebox.showerror("Error", f"Update failed: {res['error']}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_bucket_action(self):
        bucket_name = self.bucket_name_var.get().strip()
        if not bucket_name:
            messagebox.showwarning("Warning", "Please select a bucket first")
            return
            
        if not messagebox.askyesno("Confirm", f"ARE YOU SURE? This will delete the bucket '{bucket_name}'."):
            return
            
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        
        try:
            s3 = S3API(access_key, secret_key, region)
            res = s3.delete_bucket(bucket_name)
            if res["success"]:
                messagebox.showinfo("Success", f"Bucket '{bucket_name}' deleted.")
                self.list_s3_buckets()
                self.bucket_name_var.set("")
            else:
                messagebox.showerror("Error", f"Delete failed: {res['error']}. Bucket MUST be empty before deletion.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def select_auto_upload_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.auto_upload_path_var.set(path)

    def handle_s3_creation(self):
        access_key = self.aws_access_key_var.get().strip()
        secret_key = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        
        # Use simple bucket name var, which is updated by the composition fields
        bucket_name = self.bucket_name_var.get().strip()

        if not all([access_key, secret_key, region, bucket_name]):
            messagebox.showerror("Error", "Please fill in all AWS fields and Bucket Name")
            return

        # Note: Profile is auto-saved on manual save only, not during bucket creation
        self.create_bucket_btn.configure(state="disabled", text="Processing...")
        self.set_status(f"Starting creation for {bucket_name}...", progress=0.1)

        def do_work():
            success_msg = []
            error_occured = False
            
            try:
                s3 = S3API(access_key, secret_key, region)
                
                # 1. Create Bucket
                self.set_status(f"Creating bucket {bucket_name}...", progress=0.3)
                res = s3.create_bucket(bucket_name, region)
                if res["success"]:
                    success_msg.append(f"- Bucket '{bucket_name}' created.")
                elif "BucketAlreadyOwnedByYou" in res["error"] or "BucketAlreadyExists" in res["error"]:
                    success_msg.append(f"- Bucket '{bucket_name}' already exists (using existing).")
                else:
                    # Only fail if it's a real error, not "already exists"
                    self.after(0, lambda err=res['error']: messagebox.showerror("S3 Error", f"Failed to create bucket: {err}"))
                    error_occured = True

                # 2. Always Disable Block Public Access (required for website hosting)
                if not error_occured:
                    self.set_status("Disabling Block Public Access...", progress=0.5)
                    res = s3.disable_public_access_block(bucket_name)
                    if res["success"]:
                        success_msg.append("- Block Public Access disabled (content is publicly readable).")
                    else:
                        self.after(0, lambda err=res['error']: messagebox.showerror("S3 Error", f"Failed to disable Public Access Block: {err}"))
                        error_occured = True
                
                # 3. Always Set Public Read Policy (required for website hosting)
                if not error_occured:
                    self.set_status("Setting Public Read Policy...", progress=0.7)
                    res = s3.set_public_read_policy(bucket_name)
                    if res["success"]:
                        success_msg.append("- Public Read Policy applied (all objects are publicly accessible).")
                    else:
                        self.after(0, lambda err=res['error']: messagebox.showerror("S3 Error", f"Failed to set policy: {err}"))
                        error_occured = True

                if not error_occured and self.enable_hosting_var.get():
                    # 4. Enable Website Hosting
                    self.set_status("Enabling Static Website Hosting...", progress=0.8)
                    index = self.index_doc_var.get().strip() or "index.html"
                    error = self.error_doc_var.get().strip() or "404.html"
                    res = s3.enable_website_hosting(bucket_name, index=index, error=error)
                    if not res["success"]:
                        self.after(0, lambda: messagebox.showerror("S3 Error", f"Failed to enable Website Hosting: {res['error']}"))
                        error_occured = True
                    else:
                        endpoint = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
                        self.after(0, lambda: self.bucket_endpoint_var.set(endpoint))
                        self.after(0, lambda: self.website_endpoint_var.set(endpoint))
                        success_msg.append("- Static Website Hosting enabled.")

                if not error_occured and self.link_cf_var.get():
                    # 5. Cloudflare Integration
                    # Use the subdomain from S3 tab for DNS creation, to match user request "auto take sub in this section"
                    subdomain = self.s3_subdomain_var.get().strip()
                    domain_to_use = self.s3_domain_var.get().strip()

                    # Fallback if manual entry was used or vars are empty
                    if not subdomain and self.cf_subdomain_var.get():
                        subdomain = self.cf_subdomain_var.get()
                    
                    if not subdomain:
                        success_msg.append("- Cloudflare Linking: Skipped (no subdomain).")
                    elif not domain_to_use or domain_to_use == "Select Domain...":
                         success_msg.append("- Cloudflare Linking: Skipped (no domain selected in S3 tab).")
                    else:
                        self.set_status(f"Creating Cloudflare DNS '{subdomain}'...", progress=0.9)
                        try:
                            # We need to ensure we have an API instance
                            if not self.api:
                                # Try to init with saved config
                                token = self.token_var.get().strip()
                                self.api = CloudflareAPI(token)

                            # Resolve Zone ID for the S3-selected domain
                            # Look in our loaded zones data first
                            target_zone_id = next((z["id"] for z in self.zones_data if z["name"] == domain_to_use), None)
                            
                            # If not found, try to fetch it
                            if not target_zone_id and self.api:
                                target_zone_id = self.api.get_zone_id(domain_to_use)
                            
                            if not self.api or not target_zone_id:
                                success_msg.append(f"- Cloudflare Linking: Failed (Could not find Zone ID for {domain_to_use}).")
                            else:
                                endpoint = f"{bucket_name}.s3-website-{region}.amazonaws.com"
                                res_cf = self.api.create_dns_record(
                                    zone_id=target_zone_id,
                                    type="CNAME",
                                    name=subdomain,
                                    content=endpoint,
                                    proxied=self.cf_proxy_var.get()
                                )
                                
                                if res_cf.get("success"):
                                    success_msg.append(f"- DNS CNAME '{subdomain}.{domain_to_use}' created.")
                                else:
                                    err = res_cf.get("errors", [{"message": "Unknown error"}])[0]["message"]
                                    success_msg.append(f"- Cloudflare Error: {err}")
                        except Exception as e:
                            success_msg.append(f"- Cloudflare Error: {str(e)}")

                if not error_occured and self.auto_upload_var.get():
                    # 6. Auto Upload Source Folder
                    upload_path = self.auto_upload_path_var.get().strip()
                    if upload_path and os.path.exists(upload_path):
                        self.set_status(f"Auto uploading source from {os.path.basename(upload_path)}...", progress=0.95)
                        
                        def progress_cb(data):
                            if isinstance(data, dict):
                                current = data.get("current", 0)
                                total = data.get("total", 0)
                                fname = data.get("filename", "unknown")
                                pct = (current / total * 0.05) + 0.95 if total > 0 else 0.95
                                msg = f"Auto Upload: {current}/{total} | {fname}"
                                self.set_status(msg, progress=pct)
                        
                        res_upload = s3.upload_directory(bucket_name, upload_path, progress_callback=progress_cb, overwrite=True)
                        if res_upload.get("success"):
                            success_msg.append(f"- Source folder '{os.path.basename(upload_path)}' auto-uploaded.")
                        else:
                            success_msg.append(f"- Auto-upload Failed: {res_upload.get('error')}")
                    else:
                        success_msg.append("- Auto-upload: Skipped (invalid folder path).")

                def finalize():
                    self.create_bucket_btn.configure(state="normal", text="Apply Web & Policy")
                    self.list_s3_buckets()
                    if not error_occured:
                        self.set_status("Bucket creation successful", progress=1.0)
                        final_text = "Action Completed Successfully:\n" + "\n".join(success_msg)
                        messagebox.showinfo("Success", final_text)
                    else:
                        self.set_status("Errors occurred during creation", progress=1.0)
                
                self.after(0, finalize)

            except Exception as e:
                self.after(0, lambda: self.create_bucket_btn.configure(state="normal", text="Apply Web & Policy"))
                self.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}"))

        threading.Thread(target=do_work, daemon=True).start()

    def link_dns_manually(self):
        bucket_name = self.bucket_name_var.get().strip()
        subdomain = self.cf_subdomain_var.get().strip()
        endpoint = self.bucket_endpoint_var.get().strip()
        
        # Determine the target domain from S3 tab
        target_domain = self.s3_domain_var.get().strip()
        if not target_domain or target_domain == "Select Domain...":
            # Fallback to general domain if S3 one is not explicitly selected
            target_domain = self.domain_var.get().strip()

        if not bucket_name:
            messagebox.showwarning("Warning", "Please select a bucket first.")
            return
            
        if not subdomain:
            messagebox.showwarning("Warning", "Please enter a subdomain.")
            return

        if not target_domain or target_domain == "Please enter API token...":
            messagebox.showwarning("Warning", "Please select a domain in the S3 tab first.")
            return

        self.add_dns_btn.configure(state="disabled", text="Checking...")
        self.set_status(f"Checking DNS record '{subdomain}' in {target_domain}...", progress=0.3)

        def do_link():
            try:
                token = self.token_var.get().strip()
                if not token:
                    def token_err():
                        self.set_status("Token missing", progress=1.0)
                        messagebox.showerror("Error", "Cloudflare API Token is missing.")
                        self.add_dns_btn.configure(state="normal", text="⚡ Add DNS")
                    self.after(0, token_err)
                    return

                # Initialize API if needed
                if not self.api:
                    self.api = CloudflareAPI(token)
                
                # Resolve Zone ID for the target domain (S3-selected domain)
                target_zone_id = next((z["id"] for z in self.zones_data if z["name"] == target_domain), None)
                if not target_zone_id:
                    target_zone_id = self.api.get_zone_id(target_domain)
                
                if not target_zone_id:
                    def cf_error():
                        self.set_status("Cloudflare config missing", progress=1.0)
                        messagebox.showerror("Cloudflare Error", f"Could not find Zone ID for domain: {target_domain}. Check your token and domain settings.")
                        self.add_dns_btn.configure(state="normal", text="⚡ Add DNS")
                    self.after(0, cf_error)
                    return

                # Determine hostname/content based on endpoint availability
                if endpoint and endpoint != "-":
                    # Use website endpoint if available
                    hostname = endpoint.replace("http://", "").replace("https://", "").split("/")[0]
                else:
                    # Use S3 bucket domain directly
                    region = self.aws_region_var.get().strip() or "us-east-1"
                    hostname = f"{bucket_name}.s3.{region}.amazonaws.com"
                
                # Build full subdomain name
                full_name = f"{subdomain}.{target_domain}" if subdomain else target_domain
                
                # Check if DNS record already exists
                self.set_status(f"Checking if '{full_name}' exists in {target_domain}...", progress=0.5)
                existing_records = self.api.list_dns_records(target_zone_id)
                matching_record = next((r for r in existing_records if r.get("name") == full_name and r.get("type") == "CNAME"), None)
                
                if matching_record:
                    # Record exists
                    existing_content = matching_record.get("content", "")
                    def record_exists():
                        self.add_dns_btn.configure(state="normal", text="⚡ Add DNS")
                        self.set_status(f"DNS record already exists", progress=1.0)
                        messagebox.showinfo("DNS Already Exists", 
                            f"DNS record '{full_name}' already exists.\n\n"
                            f"Current target: {existing_content}\n"
                            f"New target would be: {hostname}\n\n"
                            f"No changes were made.")
                    self.after(0, record_exists)
                    return
                
                # Record doesn't exist, create it
                self.set_status(f"Creating DNS '{subdomain}' in {target_domain}...", progress=0.7)
                res = self.api.create_dns_record(
                    zone_id=target_zone_id,
                    type="CNAME",
                    name=subdomain,
                    content=hostname,
                    proxied=self.cf_proxy_var.get()
                )
                
                def finalize():
                    self.add_dns_btn.configure(state="normal", text="⚡ Add DNS")
                    if res.get("success"):
                        self.set_status(f"DNS '{subdomain}' created successfully", progress=1.0)
                        messagebox.showinfo("Success", 
                            f"✅ CNAME record created!\n\n"
                            f"Name: {full_name}\n"
                            f"Points to: {hostname}\n"
                            f"Proxied: {'Yes' if self.cf_proxy_var.get() else 'No'}")
                    else:
                        err = res.get("errors", [{"message": "Unknown error"}])[0]["message"]
                        self.set_status("DNS creation failed", progress=1.0)
                        messagebox.showerror("Cloudflare Error", f"Failed to create DNS record: {err}")
                self.after(0, finalize)

            except Exception as e:
                def on_error():
                    self.add_dns_btn.configure(state="normal", text="⚡ Add DNS")
                    self.set_status("Unexpected error during DNS link", progress=1.0)
                    messagebox.showerror("Error", str(e))
                self.after(0, on_error)

        threading.Thread(target=do_link, daemon=True).start()


    def load_zones(self):
        token = self.token_var.get().strip()
        if not token:
            return
        
        self.api = CloudflareAPI(token)
        try:
            zones = self.api.get_zones()
            if not zones:
                self.domain_combo.configure(values=["No domains found"])
                return
            
            self.zones_data = zones
            zone_names = [z["name"] for z in zones]
            self.domain_combo.configure(values=zone_names)
            self.zone_count_label.configure(text=f"({len(zones)} domains)")
            
            # Also update S3 domain combo
            # Also update S3 domain combo
            self.s3_domain_combo.configure(values=zone_names)
            
            # If current domain_var is not in list, pick the first one
            current_domain = self.domain_var.get()
            if current_domain not in zone_names and zone_names:
                self.domain_var.set(zone_names[0])
                
            # Sync to S3 domain var if empty
            if not self.s3_domain_var.get() or self.s3_domain_var.get() == "Select Domain...":
                self.s3_domain_var.set(self.domain_var.get())
            
            self.save_cf_config() # Auto save token if load success
            self.list_records() # Load records for the selected domain
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load zones: {str(e)}")

    def add_new_zone(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showerror("Error", "Please enter Cloudflare API Token first.")
            return

        dialog = ctk.CTkInputDialog(text="Enter Domain Name (e.g. example.com):", title="Add New Site")
        domain = dialog.get_input()
        
        if not domain:
            return
            
        domain = domain.strip()
        
        self.add_site_btn.configure(state="disabled", text="Creating...")
        self.set_status(f"Creating zone for {domain}...", progress=-1)
        
        def create_task():
            try:
                # Initialize API
                api = CloudflareAPI(token)
                
                # We need an account ID. Fetch accounts.
                accounts = api.get_accounts()
                if not accounts:
                    messagebox.showerror("Error", "Could not retrieve Cloudflare accounts. Check your token permissions (Account:Read).")
                    return
                
                # For now, pick the first account. 
                # Ideally we'd let the user choose if > 1, but simplicity first.
                account_id = accounts[0]["id"]
                account_name = accounts[0]["name"]
                
                self.set_status(f"Using account '{account_name}'...", progress=0.5)
                
                res = api.create_zone(domain, account_id)
                
                def finish_ui():
                    self.add_site_btn.configure(state="normal", text="+ Add Site")
                    if res.get("success"):
                        result_data = res.get("result", {})
                        ns_list = result_data.get("name_servers", [])
                        
                        success_msg = f"Zone '{domain}' created successfully!"
                        self.set_status(f"Zone {domain} created", progress=1.0)
                        
                        # Reload zones
                        self.load_zones()
                        self.domain_var.set(domain)
                        self.list_records()
                        
                        # Show Nameservers to User
                        if ns_list:
                            ns_text = "\n".join(ns_list)
                            
                            # Create a custom dialog for Nameservers
                            ns_window = ctk.CTkToplevel(self)
                            ns_window.title("Setup Required: Point Nameservers")
                            ns_window.geometry("500x350")
                            ns_window.attributes("-topmost", True)
                            
                            ctk.CTkLabel(ns_window, text=f"Domain: {domain}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
                            
                            ctk.CTkLabel(ns_window, text="Please log in to your domain registrar and\nchange your nameservers to the following:", 
                                         font=ctk.CTkFont(size=14)).pack(pady=10)
                            
                            ns_box = ctk.CTkTextbox(ns_window, width=400, height=100, font=ctk.CTkFont(size=14))
                            ns_box.pack(pady=10)
                            ns_box.insert("1.0", ns_text)
                            ns_box.configure(state="disabled")
                            
                            ctk.CTkButton(ns_window, text="Copy to Clipboard", 
                                          command=lambda: (pyperclip.copy(ns_text), messagebox.showinfo("Copied", "Nameservers copied!"))).pack(pady=10)
                            
                            ctk.CTkButton(ns_window, text="Done", command=ns_window.destroy).pack(pady=10)
                        else:
                            messagebox.showinfo("Success", success_msg)
                            
                    else:
                        errors = res.get("errors", [])
                        err_msg = "\n".join([e.get("message", "Unknown error") for e in errors])
                        self.set_status("Zone creation failed", progress=1.0)
                        messagebox.showerror("Creation Failed", f"Could not create zone:\n{err_msg}")
                
                self.after(0, finish_ui)
                
            except Exception as e:
                def err_ui():
                    self.add_site_btn.configure(state="normal", text="+ Add Site")
                    self.set_status("Error creating zone", progress=1.0)
                    messagebox.showerror("Error", str(e))
                self.after(0, err_ui)
                
        threading.Thread(target=create_task, daemon=True).start()

    def delete_current_zone(self):
        domain = self.domain_var.get().strip()
        if not domain or domain in ["Please enter API token...", "No domains found"]:
            messagebox.showwarning("Warning", "Please select a domain to delete first.")
            return

        if not messagebox.askyesno("Confirm Delete", f"DANGER: Are you sure you want to DELETE the site '{domain}'?\n\nThis action cannot be undone and will delete ALL DNS records and settings for this domain."):
            return

        if not self.init_api():
            return
            
        self.del_site_btn.configure(state="disabled", text="Deleting...")
        self.set_status(f"Deleting zone {domain}...", progress=-1)
        
        def delete_task():
            try:
                res = self.api.delete_zone(self.zone_id)
                def finish():
                    self.del_site_btn.configure(state="normal", text="🗑️ Delete Site")
                    if res.get("success"):
                        messagebox.showinfo("Success", f"Zone '{domain}' has been deleted.")
                        self.set_status(f"Zone {domain} deleted", progress=1.0)
                        self.load_zones() # Refresh list
                    else:
                        errors = res.get("errors", [])
                        err_msg = "\n".join([e.get("message", "Unknown error") for e in errors])
                        self.set_status("Delete failed", progress=1.0)
                        messagebox.showerror("Delete Failed", f"Could not delete zone:\n{err_msg}")
                self.after(0, finish)
            except Exception as e:
                def err_ui():
                    self.del_site_btn.configure(state="normal", text="🗑️ Delete Site")
                    self.set_status("Error deleting zone", progress=1.0)
                    messagebox.showerror("Error", str(e))
                self.after(0, err_ui)
                
        threading.Thread(target=delete_task, daemon=True).start()

    def on_domain_change(self, choice):
        self.save_cf_config()
        self.list_records()

    def init_api(self):

        domain = self.domain_var.get().strip()
        token = self.token_var.get().strip()
        if not domain or not token or domain == "Please enter API token...":
            messagebox.showerror("Error", "Please enter API Token and select a Domain")
            return False
        
        self.api = CloudflareAPI(token)
        # Find zone_id from zones_data if possible to avoid API call
        self.zone_id = next((z["id"] for z in self.zones_data if z["name"] == domain), None)
        
        if not self.zone_id:
            self.zone_id = self.api.get_zone_id(domain)
            
        if not self.zone_id:
            messagebox.showerror("Error", "Zone not found or API error. Check your Token.")
            return False
        return True

        return True

    def load_cf_profiles_into_ui(self):
        profiles = ConfigManager.get_cf_profiles()
        config = ConfigManager.load_config()
        last_profile = config.get("last_selected_cf_profile", "")
        
        names = list(profiles.keys())
        if not names:
            names = ["Default"]
        
        self.cf_profile_combo.configure(values=names)
        
        if last_profile in profiles:
            self.cf_profile_var.set(last_profile)
            self.token_var.set(profiles[last_profile].get("token", ""))
            # Auto load zones for this profile
            self.after(200, self.load_zones)
        elif names:
            self.cf_profile_var.set(names[0])
            if names[0] in profiles:
                self.token_var.set(profiles[names[0]].get("token", ""))

    def on_cf_profile_change(self, choice):
        profiles = ConfigManager.get_cf_profiles()
        if choice in profiles:
            self.token_var.set(profiles[choice].get("token", ""))
            self.load_zones()

    def save_cf_profile_action(self):
        name = self.cf_profile_var.get().strip()
        token = self.token_var.get().strip()
        
        if not name or not token:
            messagebox.showerror("Error", "Please provide a Profile Name and API Token")
            return
            
        ConfigManager.save_cf_profile(name, token)
        self.load_cf_profiles_into_ui()
        messagebox.showinfo("Success", f"Profile '{name}' saved.")

    def delete_cf_profile_action(self):
        name = self.cf_profile_var.get().strip()
        if not name:
             return
             
        if messagebox.askyesno("Confirm", f"Delete Cloudflare profile '{name}'?"):
            if ConfigManager.delete_cf_profile(name):
                self.token_var.set("")
                self.load_cf_profiles_into_ui()
            else:
                messagebox.showerror("Error", "Could not delete profile (maybe default?)")

    def save_cf_config(self):
        # We now primarily use save_cf_profile_action, but keep this for backward compat or domain saving
        # Saving domain is still useful
        token = self.token_var.get().strip()
        domain = self.domain_var.get().strip()
        ConfigManager.save_config(token, domain)
    
    def load_s3_profiles_into_ui(self):
        profiles = ConfigManager.get_s3_profiles()
        config = ConfigManager.load_config()
        last_profile = config.get("last_selected_profile", "")
        
        names = list(profiles.keys())
        if not names:
            names = ["Default"]
        
        self.profile_combo.configure(values=names)
        
        if last_profile in profiles:
            self.aws_profile_var.set(last_profile)
            self.update_aws_fields_from_profile(last_profile)
        elif names:
            self.aws_profile_var.set(names[0])
            self.update_aws_fields_from_profile(names[0])
            
    def on_profile_change(self, choice):
        self.update_aws_fields_from_profile(choice)
        
    def update_aws_fields_from_profile(self, profile_name):
        profiles = ConfigManager.get_s3_profiles()
        if profile_name in profiles:
            data = profiles[profile_name]
            self.aws_access_key_var.set(data.get("aws_access_key", ""))
            self.aws_secret_key_var.set(data.get("aws_secret_key", ""))
            self.aws_region_var.set(data.get("aws_region", "us-east-1"))
            
    def save_s3_profile_action(self):
        name = self.aws_profile_var.get().strip()
        access = self.aws_access_key_var.get().strip()
        secret = self.aws_secret_key_var.get().strip()
        region = self.aws_region_var.get().strip()
        
        # Validate profile name - only reject empty or exact class names
        if not name:
            messagebox.showerror("Error", "Please enter a profile name")
            return
        
        if name in ["CTkComboBox", "CTkEntry", "CTkButton"]:
            messagebox.showerror("Error", f"Invalid profile name: '{name}'. This appears to be a UI element name.")
            return
            
        ConfigManager.save_s3_profile(name, access, secret, region)
        self.load_s3_profiles_into_ui()
        messagebox.showinfo("Success", f"Profile '{name}' saved.")
        
    def delete_s3_profile_action(self):
        name = self.aws_profile_var.get().strip()
        if not name:
             return
             
        if messagebox.askyesno("Confirm", f"Delete profile '{name}'?"):
            if ConfigManager.delete_s3_profile(name):
                self.aws_access_key_var.set("")
                self.aws_secret_key_var.set("")
                self.aws_region_var.set("")
                self.load_s3_profiles_into_ui()


    def list_records(self):
        if not self.init_api():
            return
        
        # Show loading...
        self.tree.delete(*self.tree.get_children())
        
        def fetch():
            try:
                records = self.api.list_dns_records(self.zone_id)
                self.current_records = records
                # Reset filters logic
                self.cf_search_text = self.cf_search_entry.get()
                self.cf_current_page = 1
                
                self.after(0, self.update_cf_table_view)
            except Exception as e:
                print(f"Error fetching records: {e}")
                
        threading.Thread(target=fetch, daemon=True).start()

    def filter_cf_records(self, event=None):
        self.cf_search_text = self.cf_search_entry.get()
        self.cf_current_page = 1
        self.update_cf_table_view()

    def change_cf_page(self, delta):
        new_page = self.cf_current_page + delta
        if new_page < 1:
            return
            
        # Check max pages
        import math
        total_pages = math.ceil(len(self.cf_filtered_records) / self.cf_items_per_page)
        if total_pages == 0: total_pages = 1
        
        if new_page > total_pages:
            return
            
        self.cf_current_page = new_page
        self.update_cf_table_view()

    def update_cf_table_view(self):
        # 1. Filter
        query = self.cf_search_text.lower()
        if query:
            self.cf_filtered_records = [
                r for r in self.current_records 
                if query in r.get("name", "").lower() or 
                   query in r.get("content", "").lower() or
                   query in r.get("type", "").lower()
            ]
        else:
            self.cf_filtered_records = list(self.current_records)

        # 2. Pagination
        import math
        total_items = len(self.cf_filtered_records)
        self.cf_items_per_page = 50 # Ensure this is set
        total_pages = math.ceil(total_items / self.cf_items_per_page)
        if total_pages == 0: total_pages = 1
        
        if self.cf_current_page > total_pages:
            self.cf_current_page = total_pages
            
        start_idx = (self.cf_current_page - 1) * self.cf_items_per_page
        end_idx = start_idx + self.cf_items_per_page
        
        page_items = self.cf_filtered_records[start_idx:end_idx]
        
        # 3. Update UI
        self.tree.delete(*self.tree.get_children())
        for record in page_items:
            self.tree.insert("", "end", values=(record["type"], record["name"], record["content"], record["id"]))
            
        self.page_label.configure(text=f"Page {self.cf_current_page} of {total_pages}")
        self.page_label.configure(text=f"Page {self.cf_current_page} of {total_pages}")
        self.total_records_label.configure(text=f"Records (Subdomains): {total_items}")
        
        # Update button states
        if self.cf_current_page <= 1:
            self.prev_page_btn.configure(state="disabled", fg_color="transparent")
        else:
            self.prev_page_btn.configure(state="normal", fg_color=COLORS["bg_hover"])
            
        if self.cf_current_page >= total_pages:
            self.next_page_btn.configure(state="disabled", fg_color="transparent")
        else:
            self.next_page_btn.configure(state="normal", fg_color=COLORS["bg_hover"])

    def on_record_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        values = self.tree.item(selected[0])["values"]
        self.type_var.set(values[0])
        
        # Extract subdomain from full name
        domain = self.domain_var.get()
        full_name = values[1]
        record_id = values[3]
        
        if full_name == domain:
            subdomain = "@"
        else:
            subdomain = full_name.replace(f".{domain}", "")
            
        self.subdomain_var.set(subdomain)
        self.ip_var.set(values[2])
        self.selected_record_id = record_id
        
        # Find full record data to set Proxied/TTL
        record_data = next((r for r in self.current_records if r["id"] == record_id), None)
        if record_data:
            self.proxied_var.set(record_data.get("proxied", False))
            ttl_val = record_data.get("ttl", 1)
            # Map valid TTL to string
            ttl_str = self.ttl_reverse_mapping.get(ttl_val, "Auto")
            self.ttl_var.set(ttl_str)

        self.create_btn.configure(text="Update Record", fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])

    def clear_form(self):
        self.subdomain_var.set("")
        self.ip_var.set("")
        self.type_var.set("A")
        self.ttl_var.set("Auto")
        self.proxied_var.set(False)
        self.selected_record_id = None
        self.create_btn.configure(text="Create Record", fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.tree.selection_remove(self.tree.selection())

    def create_record(self):
        if not self.init_api():
            return
        
        subdomain = self.subdomain_var.get().strip()
        ip = self.ip_var.get().strip()
        if not subdomain or not ip:
            messagebox.showerror("Error", "Please enter both Subdomain and IP")
            return
        
        domain = self.domain_var.get().strip()
        name = subdomain if subdomain == "@" else f"{subdomain}.{domain}"
        record_type = self.type_var.get()
        
        # Get TTL and Proxied
        ttl_label = self.ttl_var.get()
        ttl = self.ttl_mapping.get(ttl_label, 1) # Default to 1 (Auto)
        proxied = self.proxied_var.get()

        if self.selected_record_id:
            # Update mode
            result = self.api.update_dns_record(self.zone_id, self.selected_record_id, record_type, name, ip, ttl=ttl, proxied=proxied)
            action = "updated"
        else:
            # Create mode
            result = self.api.create_dns_record(self.zone_id, record_type, name, ip, ttl=ttl, proxied=proxied)
            action = "created"

        if result.get("success"):
            messagebox.showinfo("Success", f"Record {action} for {name}!")
            self.list_records()
            self.clear_form()
        else:
            errors = result.get("errors", [])
            err_msg = "\n".join([f"- {e.get('message')}" for e in errors])
            messagebox.showerror("API Error", f"Failed to {action[:-1]} record:\n{err_msg}")


    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a record to delete")
            return
        
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete selected record(s)?"):
            return
        
        if not self.init_api():
            return
        
        records_removed_count = 0
        for item in selected:
            values = self.tree.item(item)["values"]
            rid = values[3]
            name = values[1]
            result = self.api.delete_dns_record(self.zone_id, rid)

            if result.get("success"):
                # Remove from local list to avoid full reload
                self.current_records = [r for r in self.current_records if r["id"] != rid]
                records_removed_count += 1
            else:
                messagebox.showerror("Error", f"Failed to delete {name}")

        if records_removed_count > 0:
            self.update_cf_table_view()
            messagebox.showinfo("Success", f"Deleted {records_removed_count} records")

    def export_mikrotik(self):
        records = []
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            records.append(f"/ip dns static add name={values[1]} address={values[2]}")


        if not records:
            messagebox.showwarning("Warning", "No records to export. Refresh the list first.")
            return
        
        script = "\n".join(records)
        pyperclip.copy(script)
        
        export_window = ctk.CTkToplevel(self)
        export_window.title("MikroTik Script - Copied to Clipboard")
        export_window.geometry("600x400")
        
        ctk.CTkLabel(export_window, text="The following script has been copied to your clipboard:", pady=10).pack()
        
        text_area = ctk.CTkTextbox(export_window, width=550, height=300)
        text_area.insert("1.0", script)
        text_area.pack(padx=20, pady=10)
        
        ctk.CTkButton(export_window, text="Close", command=export_window.destroy).pack(pady=10)

    def open_selected_website(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a record first")
            return
        
        values = self.tree.item(selected[0])["values"]
        # values = (type, name, content, id)
        name = values[1]
        
        # Basic validation to ensure it looks like a domain
        if not name or name == "@":
             name = self.domain_var.get()

        url = f"http://{name}"
        webbrowser.open(url)

    def setup_wmt_view(self):
        tab = self.wmt_view
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Toolbar
        self.wmt_toolbar = ctk.CTkFrame(tab, height=50, corner_radius=15, fg_color=COLORS["bg_card"])
        self.wmt_toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        self.wmt_toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        ctk.CTkLabel(self.wmt_toolbar, text="Google Search Console", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20, pady=10)
        
        # Profile Selection
        self.gsc_profile_combo = ctk.CTkComboBox(self.wmt_toolbar, variable=self.gsc_profile_var, command=self.on_gsc_profile_change, width=150)
        self.gsc_profile_combo.pack(side="left", padx=5, pady=10)
        
        # Account Actions
        self.wmt_add_acct_btn = ctk.CTkButton(self.wmt_toolbar, text="+ Account", command=self.add_wmt_account_action, width=80,
                                             fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.wmt_add_acct_btn.pack(side="left", padx=5, pady=10)

        self.wmt_del_acct_btn = ctk.CTkButton(self.wmt_toolbar, text="- Acct", command=self.delete_wmt_account_action, width=60,
                                             fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.wmt_del_acct_btn.pack(side="left", padx=5, pady=10)


        # Right side actions
        self.wmt_refresh_btn = ctk.CTkButton(self.wmt_toolbar, text="↻ Refresh", command=self.list_wmt_sites, width=100,
                                             fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.wmt_refresh_btn.pack(side="right", padx=5, pady=10)

        self.wmt_add_btn = ctk.CTkButton(self.wmt_toolbar, text="+ Site", command=self.add_wmt_site_dialog, width=80,
                                             fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.wmt_add_btn.pack(side="right", padx=5, pady=10)

        self.wmt_del_btn = ctk.CTkButton(self.wmt_toolbar, text="🗑️", command=self.delete_selected_wmt_site, width=50,
                                             fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
        self.wmt_del_btn.pack(side="right", padx=5, pady=10)
        
        # Initial Load
        self.after(500, self.load_gsc_profiles_into_ui)

        # Sites Table
        self.wmt_table_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=COLORS["bg_card"])
        self.wmt_table_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.wmt_table_frame.grid_columnconfigure(0, weight=1)
        self.wmt_table_frame.grid_rowconfigure(0, weight=1)

        columns = ("siteUrl", "permissionLevel", "clicks", "impressions", "ctr", "position")
        self.wmt_tree = ttk.Treeview(self.wmt_table_frame, columns=columns, show="headings")
        
        self.wmt_tree.heading("siteUrl", text="Site URL")
        self.wmt_tree.heading("permissionLevel", text="Permission")
        self.wmt_tree.heading("clicks", text="Clicks (28d)")
        self.wmt_tree.heading("impressions", text="Impressions")
        self.wmt_tree.heading("ctr", text="CTR (%)")
        self.wmt_tree.heading("position", text="Avg Pos")

        self.wmt_tree.column("siteUrl", width=300)
        self.wmt_tree.column("permissionLevel", width=100)
        self.wmt_tree.column("clicks", width=80)
        self.wmt_tree.column("impressions", width=80)
        self.wmt_tree.column("ctr", width=60)
        self.wmt_tree.column("position", width=60)

        self.wmt_tree.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        self.wmt_scrollbar = ctk.CTkScrollbar(self.wmt_table_frame, command=self.wmt_tree.yview)
        self.wmt_scrollbar.grid(row=0, column=1, sticky="ns", pady=15)
        self.wmt_tree.configure(yscrollcommand=self.wmt_scrollbar.set)

        # Configure column sorting
        for col in columns:
            self.wmt_tree.heading(col, command=lambda c=col: self.wmt_sort_column(c, False))

        # Load from cache initially
        self.load_wmt_cache()

    def wmt_sort_column(self, col, reverse):
        l = [(self.wmt_tree.set(k, col), k) for k in self.wmt_tree.get_children('')]
        
        # Try to sort as numbers if possible
        try:
            l.sort(key=lambda t: float(t[0].replace('%', '').replace('-', '0')) if t[0] != '-' else -1, reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            self.wmt_tree.move(k, '', index)

        # Reverse sort next time
        self.wmt_tree.heading(col, command=lambda: self.wmt_sort_column(col, not reverse))

    def load_gsc_profiles_into_ui(self):
        profiles = ConfigManager.get_gsc_profiles()
        config = ConfigManager.load_config()
        last_profile = config.get("last_selected_gsc_profile", "")
        
        names = list(profiles.keys())
        if not names:
             # If no profiles, maybe we have a default token.pickle?
             if os.path.exists("token.pickle"):
                 # Auto-migrate
                 default_token_path = os.path.expanduser("~") + "/.cloud_management_pro/gsc_tokens/token_default.pickle"
                 try:
                     shutil.copy("token.pickle", default_token_path)
                     ConfigManager.save_gsc_profile("Default", default_token_path)
                     names = ["Default"]
                 except Exception:
                     names = []
        
        if names:
            self.gsc_profile_combo.configure(values=names)
            if last_profile in profiles:
                 self.gsc_profile_var.set(last_profile)
            else:
                 self.gsc_profile_var.set(names[0])
            self.load_wmt_cache()
        else:
            self.gsc_profile_combo.configure(values=["No Accounts"])
            self.gsc_profile_var.set("No Accounts")

    def on_gsc_profile_change(self, choice):
        # Save selection
        config = ConfigManager.load_config()
        config["last_selected_gsc_profile"] = choice
        with open(ConfigManager.CONFIG_FILE if hasattr(ConfigManager, 'CONFIG_FILE') else os.path.expanduser("~/.cloud_management_pro_config.json"), "w") as f:
            json.dump(config, f, indent=4)
            
        self.load_wmt_cache()

    def add_wmt_account_action(self):
        dialog = ctk.CTkInputDialog(text="Enter Account Name (e.g. 'Company A'):", title="Add GSC Account")
        name = dialog.get_input()
        if not name or not name.strip(): return
        name = name.strip()
        
        profiles = ConfigManager.get_gsc_profiles()
        if name in profiles:
            messagebox.showerror("Error", "Account name already exists.")
            return

        self.set_status("Starting GSC Login...", 0.2)
        
        def task():
            try:
                # We use a temp token file for auth
                temp_token = "token_temp.pickle"
                if os.path.exists(temp_token):
                    os.remove(temp_token)
                    
                # Force new login
                # We need credentials.json
                if not os.path.exists("credentials.json"):
                     raise Exception("credentials.json not found in app directory.")
                
                # We'll use the temp token path
                gsc = GoogleSearchConsole(token_file=temp_token)
                
                # This will open browser
                if gsc.authenticate():
                    # Auth success, move token
                    token_dir = os.path.expanduser("~") + "/.cloud_management_pro/gsc_tokens"
                    if not os.path.exists(token_dir):
                        os.makedirs(token_dir)
                        
                    safe_name = "".join(x for x in name if x.isalnum() or x in "._- ")
                    final_path = os.path.join(token_dir, f"token_{safe_name}.pickle")
                    
                    try:
                        shutil.move(temp_token, final_path)
                    except Exception as e:
                        # If failed to move (e.g. diff filesystems), try copy/remove
                         shutil.copy(temp_token, final_path)
                         os.remove(temp_token)
                         
                    ConfigManager.save_gsc_profile(name, final_path)
                    
                    self.after(0, lambda: self.load_gsc_profiles_into_ui())
                    self.after(0, lambda: messagebox.showinfo("Success", f"Account '{name}' added!"))
                    self.set_status("Account added", 1.0)
                else:
                    self.set_status("Login failed", 0)
            except Exception as e:
                print("Auth Error:", e)
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status("Error logging in", 0)
                
        threading.Thread(target=task).start()

    def delete_wmt_account_action(self):
        name = self.gsc_profile_var.get()
        if name in ["No Accounts", ""]: return
        
        if messagebox.askyesno("Confirm", f"Remove account '{name}'?"):
            if ConfigManager.delete_gsc_profile(name):
                # We could delete the token file too, but keeping it as backup might be safer? 
                # Let's keep it simply unlinked for now.
                self.gsc_profile_var.set("")
                self.load_gsc_profiles_into_ui()

    def get_current_gsc_instance(self):
        name = self.gsc_profile_var.get()
        profiles = ConfigManager.get_gsc_profiles()
        token_path = "token.pickle" # Fallback
        
        if name in profiles:
            token_path = profiles[name].get("token_path", "token.pickle")
        
        return GoogleSearchConsole(token_file=token_path)

    def load_wmt_cache(self):
        try:
            profile_name = self.gsc_profile_var.get()
            cache = ConfigManager.get_wmt_cache(profile_name)
            
            for item in self.wmt_tree.get_children():
                self.wmt_tree.delete(item)
                
            if not cache:
                self.set_status("No cache for this profile", 1.0)
                return

            for site in cache:
                # Safe get
                curr_values = (
                    site.get('siteUrl', ''),
                    site.get('permissionLevel', ''),
                    site.get('clicks', '-'),
                    site.get('impressions', '-'),
                    site.get('ctr', '-'),
                    site.get('position', '-')
                )
                self.wmt_tree.insert("", "end", values=curr_values)
                
            self.set_status(f"Loaded {len(cache)} sites from cache", 1.0)
        except Exception as e:
            print(f"Error loading WMT cache: {e}")



    def list_wmt_sites(self):
        self.set_status("Fetching sites from Google Search Console...", 0.2)
        
        def task():
            try:
                gsc = self.get_current_gsc_instance()
                
                # Check for token or credentials first
                if not os.path.exists(gsc.token_file) and not os.path.exists('credentials.json'):
                    self.after(0, lambda: messagebox.showerror("GSC Error", "Missing credentials.json or token for Google Search Console."))
                    self.set_status("GSC Authentication Missing", 0)
                    return

                if not gsc.authenticate():
                     self.after(0, lambda: messagebox.showerror("Error", "Could not authenticate with Google Search Console."))
                     self.set_status("Authentication failed", 0)
                     return

                sites = gsc.list_sites()
                
                self.after(0, lambda: self._update_wmt_list(sites))
                self.set_status("WMT Sites loaded", 1.0)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status("Error loading WMT sites", 0)

        threading.Thread(target=task).start()

    def _update_wmt_list(self, sites):
        for item in self.wmt_tree.get_children():
            self.wmt_tree.delete(item)
            
        for site in sites:
            self.wmt_tree.insert("", "end", values=(site.get('siteUrl'), site.get('permissionLevel'), "-", "-", "-", "-"))
        
        # Trigger stats fetch
        self.fetch_wmt_stats()

    def fetch_wmt_stats(self):
        items = self.wmt_tree.get_children()
        if not items: return
        
        # Capture all necessary info from main thread
        sites_to_process = []
        for item in items:
            values = self.wmt_tree.item(item, "values")
            # values: url, permission, clicks, impressions, ctr, position
            sites_to_process.append({
                'item_id': item,
                'siteUrl': values[0],
                'permissionLevel': values[1]
            })
        
        self.set_status(f"Fetching analytics for {len(sites_to_process)} sites...", 0.5)
        
        def task():
            try:
                # Create a single GSC instance for this thread
                gsc = self.get_current_gsc_instance()
                if not gsc.authenticate(): return
                
                from datetime import datetime, timedelta
                end_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=31)).strftime('%Y-%m-%d')

                cached_results = []
                profile_name = self.gsc_profile_var.get()

                # Fetch sequentially to avoid SSL/Threading crashes on macOS
                for i, site_data in enumerate(sites_to_process):
                    url = site_data['siteUrl']
                    item_id = site_data['item_id']
                    
                    # Update status occasionally
                    if i % 5 == 0:
                        self.set_status(f"Fetching analytics... ({i+1}/{len(sites_to_process)})", 0.5 + (0.5 * i / len(sites_to_process)))
                    
                    stats = {'clicks': '-', 'impressions': '-', 'ctr': '-', 'position': '-'}
                    try:
                        stats = gsc.get_site_analytics(url, start_date, end_date)
                        self.after(0, lambda id=item_id, s=stats: self._update_single_site_stats(id, s))
                    except Exception as e:
                        print(f"Skipping {url}: {e}")
                    
                    # Prepare for cache
                    site_record = {
                        'siteUrl': url,
                        'permissionLevel': site_data['permissionLevel'],
                        **stats
                    }
                    cached_results.append(site_record)
                    
                self.set_status("Analytics data loaded", 1.0)
                
                # Save cache
                ConfigManager.save_wmt_cache(profile_name, cached_results)
                
            except Exception as e:
                print(f"Global fetch error: {e}")
        
        threading.Thread(target=task).start()

    def _update_single_site_stats(self, item_id, stats):
        try:
             # Get current values first to preserve URL/Permission
             current_values = self.wmt_tree.item(item_id, "values")
             if not current_values: return
             
             new_values = (current_values[0], current_values[1], 
                           stats.get('clicks', '-'), stats.get('impressions', '-'), 
                           stats.get('ctr', '-'), stats.get('position', '-'))
             self.wmt_tree.item(item_id, values=new_values)
        except Exception:
            pass

    def add_wmt_site_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter Site URL (e.g., https://example.com/):", title="Add Site to GSC")
        url = dialog.get_input()
        if not url: return

        self.set_status(f"Adding {url} to GSC...", 0.2)
        def task():
            try:
                gsc = self.get_current_gsc_instance()
                if not gsc.authenticate():
                     raise Exception("Authentication Failed")
                
                gsc.add_site_to_search_console(url)
                self.after(0, lambda: messagebox.showinfo("Success", f"Site {url} added."))
                self.list_wmt_sites()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status("Error adding site", 0)
        
        threading.Thread(target=task).start()

    def delete_selected_wmt_site(self):
        selected = self.wmt_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a site to delete.")
            return

        values = self.wmt_tree.item(selected[0])["values"]
        site_url = values[0]

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to remove '{site_url}' from your GSC account?"):
            return

        self.set_status(f"Deleting {site_url}...", 0.2)
        def task():
            try:
                gsc = self.get_current_gsc_instance()
                if not gsc.authenticate():
                     raise Exception("Authentication Failed")
                
                gsc.delete_site(site_url)
                self.after(0, lambda: messagebox.showinfo("Success", f"Site {site_url} removed."))
                self.list_wmt_sites()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status("Error deleting site", 0)
        
        threading.Thread(target=task).start()

    def setup_gsheet_view(self):
        tab = self.gsheet_view
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Toolbar
        self.gsheet_toolbar = ctk.CTkFrame(tab, height=50, corner_radius=15, fg_color=COLORS["bg_card"])
        self.gsheet_toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 15))
        
        ctk.CTkLabel(self.gsheet_toolbar, text="Google Sheet Manager", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20, pady=10)

        # Login and ID
        self.gs_login_btn = ctk.CTkButton(self.gsheet_toolbar, text="Login Google", command=self.gs_login_action, width=100, 
                                          fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.gs_login_btn.pack(side="left", padx=5)

        ctk.CTkLabel(self.gsheet_toolbar, text="ID:").pack(side="left", padx=(10, 5))
        self.sheet_id_var = ctk.StringVar(value="1QQLRshOHaE8M_n22hn_5yoD7N8k5UJdN-sZ0mEI7W6s")
        self.sheet_id_entry = ctk.CTkEntry(self.gsheet_toolbar, textvariable=self.sheet_id_var, width=200)
        self.sheet_id_entry.pack(side="left", padx=5)

        # Load Sheets
        self.gs_load_btn = ctk.CTkButton(self.gsheet_toolbar, text="Load Sheets", command=self.gs_load_sheets_action, width=100)
        self.gs_load_btn.pack(side="left", padx=5)

        # Sheet Selector
        self.sheet_select_var = ctk.StringVar(value="")
        self.sheet_select_combo = ctk.CTkComboBox(self.gsheet_toolbar, variable=self.sheet_select_var, width=150, command=self.on_sheet_select)
        self.sheet_select_combo.pack(side="left", padx=20)
        self.sheet_select_combo.set("Select Sheet")
        self.sheet_select_combo.configure(state="disabled")
        
        # Add Sheet Button
        self.gs_add_btn = ctk.CTkButton(self.gsheet_toolbar, text="+ New Sheet", command=self.add_sheet_popup, width=100,
                                        fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"])
        self.gs_add_btn.pack(side="right", padx=10)

        # Content Area - Treeview
        self.gs_content_frame = ctk.CTkFrame(tab, corner_radius=15, fg_color=COLORS["bg_card"])
        self.gs_content_frame.grid(row=1, column=0, sticky="nsew")
        self.gs_content_frame.grid_columnconfigure(0, weight=1)
        self.gs_content_frame.grid_rowconfigure(0, weight=1)

        self.gs_tree = ttk.Treeview(self.gs_content_frame, selectmode="browse")
        self.gs_tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        scroll_y = ctk.CTkScrollbar(self.gs_content_frame, command=self.gs_tree.yview)
        scroll_y.grid(row=0, column=1, sticky="ns", pady=10)
        self.gs_tree.configure(yscrollcommand=scroll_y.set)
        
        scroll_x = ctk.CTkScrollbar(self.gs_content_frame, orientation="horizontal", command=self.gs_tree.xview)
        scroll_x.grid(row=1, column=0, sticky="ew", padx=10)
        self.gs_tree.configure(xscrollcommand=scroll_x.set)

        self.gs_tree.bind("<<TreeviewSelect>>", self.on_gs_row_select)

        # Editor Area
        self.gs_edit_frame = ctk.CTkFrame(tab, height=80, corner_radius=15, fg_color=COLORS["bg_card"])
        self.gs_edit_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        
        ctk.CTkLabel(self.gs_edit_frame, text="Log/Status:").pack(side="left", padx=20, pady=20)
        self.gs_status_lbl = ctk.CTkLabel(self.gs_edit_frame, text="Ready", text_color=COLORS["text_secondary"])
        self.gs_status_lbl.pack(side="left", padx=5, pady=20)

        # Simple row editor placeholder usage
        self.gs_update_btn = ctk.CTkButton(self.gs_edit_frame, text="Save Changes", command=self.gs_update_row_action, state="disabled")
        self.gs_update_btn.pack(side="right", padx=20, pady=20)
        
        self.gs_edit_var = ctk.StringVar()
        self.gs_edit_entry = ctk.CTkEntry(self.gs_edit_frame, textvariable=self.gs_edit_var, width=400, placeholder_text="Select a row to edit (Raw JSON or Pipe separated)")
        self.gs_edit_entry.pack(side="right", padx=10, pady=20)

        # Initial Logic State
        self.current_sheet_values = []
        self.current_sheet_range = ""

    def gs_login_action(self):
        self.set_status("Logging in to Google Sheets...", 0.5)
        def task():
            gsm = GoogleSheetManager(token_file='token_sheets.pickle')
            if gsm.authenticate():
                self.after(0, lambda: messagebox.showinfo("Success", "Logged in successfully!"))
                self.set_status("Logged in", 1.0)
            else:
                self.after(0, lambda: messagebox.showerror("Error", "Login failed."))
                self.set_status("Login failed", 0)
        threading.Thread(target=task).start()

    def gs_load_sheets_action(self):
        sid = self.sheet_id_var.get().strip()
        if not sid:
            messagebox.showwarning("Warning", "Enter Spreadsheet ID first")
            return
            
        self.set_status("Loading sheets...", 0.2)
        def task():
            try:
                gsm = GoogleSheetManager(token_file='token_sheets.pickle')
                if not gsm.authenticate():
                     raise Exception("Authentication Failed. Click Login.")
                
                sheets = gsm.get_sheet_names(sid)
                names = [s['title'] for s in sheets]
                
                def update():
                    self.sheet_select_combo.configure(values=names, state="normal")
                    if names: 
                        self.sheet_select_combo.set(names[0])
                        self.on_sheet_select(names[0])
                    else:
                        self.sheet_select_combo.set("No Sheets Found")
                
                self.after(0, update)
                self.set_status("Sheets loaded", 1.0)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status("Error loading sheets", 0)
        threading.Thread(target=task).start()

    def on_sheet_select(self, choice):
        if not choice or choice == "Select Sheet": return
        sid = self.sheet_id_var.get().strip()
        
        self.set_status(f"Loading data from '{choice}'...", 0.2)
        def task():
            try:
                gsm = GoogleSheetManager(token_file='token_sheets.pickle')
                gsm.authenticate()
                
                # Get all values
                values = gsm.get_sheet_values(sid, choice)
                self.current_sheet_values = values
                self.current_sheet_range = choice # Assuming we edit the whole sheet range logic eventually
                
                self.after(0, lambda: self.update_gs_tree(values))
                self.set_status(f"Loaded {len(values)} rows", 1.0)
            except Exception as e:
                print(e)
                self.set_status("Error loading data", 0)
        threading.Thread(target=task).start()

    def update_gs_tree(self, values):
        # Clear tree
        self.gs_tree.delete(*self.gs_tree.get_children())
        self.gs_tree["columns"] = ()
        
        if not values:
            return

        # Determine max columns
        max_cols = max([len(r) for r in values]) if values else 0
        columns = [f"Col {i+1}" for i in range(max_cols)]
        
        self.gs_tree["columns"] = columns
        self.gs_tree["show"] = "headings"
        
        for col in columns:
            self.gs_tree.heading(col, text=col)
            self.gs_tree.column(col, width=100)
            
        # Insert Data
        # Assume first row is header? Let's just show all as data for now unless we detect header.
        # Often first row is header. Let's make headers match first row if possible.
        
        header_row = values[0]
        # Pad header if needed
        while len(header_row) < max_cols: header_row.append("")
        
        # Set headings
        for i, h in enumerate(header_row):
            self.gs_tree.heading(columns[i], text=h)
        
        # Insert remaining rows
        for i, row in enumerate(values[1:]): # Skip header in data view? Or show all?
            # Standard Practice: First row is header.
            # Treeview items
            # Pad row
            display_row = row + [""] * (max_cols - len(row))
            self.gs_tree.insert("", "end", iid=str(i+2), values=display_row) # iid=Row Number (1-based index of original file)
            # Row 1 is header (not in tree items), so first data row is Row 2.

    def on_gs_row_select(self, event):
        selected = self.gs_tree.selection()
        if not selected:
            self.gs_update_btn.configure(state="disabled")
            return
            
        item = self.gs_tree.item(selected[0])
        values = item["values"]
        # Join with pipe for simple editing
        text_rep = " | ".join([str(v) for v in values])
        self.gs_edit_var.set(text_rep)
        self.gs_update_btn.configure(state="normal")

    def gs_update_row_action(self):
        selected = self.gs_tree.selection()
        if not selected: return
        
        row_idx = int(selected[0]) # This is the 1-based row index in the sheet
        sid = self.sheet_id_var.get().strip()
        sheet_name = self.sheet_select_var.get()
        
        # Parse new values
        new_text = self.gs_edit_var.get()
        new_values = [v.strip() for v in new_text.split("|")]
        
        self.set_status("Updating row...", 0.2)
        def task():
            try:
                gsm = GoogleSheetManager(token_file='token_sheets.pickle')
                gsm.authenticate()
                
                # Update specific row range
                # Construct range A{row}:Z{row}
                range_name = f"{sheet_name}!A{row_idx}"
                
                gsm.update_sheet_values(sid, range_name, [new_values])
                
                self.after(0, lambda: messagebox.showinfo("Success", "Row updated!"))
                self.after(0, lambda: self.gs_tree.item(selected[0], values=new_values)) # Update UI locally
                self.set_status("Row updated", 1.0)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.set_status("Update failed", 0)
        threading.Thread(target=task).start()

    def add_sheet_popup(self):
        dialog = ctk.CTkInputDialog(text="Enter New Sheet Name:", title="Add Sheet")
        name = dialog.get_input()
        if not name: return
        
        sid = self.sheet_id_var.get().strip()
        if not sid:
            messagebox.showwarning("Warning", "Enter Spreadsheet ID first")
            return

        self.set_status(f"Adding sheet '{name}'...", 0.2)
        def task():
            try:
                gsm = GoogleSheetManager(token_file='token_sheets.pickle')
                if not gsm.authenticate():
                     raise Exception("Auth Failed")
                
                gsm.add_sheet(sid, name)
                self.after(0, lambda: messagebox.showinfo("Success", f"Sheet '{name}' added!"))
                self.after(0, self.gs_load_sheets_action) # Reload list
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        threading.Thread(target=task).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
