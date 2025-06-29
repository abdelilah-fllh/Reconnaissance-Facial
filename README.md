#Système de Contrôle d’Accès par Reconnaissance Faciale

##Create login table:
```sql
CREATE TABLE login (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    fullname TEXT NOT NULL
);
```

##updating "users" table:
```sql
ALTER TABLE users
ADD COLUMN statut TEXT,
ADD COLUMN role TEXT;
```

##Before launching the interface, run the create_admin.py script to create the admin login:  
**Username:** admin
**Password:** admin123
