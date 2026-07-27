import os
import requests
import streamlit as st
from huggingface_hub import InferenceClient

# --- 1. PAGE CONFIGURATION & THEME ---
st.set_page_config(
    page_title="VamshaTree | Genealogical Intelligence",
    page_icon="🌳",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #090d16;
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* High-contrast Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #334155 !important;
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Modern Swimlane Containers */
    .swimlane-container {
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
    }
    .swimlane-header {
        font-size: 1.3rem;
        font-weight: 800;
        color: #60a5fa;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 8px;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Ultra-Modern Button & Card Styling */
    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stButton"] button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    }

    /* Wikipedia Banner */
    .wiki-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 30px;
        display: flex;
        gap: 20px;
        align-items: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR SETTINGS ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>⚙️ VamshaTree Engine</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #94a3b8;'>Select the open-source LLM processing your lineage requests.</p>", unsafe_allow_html=True)

selected_model = st.sidebar.selectbox(
    "Choose Open AI Model",
    options=[
        "meta-llama/Llama-3.1-8B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen2.5-7B-Instruct"
    ],
    index=0
)

# --- 3. STATE MANAGEMENT FOR PRESETS ---
if "char_query" not in st.session_state:
    st.session_state.char_query = ""
if "uni_query" not in st.session_state:
    st.session_state.uni_query = ""
if "trigger_search" not in st.session_state:
    st.session_state.trigger_search = False

# --- 4. DATA FETCHING LOGIC ---
def fetch_wikipedia_data(query_term: str):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query_term)}"
    headers = {"User-Agent": "VamshaTree/3.0 (Educational)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            summary = data.get("extract", "")
            image_url = data.get("thumbnail", {}).get("source", None)
            return summary, image_url
    except Exception:
        pass
    return "", None

def get_hf_client():
    token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    if not token:
        return None
    return InferenceClient(token=token)

def generate_relationships(character_name: str, universe: str, wiki_text: str, model_name: str):
    client = get_hf_client()
    if not client:
        raise ValueError("Hugging Face Token missing! Please configure HF_TOKEN in Streamlit Secrets.")

    system_prompt = "You are a precise genealogical mapper."
    user_prompt = f"""
    Analyze the following historical/mythological overview of '{character_name}' from '{universe}':
    {wiki_text}
    
    Extract ONLY family relationships and categorize each strictly into one of these three swimlanes:
    [Parents], [Spouse & Kin], or [Children].
    Do NOT extract allies, enemies, or unrelated figures.
    
    Return the response strictly formatted as bullet points in this exact structure:
    - [Category] | [Relation Type]: [Target Name] | [Short Attribute]
    
    Example:
    - Parents | Father: Dasharatha | King of Ayodhya
    - Spouse & Kin | Wife: Sita | Princess of Mithila
    """

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=600,
        temperature=0.2
    )
    return response.choices[0].message.content

# --- 5. NATIVE MODAL POPUP ---
@st.dialog("Genealogical Profile", width="large")
def show_character_modal(target_name: str, relation_type: str):
    st.markdown(f"<span style='color:#60a5fa; font-size:12px; font-weight:bold; text-transform:uppercase; letter-spacing:1px;'>{relation_type}</span>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #ffffff; margin-top: 0;'>{target_name}</h2>", unsafe_allow_html=True)
    
    with st.spinner("Fetching authenticated records..."):
        summary, image_url = fetch_wikipedia_data(target_name)
    
    col1, col2 = st.columns([1, 2.5])
    with col1:
        if image_url:
            st.markdown(f"<img src='{image_url}' style='width: 100%; border-radius: 12px; border: 1px solid #334155;'>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='width:100%; aspect-ratio:1; border-radius:12px; background:#1e293b; display:flex; align-items:center; justify-content:center; border: 1px solid #334155;'><span style='font-size:40px;'>👤</span></div>", unsafe_allow_html=True)
    with col2:
        if summary:
            st.markdown(f"<p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>{summary}</p>", unsafe_allow_html=True)
        else:
            st.info("Verified biographical summary not currently available on Wikipedia.")
            
    if st.button("Close Profile", use_container_width=True):
        st.rerun()

# ==========================================
# UI: HEADER & INTRODUCTION
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center; font-size: 3.5rem; font-weight: 900; color: #ffffff;'>Vamsha<span style='color: #3b82f6;'>Tree</span></h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #94a3b8; font-weight: 400; margin-bottom: 5px;'>Explore Lineages & Kinships</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #60a5fa; font-size: 1.1rem; font-weight: 600;'>Genealogical Intelligence: Mapping Lineages Across Legend & History</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.95rem; max-width: 800px; margin: 0 auto 30px auto; line-height: 1.5;'>Leverage advanced genealogical intelligence to map complex kinship networks. Search for any historical or legendary figure to visualize authenticated family lineages, or select a featured character below to initiate your investigation.</p>", unsafe_allow_html=True)

# ==========================================
# UI: FEATURED FIGURES PRESETS
# ==========================================
st.markdown("<p style='color: #cbd5e1; font-weight: 600; font-size: 0.9rem; margin-bottom: 10px; text-align: center;'>Featured Figures to Explore:</p>", unsafe_allow_html=True)
preset_cols = st.columns(4)

