from main import SessionLocal, User, hash_password

db = SessionLocal()

email = "contacto@unamunolegal.es"
password = "mi_password_seguro_123"

# Si existe, eliminarlo para regenerarlo limpio
user_existente = db.query(User).filter(User.email == email).first()
if user_existente:
    db.delete(user_existente)
    db.commit()

# Crear usuario con hash SHA-256
hashed_pw = hash_password(password)
nuevo_usuario = User(email=email, hashed_password=hashed_pw)

db.add(nuevo_usuario)
db.commit()
db.close()

print("¡Usuario inicial recreado con éxito con hash SHA-256!")