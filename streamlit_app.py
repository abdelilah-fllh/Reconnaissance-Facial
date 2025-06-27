import streamlit as st
import cv2
from deepface import DeepFace
import pandas as pd
from datetime import datetime
import os
import shutil
import tempfile
from db import get_connection

LOG_FILE = "access_log.csv"

st.set_page_config(page_title="Contrôle d'accès", layout="wide")
st.title("🔐 Système de Contrôle d’Accès par Reconnaissance Faciale")

def get_fullname_from_postgres(filename):
    try:
        filename = os.path.basename(filename)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT fullname FROM users WHERE filename LIKE %s ORDER BY id DESC LIMIT 1",
            (f"%{filename}",)
        )
        res = cur.fetchone()
        return res[0] if res else filename
    except Exception as e:
        st.error(f"[DB] {e}")
        return filename
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

def get_all_image_paths():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT filename FROM users")
        result = cur.fetchall()
        return [row[0] for row in result]
    except Exception as e:
        st.error(f"[DB] {e}")
        return []
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

def log_access(person, status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame([[now, person, status]],
                      columns=["datetime", "person", "status"])
    df.to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

def recognize_face(frame):
    temp = "temp.jpg"
    cv2.imwrite(temp, frame)
    try:
        image_paths = get_all_image_paths()
        if not image_paths:
            return "❌ Aucune image dans la base."

        with tempfile.TemporaryDirectory() as temp_dir:
            for path in image_paths:
                if os.path.exists(path):
                    shutil.copy(path, os.path.join(temp_dir, os.path.basename(path)))

            res = DeepFace.find(img_path=temp, db_path=temp_dir, enforce_detection=False)

            if res[0].shape[0] > 0:
                filename = os.path.basename(res[0].iloc[0]['identity'])
                fullname = get_fullname_from_postgres(filename)
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

st.sidebar.header("➕ Ajouter un utilisateur")
name = st.sidebar.text_input("Nom complet")
photo = st.sidebar.file_uploader("Photo (jpg)", type=['jpg'])

if name and photo:
    filename = f"{name.replace(' ', '_')}.jpg"
    img_path = os.path.join("images", filename)
    os.makedirs("images", exist_ok=True)
    with open(img_path, "wb") as f:
        f.write(photo.getbuffer())
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (filename, fullname) VALUES (%s, %s) ON CONFLICT (filename) DO NOTHING",
            (img_path, name)
        )
        conn.commit()
        st.sidebar.success(f"✅ {name} ajouté avec succès !")
    except Exception as e:
        st.sidebar.error(f"Erreur DB : {e}")
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

tab1, tab2, tab3 = st.tabs(["📸 Scanner", "📄 Historique", "📊 Stats"])

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
        df_h = pd.read_csv(LOG_FILE)
        st.dataframe(df_h)
        st.download_button("Télécharger CSV", df_h.to_csv(index=False), "access_log.csv")
    else:
        st.info("Aucun accès enregistré.")

with tab3:
    st.subheader("📊 Statistiques d'accès")
    if os.path.exists(LOG_FILE):
        df_s = pd.read_csv(LOG_FILE)
        st.bar_chart(df_s["status"].value_counts())
    else:
        st.info("Pas encore de données.")