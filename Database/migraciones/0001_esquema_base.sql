-- 0001_esquema_base.sql
-- Solo el registro de migraciones; las tablas de negocio llegan en migraciones posteriores.
CREATE TABLE IF NOT EXISTS esquema_migracion (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT    NOT NULL UNIQUE,
    checksum    TEXT    NOT NULL,
    aplicada_en TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
