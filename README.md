# LOKL - Sistema de Automatización de Sprints

Sistema integral de automatización para gestión de sprints en Notion que captura métricas de performance del equipo y crea nuevos sprints automáticamente.

## Descripción General

Este sistema automatiza el proceso de cierre de sprints, captura las métricas de rendimiento de cada persona del equipo y crea automáticamente el siguiente sprint. Está diseñado para funcionar con las bases de datos de Notion del sistema LOKL de gestión de proyectos.

### Funcionalidades Principales

- **Captura automática de performance** al cierre de cada sprint
- **Creación automática del siguiente sprint** con fechas calculadas
- **Filtrado inteligente de tareas imprevistas** para métricas justas
- **Logging detallado** para auditoría y debugging
- **Interfaz web opcional** con Streamlit para ejecución manual
- **Validaciones de integridad** para evitar duplicados

## Estructura del Proyecto

```
NOTION SISTEMA DE SPRINTS/
├── venv/                     # Entorno virtual Python
├── .env                      # Variables de entorno (configuración)
├── requirements.txt          # Dependencias del proyecto
├── README.md                 # Esta documentación
├── sprint_automation.py      # Script principal de automatización
├── diagnose.py              # Script de diagnóstico del sistema
├── test_connection.py        # Prueba de conexión con Notion
├── app.py                   # Interfaz web Streamlit (opcional)
└── sprint_automation.log    # Archivo de logs (generado automáticamente)
```

## Configuración

### 1. Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_SPRINTS_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_TAREAS_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_PERSONAS_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_PERFORMANCE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. Instalación de Dependencias

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de Notion

#### Requisitos en Notion:
- Workspace con plan de pago (requerido para API)
- Integración creada con permisos de lectura/escritura
- Bases de datos configuradas según estructura LOKL

#### Permisos necesarios:
- **Sprints:** Lectura y escritura
- **Tareas:** Lectura y escritura
- **Personas:** Lectura
- **Performance:** Lectura y escritura

## Uso del Sistema

### Ejecución Automática (Recomendada)

```bash
# Cierre completo: captura performance + crea nuevo sprint
python sprint_automation.py

# Solo crear nuevo sprint (sin cierre)
python sprint_automation.py --crear-sprint
```

### Interfaz Web (Opcional)

```bash
# Ejecutar interfaz Streamlit
streamlit run app.py
```

Abrir navegador en `http://localhost:8501`

### Diagnóstico del Sistema

```bash
# Verificar configuración y conexiones
python diagnose.py

# Probar solo conexión a Notion
python test_connection.py
```

## Lógica de Automatización

### Proceso de Cierre de Sprint

1. **Obtener sprint actual** (marcado como "Es actual")
2. **Recuperar todas las tareas** del sprint
3. **Agrupar tareas por persona** asignada
4. **Aplicar filtro de tareas imprevistas** para métricas justas
5. **Calcular métricas de performance** por persona
6. **Crear registros en tabla Performance**
7. **Establecer relaciones bidireccionales** entre tareas y performance
8. **Marcar sprint como Finalizado**
9. **Crear automáticamente el siguiente sprint**

### Filtrado de Tareas Imprevistas

#### Lógica Aplicada:
- ✅ **Tareas normales (Alta/Media/Baja):** Siempre incluidas
- ✅ **Tareas imprevistas completadas:** Incluidas en métricas
- ❌ **Tareas imprevistas NO completadas:** Excluidas de métricas

#### Propósito:
Las tareas imprevistas no completadas no deben penalizar el rendimiento, ya que son interrupciones no planificadas. Sin embargo, las imprevistas completadas sí cuentan positivamente.

### Cálculo de Métricas

```python
# Métricas calculadas por persona
eficiencia = (carga_completada / carga_asignada) * 100
productividad = (tareas_completadas / tareas_totales) * 100
score_performance = (eficiencia + productividad) / 2
```

## Bases de Datos de Notion

### Tablas Requeridas:

#### 1. Sprints
- **Propiedades clave:** Nombre, Fecha inicio, Fecha fin, Estado, Es actual
- **Relaciones:** Tareas (bidireccional)

#### 2. Tareas  
- **Propiedades clave:** Nombre, Sprint, Personas, Prioridad, Tamaño, Estado, Carga
- **Relaciones:** Sprint, Personas, Performance vinculada (bidireccionales)

#### 3. Personas
- **Propiedades clave:** Nombre, Área, Estado, Capacidad por sprint
- **Relaciones:** Tareas (bidireccional)

