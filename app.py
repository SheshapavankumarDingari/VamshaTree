import os
import requests
import re
import wikipedia
import streamlit as st
from huggingface_hub import InferenceClient
from concurrent.futures import ThreadPoolExecutor

# --- 1. PAGE CONFIGURATION & THEME ---
st.set_page_config(page_title="VamshaTree | Genealogical Intelligence", page_icon="🌳", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Base Theme */
    .stApp { background-color: #0b0f19; color: #f8fafc; font-family: 'Inter', -apple-system, sans-serif; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }

    /* Semantic Swimlane Containers */
    .swimlane-Parents { border-top: 3px solid #a855f7 !important; }
    .swimlane-Spouses { border-top: 3px solid #ec4899 !important; }
    .swimlane-Kin { border-top: 3px solid #14b8a6 !important; }
    .swimlane-Children { border-top: 3px solid #22c55e !important; }
    
    /* Native Card Container Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #1e293b !important;
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%) !important;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #3b82f6 !important;
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 25px -5px rgba(59, 130, 246, 0.15) !important;
    }

    /* HTML Card Internals */
    .card-img-container { display: flex; justify-content: center; margin-bottom: 12px; }
    .card-img { width: 75px; height: 75px; border-radius: 50%; object-fit: cover; border: 2px solid #3b82f6; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
    .card-fallback { width: 75px; height: 75px; border-radius: 50%; background: #1e293b; border: 2px solid #475569; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: bold; color: #64748b; }
    .card-relation { text-align: center; color: #3b82f6; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .card-name { text-align: center; color: #f8fafc; font-size: 1.15rem; font-weight: 700; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .card-desc { text-align: center; color: #94a3b8; font-size: 0.85rem; line-height: 1.4; height: 2.8em; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; margin-bottom: 10px; }

    /* Lane Headers */
    .lane-header { font-size: 1.25rem; font-weight: 800; color: #f8fafc; margin-top: 2rem; margin-bottom: 1.5rem; border-bottom: 2px solid #1e293b; padding-bottom: 0.5rem; letter-spacing: 0.05em; text-transform: uppercase; }

    /* Wikipedia Banner */
    .wiki-banner { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 16px; padding: 24px; margin-bottom: 20px; display: flex; gap: 24px; align-items: center; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5); }
    .breadcrumb { font-size: 0.85rem; color: #64748b; margin-bottom: 25px; padding: 10px 15px; background: rgba(30,41,59,0.5); border-radius: 8px; display: inline-block;}
    .breadcrumb span { color: #3b82f6; font-weight: 600; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. ROBUST STATE MANAGEMENT ---
# Removed the unnecessary 'prepare_search' middle-man state
if "char_query" not in st.session_state: st.session_state.char_query = ""
if "uni_query" not in st.session_state: st.session_state.uni_query = ""