if preset_cols[0].button("🏹 Arjuna (Mahabharata)", use_container_width=True):
    st.session_state.char_query = "Arjuna"
    st.session_state.uni_query = "Mahabharata"
    st.session_state.trigger_search = True
if preset_cols[1].button("👑 Rama (Ramayana)", use_container_width=True):
    st.session_state.char_query = "Rama"
    st.session_state.uni_query = "Ramayana"
    st.session_state.trigger_search = True
if preset_cols[2].button("⚡ Zeus (Greek Mythology)", use_container_width=True):
    st.session_state.char_query = "Zeus"
    st.session_state.uni_query = "Greek Mythology"
    st.session_state.trigger_search = True
if preset_cols[3].button("🐺 Odin (Norse Mythology)", use_container_width=True):
    st.session_state.char_query = "Odin"
    st.session_state.uni_query = "Norse Mythology"
    st.session_state.trigger_search = True

st.markdown("<hr style='border-color: #1e293b; margin: 30px 0;'>", unsafe_allow_html=True)

# ==========================================
# UI: SEARCH INPUTS (MODERN, NO LABELS)
# ==========================================
with st.container():
    col1, col2, col3 = st.columns([3, 3, 2])
    with col1:
        # label_visibility="collapsed" hides the label entirely for a clean, modern look
        character = st.text_input("Entity Name", value=st.session_state.char_query, placeholder="Entity Name (e.g., Rama)", label_visibility="collapsed")
    with col2:
        universe = st.text_input("Universe / Context", value=st.session_state.uni_query, placeholder="Universe (e.g., Ramayana)", label_visibility="collapsed")
    with col3:
        # Because the labels are collapsed, the button aligns perfectly without needing <br> spacing
        generate_btn = st.button("Generate Lineage", type="primary", use_container_width=True)

# ==========================================
# LOGIC: EXECUTE GENERATION
# ==========================================
if generate_btn or st.session_state.trigger_search:
    st.session_state.trigger_search = False # Reset trigger
    
    if not character or not universe:
        st.warning("Please provide both an Entity Name and a Universe.")
    else:
        with st.spinner("Extracting genealogical records..."):
            try:
                # 1. Fetch Main Wikipedia Data
                wiki_summary, wiki_image = fetch_wikipedia_data(f"{character} {universe}")

                # Render Main Overview Banner (Only if summary exists)
                if wiki_summary:
                    banner_html = "<div class='wiki-banner'>"
                    if wiki_image:
                        banner_html += f"<img src='{wiki_image}' width='100' height='100' style='border-radius:8px; object-fit:cover; border: 1px solid #475569;'>"
                    banner_html += f"""
                        <div>
                            <span style='background:#1e40af; color:#bfdbfe; font-size:10px; padding:3px 8px; border-radius:12px; font-weight:700; text-transform:uppercase;'>Verified Entity</span>
                            <h3 style="color: #ffffff; margin: 4px 0 6px 0;">{character} ({universe})</h3>
                            <p style="color: #cbd5e1; font-size: 0.9rem; margin: 0; line-height: 1.4;">{wiki_summary}</p>
                        </div>
                    </div>
                    """
                    st.markdown(banner_html, unsafe_allow_html=True)

                # 2. Generate AI Relationships
                raw_output = generate_relationships(character, universe, wiki_summary, selected_model)

                # 3. Parse and strictly map into 3 Swimlanes
                swimlanes = {"Parents": [], "Spouse & Kin": [], "Children": []}
                
                for line in raw_output.split("\n"):
                    if "|" in line and ":" in line:
                        clean = line.replace("-", "").strip()
                        parts = clean.split("|")
                        if len(parts) >= 3:
                            lane = parts[0].strip().replace("[", "").replace("]", "")
                            rel_info = parts[1].strip().split(":")
                            relation = rel_info[0].strip()
                            target = rel_info[1].strip() if len(rel_info) > 1 else ""
                            desc = parts[2].strip()

                            if lane in swimlanes:
                                swimlanes[lane].append({"relation": relation, "target": target, "desc": desc})

                # 4. Render Interactive Swimlanes
                st.markdown("<h2 style='margin-top: 20px; font-weight: 800; color: #f8fafc;'>Kinship Networks</h2>", unsafe_allow_html=True)
                
                for lane_name, items in swimlanes.items():
                    if items:
                        st.markdown(f"""
                            <div class="swimlane-container">
                                <div class="swimlane-header">{lane_name}</div>
                        """, unsafe_allow_html=True)
                        
                        cols = st.columns(min(len(items), 4))
                        for idx, card in enumerate(items):
                            with cols[idx % 4]:
                                # Native Interactive Streamlit Card Structure
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#60a5fa; font-size:11px; font-weight:700; text-transform:uppercase; margin-bottom:5px;'>{card['relation']}</div>", unsafe_allow_html=True)
                                    
                                    # The character's name serves as the primary action button to open the modal
                                    if st.button(f"👤 {card['target']}", key=f"modal_btn_{lane_name}_{idx}_{card['target']}", use_container_width=True):
                                        show_character_modal(card['target'], card['relation'])
                                        
                                    st.markdown(f"<div style='color:#94a3b8; font-size:12px; line-height:1.3; margin-top:5px;'>{card['desc']}</div>", unsafe_allow_html=True)
                                    
                        st.markdown("</div>", unsafe_allow_html=True)

            except Exception as err:
                st.error(f"❌ Generation interrupted: {str(err)}")
