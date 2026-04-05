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
    with st.spinner('Analyse et filtrage des sports à 2 issues...'):
        # On essaie de cibler, mais le filtre interne fera le vrai travail
        url = f'https://api.the-odds-api.com/v4/sports/upcoming/odds/?apiKey={API_KEY}&regions=eu&markets=h2h'
        response = requests.get(url)
        data = response.json()
        results = []

        for match in data:
            cotes = {}
            for b in match.get('bookmakers', []):
                if b['key'] in BOOKIES_FR:
                    outcomes = b['markets'][0]['outcomes']
                    
                    # --- LA SÉCURITÉ ANTI-FOOT EST ICI ---
                    # Si outcomes a 3 éléments (V1, N, V2), c'est du foot -> On ignore.
                    if len(outcomes) == 2:
                        cotes[b['title']] = [outcomes[0]['price'], outcomes[1]['price']]
            
            # On ne continue que si on a trouvé au moins 2 bookmakers pour ce match
            if len(cotes) >= 2:
                noms_bookies = list(cotes.keys())
                for i in range(len(noms_bookies)):
                    for j in range(i + 1, len(noms_bookies)): # i+1 évite de comparer A-B puis B-A
                        
                        b1_name, b2_name = noms_bookies[i], noms_bookies[j]
                        v1, v2 = cotes[b1_name][0], cotes[b2_name][1]
                        
                        rendement = (1/v1) + (1/v2)
                        profit_theorique = (1 - rendement) * 100

                        if profit_theorique > -1.0:
                            # Calcul des mises arrondies
                            mise_1_raw = (1/v1 / rendement) * mise_totale_cible
                            mise_1_propre = round(mise_1_raw / arrondi) * arrondi
                            
                            # Ajustement mise 2
                            mise_2_propre = (mise_1_propre * v1) / v2
                            mise_2_propre = round(mise_2_propre / arrondi) * arrondi
                            
                            total_reel = mise_1_propre + mise_2_propre
                            gain_si_1 = (mise_1_propre * v1) - total_reel
                            gain_si_2 = (mise_2_propre * v2) - total_reel
                            
                            if gain_si_1 > -0.5 and gain_si_2 > -0.5:
                                results.append({
                                    'Sport': match.get('sport_title', 'Inconnu'),
                                    'Match': f"{match['home_team']} vs {match['away_team']}",
                                    'Profit %': f"{round((min(gain_si_1, gain_si_2)/total_reel)*100, 2)}%",
                                    'Mise 1': f"{int(mise_1_propre)}€ sur {b1_name} ({v1})",
                                    'Mise 2': f"{int(mise_2_propre)}€ sur {b2_name} ({v2})",
                                    'Gain Net': f"{round(min(gain_si_1, gain_si_2), 2)}€",
                                    'Total': f"{int(total_reel)}€"
                                })

        if results:
            st.success(f"✅ {len(results)} opportunités trouvées !")
            st.table(pd.DataFrame(results))
        else:
            st.info("Aucun profit détecté. Les cotes ARJEL sont très serrées !")
