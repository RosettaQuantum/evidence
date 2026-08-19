# Procedencia verificable en FUENTE DE TERCEROS

Este archivo existe para la tercera categoría de referencias de procedencia: archivos que un
sello cita por sha256 y que **no podemos republicar** (licencia o propiedad de terceros), pero
que **sí son verificables** porque el tercero los sirve desde su fuente oficial. La diferencia
con una pérdida (PROCEDENCIA-PERDIDA.md) tiene que ser **comprobable por el auditor, no
declarada por nosotros**: cada entrada exige la URL oficial y la instrucción de verificación,
y una entrada sin URL hace fallar al auditor entero — si no hay fuente pública donde bajar el
original, no es «verificable en fuente de terceros»: es una pérdida con mejor nombre.

Formato de entrada (los tres campos son obligatorios):

- `sha256:` el hash completo del archivo exacto que el sello cita.
- `fuente-oficial:` la URL del tercero donde el original vive.
- `verificacion:` cómo un tercero pasa de esa URL al hash citado.

---

## `Airbus-Challenge-Statement-vF.pdf` — `sha256:4a2e084dd25d49343c98475091eede479513779c4306e90260f9b9cf518f77c6`

**Lo declara**: `RQ-PREREG-AIRBUS-001`.
**fuente-oficial**: https://quantumaiportal.thequantuminsider.com
**verificacion**: iniciar sesión en el portal del 2026 Global Quantum + AI Challenge (registro
abierto a participantes), abrir el desafío de Airbus, descargar «Challenge Statement vF» y
recomputar `shasum -a 256` sobre el PDF descargado: debe dar el hash de arriba.
**por qué no se republica**: documento de Airbus/The Quantum Insider; no somos sus licenciantes.

## `HSBC-Challenge-Statement-vF-1.pdf` — `sha256:cf7051b97f30fca3bc60cbb65b002a43601df85ceba094426737550f1340da69`

**Lo declara**: `RQ-PREREG-HSBC-001`.
**fuente-oficial**: https://quantumaiportal.thequantuminsider.com
**verificacion**: iniciar sesión en el portal del 2026 Global Quantum + AI Challenge, abrir el
desafío de HSBC, descargar «Challenge Statement vF» y recomputar `shasum -a 256` sobre el PDF:
debe dar el hash de arriba.
**por qué no se republica**: documento de HSBC/The Quantum Insider; no somos sus licenciantes.