#### 4. Performance
- **Propiedades clave:** Nombre, Persona, Sprint, Carga asignada, Tareas completadas, Score Performance
- **Relaciones:** Persona, Sprint, Tareas vinculadas

## Logging y Monitoreo

### Archivo de Logs
- **Ubicación:** `sprint_automation.log`
- **Formato:** `YYYY-MM-DD HH:MM:SS - LEVEL - MESSAGE`
- **Niveles:** INFO, WARNING, ERROR, CRITICAL

### Información Registrada:
- Sprints procesados
- Personas y tareas analizadas
- Filtrado de tareas imprevistas
- Métricas calculadas
- Errores y excepciones
- Registros creados/actualizados

### Ejemplo de Log:
```
2025-01-15 10:30:45 - INFO - Sprint actual encontrado: Sprint 27
2025-01-15 10:30:46 - INFO - Se encontraron 45 tareas para el sprint
2025-01-15 10:30:47 - INFO - Filtrado de tareas para Juan Esteban:
2025-01-15 10:30:47 - INFO -   - Tareas originales: 12
2025-01-15 10:30:47 - INFO -   - Tareas para métricas: 9
2025-01-15 10:30:47 - INFO -   - Tareas excluidas: 3
2025-01-15 10:30:47 - INFO - ✅ Performance capturado para Juan Esteban - Sprint 27
```

## Funciones Principales

### `obtener_sprint_actual()`
Encuentra el sprint marcado como "Es actual" en la base de datos.

### `obtener_tareas_del_sprint(sprint_id)`
Recupera todas las tareas relacionadas con un sprint usando paginación.

### `filtrar_tareas_para_metricas(tareas)`
Aplica la lógica de filtrado de tareas imprevistas para cálculo justo de métricas.

### `crear_registro_performance(persona_id, sprint_id, sprint_info, tareas)`
Crea un registro de performance calculando métricas y estableciendo relaciones.

### `crear_nuevo_sprint(sprint_actual_info)`
Genera automáticamente el siguiente sprint con fechas calculadas.

### `ejecutar_cierre_sprint()`
Función principal que orquesta todo el proceso de cierre.

## Validaciones y Seguridad

### Prevención de Duplicados
- Verifica existencia de registros de performance antes de crear
- Valida si el siguiente sprint ya existe antes de crear
- Confirma sprint actual antes de procesar

### Manejo de Errores
- Excepciones capturadas y loggeadas
- Rollback automático en caso de fallas críticas
- Validación de datos antes de procesamiento

### Integridad de Datos
- Relaciones bidireccionales mantenidas
- Validación de IDs de Notion
- Verificación de propiedades requeridas

## Deployment y Automatización

### Cron Job (Recomendado)
```bash
# Ejecutar cada 15 días a las 2:00 AM
0 2 */15 * * /path/to/venv/bin/python /path/to/sprint_automation.py
```

### AWS Lambda (Alternativa)
- Configurar trigger con EventBridge
- Empaquetar dependencias en layer
- Variables de entorno en configuración

### Docker (Opcional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "sprint_automation.py"]
```

## Troubleshooting

### Errores Comunes

#### "No se encontró un sprint activo"
- Verificar que hay un sprint con "Es actual" = true
- Confirmar fechas del sprint cubren la fecha actual

#### "Error al obtener información de persona"
- Validar permisos de la integración en Notion
- Verificar que las personas tienen relación con tareas

#### "Ya existe un registro de Performance"
- Normal si se ejecuta múltiples veces el mismo sprint
- Revisar logs para confirmar que no es error de lógica

### Comandos de Diagnóstico
```bash
# Verificar configuración completa
python diagnose.py

# Probar conexión específica
python test_connection.py

# Revisar logs recientes
tail -n 50 sprint_automation.log

# Verificar variables de entorno
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Token:', 'OK' if os.getenv('NOTION_TOKEN') else 'MISSING')"
```



## Soporte y Mantenimiento

### Contacto Técnico
- **Sistema desarrollado para:** LOKL
- **Mantenido por:** Equipo de Tecnología
- **Última actualización:** Mayo 2025

### Contribuciones
Para modificaciones del sistema:
1. Crear backup del código actual
2. Probar cambios en entorno de desarrollo
3. Validar con datos de prueba
4. Actualizar documentación
5. Ejecutar suite de pruebas completa

### Licencia
Sistema propietario para uso interno de LOKL.