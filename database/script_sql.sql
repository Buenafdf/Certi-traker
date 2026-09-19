-- ============================================================
-- Certi-Tracker: Gestor de Cursos
-- Script de creacion de la base de datos y la tabla principal
-- Motor: SQL Server (compatible con SQL Server Management Studio 18+)
-- ============================================================

IF DB_ID('GestorCursos') IS NULL
BEGIN
    CREATE DATABASE GestorCursos;
END;
GO

USE GestorCursos;
GO

IF OBJECT_ID('dbo.cursos_certificados', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.cursos_certificados (
        id INT IDENTITY(1,1) PRIMARY KEY,
        titulo VARCHAR(255) NOT NULL,
        plataforma VARCHAR(100),
        tipo VARCHAR(50),
        estado VARCHAR(50) DEFAULT 'Por iniciar',
        link_curso VARCHAR(MAX),
        link_certificado VARCHAR(MAX),
        fecha_registro DATETIME DEFAULT GETDATE()
    );
END;
GO

-- Tabla de historial de cursos eliminados (guarda el motivo de eliminacion)
IF OBJECT_ID('dbo.registro_eliminaciones', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.registro_eliminaciones (
        id INT IDENTITY(1,1) PRIMARY KEY,
        curso_titulo VARCHAR(255) NOT NULL,
        motivo VARCHAR(MAX),
        fecha_eliminacion DATETIME DEFAULT GETDATE()
    );
END;
GO

-- Datos de ejemplo (opcional)
-- INSERT INTO dbo.cursos_certificados (titulo, plataforma, tipo, estado, link_curso, link_certificado)
-- VALUES
--     ('Fundamentos de Python', 'Coursera', 'Gratuito', 'Completado', 'https://www.coursera.org/learn/python', 'https://www.coursera.org/certificate/abcdef'),
--     ('Flask y bases de datos', 'Udemy', 'De pago', 'En curso', 'https://www.udemy.com/course/flask', NULL);
-- GO