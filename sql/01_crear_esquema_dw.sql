-- ============================================================
-- DATA WAREHOUSE - EVA AGRÍCOLA
-- Proyecto ETL - ODS 2: Hambre Cero
--
-- Archivo: 01_crear_esquema_dw.sql
-- Propósito: Crear la estructura física del Data Warehouse
-- ============================================================


-- ============================================================
-- 1. CREACIÓN DE LA BASE DE DATOS
-- ============================================================

CREATE DATABASE IF NOT EXISTS dw_eva_agricola
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE dw_eva_agricola;


-- ============================================================
-- 2. ELIMINACIÓN DE TABLAS EXISTENTES
-- ============================================================
-- Se eliminan primero las tablas que contienen FK.

DROP TABLE IF EXISTS fact_produccion_agricola;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_cultivo;
DROP TABLE IF EXISTS dim_geografia;


-- ============================================================
-- 3. DIMENSIÓN GEOGRAFÍA
-- ============================================================
-- Representa el lugar donde se realiza la observación agrícola.
--
-- Grain:
-- Una fila representa un municipio.
--
-- Identificador de negocio:
-- codigo_municipio
--
-- No se implementa SCD Type 2 porque el análisis histórico
-- 2019-2025 no encontró variaciones en los atributos geográficos.
-- ============================================================

CREATE TABLE dim_geografia (

    sk_geografia INT UNSIGNED NOT NULL AUTO_INCREMENT,

    codigo_departamento VARCHAR(2) NOT NULL,
    departamento VARCHAR(100) NOT NULL,

    codigo_municipio VARCHAR(5) NOT NULL,
    municipio VARCHAR(100) NOT NULL,

    PRIMARY KEY (sk_geografia),

    UNIQUE KEY uk_dim_geografia_codigo_municipio
        (codigo_municipio)

) ENGINE = InnoDB
  DEFAULT CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;


-- ============================================================
-- 4. DIMENSIÓN CULTIVO
-- ============================================================
-- Representa el cultivo y su clasificación agrícola.
--
-- Grain:
-- Una fila representa un código de cultivo.
--
-- Identificador de negocio:
-- codigo_cultivo
--
-- El análisis histórico 2019-2025 no encontró variaciones
-- en los atributos asociados a los códigos de cultivo.
-- Por tanto, no se implementa SCD Type 2.
-- ============================================================

CREATE TABLE dim_cultivo (

    sk_cultivo INT UNSIGNED NOT NULL AUTO_INCREMENT,

    codigo_cultivo VARCHAR(7) NOT NULL,

    grupo_cultivo VARCHAR(100) NOT NULL,
    subgrupo VARCHAR(100) NOT NULL,

    cultivo VARCHAR(100) NOT NULL,
    desagregacion_cultivo VARCHAR(100) NOT NULL,

    nombre_cientifico VARCHAR(100) NOT NULL,

    ciclo_cultivo VARCHAR(20) NOT NULL,

    PRIMARY KEY (sk_cultivo),

    UNIQUE KEY uk_dim_cultivo_codigo
        (codigo_cultivo)

) ENGINE = InnoDB
  DEFAULT CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;


-- ============================================================
-- 5. DIMENSIÓN TIEMPO
-- ============================================================
-- Representa los períodos de observación definidos por EVA.
--
-- No se utiliza un calendario diario.
--
-- Ejemplos de periodo:
-- 2019
-- 2019A
-- 2019B
-- 2020
-- 2020A
-- 2020B
--
-- El período anual es una observación independiente de A y B.
-- No se calcula automáticamente como A + B.
--
-- Grain:
-- Una fila representa un período EVA.
--
-- Identificador de negocio:
-- periodo
-- ============================================================

CREATE TABLE dim_tiempo (

    sk_tiempo INT UNSIGNED NOT NULL AUTO_INCREMENT,

    anio SMALLINT UNSIGNED NOT NULL,

    periodo VARCHAR(5) NOT NULL,

    tipo_periodo VARCHAR(20) NOT NULL,

    semestre CHAR(1) NULL,

    PRIMARY KEY (sk_tiempo),

    UNIQUE KEY uk_dim_tiempo_periodo
        (periodo)

) ENGINE = InnoDB
  DEFAULT CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;


-- ============================================================
-- 6. TABLA DE HECHOS
-- ============================================================
-- Representa la observación agrícola.
--
-- Grain:
--
-- Una fila representa una observación agrícola de un cultivo,
-- en un municipio, para un período específico de un año
-- determinado.
--
-- Grain de negocio:
--
-- municipio + cultivo + año/periodo
--
-- En el modelo físico se representa mediante:
--
-- sk_geografia + sk_cultivo + sk_tiempo
--
-- Esta combinación debe ser única.
-- ============================================================

CREATE TABLE fact_produccion_agricola (

    sk_produccion_agricola INT UNSIGNED NOT NULL AUTO_INCREMENT,

    sk_geografia INT UNSIGNED NOT NULL,
    sk_cultivo INT UNSIGNED NOT NULL,
    sk_tiempo INT UNSIGNED NOT NULL,

    area_sembrada DECIMAL(7,2) NOT NULL,
    area_cosechada DECIMAL(7,2) NOT NULL,

    produccion DECIMAL(9,2) NOT NULL,
    rendimiento DECIMAL(5,2) NOT NULL,

    PRIMARY KEY (sk_produccion_agricola),

    -- Protección física del grain
    UNIQUE KEY uk_fact_grain (
        sk_geografia,
        sk_cultivo,
        sk_tiempo
    ),

    -- Integridad referencial
    CONSTRAINT fk_fact_geografia
        FOREIGN KEY (sk_geografia)
        REFERENCES dim_geografia (sk_geografia),

    CONSTRAINT fk_fact_cultivo
        FOREIGN KEY (sk_cultivo)
        REFERENCES dim_cultivo (sk_cultivo),

    CONSTRAINT fk_fact_tiempo
        FOREIGN KEY (sk_tiempo)
        REFERENCES dim_tiempo (sk_tiempo),

    -- Las métricas agrícolas no pueden ser negativas
    CONSTRAINT chk_fact_area_sembrada
        CHECK (area_sembrada >= 0),

    CONSTRAINT chk_fact_area_cosechada
        CHECK (area_cosechada >= 0),

    CONSTRAINT chk_fact_produccion
        CHECK (produccion >= 0),

    CONSTRAINT chk_fact_rendimiento
        CHECK (rendimiento >= 0)

) ENGINE = InnoDB
  DEFAULT CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;


-- ============================================================
-- 7. VALIDACIÓN DE LA ESTRUCTURA
-- ============================================================

SHOW TABLES;

DESCRIBE dim_geografia;
DESCRIBE dim_cultivo;
DESCRIBE dim_tiempo;
DESCRIBE fact_produccion_agricola;