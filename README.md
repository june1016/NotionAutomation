# 🚀 Notion Automation Systems

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-API-000000?style=for-the-badge&logo=notion&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Ready-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)
![LOKL](https://img.shields.io/badge/LOKL-Automatizaci%C3%B3n-6DEBB9?style=for-the-badge)
![Privado](https://img.shields.io/badge/Access-Private-lightgrey?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)

<!-- Si aun no esta para produccion: ![Status](https://img.shields.io/badge/Status-Beta-yellow?style=for-the-badge)
-->


Sistemas de automatización empresarial para Notion que optimizan la gestión de proyectos mediante sprints de 15 días, monitoreo en tiempo real de tareas y análisis automatizado de rendimiento del equipo.

## ✨ **Características Principales**

- 🎯 **Cierre automático de sprints** cada 15 días con métricas de rendimiento
- 👀 **Monitoreo en tiempo real** de modificaciones en tareas
- 🔒 **Sistema de bloqueo** que previene cambios no autorizados post-sprint
- 📊 **Análisis automático de performance** individual y por departamento
- 🔄 **Creación automática** del siguiente sprint con configuración base
- 📝 **Logging completo** y trazabilidad de todas las operaciones

---

## 🏗️ **Arquitectura del Sistema**

### **Sistema 1: Automatización de Cierre de Sprint**
```
📅 Ejecución Diaria (6:00 PM COL) → 🔍 Verificar Fecha → 🎯 Cerrar Sprint (si aplica) → 📊 Capturar Performance → 🆕 Crear Nuevo Sprint
```

### **Sistema 2: Monitoreo de Tareas en Tiempo Real**
```
📡 Webhooks Notion → 🔍 Validar Cambios → 🛡️ Aplicar Reglas → 🔄 Revertir (si necesario) → 📝 Registrar en Log
```

---

## 📁 **Estructura del Proyecto**

```
notion-automation-systems/
├── auto/                                # 🚀 Sistemas de automatización principales
│   ├── sistema_cierre_sprint/          # 🎯 Automatización de cierre de sprints
│   │   ├── __init__.py
│   │   ├── sprint_automation.py        # Script principal de automatización
│   │   └── sprint_automation.log       # Logs de ejecución
│   └── sistema_monitoreo/              # 👀 Monitoreo en tiempo real
│       ├── __init__.py
│       ├── setup_monitoring.py         # Configuración inicial del sistema
│       ├── task_monitor.py             # Motor de monitoreo reactivo
│       ├── webhook_server.py           # Servidor de webhooks
│       ├── webhook_server.log          # Logs del servidor
│       └── task_snapshots.json         # Snapshots de estado de tareas
├── test/                               # 🧪 Suite de pruebas completa
│   ├── core/                          # Tests básicos del sistema
│   │   ├── test_connection.py         # Verificación de conectividad
│   │   └── verify_env.py              # Validación de configuración
│   ├── sistema_cierre_sprint/         # Tests del sistema de cierre
│   │   ├── debug_departamentos.py     # Diagnóstico de departamentos
│   │   ├── diagnostic_tareas.py       # Diagnóstico de tareas
│   │   ├── test_sistema_hibrido.py    # Test de lógica híbrida
│   │   └── test_sprint_automation.py  # Test completo de automatización
│   └── sistema_monitoreo/             # Tests del sistema de monitoreo
├── .env.example                       # Plantilla de variables de entorno
├── .gitignore                         # Archivos excluidos del repositorio
├── requirements.txt                   # Dependencias Python
└── README.md                          # Documentación completa
```

---

## 🚀 **Instalación y Configuración**

### **1. Clonar Repositorio**
```bash
git clone 
cd 
```

### **2. Configurar Entorno Virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

### **3. Instalar Dependencias**
```bash
pip install -r requirements.txt
```

### **4. Configurar Variables de Entorno**
```bash
cp .env.example .env
# Editar .env con tus credenciales de Notion
```

### **5. Verificar Configuración**
```bash
python test/core/verify_env.py
python test/core/test_connection.py
```

---

## ⚙️ **Configuración de Notion**

### **Bases de Datos Requeridas:**

| Base de Datos | Propósito | Propiedades Críticas |
|---------------|-----------|---------------------|
| **Sprints** | Gestión de ciclos de 15 días | `Nombre`, `Fecha Inicio`, `Fecha Fin`, `Es Actual`, `Monitoreo Activo` |
| **Tareas** | Actividades del equipo | `Nombre`, `Estado`, `Prioridad`, `Personas`, `Sprint`, `Tamaño` |
| **Personas** | Miembros del equipo | `Nombre`, `Cargo`, `Cuenta Notion`, `Área`, `Capacidad Semanal` |
| **Performance** | Métricas históricas | `Persona`, `Sprint`, `Score Performance`, `Carga Completada` |
| **Departamentos** | Organización empresarial | `Nombre`, `Descripción`, `Responsable` |
| **Log Modificaciones** | Auditoría de cambios | `Tarea Afectada`, `Usuario`, `Acción Tomada`, `Fecha Modificación` |

---

## 🎯 **Sistema de Cierre de Sprint**

### **Funcionalidades:**
- ✅ **Detección automática** del último día de sprint
- ✅ **Captura de métricas** de rendimiento individual
- ✅ **Filtrado inteligente** de tareas (excluye imprevistas no completadas)
- ✅ **Creación automática** del siguiente sprint
- ✅ **Logging detallado** de todo el proceso

### **Ejecución:**
```bash
# Ejecución diaria automatizada (recomendado)
python auto/sistema_cierre_sprint/sprint_automation.py --daily

# Verificar si hay cierre programado hoy
python auto/sistema_cierre_sprint/sprint_automation.py --check

# Forzar cierre manual (solo testing)
python auto/sistema_cierre_sprint/sprint_automation.py
```

### **Cron Job Recomendado:**
```bash
# Ejecutar diariamente a las 6:00 PM Colombia (23:00 UTC)
0 23 * * * cd /path/to/project && python auto/sistema_cierre_sprint/sprint_automation.py --daily
```

---

## 👀 **Sistema de Monitoreo en Tiempo Real**

### **Funcionalidades:**
- 🔒 **Bloqueo automático** de modificaciones después del día 4 del sprint
- 🔄 **Reversión instantánea** de cambios no autorizados
- 📝 **Logging completo** de todas las modificaciones
- 🚨 **Detección de evasión** de restricciones
- 🗑️ **Control de eliminaciones** de tareas

### **Reglas de Negocio:**
- **Días 1-4**: Modificaciones libres
- **Día 5+**: Solo cambios de estado y tareas imprevistas
- **Excepciones**: Tareas marcadas como "Imprevista" pueden modificarse siempre

### **Configuración:**
```bash
# 1. Configurar monitoreo inicial
python auto/sistema_monitoreo/setup_monitoring.py

# 2. Iniciar servidor de webhooks
python auto/sistema_monitoreo/webhook_server.py
```

### **Webhook URL:**
```
http://tu-servidor.com:5000/webhook
```

---

## 🧪 **Testing y Calidad**

### **Tests Disponibles:**

#### **Core System Tests:**
```bash
python test/core/verify_env.py          # Verificar configuración
python test/core/test_connection.py     # Test de conectividad
```

#### **Sprint Automation Tests:**
```bash
python test/sistema_cierre_sprint/test_sprint_automation.py      # Test completo
python test/sistema_cierre_sprint/test_sistema_hibrido.py        # Test lógica híbrida
python test/sistema_cierre_sprint/debug_departamentos.py         # Debug departamentos
python test/sistema_cierre_sprint/diagnostic_tareas.py           # Debug tareas
```

#### **Monitoring System Tests:**
```bash
# Tests específicos del sistema de monitoreo disponibles en desarrollo
```

### **Ejecutar Tests Completos:**
```bash
# Ejecutar todos los tests antes de deployment
python -m pytest test/ -v
```

---

## 📊 **Métricas y Monitoreo**

### **Logs Generados:**
- `auto/sistema_cierre_sprint/sprint_automation.log` - Logs de cierre de sprint
- `auto/sistema_monitoreo/webhook_server.log` - Logs de monitoreo en tiempo real
- `task_snapshots.json` - Estados de tareas para comparación

### **Endpoints de Monitoreo:**
- `GET /status` - Estado del sistema de monitoreo
- `GET /test` - Verificación de funcionamiento
- `POST /debug` - Debug de webhooks

---

## 🚨 **Códigos de Salida**

| Código | Descripción |
|--------|-------------|
| `0` | Éxito en la operación |
| `1` | Error crítico que requiere intervención |

---

## 📚 **Documentación Adicional**

### **Variables de Entorno:**
Consulta `.env.example` para la lista completa de variables requeridas.

### **Configuración de Webhooks:**
1. Crear integración en Notion
2. Configurar webhook URL: `https://tu-dominio.com/webhook`
3. Suscribirse a eventos: `page.created`, `page.updated`, `page.deleted`

### **Troubleshooting:**
- **Error de conexión**: Verificar `NOTION_TOKEN` y permisos de integración
- **Tareas no detectadas**: Ejecutar `diagnostic_tareas.py`
- **Problemas de departamentos**: Ejecutar `debug_departamentos.py`

---

## 🤝 **Contribución**

1. Fork el repositorio
2. Crear branch feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'feat: agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📄 **Licencia**

Este proyecto es privado no se permite el uso de este sin el permiso.

---

## 👥 **Soporte**

Para soporte técnico o preguntas:
- 📧 Email: Juanesteban@lokl.life
- 📋 Issues: [GitHub Issues](https://github.com/june1016/NotionAutomationLOKL)

---

## 🔄 **Changelog**

### v1.0.0 (2025-06-19)
- ✨ Sistema completo de automatización de cierre de sprint
- ✨ Sistema de monitoreo en tiempo real con webhooks
- ✨ Suite completa de testing y diagnóstico
- ✨ Documentación completa y badges informativos

---
