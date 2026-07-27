import os
import requests
import streamlit as st
from huggingface_hub import InferenceClient

# --- 1. PAGE CONFIGURATION & HIGH-CONTRAST UI THEME ---
st.set_page_config(
    page_title="StoryMap Generator | Interactive Graph & Modal Engine",
    page_icon="🗺️",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #090d16;
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* High-contrast Sidebar & Navigation Styling */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #334155 !important;
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    .stSelectbox label, .stTextInput label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Swimlane Containers */
    .swimlane-container {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 24px;
        backdrop-filter: blur(8px);
    }
    .swimlane-header {
        font-size: 1.25rem;
        font-weight: 800;
        color: #60a5fa;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 8px;
        margin-bottom: 16px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Interactive Relationship Cards */
    .story-card {
        background: linear-gradient(135deg, #131c2e 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 14px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
        margin-bottom: 12px;
        text-align: center;
    }
    .card-img {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #3b82f6;
        margin-bottom: 10px;
    }
    .badge-pill {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 12px;
        border: 1px solid rgba(59, 130, 246, 0.4);
        margin-bottom: 6px;
    }
    .card-title {
        color: #ffffff !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        margin: 0 0 4px 0 !important;
    }
    .card-desc {
        color: #cbd5e1 !important;
        font-size: 0.8rem !important;
        margin: 0 0 12px 0 !important;
    }

    /* Wikipedia Summary Banner */
    .wiki-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #475569;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 30px;
        display: flex;
        gap: 20px;
        align-items: center;
    }
    .wiki-img {
        border-radius: 12px;
        object-fit: cover;
        border: 2px solid #3b82f6;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR NAVIGATION & SETTINGS ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>🗺️ StoryMap Studio</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #94a3b8;'>Navigate and configure your open AI engine.</p>", unsafe_allow_html=True)

nav_mode = st.sidebar.radio("Navigation", ["Explore StoryMap", "Project Details"])

selected_model = st.sidebar.selectbox(
    "Choose Open AI Model",
    options=[
        "meta-llama/Llama-3.1-8B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen2.5-7B-Instruct"
    ],
    index=0
)

# --- 3. WIKIPEDIA FAST REST API INTEGRATION ---
def fetch_wikipedia_data(query_term: str):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query_term)}"
    headers = {"User-Agent": "StoryMapGenerator/2.5 (Educational Project)"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            summary = data.get("extract", "No overview summary available.")
            image_url = data.get("thumbnail", {}).get("source", None)
            return summary, image_url
    except Exception:
        pass
    return "Summary unavailable.", None

# --- 4. HUGGING FACE CLIENT ---
def get_hf_client():
    token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    if not token:
        return None
    return InferenceClient(token=token)

def generate_relationships(character_name: str, universe: str, wiki_text: str, model_name: str):
    client = get_hf_client()
    if not client:
        raise ValueError("Hugging Face Token missing! Please configure HF_TOKEN in Streamlit Secrets.")

    system_prompt = "You are an expert mythological and historical relationship mapper."
    user_prompt = f"""
    Analyze the overview text about '{character_name}' in the context of '{universe}':
    {wiki_text}
    
    Extract key relationships and categorize each into one of these strict swimlane categories:
    [Parents], [Family], [Children], or [Allies].
    
    Return the response strictly formatted as bullet points in this exact structure:
    - [Category] | [Relation Type]: [Target Name] | [Short Attribute]
    
    Example:
    - Family | Wife: Sita | Princess of Mithila
    """

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=700,
        temperature=0.3
    )
    return response.choices[0].message.content

# --- 5. NATIVE MODAL WINDOW POPUP ---
@st.dialog("Character Profile & Details", width="large")
def show_character_modal(target_name: str, relation_type: str):
    st.markdown(f"<span class='badge-pill'>{relation_type}</span>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #ffffff; margin-top: 0;'>{target_name}</h2>", unsafe_allow_html=True)
    
    with st.spinner(f"Fetching live details for {target_name} from Wikipedia..."):
        summary, image_url = fetch_wikipedia_data(target_name)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if image_url:
            st.markdown(f"<img src='{image_url}' style='width: 100%; border-radius: 12px; border: 2px solid #3b82f6;'>", unsafe_allow_html=True)
        else:
            st.info("No profile image found on Wikipedia.")
    with col2:
        st.markdown(f"<p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.5;'>{summary}</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Close Window", use_container_width=True):
        st.rerun()

# ==========================================
# PAGE ROUTING: EXPLORE STORYMAP
# ==========================================
if nav_mode == "Explore StoryMap":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem; font-weight: 900; color: #ffffff;'>Story<span style='color: #3b82f6;'>Map</span> Generator</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #94a3b8; font-size: 1rem; margin-bottom: 2rem;'>Click any relationship card to open an interactive modal profile loaded via Wikipedia Fast API.</p>", unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            character = st.text_input("Character Name", value="Rama")
        with col2:
            universe = st.text_input("Universe / Context", value="Ramayana")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            generate_btn = st.button("Generate StoryMap", type="primary", use_container_width=True)

    if generate_btn:
        if not character or not universe:
            st.warning("Please enter both a character name and universe.")
        else:
            with st.spinner("Mining Wikipedia & mapping swimlanes..."):
                try:
                    # 1. Fetch Main Character Wikipedia Summary & Image
                    wiki_summary, wiki_image = fetch_wikipedia_data(f"{character} {universe}")

                    # Render Main Overview Banner
                    st.markdown("<br>", unsafe_allow_html=True)
                    banner_html = f"""
                    <div class="wiki-banner">
                    """
                    if wiki_image:
                        banner_html += f"<img src='{wiki_image}' width='120' height='120' class='wiki-img'>"
                    banner_html += f"""
                        <div>
                            <span class="badge-pill">Main Entity Overview</span>
                            <h3 style="color: #ffffff; margin: 4px 0 8px 0;">{character} ({universe})</h3>
                            <p style="color: #cbd5e1; font-size: 0.9rem; margin: 0; line-height: 1.4;">{wiki_summary}</p>
                        </div>
                    </div>
                    """
                    st.markdown(banner_html, unsafe_allow_html=True)

                    # 2. Generate AI Relationships
                    raw_output = generate_relationships(character, universe, wiki_summary, selected_model)

                    # 3. Parse and Organize into Swimlanes
                    swimlanes = {"Parents": [], "Family": [], "Children": [], "Allies": []}
                    
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

                    # Render Swimlanes Layout with Interactive Modal Triggers
                    st.markdown("<h2 style='margin-top: 30px; font-weight: 800; color: #f8fafc;'>🏊‍♂️ Relationship Swimlanes</h2>", unsafe_allow_html=True)
                    
                    for lane_name, items in swimlanes.items():
                        if items:
                            st.markdown(f"""
                                <div class="swimlane-container">
                                    <div class="swimlane-header">{lane_name} Lane</div>
                            """, unsafe_allow_html=True)
                            
                            cols = st.columns(min(len(items), 3))
                            for idx, card in enumerate(items):
                                with cols[idx % 3]:
                                    # Fetch thumbnail for the card entity
                                    _, card_img = fetch_wikipedia_data(card['target'])
                                    img_tag = f"<img src='{card_img}' class='card-img'>" if card_img else "<div style='width:70px; height:70px; border-radius:50%; background:#1e293b; margin:0 auto 10px auto; display:flex; align-items:center; justify-content:center; color:#60a5fa; font-weight:bold;'>👤</div>"
                                    
                                    st.markdown(f"""
                                        <div class="story-card">
                                            {img_tag}
                                            <span class="badge-pill">{card['relation']}</span>
                                            <h4 class="card-title">{card['target']}</h4>
                                            <p class="card-desc">{card['desc']}</p>
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Clickable button that opens modal dialog
                                    if st.button(f"🔍 View Profile", key=f"btn_{lane_name}_{idx}_{card['target']}"):
                                        show_character_modal(card['target'], card['relation'])
                                        
                            st.markdown("</div>", unsafe_allow_html=True)

                except Exception as err:
                    st.error(f"❌ Error during generation: {str(err)}")

# ==========================================
# PAGE ROUTING: PROJECT DETAILS
# ==========================================
elif nav_mode == "Project Details":
    st.markdown("<h1 style='font-weight: 800;'>📂 Project Details & Master List</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Overview of the StoryMap Generator architecture and roadmap.</p>", unsafe_allow_html=True)
    
    st.markdown("""
        <div class="swimlane-container">
            <h3 style="color: #60a5fa;">Interactive Modal & Fast API Architecture</h3>
            <p style="color: #cbd5e1; line-height: 1.5;">
            This build implements advanced UI components:
            <br>1. <strong>Wikipedia REST Summary API</strong> retrieves high-res thumbnail imagery and summaries both on initial search and dynamically inside modal windows.
            <br>2. <strong>Streamlit Native Dialogs (`@st.dialog`)</strong> power pop-up modals for every character card.
            <br>3. <strong>Swimlane Grouping</strong> organizes family, parents, children, and allies into structured visual lanes.
            </p>
        </div>
    """, unsafe_allow_html=True)
