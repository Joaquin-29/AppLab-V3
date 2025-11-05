import csv

# Leer el archivo CSV con delimitador ;
with open('FORMULAS TOTAL 27 11 2023(RJALU_CargasAnodizado ) (1).csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file, delimiter=';')
    lines = list(reader)

print(f"Total lines: {len(lines)}")

# Procesar las líneas
recipes = {}
current_article = None
components = []

i = 0
while i < len(lines):
    row = lines[i]
    if row and len(row) > 4 and row[0] == 'Artículo':
        print(f"About to save: current_article={repr(current_article)}, len(components)={len(components)}")
        if current_article and components:
            recipes[current_article] = components
            print(f"Saved recipe for {current_article} with {len(components)} components")
        # Extraer el nuevo artículo
        article_code = row[1] if len(row) > 1 else ''
        article_name = row[4] if len(row) > 4 else ''
        current_article = f"{article_code} {article_name}".strip()
        components = []
        print(f"Found article: '{current_article}'")
    elif row and row[0].strip() == '1' and len(row) > 12:
        # Líneas de componentes
        component_name = row[13]
        if component_name:
            unit = row[15] if len(row) > 15 else ''
            quantity = row[16] if len(row) > 16 else ''
            if unit and quantity:
                components.append((component_name, unit.strip(), quantity))
    i += 1

# Guardar la última receta
if current_article and components:
    recipes[current_article] = components
    print(f"Saved recipe for {current_article} with {len(components)} components")

print(f"Total recipes: {len(recipes)}")

# Escribir el archivo limpio
with open('processed_recipes_full.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Artículo', 'Componente', 'Unidad', 'Cantidad'])
    for article, comps in recipes.items():
        for comp in comps:
            writer.writerow([article, comp[0], comp[1], comp[2]])

print("Procesamiento completado. Archivo 'processed_recipes_full.csv' creado.")