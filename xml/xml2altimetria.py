import xml.etree.ElementTree as ET
import sys

class Xml2Altimetria:
    """
    Clase para generar un SVG simplificado de altimetría
    con una polínea roja y nombres verticales.
    """

    def __init__(self, entrada_xml, salida_svg):
        self.entrada_xml = entrada_xml
        self.salida_svg = salida_svg
        self.ns = {'ns': 'http://www.uniovi.es'}

        # Dimensiones del lienzo SVG
        self.ancho_svg = 500
        self.alto_svg = 350
        self.margen_x = 30
        self.margen_superior = 20
        self.margen_inferior = 150  # Espacio para los textos verticales

    def cargar_xml(self):
        """Carga el documento XML y devuelve la raíz del árbol DOM."""
        try:
            arbol = ET.parse(self.entrada_xml)
            return arbol.getroot()
        except IOError:
            print(f"Error: No se encuentra el archivo {self.entrada_xml}")
            sys.exit(1)
        except ET.ParseError as e:
            print(f"Error procesando el archivo XML {self.entrada_xml}: {e}")
            sys.exit(1)

    def _obtener_texto(self, nodo, expresion_xpath):
        """Extrae el texto mediante una expresión XPath."""
        elem = nodo.find(expresion_xpath, self.ns)
        return elem.text.strip() if elem is not None and elem.text else ""

    def extraer_puntos(self, raiz):
        """Extrae todos los puntos de la etapa con altitud y nombre."""
        puntos = []

        # 1. Inicio
        coord_inicio = raiz.find('ns:coordenadasInicio/ns:coordenadas', self.ns)
        if coord_inicio is not None:
            alt = self._obtener_texto(coord_inicio, 'ns:altitud')
            if alt:
                puntos.append({'altitud': float(alt), 'nombre': 'Inicio'})

        # 2. Hitos (Puertos, Sprints, etc.)
        hitos = raiz.findall('ns:hitos/*', self.ns)
        for hito in hitos:
            coord_nodo = hito.find('ns:coordenadas', self.ns)
            if coord_nodo is not None:
                alt = self._obtener_texto(coord_nodo, 'ns:altitud')
                nombre = self._obtener_texto(hito, 'ns:nombre')
                if alt:
                    puntos.append({'altitud': float(alt), 'nombre': nombre})

        # 3. Puntos Anónimos
        puntos_anonimos = raiz.findall('ns:puntosAnonimos/ns:puntoAnonimo', self.ns)
        for pa in puntos_anonimos:
            coord_nodo = pa.find('ns:coordenadas', self.ns)
            if coord_nodo is not None:
                alt = self._obtener_texto(coord_nodo, 'ns:altitud')
                nombre = self._obtener_texto(pa, 'ns:nombre')
                if alt:
                    puntos.append({'altitud': float(alt), 'nombre': nombre})

        # 4. Meta / Final
        coord_final = raiz.find('ns:coordenadasFinal/ns:coordenadas', self.ns)
        if coord_final is not None:
            alt = self._obtener_texto(coord_final, 'ns:altitud')
            if alt:
                puntos.append({'altitud': float(alt), 'nombre': 'Final'})

        return puntos

    def generar_svg(self):
        """Genera el código SVG con el estilo exacto de la plantilla."""
        raiz = self.cargar_xml()
        puntos = self.extraer_puntos(raiz)

        if not puntos:
            print("No se encontraron puntos en el XML.")
            return

        max_alt = max(p['altitud'] for p in puntos) or 1.0
        min_alt = min(p['altitud'] for p in puntos)

        ancho_util = self.ancho_svg - (2 * self.margen_x)
        alto_util = self.alto_svg - self.margen_superior - self.margen_inferior
        y_suelo = self.alto_svg - self.margen_inferior

        num_puntos = len(puntos)
        paso_x = ancho_util / (num_puntos - 1) if num_puntos > 1 else ancho_util

        # Mapear coordenadas a píxeles
        puntos_px = []
        for i, p in enumerate(puntos):
            x_px = self.margen_x + (i * paso_x)
            # Escalar altitud
            y_px = y_suelo - ((p['altitud'] - min_alt) / (max_alt - min_alt if max_alt != min_alt else 1)) * alto_util
            puntos_px.append((x_px, y_px, p['nombre']))

        # Trazado de la polínea (Perfil + Línea base)
        coordenadas_linea = [f"{x:.1f},{y:.1f}" for x, y, _ in puntos_px]
        # Cerramos la polínea hacia la esquina inferior derecha e izquierda para hacer la base
        coordenadas_linea.append(f"{puntos_px[-1][0]:.1f},{y_suelo:.1f}")
        coordenadas_linea.append(f"{puntos_px[0][0]:.1f},{y_suelo:.1f}")
        coordenadas_linea.append(f"{puntos_px[0][0]:.1f},{puntos_px[0][1]:.1f}")

        lineas_svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{self.ancho_svg}" height="{self.alto_svg}">',
            f'  <polyline points="{" ".join(coordenadas_linea)}" stroke="red" stroke-width="3" fill="none" />'
        ]

        # Textos verticales debajo del eje base
        for x, _, nombre in puntos_px:
            if nombre:
                lineas_svg.append(
                    f'  <text x="{x:.1f}" y="{y_suelo + 10:.1f}" font-family="sans-serif" font-size="12" '
                    f'transform="rotate(90 {x:.1f} {y_suelo + 10:.1f})">{nombre}</text>'
                )

        lineas_svg.append('</svg>')

        with open(self.salida_svg, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lineas_svg))

        print(f"Archivo SVG simplificado generado correctamente: {self.salida_svg}")

def main():
    conversor = Xml2Altimetria('etapaEsquema.xml', 'altimetria.svg')
    conversor.generar_svg()

if __name__ == '__main__':
    main()