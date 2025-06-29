import cv2
from deepface import DeepFace
import pandas as pd
from datetime import datetime
import os
import shutil
import tempfile
from db import get_connection

LOG_FILE = "access_log.csv"

def get_fullname_from_filename(filename):
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
        print(f"[DB ERROR] {e}")
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
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

def log_access(person, status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame([[now, person, status]], columns=["datetime", "person", "status"])
    df.to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

def recognize_face(img_path):
    try:
        image_paths = get_all_image_paths()
        if not image_paths:
            print("❌ Aucune image dans la base de données.")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            for path in image_paths:
                if os.path.exists(path):
                    shutil.copy(path, os.path.join(temp_dir, os.path.basename(path)))

            res = DeepFace.find(img_path=img_path, db_path=temp_dir,
                                enforce_detection=False, detector_backend='opencv')

            if res[0].shape[0] > 0:
                filename = os.path.basename(res[0].iloc[0]['identity'])
                fullname = get_fullname_from_filename(filename)
                print(f"✅ Accès autorisé : {fullname}")
                log_access(fullname, "autorisé")
            else:
                print("⛔ Accès refusé")
                log_access("inconnu", "refusé")
    except Exception as e:
        print(f"[RECOGNITION ERROR] {e}")

# === Webcam Execution ===
cap = cv2.VideoCapture(0)
print("Appuyez sur ESPACE pour scanner, 'q' pour quitter.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Contrôle d'accès", frame)
    key = cv2.waitKey(1)

    if key == ord(' '):
        temp = "temp.jpg"
        cv2.imwrite(temp, frame)
        recognize_face(temp)
        os.remove(temp)
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
