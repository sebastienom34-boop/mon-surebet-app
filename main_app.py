import streamlit as st
import requests
import pandas as pd
import math

# --- CONFIGURATION ---
API_KEY = st.secrets["api_key"]

st.set_page_config(page_title="Surebet Scanner Pro", layout="wide")

st.title("🎯 Scanner de Surebets (Mises Arrondies)")
st.sidebar.header("⚙️ Paramètres")
mise_totale_cible = st.sidebar.number_input("Budget total environ (€)", value=100)
arrondi = st.sidebar.selectbox("Arrondir les mises à :", [1, 2, 5, 10], index=2) # Par défaut arrondi à 5€

BOOKIES_FR = ['winamax', 'pmufr', 'unibet_fr', 'betclic_fr']

if st.button('🚀 Scanner avec Mises Discrètes'):
    with st.spinner('Analyse et calcul des arrondis...'):
        # On cible uniquement les ligues majeures (disponibles partout en France)
url = f'https://api.the-odds-api.com/v4/sports/tennis_atp,tennis_wta,basketball_nba,basketball_euroleague/odds/?apiKey={API_KEY}&regions=eu&markets=h2h'
        response = requests.get(url)
        data = response.json()
        results = []

        for match in data:
            cotes = {}
            for b in match.get('bookmakers', []):
                if b['key'] in BOOKIES_FR:
                    outcomes = b['markets'][0]['outcomes']
                    cotes[b['title']] = [outcomes[0]['price'], outcomes[1]['price']]
            
            noms_bookies = list(cotes.keys())
            for i in range(len(noms_bookies)):
                for j in range(len(noms_bookies)):
                    if i == j: continue
                    
                    b1_name, b2_name = noms_bookies[i], noms_bookies[j]
                    v1, v2 = cotes[b1_name][0], cotes[b2_name][1]
                    
                    rendement = (1/v1) + (1/v2)
                    profit_theorique = (1 - rendement) * 100

                    if profit_theorique > -1.0: # On garde une marge pour le test
                        # --- CALCUL AVEC ARRONDI ---
                        # 1. Mise théorique sur le premier bookmaker
                        mise_1_raw = (1/v1 / rendement) * mise_totale_cible
                        # 2. On arrondit cette mise (ex: 48.5 -> 50)
                        mise_1_propre = round(mise_1_raw / arrondi) * arrondi
                        
                        # 3. On ajuste la mise 2 pour équilibrer par rapport à la mise 1 arrondie
                        # Formule : mise_2 = (mise_1 * cote_1) / cote_2
                        mise_2_propre = (mise_1_propre * v1) / v2
                        # On l'arrondit aussi pour la discrétion
                        mise_2_propre = round(mise_2_propre / arrondi) * arrondi
                        
                        total_reel = mise_1_propre + mise_2_propre
                        gain_si_1 = (mise_1_propre * v1) - total_reel
                        gain_si_2 = (mise_2_propre * v2) - total_reel
                        
                        # On ne garde que si les deux issues sont bénéficiaires (ou presque)
                        if gain_si_1 > -0.5 and gain_si_2 > -0.5:
                            results.append({
                                'Match': f"{match['home_team']} vs {match['away_team']}",
                                'Profit %': f"{round((min(gain_si_1, gain_si_2)/total_reel)*100, 2)}%",
                                'Mise 1': f"{int(mise_1_propre)}€ sur {b1_name} ({v1})",
                                'Mise 2': f"{int(mise_2_propre)}€ sur {b2_name} ({v2})",
                                'Gain Net min': f"{round(min(gain_si_1, gain_si_2), 2)}€",
                                'Total Misé': f"{int(total_reel)}€"
                            })

        if results:
            st.success(f"✅ {len(results)} opportunités trouvées !")
            st.table(pd.DataFrame(results))
        else:
            st.info("Aucun profit détecté avec ces arrondis. Essaie de baisser l'arrondi ou le seuil.")
