-- Certi-Tracker: esquema SQLite
-- Ejecutado automáticamente por init_db() al arrancar la app

CREATE TABLE IF NOT EXISTS cursos_certificados (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT    NOT NULL CHECK(length(titulo) <= 255),
    plataforma       TEXT    CHECK(length(plataforma) <= 100),
    tipo             TEXT    CHECK(tipo IS NULL OR tipo = '' OR tipo IN ('Gratuito', 'De pago')),
    estado           TEXT    NOT NULL DEFAULT 'Por iniciar'
                             CHECK(estado IN ('Por iniciar', 'En curso', 'Completado')),
    link_curso       TEXT    CHECK(length(link_curso) <= 2048),
    link_certificado TEXT    CHECK(length(link_certificado) <= 2048),
    fecha_registro   TEXT    NOT NULL DEFAULT (datetime('now', '-5 hours'))
);

CREATE TABLE IF NOT EXISTS registro_eliminaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    curso_titulo     TEXT    NOT NULL,
    motivo           TEXT    CHECK(length(motivo) <= 1000),
    fecha_eliminacion TEXT   NOT NULL DEFAULT (datetime('now', '-5 hours'))
);

