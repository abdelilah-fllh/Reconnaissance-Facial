# === streamlit_app.py ===
import streamlit as st
import cv2
from deepface import DeepFace
import pandas as pd
from datetime import datetime
import os
import shutil
import tempfile
from db import get_connection
from auth import get_user, verify_password, hash_password

LOG_FILE = "access_log.csv"

# Session init
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Page title
st.set_page_config(page_title="Système de Contrôle d’Accès", layout="wide")
st.title("🔐 Système de Contrôle d’Accès par Reconnaissance Faciale")

# Login form
if not st.session_state.authenticated:
    st.header("Connexion Admin")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        user = get_user(username)
        if user and verify_password(password, user['password_hash']):
            st.session_state.authenticated = True
            st.session_state.user_info = user
            st.rerun()
        else:
            st.error("Identifiants invalides.")
    st.stop()

user = st.session_state.user_info
st.sidebar.success(f"Connecté en tant que {user['fullname']}")

# Logout button
if st.sidebar.button("🚪 Se déconnecter"):
    st.session_state.authenticated = False
    st.session_state.user_info = {}
    st.rerun()

# === Admin tools ===
st.sidebar.markdown("### ➕ Ajouter un utilisateur")
new_name = st.sidebar.text_input("Nom complet")
new_role = st.sidebar.selectbox("Rôle", ["agent", "technicien", "visiteur"])
new_photo = st.sidebar.file_uploader("Photo (JPG uniquement)", type=["jpg"])

if new_name and new_photo:
    os.makedirs("images", exist_ok=True)
    filename = f"images/{new_name.replace(' ', '_')}.jpg"
    with open(filename, "wb") as f:
        f.write(new_photo.getbuffer())

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (filename, fullname, role)
            VALUES (%s, %s, %s)
        """, (filename, new_name, new_role))
        conn.commit()
        st.sidebar.success("Utilisateur ajouté avec succès ✅")
    except Exception as e:
        st.sidebar.error(f"Erreur DB : {e}")
    finally:
        cur.close()
        conn.close()

# Access logging
def log_access(person, status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame([[now, person, status]], columns=["datetime", "person", "status"])
    df.to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

# Facial recognition
def recognize_face(frame):
    temp = "temp.jpg"
    frame = cv2.resize(frame, (640, 480))
    cv2.imwrite(temp, frame)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT filename, fullname FROM users")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return "❌ Aucune image dans la base."

        path_to_name = {row[0]: row[1] for row in rows}

        with tempfile.TemporaryDirectory() as temp_dir:
            for path in path_to_name.keys():
                if os.path.exists(path):
                    img = cv2.imread(path)
                    if img is not None and img.shape[0] < 3000 and img.shape[1] < 3000:
                        shutil.copy(path, os.path.join(temp_dir, os.path.basename(path)))

            res = DeepFace.find(
                img_path=temp,
                db_path=temp_dir,
                model_name='Facenet512',
                enforce_detection=False
            )

            if res[0].shape[0] > 0:
                res[0] = res[0].iloc[:1]
                matched_path = res[0].iloc[0]['identity']
                matched_filename = os.path.basename(matched_path)
                for full_path, name in path_to_name.items():
                    if os.path.basename(full_path) == matched_filename:
                        fullname = name
                        break
                else:
                    fullname = matched_filename

                log_access(fullname, "autorisé")
                return f"✅ Accès autorisé : {fullname}"
            else:
                log_access("inconnu", "refusé")
                return "⛔ Accès refusé"
    except Exception as e:
        return f"Erreur : {e}"
    finally:
        if os.path.exists(temp):
            os.remove(temp)

# Tabs for app
tab1, tab2, tab3 = st.tabs(["📸 Scanner", "📄 Historique", "📊 Statistiques"])

with tab1:
    st.subheader("📸 Capture et reconnaissance")
    if st.button("Scanner maintenant"):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            st.image(frame, caption="Visage capturé", channels="BGR")
            message = recognize_face(frame)
            if "✅" in message:
                st.success(message)
            else:
                st.warning(message)
        cap.release()

with tab2:
    st.subheader("📄 Journal des accès")
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        st.dataframe(df)
        st.download_button("Télécharger CSV", df.to_csv(index=False), "access_log.csv")
    else:
        st.info("Aucun accès enregistré.")

with tab3:
    st.subheader("📊 Statistiques")
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        st.bar_chart(df["status"].value_counts())
    else:
        st.info("Pas encore de données.")