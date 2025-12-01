DROP DATABASE IF EXISTS reto_habitos;
CREATE DATABASE reto_habitos;
USE reto_habitos;

-- =============================
-- TABLA PRINCIPAL: USERS
-- =============================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    role_id INT NOT NULL DEFAULT 2,   -- 1=admin, 2=user, 3=coach
    points INT DEFAULT 0,
    level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================
-- TABLA: RETOS
-- =============================
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

-- =============================
-- TABLA: PARTICIPANTES (no retos_usuarios)
-- =============================
CREATE TABLE participantes (
    user_id INT NOT NULL,
    reto_id INT NOT NULL,
    fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, reto_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reto_id) REFERENCES retos(id) ON DELETE CASCADE
);

-- =============================
-- TABLA: PROGRESO DIARIO
-- =============================
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

-- =============================
-- TABLA: COMENTARIOS EN RETOS
-- =============================
CREATE TABLE comentarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reto_id INT NOT NULL,
    mensaje TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reto_id) REFERENCES retos(id) ON DELETE CASCADE
);

-- =============================
-- TABLA: LOGROS
-- =============================
CREATE TABLE logros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    puntos INT NOT NULL
);

-- =============================
-- TABLA: USER_LOGROS (relación)
-- =============================
CREATE TABLE user_logros (
    user_id INT NOT NULL,
    logro_id INT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, logro_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (logro_id) REFERENCES logros(id) ON DELETE CASCADE
);

