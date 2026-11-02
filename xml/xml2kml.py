import xml.etree.ElementTree as ET
import sys

class Xml2Kml:
    """
    Clase para procesar un archivo XML de una etapa ciclista
    y generar un archivo KML con marcas de puntos de interés y
    la ruta conformada únicamente por los puntos anónimos.
    """

    # Definición de estilos con colores en formato KML (aabbggrr)
    # ff0000ff = rojo, ff00ff00 = verde, ffff0000 = azul, ff00ffff = amarillo
    ESTILOS = {
        'salida': {'id': 'estiloSalida', 'color': 'ff0000ff', 'icono': 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'},
        'meta': {'id': 'estiloMeta', 'color': 'ff0000ff', 'icono': 'http://maps.google.com/mapfiles/kml/paddle/red-stars.png'},
        'puerto': {'id': 'estiloPuerto', 'color': 'ff00ff00', 'icono': 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png'},
        'sprint': {'id': 'estiloSprint', 'color': 'ffff0000', 'icono': 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'},
        'anonimo': {'id': 'estiloAnonimo', 'color': 'ff00ffff', 'icono': 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png'}
    }

    def __init__(self, entrada_xml, salida_kml):
        self.entrada_xml = entrada_xml
        self.salida_kml = salida_kml
        # Espacio de nombres configurado en etapaEsquema.xml
        self.ns = {'ns': 'http://www.uniovi.es'}

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
        """Método auxiliar para extraer texto usando expresiones XPath con ElementTree."""
        elem = nodo.find(expresion_xpath, self.ns)
        return elem.text.strip() if elem is not None and elem.text else ""

    def _extraer_coordenadas(self, nodo_coordenadas):
        """Extrae lon, lat, alt a partir de un nodo <coordenadas> mediante XPath."""
        lon = self._obtener_texto(nodo_coordenadas, 'ns:longitudGeo')
        lat = self._obtener_texto(nodo_coordenadas, 'ns:latitud')
        alt = self._obtener_texto(nodo_coordenadas, 'ns:altitud')
        return lon, lat, alt

    def generar_kml(self):
        """Procesa los nodos mediante expresiones XPath y escribe el archivo KML."""
        raiz = self.cargar_xml()

        # Extraer datos de la etapa mediante XPath
        nombre_etapa = self._obtener_texto(raiz, 'ns:nombre')
        inicio_ciudad = self._obtener_texto(raiz, 'ns:ciudadInicio')
        final_ciudad = self._obtener_texto(raiz, 'ns:ciudadFinal')

        lineas_kml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2">',
            '  <Document>',
            f'    <name>{nombre_etapa}</name>',
            '    <description>Planimetría de la etapa</description>'
        ]

        # Estilos de los iconos en KML
        for clave, est in self.ESTILOS.items():
            lineas_kml.append(f'    <Style id="{est["id"]}">')
            lineas_kml.append('      <IconStyle>')
            lineas_kml.append(f'        <color>{est["color"]}</color>')
            lineas_kml.append(f'        <Icon><href>{est["icono"]}</href></Icon>')
            lineas_kml.append('      </IconStyle>')
            lineas_kml.append('    </Style>')

        # 1. Punto de Salida (Punto de Interés - Rojo)
        coord_salida = raiz.find('ns:coordenadasInicio/ns:coordenadas', self.ns)
        if coord_salida is not None:
            lon_s, lat_s, alt_s = self._extraer_coordenadas(coord_salida)
            str_coord_s = f"{lon_s},{lat_s},{alt_s}"
            lineas_kml.append(self._crear_placemark(f"Salida: {inicio_ciudad}", str_coord_s, self.ESTILOS['salida']['id']))

        # 2. Hitos: Puertos de Montaña (Verde) y Sprints Intermedios (Azul) - Puntos de Interés
        hitos = raiz.findall('ns:hitos/*', self.ns)
        for hito in hitos:
            tag = hito.tag.split('}')[-1] if '}' in hito.tag else hito.tag
            coord_nodo = hito.find('ns:coordenadas', self.ns)

            if coord_nodo is not None:
                lon, lat, alt = self._extraer_coordenadas(coord_nodo)
                str_coord = f"{lon},{lat},{alt}"

                if tag == 'puertoMontañaPuntuable':
                    cat = self._obtener_texto(hito, 'ns:categoriaPuertoMontaña')
                    dist = self._obtener_texto(hito, 'ns:distanciaASalida')
                    lineas_kml.append(self._crear_placemark(
                        f"Puerto de Montaña ({cat} cat.) - Km {dist}",
                        str_coord,
                        self.ESTILOS['puerto']['id']
                    ))
                elif tag == 'sprintIntermedio':
                    dist = self._obtener_texto(hito, 'ns:distanciaASalida')
                    lineas_kml.append(self._crear_placemark(
                        f"Sprint Intermedio - Km {dist}",
                        str_coord,
                        self.ESTILOS['sprint']['id']
                    ))

        # 3. Punto de Meta (Punto de Interés - Rojo)
        coord_meta = raiz.find('ns:coordenadasFinal/ns:coordenadas', self.ns)
        if coord_meta is not None:
            lon_m, lat_m, alt_m = self._extraer_coordenadas(coord_meta)
            str_coord_m = f"{lon_m},{lat_m},{alt_m}"
            lineas_kml.append(self._crear_placemark(f"Meta: {final_ciudad}", str_coord_m, self.ESTILOS['meta']['id']))

        # 4. Puntos Anónimos (Marcadores Amarillos Y construcción de la línea de la ruta)
        coordenadas_ruta = []
        puntos_anonimos = raiz.findall('ns:puntosAnonimos/ns:puntoAnonimo', self.ns)
        for idx, pa in enumerate(puntos_anonimos, 1):
            coord_nodo = pa.find('ns:coordenadas', self.ns)
            if coord_nodo is not None:
                lon, lat, alt = self._extraer_coordenadas(coord_nodo)
                str_coord = f"{lon},{lat},{alt}"

                # Añadir a la lista exclusiva para trazar la ruta
                coordenadas_ruta.append(str_coord)

                # Añadir punto de interés anónimo (amarillo)
                nombre_punto = self._obtener_texto(pa, 'ns:nombre')
                if not nombre_punto:
                    nombre_punto = f"Punto Anónimo {idx}"

                lineas_kml.append(self._crear_placemark(
                    nombre_punto,
                    str_coord,
                    self.ESTILOS['anonimo']['id']
                ))

        # 5. Trazado de la línea de la ruta UNICAMENTE con puntos anónimos
        if coordenadas_ruta:
            lineas_kml.append('    <Placemark>')
            lineas_kml.append('      <name>Ruta de la etapa</name>')
            lineas_kml.append('      <Style>')
            lineas_kml.append('        <LineStyle>')
            lineas_kml.append('          <color>ff0000ff</color>') # Línea roja
            lineas_kml.append('          <width>4</width>')
            lineas_kml.append('        </LineStyle>')
            lineas_kml.append('      </Style>')
            lineas_kml.append('      <LineString>')
            lineas_kml.append('        <extrude>1</extrude>')
            lineas_kml.append('        <tessellate>1</tessellate>')
            lineas_kml.append('        <coordinates>')
            lineas_kml.append('          ' + ' '.join(coordenadas_ruta))
            lineas_kml.append('        </coordinates>')
            lineas_kml.append('      </LineString>')
            lineas_kml.append('    </Placemark>')

        lineas_kml.append('  </Document>')
        lineas_kml.append('</kml>')

        # Guardar archivo KML
        with open(self.salida_kml, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lineas_kml))

        print(f"Archivo KML generado correctamente: {self.salida_kml}")

    def _crear_placemark(self, nombre, coord_str, id_estilo):
        """Genera el bloque XML de un Placemark."""
        return f"""    <Placemark>
      <name>{nombre}</name>
      <styleUrl>#{id_estilo}</styleUrl>
      <Point>
        <coordinates>{coord_str}</coordinates>
      </Point>
    </Placemark>"""

def main():
    conversor = Xml2Kml('etapaEsquema.xml', 'etapa.kml')
    conversor.generar_kml()

if __name__ == '__main__':
    main()