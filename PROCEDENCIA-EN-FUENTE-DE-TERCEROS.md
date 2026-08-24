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

## `ieee-fraud-detection.zip` — `sha256:4cc646da09d0a9b265983ffed775b1f9ee15af5266586df610e04d6adae0b829`

**Lo declara**: `RQ-DATA-HSBC-IEEE-001` (manifiesto sellado antes de entrenar).  
**bytes**: 123.856.947

**fuente-oficial**: https://www.kaggle.com/competitions/ieee-fraud-detection/data

**verificacion**: crear una cuenta en Kaggle y **aceptar las reglas de la competencia** (sin eso la descarga devuelve 403); luego `kaggle competitions download -c ieee-fraud-detection`, descomprimir, y recomputar `shasum -a 256 ieee-fraud-detection.zip`: debe dar el hash de arriba.

**Raiz de la cadena**: es el unico artefacto que viene directo del endpoint (`GET /api/v1/competitions/data/download-all/ieee-fraud-detection`). Los cinco CSV son producto de descomprimirlo.

**por que no se republica**: las reglas de Kaggle §7.B prohiben redistribuir el dataset y §7.A lo limita a uso no comercial. Se usa solo como benchmark dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del statement de HSBC). Ningun byte entra a este repositorio.

**salvedad**: Kaggle publica `totalBytes` por archivo —**los tamanos tienen ancla externa**— pero **no publica checksums**. Este sha256 lo computamos nosotros: fija los bytes para que la corrida sea reproducible y **no certifica procedencia**.

## `train_transaction.csv` — `sha256:3a5c83ab6b3cc13dcabe5ffa9f522307fd5f7f7b6e6f6a60c32284ca6283d642`

**Lo declara**: `RQ-DATA-HSBC-IEEE-001` (manifiesto sellado antes de entrenar).  
**bytes**: 683.351.067

**fuente-oficial**: https://www.kaggle.com/competitions/ieee-fraud-detection/data

**verificacion**: crear una cuenta en Kaggle y **aceptar las reglas de la competencia** (sin eso la descarga devuelve 403); luego `kaggle competitions download -c ieee-fraud-detection`, descomprimir, y recomputar `shasum -a 256 train_transaction.csv`: debe dar el hash de arriba.

590.540 filas, 394 columnas, 20.663 fraudes (3,499 %). Es el unico archivo con etiquetas: la evaluacion sale de una particion temporal dentro de el.

**por que no se republica**: las reglas de Kaggle §7.B prohiben redistribuir el dataset y §7.A lo limita a uso no comercial. Se usa solo como benchmark dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del statement de HSBC). Ningun byte entra a este repositorio.

**salvedad**: Kaggle publica `totalBytes` por archivo —**los tamanos tienen ancla externa**— pero **no publica checksums**. Este sha256 lo computamos nosotros: fija los bytes para que la corrida sea reproducible y **no certifica procedencia**.

## `train_identity.csv` — `sha256:b63c725d8377be90a995268d97f347c17d456b95db45807adcf9f59cd603c37c`

**Lo declara**: `RQ-DATA-HSBC-IEEE-001` (manifiesto sellado antes de entrenar).  
**bytes**: 26.529.680

**fuente-oficial**: https://www.kaggle.com/competitions/ieee-fraud-detection/data

**verificacion**: crear una cuenta en Kaggle y **aceptar las reglas de la competencia** (sin eso la descarga devuelve 403); luego `kaggle competitions download -c ieee-fraud-detection`, descomprimir, y recomputar `shasum -a 256 train_identity.csv`: debe dar el hash de arriba.

144.233 filas, 41 columnas.

**por que no se republica**: las reglas de Kaggle §7.B prohiben redistribuir el dataset y §7.A lo limita a uso no comercial. Se usa solo como benchmark dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del statement de HSBC). Ningun byte entra a este repositorio.

**salvedad**: Kaggle publica `totalBytes` por archivo —**los tamanos tienen ancla externa**— pero **no publica checksums**. Este sha256 lo computamos nosotros: fija los bytes para que la corrida sea reproducible y **no certifica procedencia**.

