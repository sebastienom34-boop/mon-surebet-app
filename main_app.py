import streamlit as st
import requests
import pandas as pd

# --- CONFIGURATION ---
# Assure-toi que ta clé API est bien dans les secrets de Streamlit
API_KEY = st.secrets["api_key"]

st.set_page_config(page_title="Surebet Scanner ARJEL", layout="wide")

st.title("🎯 Scanner de Surebets : Winamax | Unibet | Betclic")
st.sidebar.header("⚙️ Paramètres de mise")
mise_totale_cible = st.sidebar.number_input("Budget total souhaité (€)", value=100)
arrondi = st.sidebar.selectbox("Arrondir les mises à :", [1, 2, 5, 10], index=2) 

# Liste précise des clés API pour les 3 gros bookmakers FR
# Note : 'unibet_fr' et 'betclic_fr' sont les clés standards de l'API
BOOKIES_CIBLES = ['winamax', 'unibet_fr', 'betclic_fr']

if st.button('🚀 Lancer le Scan (Tennis, Basket, Volley)'):
    with st.spinner('Analyse des décalages de cotes...'):
        # On scanne la région 'eu' (Europe) qui contient nos 3 bookmakers
        url = f'https://api.the-odds-api.com/v4/sports/upcoming/odds/?apiKey={API_KEY}&regions=eu&markets=h2h'
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if response.status_code != 200:
                st.error(f"Erreur API : {data.get('message', 'Impossible de récupérer les données')}")
                st.stop()

            results = []

            for match in data:
                cotes = {}
                # 1. Extraction des cotes pour nos 3 bookmakers uniquement
                for b in match.get('bookmakers', []):
                    if b['key'] in BOOKIES_CIBLES:
                        market = b['markets'][0]
                        outcomes = market['outcomes']
                        
                        # --- SÉCURITÉ ANTI-PIÈGE (FOOT) ---
                        # On ignore les matchs à 3 issues (Victoire, Nul, Défaite)
                        # On ne garde que le Tennis, Basket, etc. (2 issues)
                        if len(outcomes) != 2:
                            continue
                            
                        # On stocke les cotes avec le nom du joueur/équipe pour être précis
                        cotes[b['title']] = {o['name']: o['price'] for o in outcomes}

                # 2. Comparaison croisée des cotes
                noms_bookies_trouves = list(cotes.keys())
                
                # Il nous faut au moins 2 bookmakers différents sur le match
                if len(noms_bookies_trouves) >= 2:
                    for i in range(len(noms_bookies_trouves)):
                        for j in range(i + 1, len(noms_bookies_trouves)):
                            b1_name = noms_bookies_trouves[i]
                            b2_name = noms_bookies_trouves[j]
                            
                            equipes = list(cotes[b1_name].keys())
                            if len(equipes) < 2: continue
                            
                            eq1, eq2 = equipes[0], equipes[1]
                            
                            # On teste les deux combinaisons possibles
                            # Combinaison A : Mise sur Equipe 1 chez Bookie 1 / Mise sur Equipe 2 chez Bookie 2
                            v1_a, v2_a = cotes[b1_name][eq1], cotes[b2_name][eq2]
                            # Combinaison B : Mise sur Equipe 2 chez Bookie 1 / Mise sur Equipe 1 chez Bookie 2
                            v1_b, v2_b = cotes[b1_name][eq2], cotes[b2_name][eq1]

                            for v1, v2, nom_1, nom_2, bk1, bk2 in [
                                (v1_a, v2_a, eq1, eq2, b1_name, b2_name),
                                (v1_b, v2_b, eq2, eq1, b1_name, b2_name)
                            ]:
                                rendement = (1/v1) + (1/v2)
                                
                                # Si rendement < 1 = Surebet détecté !
                                if rendement < 0.999: # On accepte à partir de 0.1% de profit
                                    
                                    # --- CALCUL DES MISES ARRONDIES ---
                                    # Mise théorique pour équilibrer parfaitement
                                    m1_raw = (1/v1 / rendement) * mise_totale_cible
                                    m1 = round(m1_raw / arrondi) * arrondi
                                    if m1 == 0: m1 = arrondi
                                    
                                    # Mise 2 calculée par rapport à la mise 1 arrondie
                                    m2_raw = (m1 * v1) / v2
                                    m2 = round(m2_raw / arrondi) * arrondi
                                    if m2 == 0: m2 = arrondi
                                    
                                    total_misé = m1 + m2
                                    gain_si_1 = (m1 * v1) - total_misé
                                    gain_si_2 = (m2 * v2) - total_misé
                                    profit_min = min(gain_si_1, gain_si_2)
                                    perc = (profit_min / total_misé) * 100

                                    if profit_min > -0.2: # On affiche si c'est au moins à l'équilibre
                                        results.append({
                                            'Sport': match['sport_title'],
                                            'Match': f"{eq1} vs {eq2}",
                                            'Profit %': f"{round(perc, 2)}%",
                                            'Pari 1': f"{int(m1)}€ sur {bk1} ({nom_1} @{v1})",
                                            'Pari 2': f"{int(m2)}€ sur {bk2} ({nom_2} @{v2})",
                                            'Bénéfice Net': f"{round(profit_min, 2)}€",
                                            'Total à miser': f"{int(total_misé)}€"
                                        })

            if results:
                st.success(f"✅ {len(results)} opportunités détectées !")
                df = pd.DataFrame(results)
                # On trie par profit maximum
                df = df.sort_values(by='Profit %', ascending=False)
                st.table(df)
            else:
                st.info("Aucun surebet détecté actuellement sur ce trio. Réessaie dans quelques minutes !")
                
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Conseil :** Privilégie le Tennis et la NBA. Le Foot est ignoré car le match nul n'est pas géré ici.")
