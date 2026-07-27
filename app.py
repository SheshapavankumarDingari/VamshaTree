import os
import requests
import wikipedia
import re
import streamlit as st
from huggingface_hub import InferenceClient
from concurrent.futures import ThreadPoolExecutor

# --- 1. PAGE CONFIGURATION & THEME ---
st.set_page_config(page_title="VamshaTree | Genealogical Intelligence", page_icon="🌳", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Base Theme */
    .stApp { background-color: #0b0f19; color: #f8fafc; font-family: 'Inter', -apple-system, sans-serif; }
    
    /* SPECIFIC FIX: Pins the sidebar width and prevents auto-collapse on reruns */
    [data-testid="stSidebar"] { 
        background-color: #0f172a !important; 
        border-right: 1px solid #1e293b !important; 
        min-width: 280px !important;
    }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    [data-testid="stSidebar"] div[data-baseweb="select"] * { color: #f8fafc !important; background-color: #0f172a !important; }

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
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. STATE MANAGEMENT ---
if "char_query" not in st.session_state: st.session_state.char_query = ""
if "uni_query" not in st.session_state: st.session_state.uni_query = ""
if "trigger_search" not in st.session_state: st.session_state.trigger_search = False
if "current_results" not in st.session_state: st.session_state.current_results = None
if "search_history" not in st.session_state: st.session_state.search_history = [] 

# --- 3. SIDEBAR NAVIGATION & PRESETS ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>⚙️ VamshaTree Engine</h2>", unsafe_allow_html=True)
selected_model = st.sidebar.selectbox("AI Model", ["meta-llama/Llama-3.1-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3", "Qwen/Qwen2.5-7B-Instruct"], index=0)

st.sidebar.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<h4 style='color: #f8fafc; font-weight: 700; margin-bottom: 10px;'>Session History</h4>", unsafe_allow_html=True)

if not st.session_state.search_history:
    st.sidebar.markdown("<p style='color: #64748b; font-size: 0.85rem;'>No searches yet this session.</p>", unsafe_allow_html=True)
else:
    for item in st.session_state.search_history:
        h_name, h_uni, h_img = item
        cols = st.sidebar.columns([1, 3])
        with cols[0]:
            if h_img:
                st.markdown(f"<img src='{h_img}' style='width:32px; height:32px; border-radius:50%; object-fit:cover; border: 1px solid #3b82f6;'>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='width:32px; height:32px; border-radius:50%; background:#1e293b; display:flex; align-items:center; justify-content:center; font-size:12px; color:#94a3b8;'>{h_name[0]}</div>", unsafe_allow_html=True)
        with cols[1]:
            if st.button(f"{h_name}", key=f"history_btn_{h_name}_{h_uni}", use_container_width=True):
                st.session_state.char_query = h_name
                st.session_state.uni_query = h_uni
                st.session_state.trigger_search = True
                st.rerun()

# --- 4. DATA LOGIC ---
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_wikipedia_data(character: str, universe: str):
    try:
        search_query = f"{character} {universe}" if universe else character
        results = wikipedia.search(search_query, results=1)
        
        if not results and universe:
            results = wikipedia.search(character, results=1)
            
        if results:
            exact_title = results[0]
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(exact_title)}"
            res = requests.get(url, headers={"User-Agent": "VamshaTree/12.0"}, timeout=3)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("type") != "disambiguation":
                    summary = data.get("extract", "")
                    image = data.get("thumbnail", {}).get("source", None)
                    if summary: return summary, image
    except Exception: pass
    return "", None

def get_hf_client():
    token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    return InferenceClient(token=token) if token else None

def generate_relationships(character_name: str, universe: str, wiki_text: str, model_name: str):
    client = get_hf_client()
    if not client: raise ValueError("Hugging Face API Token missing in Streamlit Secrets.")
    prompt = f"""
    Entity: '{character_name}'
    Universe: '{universe}'
    Context Overview: {wiki_text}
    Using your internal knowledge, map the family tree for this entity.
    Extract ONLY family relationships and categorize each strictly into one of these FOUR swimlanes: [Parents], [Spouses], [Kin], or [Children].
    Return the response strictly formatted as bullet points in this EXACT structure:
    - [Category] | Relation: Target Name | Short Attribute
    """
    response = client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": "You are a precise genealogical mapper."}, {"role": "user", "content": prompt}], max_tokens=800, temperature=0.1)
    return response.choices[0].message.content

# --- 5. INTERACTIVE MODAL ---
@st.dialog("Genealogical Profile", width="large")
def show_character_modal(target_name: str, relation_type: str, summary: str, image: str, universe: str):
    st.caption(f"**RELATIONSHIP:** {relation_type.upper()}")
    st.subheader(target_name)
    
    col1, col2 = st.columns([1, 2.5])
    with col1:
        if image: st.image(image, use_column_width=True)
        else: st.info("No verified profile image found.")
    with col2:
        if summary: st.write(summary)
        else: st.warning("Verified biographical summary not currently available on Wikipedia.")
    
    st.divider()
    
    if st.button(f"Explore Lineage for {target_name} ➔", type="primary", use_container_width=True):
        st.session_state.char_query = target_name
        st.session_state.uni_query = universe 
        st.session_state.current_results = None  
        st.session_state.trigger_search = True   
        st.rerun()  

# --- UI HEADER ---
st.markdown("<br><h1 style='text-align: center; font-size: 3.5rem; font-weight: 900; color: #ffffff; letter-spacing: -1px;'>Vamsha<span style='color: #3b82f6;'>Tree</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1rem; max-width: 800px; margin: 0 auto 30px auto;'>Genealogical Intelligence: Mapping Lineages Across Legend & History.</p>", unsafe_allow_html=True)

# --- UI SEARCH ---
with st.container():
    col1, col2, col3 = st.columns([3, 3, 2])
    with col1: character = st.text_input("Entity", value=st.session_state.char_query, placeholder="Entity Name (e.g., Rama)", label_visibility="collapsed")
    with col2: universe = st.text_input("Universe", value=st.session_state.uni_query, placeholder="Universe/Context (e.g., Ramayana)", label_visibility="collapsed")
    with col3: generate_btn = st.button("Map Lineage", type="primary", use_container_width=True)

# --- LOGIC EXECUTION ---
if generate_btn or st.session_state.trigger_search:
    st.session_state.trigger_search = False
    if character and universe:
        with st.spinner(f"Mapping kinship network for {character}..."):
            try:
                wiki_summary, wiki_image = fetch_wikipedia_data(character, universe)
                
                history_entry = (character, universe, wiki_image)
                if history_entry not in st.session_state.search_history:
                    st.session_state.search_history.append(history_entry)

                raw_output = generate_relationships(character, universe, wiki_summary, selected_model)

                swimlanes = {"Parents": [], "Spouses": [], "Kin": [], "Children": []}
                
                for line in raw_output.split("\n"):
                    line = line.strip(" -*•")
                    if "|" in line and ":" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            raw_category = parts[0].strip(" []").lower()
                            rest = "|".join(parts[1:])
                            if ":" in rest:
                                rel, target_desc = rest.split(":", 1)
                                rel = rel.strip()
                                if "|" in target_desc:
                                    tgt, desc = target_desc.split("|", 1)
                                else:
                                    tgt, desc = target_desc, ""
                                    
                                tgt, desc = tgt.strip(), desc.strip()
                                
                                if tgt:
                                    if "parent" in raw_category: swimlanes["Parents"].append({"relation": rel, "target": tgt, "desc": desc})
                                    elif "spouse" in raw_category: swimlanes["Spouses"].append({"relation": rel, "target": tgt, "desc": desc})
                                    elif "kin" in raw_category or "sibling" in raw_category: swimlanes["Kin"].append({"relation": rel, "target": tgt, "desc": desc})
                                    elif "child" in raw_category: swimlanes["Children"].append({"relation": rel, "target": tgt, "desc": desc})

                all_targets = [item['target'] for lane in swimlanes.values() for item in lane]
                target_data_map = {}
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    for t_name, data in executor.map(lambda t: (t, fetch_wikipedia_data(t, universe)), all_targets):
                        target_data_map[t_name] = {"summary": data[0], "image": data[1]}

                st.session_state.current_results = { "character": character, "universe": universe, "summary": wiki_summary, "image": wiki_image, "swimlanes": swimlanes, "target_data": target_data_map }
            except Exception as err: 
                st.error(f"❌ Generation Error: {str(err)}")

# --- RESULTS RENDERING ---
if st.session_state.current_results:
    res = st.session_state.current_results
    
    banner_html = f"<div class='wiki-banner'>"
    if res['image']: 
        banner_html += f"<img src='{res['image']}' width='100' height='100' style='border-radius:50%; object-fit:cover; border: 3px solid #3b82f6;'>"
    else: 
        banner_html += f"<div style='width:100px; height:100px; border-radius:50%; background:#1e293b; border: 3px solid #475569; display:flex; align-items:center; justify-content:center; font-size:36px; font-weight:bold; color:#64748b;'>{res['character'][0].upper() if res['character'] else '?'}</div>"
    
    banner_html += f"<div><span style='background:rgba(59, 130, 246, 0.2); color:#93c5fd; font-size:10px; padding:4px 10px; border-radius:12px; font-weight:800; text-transform:uppercase;'>Verified Entity</span><h2 style='color: #ffffff; margin: 6px 0 6px 0;'>{res['character']}</h2><p style='color: #cbd5e1; font-size: 0.9rem; margin: 0; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;'>{res['summary'] or 'Summary unavailable.'}</p></div></div>"
    st.markdown(banner_html, unsafe_allow_html=True)

    if sum(len(items) for items in res["swimlanes"].values()) == 0:
         st.warning("⚠️ The AI Engine could not extract relationship data. Try providing a more specific Universe.")

    for lane_name, items in res["swimlanes"].items():
        if items:
            css_class = lane_name.split(" ")[0] 
            st.markdown(f"<div class='lane-header lane-{css_class}'>{lane_name}</div>", unsafe_allow_html=True)
            
            cols = st.columns(4)
            for idx, card in enumerate(items):
                with cols[idx % 4]:
                    with st.container(border=True):
                        t_info = res["target_data"].get(card['target'], {"summary": "", "image": None})
                        fallback = card['target'][0].upper() if card['target'] else "?"
                        
                        if t_info['image']:
                            img_html = f"<img src='{t_info['image']}' class='card-img'>"
                        else:
                            img_html = f"<div class='card-fallback'>{fallback}</div>"
                        
                        card_html = f"""
                        <div class='card-img-container'>{img_html}</div>
                        <div class='card-relation'>{card['relation']}</div>
                        <div class='card-name' title="{card['target']}">{card['target']}</div>
                        <div class='card-desc'>{card['desc']}</div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        if st.button("View Profile", key=f"btn_{lane_name}_{idx}_{card['target']}", type="primary", use_container_width=True):
                            show_character_modal(card['target'], card['relation'], t_info["summary"], t_info["image"], res["universe"])
