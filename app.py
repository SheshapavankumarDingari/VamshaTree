import os
import streamlit as st
import wikipedia
from google import genai

# --- 1. PAGE CONFIGURATION & SLATE THEME ---
st.set_page_config(
    page_title="StoryMap Generator | AI Lineage & Relationship Engine",
    page_icon="🗺️",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .story-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(51, 65, 85, 0.6);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        margin-bottom: 16px;
    }
    .badge-pill {
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
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR MODEL CONFIGURATION DROPDOWN ---
st.sidebar.markdown("<h2 style='color: #f8fafc; font-weight: 800;'>⚙️ Engine Settings</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #94a3b8;'>Select your target Gemini model dynamically without touching code.</p>", unsafe_allow_html=True)

selected_model = st.sidebar.selectbox(
    "Choose Gemini Model",
    options=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"],
    index=0 # Defaults to gemini-1.5-flash (most universally stable)
)

# --- 3. GEMINI CLIENT INITIALIZATION ---
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

# --- 4. CORE STORYMAP EXTRACTION FUNCTION ---
def generate_story_map_data(character_name: str, context_universe: str, model_name: str):
    client = get_gemini_client()
    if not client:
        raise ValueError("Gemini API Key missing! Please configure GEMINI_API_KEY in your Streamlit Secrets.")

    # 1. Scrape Wikipedia page
    try:
        wiki_page = wikipedia.page(f"{character_name} {context_universe}")
        raw_text = wiki_page.content[:15000] # Limit text length for token efficiency
    except wikipedia.exceptions.DisambiguationError as e:
        wiki_page = wikipedia.page(e.options[0])
        raw_text = wiki_page.content[:15000]
    except Exception as e:
        raise RuntimeError(f"Wikipedia search failed: {str(e)}")

    # 2. Prompt Gemini using the model selected from the dropdown
    prompt = f"""
    You are an expert mythological and historical relationship mapper.
    Analyze the text below about '{character_name}' in the context of '{context_universe}'.
    Extract key relationships (Father, Mother, Spouse, Child, Sibling, Ally, Enemy) and essential attributes.
    
    Return the response cleanly formatted as items separated by bullet points in this exact structure:
    - [Relation Type]: [Target Name] | [Short Attribute or Description]
    
    Source Text:
    {raw_text}
    """

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return response.text

# --- 5. STREAMLIT USER INTERFACE ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center; font-size: 3rem; font-weight: 900;'>Story<span style='color: #3b82f6;'>Map</span> Generator</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #94a3b8; font-size: 1rem; margin-bottom: 2rem;'>Active AI Engine: <strong style='color: #60a5fa;'>{selected_model}</strong></p>", unsafe_allow_html=True)

# Input Form
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
        with st.spinner(f"Mining Wikipedia & analyzing relationships using {selected_model}..."):
            try:
                raw_output = generate_story_map_data(character, universe, selected_model)
                
                st.success(f"Successfully generated StoryMap for {character}!")
                st.markdown(f"<h3 style='margin-top: 30px; font-weight: 700;'>Relationship & Attribute Graph</h3>", unsafe_allow_html=True)

                # Parse and render Gemini bullet points into modern UI cards
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
                                    <h4 style="color: #f8fafc; margin: 4px 0 8px 0; font-weight: 700;">{card['target']}</h4>
                                    <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">{card['desc']}</p>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='story-card'><p>{raw_output}</p></div>", unsafe_allow_html=True)

            except Exception as err:
                st.error(f"❌ Error during generation: {str(err)}")
