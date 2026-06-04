# ============================================================
# Codigo para estudar gpkg
# ============================================================

import fiona

gpkg_path = "ArqAcores_GOcidental_CAOP2025.gpkg"

camadas = fiona.listlayers(gpkg_path)
print("Camadas reais encontradas no teu GeoPackage:")
for camada in camadas:
    print(f"- {camada}")