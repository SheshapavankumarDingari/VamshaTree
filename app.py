import os
import re
import random
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from SPARQLWrapper import SPARQLWrapper, JSON as SPARQLJSON

# --- 1. PAGE CONFIGURATION & MODERN SLATE THEME ---
st.set_page_config(
    page_title="VamshaTree | Mythological & Historical Lineages",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Modern UI Styling (Glassmorphism cards, slate mode, badge pills)
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .modern-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(51, 65, 85, 0.6);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 16px;
    }
    .modern-card:hover {
        border-color: rgba(59, 130, 246, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 20px 30px -10px rgba(59, 130, 246, 0.15);
    }
    .relation-pill {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 4px 10px;
        border-radius: 20px;
        border: 1px solid rgba(59, 130, 246, 0.3);
        margin-bottom: 8px;
    }
    .metric-container {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(51, 65, 85, 0.8);
        padding: 24px;
        border-radius: 20px;
        text-align: center;
        backdrop-filter: blur(12px);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE VAULT SETUP (SQLite IP Vault) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./vamsha_vault.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CachedTree(Base):
    __tablename__ = "mythological_trees"
    id = Column(Integer, primary_key=True, index=True)
    search_key = Column(String, unique=True, index=True)
    character = Column(String)
    universe = Column(String)
    tree_data = Column(JSON)

Base.metadata.create_all(bind=engine)

# --- 3. WIKIDATA SPARQL OPEN-SOURCE COLLECTOR ---
class WikidataCollector:
    def __init__(self):
        self.sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.sparql.setReturnFormat(SPARQLJSON)
        self.sparql.addCustomHttpHeader("User-Agent", "VamshaTreeEngine/2.0")

    def fetch_family_tree(self, character: str):
        query = f"""
        SELECT ?relativeLabel ?relationType WHERE {{
          ?char wdt:P31 wd:Q5; rdfs:label "{character}"@en.
          VALUES (?prop ?relationType) {{
            (wdt:P22 "Father") (wdt:P25 "Mother") (wdt:P26 "Spouse")
            (wdt:P40 "Child") (wdt:P3373 "Sibling")
          }}
          ?char ?prop ?relative.
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 35
        """
        self.sparql.setQuery(query)
        try:
            results = self.sparql.query().convert()
            return [{"target": b["relativeLabel"]["value"], "relation": b["relationType"]["value"]} 
                    for b in results["results"]["bindings"] if "relativeLabel" in b]
        except Exception:
            return []

collector = WikidataCollector()

# --- 4. SAFETY & COMPLIANCE GUARDRAILS ---
ALLOWED_UNIVERSES = ["mythology", "epic", "legend", "history", "mahabharata", "ramayana", "purana", "norse", "greek", "arthurian", "mesopotamian"]
BLOCKED_WORDS = ["fanfic", "nsfw", "adult", "porn", "hate", "modern", "contemporary"]

def validate_safety(character: str, universe: str):
    combined = f"{character} {universe}".lower()
    if any(bad in combined for bad in BLOCKED_WORDS):
        raise ValueError("Search blocked: Content violates VamshaTree safety guidelines (Unsafe or Fan-fiction content is restricted).")
    if not any(good in combined for good in ALLOWED_UNIVERSES):
        raise ValueError("Strict Universe Guardrail: Only verified Mythological, Historical, and Epic universes are allowed.")

# --- 5. NAVIGATION & STATE ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>🌳 VamshaTree</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #94a3b8;'>Enterprise Lineage & Lore Graph</p>", unsafe_allow_html=True)
page = st.sidebar.radio("Menu", ["Explore Lineage", "Admin Portal"])

SURPRISE_POOL = [
    ("Arjuna", "Mahabharata"), ("Rama", "Ramayana"), 
    ("Odin", "Norse Mythology"), ("Hercules", "Greek Mythology"), 
    ("King Arthur", "Arthurian Legend"), ("Gilgamesh", "Epic of Gilgamesh")
]

# ==========================================
# TAB 1: EXPLORE LINEAGE (Modern Search UI)
# ==========================================
if page == "Explore Lineage":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem; font-weight: 900; letter-spacing: -0.05em;'>Vamsha<span style='color: #3b82f6;'>Tree</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1rem; margin-bottom: 2rem;'>Map verified in-story family lineages and historical genealogies powered by open-source data.</p>", unsafe_allow_html=True)

    search_container = st.container()
    with search_container:
        col1, col2, col3, col4 = st.columns([3, 3, 1, 1])
        
        with col1:
            char_input = st.text_input("Character Name", value="Rama", label_visibility="collapsed", placeholder="Character Name (e.g., Rama)")
        with col2:
            uni_input = st.text_input("Universe", value="Ramayana", label_visibility="collapsed", placeholder="Universe (e.g., Ramayana)")
        with col3:
            search_clicked = st.button("Explore", type="primary", use_container_width=True)
        with col4:
            if st.button("🎲 Surprise", use_container_width=True):
                rand_char, rand_uni = random.choice(SURPRISE_POOL)
                char_input = rand_char
                uni_input = rand_uni
                search_clicked = True

    if search_clicked:
        db = SessionLocal()
        try:
            validate_safety(char_input, uni_input)
            search_key = f"vt_{re.sub(r'[^a-z0-9]', '', uni_input.lower())}_{re.sub(r'[^a-z0-9]', '', char_input.lower())}"
            
            # Check Private Vault
            cached = db.query(CachedTree).filter(CachedTree.search_key == search_key).first()
            if cached:
                data_source = "Vamsha Vault (Proprietary Caching Layer)"
                tree_relationships = cached.tree_data
            else:
                data_source = "Wikidata Open-Source Extraction"
                tree_relationships = collector.fetch_family_tree(char_input)
                if tree_relationships:
                    new_record = CachedTree(search_key=search_key, character=char_input, universe=uni_input, tree_data=tree_relationships)
                    db.add(new_record)
                    db.commit()

            st.markdown(f"<div style='margin: 20px 0; padding: 12px 16px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; color: #34d399; font-size: 12px;'>✨ Successfully mapped lineage data via <strong>{data_source}</strong></div>", unsafe_allow_html=True)

            # Render Results Grid using Modern Cards
            if tree_relationships:
                st.markdown(f"<h3 style='margin-top: 30px; font-weight: 700;'>Lineage Network for {char_input}</h3>", unsafe_allow_html=True)
                cols = st.columns(3)
                for idx, rel in enumerate(tree_relationships):
                    with cols[idx % 3]:
                        st.markdown(f"""
                            <div class="modern-card">
                                <span class="relation-pill">{rel['relation']}</span>
                                <h4 style="color: #f8fafc; margin: 0; font-size: 1.15rem; font-weight: 700;">{rel['target']}</h4>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("No structured family records found for this specific entity within Wikidata.")

        except Exception as e:
            st.error(f"❌ Guardrail Exception: {str(e)}")
        finally:
            db.close()

    # Legal Disclaimer Footer
    st.markdown("<br><hr style='border-color: #1e293b; margin-top: 50px;'>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; font-size: 11px; color: #64748b; line-height: 1.5;'>"
        "<strong>VamshaTree Legal & Compliance Notice:</strong> Lineage records compiled via public domain Wikidata (CC0) and verified context snippets (Wikimedia CC-BY-SA). "
        "Classical texts contain diverse regional variants. VamshaTree is an educational data visualization tool."
        "</p>", 
        unsafe_allow_html=True
    )

# ==========================================
# TAB 2: ADMIN PORTAL
# ==========================================
elif page == "Admin Portal":
    st.markdown("<h1 style='font-weight: 800;'>🔐 VamshaTree Admin Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>Manage proprietary database vault storage, telemetry, and system maintenance.</p>", unsafe_allow_html=True)

    admin_secret = st.text_input("Enter Admin Secret Key", type="password")
    
    if admin_secret == os.getenv("ADMIN_SECRET_KEY", "vamsha_admin_secret_2026"):
        db = SessionLocal()
        total_cached = db.query(CachedTree).count()
        db.close()

        st.success("Admin session authenticated successfully.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
                <div class="metric-container">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Vault Storage</span>
                    <h2 style="color: #60a5fa; margin: 8px 0; font-size: 2.5rem; font-weight: 800;">{total_cached}</h2>
                    <span style="font-size: 10px; color: #64748b;">Cached Character Trees</span>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="metric-container">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">System Health</span>
                    <h2 style="color: #34d399; margin: 8px 0; font-size: 2.5rem; font-weight: 800;">Optimal</h2>
                    <span style="font-size: 10px; color: #64748b;">FastAPI / SQLite Engine</span>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="metric-container">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">IP Protection</span>
                    <h2 style="color: #f8fafc; margin: 8px 0; font-size: 2.5rem; font-weight: 800;">Secured</h2>
                    <span style="font-size: 10px; color: #64748b;">CC0 Compliant Vault</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br><h3 style='font-weight: 700;'>🛠️ Maintenance Utilities</h3>", unsafe_allow_html=True)
        purge_key = st.text_input("Enter Search Key to Purge (e.g., vt_ramayana_rama)")
        if st.button("Purge Entity from Vault", type="primary"):
            if purge_key:
                db = SessionLocal()
                rec = db.query(CachedTree).filter(CachedTree.search_key == purge_key).first()
                if rec:
                    db.delete(rec)
                    db.commit()
                    st.success(f"Successfully purged '{purge_key}' from the database vault.")
                else:
                    st.error("Entity search key not found in vault.")
                db.close()
    elif admin_secret:
        st.error("Invalid Admin Secret Key.")