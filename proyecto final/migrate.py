import mysql.connector
from mysql.connector import errorcode

# CONFIGURA TU CONEXIÓN A MYSQL
CONFIG = {
    "user": "root",
    "password": "LqOENOSXqKWnVMOnhezTRehIGIrecUiL",
    "host": "mysql.railway.internal",
}

SQL_SCRIPT = """
DROP DATABASE IF EXISTS reto_habitos;
CREATE DATABASE reto_habitos;
USE reto_habitos;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    role_id INT NOT NULL DEFAULT 2,
    points INT DEFAULT 0,
    level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE retos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    duracion INT DEFAULT 7,
    publico TINYINT DEFAULT 1,
    creador_id INT NOT NULL,
    puntos_por_dia INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creador_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE participantes (
    user_id INT NOT NULL,
    reto_id INT NOT NULL,
    fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, reto_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reto_id) REFERENCES retos(id) ON DELETE CASCADE
);

CREATE TABLE progreso (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reto_id INT NOT NULL,
    fecha DATE NOT NULL,
    completado TINYINT DEFAULT 0,
    UNIQUE KEY unico (user_id, reto_id, fecha),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reto_id) REFERENCES retos(id) ON DELETE CASCADE
);

CREATE TABLE comentarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reto_id INT NOT NULL,
    mensaje TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reto_id) REFERENCES retos(id) ON DELETE CASCADE
);

CREATE TABLE logros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    puntos INT NOT NULL
);

CREATE TABLE user_logros (
    user_id INT NOT NULL,
    logro_id INT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, logro_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (logro_id) REFERENCES logros(id) ON DELETE CASCADE
);
"""

def run_migration():
    try:
        print("Conectando a MySQL...")
        connection = mysql.connector.connect(**CONFIG)
        cursor = connection.cursor()

        print("Ejecutando migración...")
        sql_commands = SQL_SCRIPT.split(";")

        for command in sql_commands:
            command = command.strip()
            if command:
                cursor.execute(command)

        print("Migración completada con éxito 💙")

    except mysql.connector.Error as err:
        print("Error al ejecutar migración:", err)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    run_migration()
