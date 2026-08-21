import streamlit as st
import openai
import json

# Nastavení stránky
st.set_page_config(page_title="AutoCheck CZ", page_icon="🚗")

st.title("🚗 AutoCheck CZ")
st.subheader("Rychlá analýza ojetiny pomocí AI")

# Sidebar pro API klíč (aby ho uživatel mohl vložit nebo se načetl z prostředí)
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# Formulář
with st.form("car_form"):
    col1, col2 = st.columns(2)
    model = col1.text_input("Značka a model", value="Škoda Octavia 1.5 TSI")
    year = col2.number_input("Rok výroby", min_value=1990, max_value=2026, value=2021)
    
    km = col1.number_input("Nájezd (km)", min_value=0, value=118000)
    price = col2.number_input("Cena (Kč)", min_value=0, value=399000)
    
    fuel = st.selectbox("Palivo", ["Benzín", "Nafta", "Hybrid", "Elektro"])
    gearbox = st.selectbox("Převodovka", ["Manuální", "Automatická"])
    
    submitted = st.form_submit_button("Analyzovat nabídku")

if submitted:
    if not api_key:
        st.error("Prosím, vlož v levém panelu svůj OpenAI API klíč.")
    else:
        with st.spinner('AI analyzuje data...'):
            client = openai.OpenAI(api_key=api_key)
            
            prompt = f"""
            Jsi expert na trh ojetých vozů v ČR. Analyzuj: {model}, {year}, {km} km, {price} Kč, {fuel}, {gearbox}.
            Vrať odpověď POUZE jako JSON s těmito klíči: verdict, fair_price_min, fair_price_max, price_ratio_text, servicing_cost, checklist.
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" }
                )
                data = json.loads(response.choices[0].message.content)
                
                # Zobrazení výsledků
                color = "green" if "ZAJÍMAVÁ" in data['verdict'] else "orange" if "MÍRNĚ" in data['verdict'] else "red"
                st.subheader(f"Výsledek: {data['verdict']}")
                
                st.metric("Odhadovaná férová cena", f"{data['fair_price_min']:,} - {data['fair_price_max']:,} Kč")
                st.write(f"**Poměr cena/nájezd:** {data['price_ratio_text']}")
                st.write(f"**Odhad servisu (2 roky):** {data['servicing_cost']}")
                
                st.write("### 🔍 Co zkontrolovat")
                for item in data['checklist']:
                    st.write(f"- {item}")
                    
            except Exception as e:
                st.error(f"Nastala chyba: {e}")