## `test_transaction.csv` — `sha256:2a8e51f1d335a86025d2b7f45beb9b78d0ab1edd726ef531d8b71a8a0065c011`

**Lo declara**: `RQ-DATA-HSBC-IEEE-001` (manifiesto sellado antes de entrenar).  
**bytes**: 613.194.934

**fuente-oficial**: https://www.kaggle.com/competitions/ieee-fraud-detection/data

**verificacion**: crear una cuenta en Kaggle y **aceptar las reglas de la competencia** (sin eso la descarga devuelve 403); luego `kaggle competitions download -c ieee-fraud-detection`, descomprimir, y recomputar `shasum -a 256 test_transaction.csv`: debe dar el hash de arriba.

506.691 filas, 393 columnas. **NO trae `isFraud`**: es el test de la competencia con etiquetas ocultas, asi que ninguna metrica propia puede calcularse sobre el.

**por que no se republica**: las reglas de Kaggle §7.B prohiben redistribuir el dataset y §7.A lo limita a uso no comercial. Se usa solo como benchmark dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del statement de HSBC). Ningun byte entra a este repositorio.

**salvedad**: Kaggle publica `totalBytes` por archivo —**los tamanos tienen ancla externa**— pero **no publica checksums**. Este sha256 lo computamos nosotros: fija los bytes para que la corrida sea reproducible y **no certifica procedencia**.

## `test_identity.csv` — `sha256:3e5978cb13ca5e72f52babc4349ae0125e14b87ca8bfabe952ab67bb4ff1e10b`

**Lo declara**: `RQ-DATA-HSBC-IEEE-001` (manifiesto sellado antes de entrenar).  
**bytes**: 25.797.161

**fuente-oficial**: https://www.kaggle.com/competitions/ieee-fraud-detection/data

**verificacion**: crear una cuenta en Kaggle y **aceptar las reglas de la competencia** (sin eso la descarga devuelve 403); luego `kaggle competitions download -c ieee-fraud-detection`, descomprimir, y recomputar `shasum -a 256 test_identity.csv`: debe dar el hash de arriba.

141.907 filas, 41 columnas.

**por que no se republica**: las reglas de Kaggle §7.B prohiben redistribuir el dataset y §7.A lo limita a uso no comercial. Se usa solo como benchmark dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del statement de HSBC). Ningun byte entra a este repositorio.

**salvedad**: Kaggle publica `totalBytes` por archivo —**los tamanos tienen ancla externa**— pero **no publica checksums**. Este sha256 lo computamos nosotros: fija los bytes para que la corrida sea reproducible y **no certifica procedencia**.

## `sample_submission.csv` — `sha256:50d7e0d6fcfc6e498efc297001f252101512ccdcb34aefbde6db98f8242a3626`

**Lo declara**: `RQ-DATA-HSBC-IEEE-001` (manifiesto sellado antes de entrenar).  
**bytes**: 6.080.314

**fuente-oficial**: https://www.kaggle.com/competitions/ieee-fraud-detection/data

**verificacion**: crear una cuenta en Kaggle y **aceptar las reglas de la competencia** (sin eso la descarga devuelve 403); luego `kaggle competitions download -c ieee-fraud-detection`, descomprimir, y recomputar `shasum -a 256 sample_submission.csv`: debe dar el hash de arriba.

506.691 filas, 2 columnas. Plantilla de envio de Kaggle.

**por que no se republica**: las reglas de Kaggle §7.B prohiben redistribuir el dataset y §7.A lo limita a uso no comercial. Se usa solo como benchmark dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del statement de HSBC). Ningun byte entra a este repositorio.

**salvedad**: Kaggle publica `totalBytes` por archivo —**los tamanos tienen ancla externa**— pero **no publica checksums**. Este sha256 lo computamos nosotros: fija los bytes para que la corrida sea reproducible y **no certifica procedencia**.
