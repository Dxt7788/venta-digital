from werkzeug.security import generate_password_hash

# Encriptar la contraseña
password = 'MCPE1234'
hashed_password = generate_password_hash(password)
print(hashed_password)
