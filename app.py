import os
import requests
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
    .swimlane-Parents { border-top: 3px solid #a855f7 !important; } /* Purple for Ascendants */
    .swimlane-Spouse { border-top: 3px solid #14b8a6 !important; } /* Teal for Lateral */
    .swimlane-Children { border-top: 3px solid #22c55e !important; } /* Green for Descendants */
    
    .swimlane-container {
        background: rgba(15, 23, 42, 0.4); border: 1px solid #1e293b;
        border-radius: 12px; padding: 24px; margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .swimlane-header {
        font-size: 1.1rem; font-weight: 800; color: #94a3b8;
        padding-bottom: 8px; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* FULL CARD BUTTON STYLING */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #131c2e 0%, #0f172a 100%) !important;
        border: 1px solid #334155 !important; border-radius: 12px !important;
        padding: 0 !important; height: auto !important; width: 100% !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important; display: block !important;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #3b82f6 !important; transform: translateY(-3px) !important;
        box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.2) !important;
    }

    .card-content { padding: 16px; display: flex; flex-direction: column; align-items: center; text-align: center; box-sizing: border-box; }
    .profile-img { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 2px solid #3b82f6; margin-bottom: 12px; }
    .profile-placeholder { width: 72px; height: 72px; border-radius: 50%; background-color: #1e293b; border: 2px solid #475569; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-bottom: 12px; color: #94a3b8;}
    
    .card-title { color: #ffffff; font-size: 1.05rem; font-weight: 700; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;}
    .card-desc { color: #94a3b8; font-size: 0.8rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; white-space: normal; width: 100%;}

    .wiki-banner { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px; display: flex; gap: 20px; align-items: center; }
    
    /* Breadcrumb styling */
    .breadcrumb { font-size: 0.85rem; color: #64748b; margin-bottom: 20px; }
    .breadcrumb span { color: #3b82f6; font-weight: 600; cursor: pointer; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. ROBUST STATE MANAGEMENT (CRITICAL FIX) ---
# We must explicitly define all state variables here before the app tries to read them.
if "char_query" not in st.session_state:
    st.session_state.char_query = ""
if "uni_query" not in st.session_state:
    st.session_state.uni_query = ""
if "trigger_search" not in st.session_state:
    st.session_state.trigger_search = False
if "history" not in st.session_state:
    st.session_state.history = []
if "current_results" not in st.session_state:
    st.session_state.current_results = None

# --- 3. SIDEBAR ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>⚙️ Engine Settings</h2>", unsafe_allow_html=True)
selected_model = st.sidebar.selectbox("Choose AI Model", ["meta-llama/Llama-3.1-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3", "Qwen/Qwen2.5-7B-Instruct"], index=0)

# --- 4. DATA LOGIC ---
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_wikipedia_data(query_term: str):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query_term)}"
    try:
        res = requests.get(url, headers={"User-Agent": "VamshaTree/5.0"}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return data.get("extract", ""), data.get("thumbnail", {}).get("source", None)
    except: pass
    return "", None

def get_hf_client():
    token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    return InferenceClient(token=token) if token else None

def generate_relationships(character_name: str, universe: str, wiki_text: str, model_name: str):
    client = get_hf_client()
    if not client: raise ValueError("Hugging Face Token missing!")
    prompt = f"""Analyze '{character_name}' from '{universe}':\n{wiki_text}\nExtract ONLY family relationships strictly into these swimlanes: [Parents], [Spouse & Kin], or [Children].\nFormat exactly as:\n- [Category] | [Relation Type]: [Target Name] | [Short Attribute]"""
    response = client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": "You are a precise genealogical mapper."}, {"role": "user", "content": prompt}], max_tokens=600, temperature=0.1)
    return response.choices[0].message.content

# --- 5. INTERACTIVE MODAL (With Drill-Down UX) ---
@st.dialog("Genealogical Profile", width="large")
def show_character_modal(target_name: str, relation_type: str, summary: str, image: str, universe: str):
    st.markdown(f"<span style='color:#60a5fa; font-size:12px; font-weight:bold; text-transform:uppercase;'>{relation_type}</span>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #ffffff; margin-top: 0; margin-bottom: 20px;'>{target_name}</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2.5])
    with col1:
        if image: st.markdown(f"<img src='{image}' style='width: 100%; border-radius: 12px; border: 1px solid #334155;'>", unsafe_allow_html=True)
        else: 
            fallback_char = target_name[0] if target_name else "?"
            st.markdown(f"<div class='profile-placeholder' style='width:100%; aspect-ratio:1; border-radius:12px;'>{fallback_char}</div>", unsafe_allow_html=True)
    with col2:
        if summary: st.markdown(f"<p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>{summary}</p>", unsafe_allow_html=True)
        else: st.info("Verified biographical summary not currently available on Wikipedia.")
    
    st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # UX UPGRADE: The Drill-Down Button
    if st.button(f"🔍 Explore {target_name}'s Lineage", type="primary", use_container_width=True):
        st.session_state.char_query = target_name
        st.session_state.uni_query = universe # Keep same universe
        st.session_state.trigger_search = True
        st.rerun()

# --- UI RENDERING ---
st.markdown("<br><h1 style='text-align: center; font-size: 3.5rem; font-weight: 900; color: #ffffff;'>Vamsha<span style='color: #3b82f6;'>Tree</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.95rem; max-width: 800px; margin: 0 auto 30px auto;'>Leverage advanced genealogical intelligence to map complex kinship networks.</p>", unsafe_allow_html=True)

# Breadcrumb UX
if st.session_state.history:
    path = " > ".join([f"<span>{h}</span>" for h in st.session_state.history])
    st.markdown(f"<div class='breadcrumb'>Exploration Path: {path}</div>", unsafe_allow_html=True)

with st.container():
    col1, col2, col3 = st.columns([3, 3, 2])
    with col1: character = st.text_input("Entity", value=st.session_state.char_query, placeholder="Entity Name (e.g., Rama)", label_visibility="collapsed")
    with col2: universe = st.text_input("Universe", value=st.session_state.uni_query, placeholder="Universe (e.g., Ramayana)", label_visibility="collapsed")
    with col3: generate_btn = st.button("Generate Lineage", type="primary", use_container_width=True)

# --- LOGIC EXECUTION ---
if generate_btn or st.session_state.trigger_search:
    st.session_state.trigger_search = False
    if character and universe:
        # Update History cleanly
        if not st.session_state.history or st.session_state.history[-1] != character:
            st.session_state.history.append(character)

        with st.spinner(f"Mapping kinship network for {character}..."):
            try:
                wiki_summary, wiki_image = fetch_wikipedia_data(f"{character} {universe}")
                raw_output = generate_relationships(character, universe, wiki_summary, selected_model)

                swimlanes = {"Parents": [], "Spouse & Kin": [], "Children": []}
                for line in raw_output.split("\n"):
                    if "|" in line and ":" in line:
                        clean = line.replace("-", "").strip()
                        parts = clean.split("|")
                        if len(parts) >= 3:
                            lane = parts[0].strip().replace("[", "").replace("]", "")
                            rel, tgt = parts[1].split(":")[0].strip(), parts[1].split(":")[1].strip() if ":" in parts[1] else ""
                            if lane in swimlanes and tgt:
                                swimlanes[lane].append({"relation": rel, "target": tgt, "desc": parts[2].strip()})

                all_targets = [item['target'] for lane in swimlanes.values() for item in lane]
                target_data_map = {}
                with ThreadPoolExecutor(max_workers=10) as executor:
                    for t_name, data in executor.map(lambda t: (t, fetch_wikipedia_data(t)), all_targets):
                        target_data_map[t_name] = {"summary": data[0], "image": data[1]}

                st.session_state.current_results = { "character": character, "universe": universe, "summary": wiki_summary, "image": wiki_image, "swimlanes": swimlanes, "target_data": target_data_map }
            except Exception as err: st.error(f"❌ Generation interrupted: {str(err)}")

# --- RESULTS RENDERING ---
# This is where your code crashed before. It is now safely protected by the initialization block at the top.
if st.session_state.current_results:
    res = st.session_state.current_results
    
    # Banner
    banner_html = f"<div class='wiki-banner'>"
    if res['image']: 
        banner_html += f"<img src='{res['image']}' width='90' height='90' style='border-radius:12px; object-fit:cover; border: 1px solid #475569;'>"
    else: 
        fallback = res['character'][0] if res['character'] else "?"
        banner_html += f"<div class='profile-placeholder' style='width:90px; height:90px; border-radius:12px;'>{fallback}</div>"
        
    banner_html += f"<div><span style='background:#1e40af; color:#bfdbfe; font-size:10px; padding:3px 8px; border-radius:12px; font-weight:700;'>Entity Origin</span><h3 style='color: #ffffff; margin: 4px 0 4px 0;'>{res['character']}</h3><p style='color: #cbd5e1; font-size: 0.85rem; margin: 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;'>{res['summary'] or 'Wiki data pending.'}</p></div></div>"
    st.markdown(banner_html, unsafe_allow_html=True)

    # Swimlanes
    for lane_name, items in res["swimlanes"].items():
        if items:
            css_class = lane_name.split(" ")[0] # Extracts "Parents", "Spouse", or "Children" for CSS targeting
            st.markdown(f"<div class='swimlane-container swimlane-{css_class}'><div class='swimlane-header'>{lane_name}</div>", unsafe_allow_html=True)
            cols = st.columns(min(len(items), 4))
            for idx, card in enumerate(items):
                with cols[idx % 4]:
                    t_info = res["target_data"].get(card['target'], {"summary": "", "image": None})
                    
                    fallback_char = card['target'][0] if card['target'] else "?"
                    img_html = f"<img src='{t_info['image']}' class='profile-img'>" if t_info['image'] else f"<div class='profile-placeholder'>{fallback_char}</div>"
                    
                    content = f"<div class='card-content'>{img_html}<div style='color:#60a5fa; font-size:10px; font-weight:800; text-transform:uppercase; margin-bottom:4px;'>{card['relation']}</div><div class='card-title'>{card['target']}</div><div class='card-desc'>{card['desc']}</div></div>"
                    
                    if st.button(content, key=f"btn_{lane_name}_{idx}_{card['target']}", use_container_width=True):
                        show_character_modal(card['target'], card['relation'], t_info["summary"], t_info["image"], res["universe"])
            st.markdown("</div>", unsafe_allow_html=True)
