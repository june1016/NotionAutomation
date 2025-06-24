"""
Verificador de Configuración de Entorno
======================================

Analiza y valida completamente la configuración del archivo .env, verificando que todas
las variables necesarias estén presentes y que las conexiones con Notion funcionen
correctamente. Incluye diagnóstico detallado para facilitar troubleshooting.

FUNCIONES:
- Verificación de variables de entorno requeridas y opcionales
- Test de conectividad con cada base de datos
- Diagnóstico de problemas de configuración
- Recomendaciones para solucionar errores encontrados

EJECUCIÓN:
python Test/Core/verify_env.py

CASOS DE USO:
- Configuración inicial del sistema
- Diagnóstico de problemas de conectividad
- Verificación antes de deploy a producción
"""

import os
from dotenv import load_dotenv
from notion_client import Client

# Cargar variables de entorno
load_dotenv()

def verificar_configuracion_env():
    """Verifica la configuración del archivo .env"""
    print("🔍 VERIFICANDO CONFIGURACIÓN .env")
    print("=" * 50)
    
    # Variables requeridas
    variables_requeridas = {
        "NOTION_TOKEN": "Token de autenticación de Notion",
        "DB_SPRINTS_ID": "ID de la base de datos Sprints",
        "DB_TAREAS_ID": "ID de la base de datos Tareas", 
        "DB_PERSONAS_ID": "ID de la base de datos Personas",
        "DB_PERFORMANCE_ID": "ID de la base de datos Performance"
    }
    
    # Variables opcionales pero útiles
    variables_opcionales = {
        "DB_DEPARTAMENTOS_ID": "ID de la base de datos Departamentos"
    }
    
    # Verificar variables requeridas
    faltantes = []
    
    for var, descripcion in variables_requeridas.items():
        valor = os.getenv(var)
        if valor:
            print(f"✅ {var}: {valor[:20]}... ({descripcion})")
        else:
            print(f"❌ {var}: FALTANTE ({descripcion})")
            faltantes.append(var)
    
    print("\n📋 VARIABLES OPCIONALES:")
    for var, descripcion in variables_opcionales.items():
        valor = os.getenv(var)
        if valor:
            print(f"✅ {var}: {valor[:20]}... ({descripcion})")
        else:
            print(f"⚠️  {var}: NO CONFIGURADA ({descripcion})")
    
    # Probar conexión si hay token
    if os.getenv("NOTION_TOKEN"):
        print(f"\n🔗 PROBANDO CONEXIÓN CON NOTION...")
        try:
            notion = Client(auth=os.getenv("NOTION_TOKEN"))
            
            # Probar cada BD
            for var in variables_requeridas.keys():
                if var == "NOTION_TOKEN":
                    continue
                
                db_id = os.getenv(var)
                if db_id:
                    try:
                        response = notion.databases.retrieve(db_id)
                        title_list = response.get("title", [])
                        db_name = title_list[0].get("text", {}).get("content", "Sin título") if title_list else "Sin título"
                        print(f"  ✅ {var}: '{db_name}' - Accesible")
                    except Exception as e:
                        print(f"  ❌ {var}: Error - {e}")
                        faltantes.append(f"{var}_ACCESS")
            
            # Probar BD Departamentos si está configurada
            db_dept_id = os.getenv("DB_DEPARTAMENTOS_ID")
            if db_dept_id:
                try:
                    response = notion.databases.retrieve(db_dept_id)
                    title_list = response.get("title", [])
                    db_name = title_list[0].get("text", {}).get("content", "Sin título") if title_list else "Sin título"
                    print(f"  ✅ DB_DEPARTAMENTOS_ID: '{db_name}' - Accesible")
                except Exception as e:
                    print(f"  ❌ DB_DEPARTAMENTOS_ID: Error - {e}")
        
        except Exception as e:
            print(f"  ❌ Error de conexión: {e}")
            faltantes.append("NOTION_CONNECTION")
    
    # Resumen
    print(f"\n📊 RESUMEN:")
    if not faltantes:
        print("🎉 ¡Configuración completa y funcional!")
        return True
    else:
        print(f"⚠️  Problemas encontrados: {len(faltantes)}")
        for problema in faltantes:
            print(f"  - {problema}")
        
        if "DB_DEPARTAMENTOS_ID" not in [p for p in faltantes if "DEPARTAMENTOS" in p]:
            print(f"\n💡 POSIBLE SOLUCIÓN para departamentos:")
            print(f"   El problema de 'Sin departamento asignado' puede deberse a:")
            print(f"   1. Falta configurar DB_DEPARTAMENTOS_ID en .env")
            print(f"   2. Las personas no tienen bien configurada la relación con Departamentos")
            print(f"   3. Nombre de propiedad incorrecto ('Área' vs 'Departamento')")
        
        return False

def buscar_id_departamentos():
    """Intenta encontrar el ID de la BD Departamentos"""
    print(f"\n🔍 INTENTANDO ENCONTRAR BD DEPARTAMENTOS...")
    
    if not os.getenv("NOTION_TOKEN"):
        print("❌ Sin token de Notion, no se puede buscar")
        return None
    
    # Este método requeriría permisos especiales de Notion para listar todas las BDs
    # Por ahora solo podemos sugerir cómo encontrarlo manualmente
    
    print("💡 CÓMO ENCONTRAR EL ID DE DEPARTAMENTOS:")
    print("1. Ve a tu workspace de Notion")
    print("2. Abre la base de datos 'Departamentos'")
    print("3. En la URL, copia el ID que está después de '/' y antes de '?'")
    print("   Ejemplo: https://notion.so/workspace/1234567890abcdef1234567890abcdef")
    print("            El ID sería: 1234567890abcdef1234567890abcdef")
    print("4. Agrega esta línea a tu .env:")
    print("   DB_DEPARTAMENTOS_ID=tu_id_aqui")

if __name__ == "__main__":
    config_ok = verificar_configuracion_env()
    
    if not config_ok:
        buscar_id_departamentos()
    
    print(f"\n{'='*50}")
    print("🚀 Para continuar con el testing:")
    if config_ok:
        print("python Test/SistemaCierreSprint/test_sprint_automation.py --ejecutar-performance")
    else:
        print("1. Corrige los problemas del .env")
        print("2. Ejecuta python Test/SistemaCierreSprint/debug_departamentos.py")
        print("3. Luego ejecuta el test de performance")