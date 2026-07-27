import os
import streamlit as st
import wikipedia
from huggingface_hub import InferenceClient

# --- 1. PAGE CONFIGURATION & HIGH-CONTRAST SLATE THEME ---
st.set_page_config(
    page_title="StoryMap Generator | Open-Source AI Engine",
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
    .stTextInput label, .stSelectbox label {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    .story-card {
        background: linear-gradient(135deg, #131c2e 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 22px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        margin-bottom: 16px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .story-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }
    .badge-pill {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 5px 12px;
        border-radius: 20px;
        border: 1px solid rgba(59, 130, 246, 0.4);
        margin-bottom: 10px;
    }
    .card-title {
        color: #ffffff !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        margin: 4px 0 8px 0 !important;
    }
    .card-desc {
        color: #cbd5e1 !important;
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
        margin: 0 !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR FREE OPEN-SOURCE MODEL DROPDOWN ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>⚙️ Open Engine Settings</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #94a3b8;'>Select a free open-source model hosted via Hugging Face.</p>", unsafe_allow_html=True)

selected_model = st.sidebar.selectbox(
    "Choose Open Model",
    options=[
        "meta-llama/Llama-3.1-8B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen2.5-7B-Instruct"
    ],
    index=0
)

# --- 3. HUGGING FACE CLIENT INITIALIZATION ---
def get_hf_client():
    token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    if not token:
        return None
    return InferenceClient(token=token)

# --- 4. CORE STORYMAP EXTRACTION FUNCTION ---
def generate_story_map_data(character_name: str, context_universe: str, model_name: str):
    client = get_hf_client()
    if not client:
        raise ValueError("Hugging Face Token missing! Please configure HF_TOKEN in your Streamlit Secrets.")

    # 1. Scrape Wikipedia page
    try:
        wiki_page = wikipedia.page(f"{character_name} {context_universe}")
        raw_text = wiki_page.content[:12000] # Limit token length for open-source limits
    except wikipedia.exceptions.DisambiguationError as e:
        wiki_page = wikipedia.page(e.options[0])
        raw_text = wiki_page.content[:12000]
    except Exception as e:
        raise RuntimeError(f"Wikipedia search failed: {str(e)}")

    # 2. Craft prompt for open-source model instructions
    system_prompt = "You are an expert mythological and historical relationship mapper. Extract key relationships and attributes cleanly."
    user_prompt = f"""
    Analyze the text below about '{character_name}' in the context of '{context_universe}'.
    Extract key relationships (Father, Mother, Spouse, Child, Sibling, Ally, Enemy) and essential attributes.
    
    Return the response strictly formatted as bullet points in this exact structure:
    - [Relation Type]: [Target Name] | [Short Attribute or Description]
    
    Source Text:
    {raw_text}
    """

    # 3. Call Hugging Face Serverless Chat Completion API
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=800,
        temperature=0.3
    )
    return response.choices[0].message.content

# --- 5. STREAMLIT USER INTERFACE ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center; font-size: 3rem; font-weight: 900; color: #ffffff;'>Story<span style='color: #3b82f6;'>Map</span> Generator</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #94a3b8; font-size: 1rem; margin-bottom: 2rem;'>Active Free Open Model: <strong style='color: #60a5fa;'>{selected_model}</strong></p>", unsafe_allow_html=True)

# Input Form Container
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
        st.warning("Please enter both a character name and context universe.")
    else:
        with st.spinner(f"Mining Wikipedia & querying {selected_model}..."):
            try:
                raw_output = generate_story_map_data(character, universe, selected_model)
                
                st.success(f"Successfully generated StoryMap for {character}!")
                st.markdown(f"<h3 style='margin-top: 30px; font-weight: 700; color: #f8fafc;'>Relationship & Attribute Graph</h3>", unsafe_allow_html=True)

                # Parse and render output into cards
                lines = raw_output.split("\n")
                cards_data = []
                for line in lines:
                    if ":" in line and "|" in line:
                        clean_line = line.replace("-", "").strip()
                        parts = clean_line.split(":", 1)
                        relation = parts[0].strip()
                        rest = parts[1].split("|", 1)
                        target = rest[0].strip()
                        desc = rest[1].strip() if len(rest) > 1 else ""
                        cards_data.append({"relation": relation, "target": target, "desc": desc})

                if cards_data:
                    cols = st.columns(3)
                    for idx, card in enumerate(cards_data):
                        with cols[idx % 3]:
                            st.markdown(f"""
                                <div class="story-card">
                                    <span class="badge-pill">{card['relation']}</span>
                                    <h4 class="card-title">{card['target']}</h4>
                                    <p class="card-desc">{card['desc']}</p>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='story-card'><p style='color: #f8fafc;'>{raw_output}</p></div>", unsafe_allow_html=True)

            except Exception as err:
                st.error(f"❌ Error during generation: {str(err)}")
