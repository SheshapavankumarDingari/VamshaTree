import os
import requests
import re
import streamlit as st
from huggingface_hub import InferenceClient
from concurrent.futures import ThreadPoolExecutor

# --- 1. PAGE CONFIGURATION & THEME ---
st.set_page_config(page_title="VamshaTree | Genealogical Intelligence", page_icon="🌳", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #090d16; color: #f8fafc; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #334155 !important; }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }

    /* Semantic Swimlane Containers */
    .swimlane-Parents { border-top: 3px solid #a855f7 !important; }
    .swimlane-Spouse { border-top: 3px solid #14b8a6 !important; }
    .swimlane-Children { border-top: 3px solid #22c55e !important; }
    
    .swimlane-container {
        background: rgba(15, 23, 42, 0.4); border: 1px solid #1e293b;
        border-radius: 12px; padding: 24px; margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .swimlane-header {
        font-size: 1.1rem; font-weight: 800; color: #94a3b8;
        padding-bottom: 8px; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* --- NATIVE STREAMLIT CARD STYLING --- */
    /* Target Streamlit's native bordered containers to make them look like premium cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, #131c2e 0%, #0f172a 100%) !important;
        border: 1px solid #334155 !important;
        border-radius: 14px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #3b82f6 !important;
        transform: translateY(-4px) !important;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.25) !important;
    }

    /* Style the native button INSIDE the card to look like a sleek interactive title */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button {
        background-color: rgba(59, 130, 246, 0.05) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border-radius: 8px !important;
        padding: 4px 0 !important;
        margin: 4px 0 !important;
        min-height: 2.5rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button:hover {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    /* Wikipedia Banner */
    .wiki-banner { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px; display: flex; gap: 20px; align-items: center; }
    
    /* Breadcrumb styling */
    .breadcrumb { font-size: 0.85rem; color: #6474
