-- ============================================================
-- R1
-- ¿Cómo han evolucionado la producción y el rendimiento de los cultivos colombianos entre 2019 y 2025?
-- ============================================================
SELECT
    t.anio,
    t.tipo_periodo,
    SUM(f.produccion) AS produccion_total_ton,
    SUM(f.area_cosechada) AS area_cosechada_total_ha,
    ROUND(
        SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0),
        2
    ) AS rendimiento_calculado_ton_ha
FROM fact_produccion_agricola f
INNER JOIN dim_tiempo t
    ON f.sk_tiempo = t.sk_tiempo
GROUP BY
    t.anio,
    t.tipo_periodo
ORDER BY
    t.anio,
    t.tipo_periodo;


-- ============================================================
-- R2
-- ¿Qué departamentos y municipios presentan los mayores y menores 
-- niveles de rendimiento para los diferentes cultivos?
-- ============================================================

SELECT
    g.departamento,
    g.municipio,
    c.cultivo,
    SUM(f.produccion) AS produccion_total_ton,
    SUM(f.area_cosechada) AS area_cosechada_total_ha,
    ROUND(
        SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0),
        2
    ) AS rendimiento_ton_ha
FROM fact_produccion_agricola f
JOIN dim_geografia g
    ON f.sk_geografia = g.sk_geografia
JOIN dim_cultivo c
    ON f.sk_cultivo = c.sk_cultivo
GROUP BY
    g.departamento,
    g.municipio,
    c.cultivo
ORDER BY
    rendimiento_ton_ha DESC;


-- ============================================================
-- R3
-- ¿En qué territorios o cultivos el área agrícola utilizada no se traduce 
-- proporcionalmente en una mayor producción?
-- ============================================================
SELECT
    g.departamento,
    c.cultivo,
    ROUND(SUM(f.area_cosechada), 2) AS area_cosechada_ha,
    ROUND(SUM(f.produccion), 2) AS produccion_ton,
    ROUND(
        SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0),
        2
    ) AS rendimiento_ton_ha,
    CASE
        WHEN SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0) < 1
            THEN 'Bajo rendimiento'
        WHEN SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0) < 3
            THEN 'Rendimiento medio'
        ELSE 'Alto rendimiento'
    END AS categoria_rendimiento
FROM fact_produccion_agricola f
JOIN dim_geografia g
    ON f.sk_geografia = g.sk_geografia
JOIN dim_cultivo c
    ON f.sk_cultivo = c.sk_cultivo
GROUP BY
    g.departamento,
    c.cultivo
HAVING SUM(f.area_cosechada) > 0
ORDER BY rendimiento_ton_ha ASC;

-- ============================================================
-- R4
-- ¿Qué cultivos concentran mayor producción y cuáles presentan los mejores o peores rendimientos 
-- durante el periodo analizado?
-- ============================================================

SELECT
    c.grupo_cultivo,
    c.subgrupo,
    c.cultivo,
    c.ciclo_cultivo,
    SUM(f.produccion) AS produccion_total_ton,
    SUM(f.area_cosechada) AS area_cosechada_total_ha,
    ROUND(
        SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0),
        2
    ) AS rendimiento_ton_ha
FROM fact_produccion_agricola f
JOIN dim_cultivo c
    ON f.sk_cultivo = c.sk_cultivo
GROUP BY
    c.grupo_cultivo,
    c.subgrupo,
    c.cultivo,
    c.ciclo_cultivo
HAVING SUM(f.area_cosechada) > 0
ORDER BY produccion_total_ton DESC;

-- ============================================================
-- R5
-- ¿Existen diferencias relevantes en producción, área y rendimiento entre cultivos transitorios y permanentes, y cómo cambian 
-- según el periodo registrado?
-- ============================================================

SELECT
    c.ciclo_cultivo,
    t.anio,
    t.tipo_periodo,
    SUM(f.area_sembrada) AS area_sembrada_total_ha,
    SUM(f.area_cosechada) AS area_cosechada_total_ha,
    SUM(f.produccion) AS produccion_total_ton,
    ROUND(
        SUM(f.produccion) / NULLIF(SUM(f.area_cosechada), 0),
        2
    ) AS rendimiento_ton_ha
FROM fact_produccion_agricola f
JOIN dim_cultivo c
    ON f.sk_cultivo = c.sk_cultivo
JOIN dim_tiempo t
    ON f.sk_tiempo = t.sk_tiempo
GROUP BY
    c.ciclo_cultivo,
    t.anio,
    t.tipo_periodo
ORDER BY
    t.anio,
    t.tipo_periodo,
    c.ciclo_cultivo;