# Documentacion: Sistema de Ubicaciones para Mapas en Tours

## Resumen

Se implemento un sistema para agregar **multiples ubicaciones/lugares** a cada tour, permitiendo mostrar un **mapa interactivo** con la ruta del viaje en el frontend.

**Ejemplo:** El tour "Ecuador Aventura" puede tener las ubicaciones: Quito → Cotopaxi → Banos → Cuenca → Guayaquil

---

## 1. Estructura de Datos

### Tabla: `travel.tour_ubicaciones`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | BIGINT | ID unico |
| `tour_id` | BIGINT | FK al tour |
| `nombre` | VARCHAR(255) | Nombre del lugar (ej: "Quito") |
| `pais` | VARCHAR(100) | Pais (ej: "Ecuador") |
| `provincia` | VARCHAR(150) | Provincia/Estado (ej: "Pichincha") |
| `ciudad` | VARCHAR(150) | Ciudad (ej: "Quito") |
| `descripcion` | TEXT | Descripcion del lugar |
| `latitud` | DECIMAL(10,8) | Coordenada latitud (ej: -0.180653) |
| `longitud` | DECIMAL(11,8) | Coordenada longitud (ej: -78.467838) |
| `orden` | INTEGER | Orden de visita (1, 2, 3...) |
| `dia_inicio` | INTEGER | Dia del itinerario en que se llega |
| `dia_fin` | INTEGER | Dia del itinerario en que se sale |
| `tipo_ubicacion` | VARCHAR(50) | Tipo: "origen", "destino", "parada", "punto_interes" |
| `imagen_url` | TEXT | URL de imagen del lugar (opcional) |
| `activo` | BOOLEAN | Si esta activo o no |

---

## 2. Endpoints del API

### 2.1 Endpoints ADMIN (requieren JWT de admin)

#### Listar ubicaciones de un tour
```
GET /admin/tours/{tour_id}/ubicaciones
Authorization: Bearer {token}
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "tour_id": 1,
    "nombre": "Quito",
    "pais": "Ecuador",
    "provincia": "Pichincha",
    "ciudad": "Quito",
    "descripcion": "Capital de Ecuador, centro historico UNESCO",
    "latitud": -0.180653,
    "longitud": -78.467838,
    "orden": 1,
    "dia_inicio": 1,
    "dia_fin": 1,
    "tipo_ubicacion": "origen",
    "imagen_url": "/uploads/lugares/quito.jpg",
    "activo": true
  },
  {
    "id": 2,
    "tour_id": 1,
    "nombre": "Cotopaxi",
    ...
  }
]
```

---

#### Crear una ubicacion
```
POST /admin/tours/{tour_id}/ubicaciones
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "nombre": "Quito",
  "pais": "Ecuador",
  "provincia": "Pichincha",
  "ciudad": "Quito",
  "descripcion": "Capital de Ecuador, centro historico patrimonio UNESCO",
  "latitud": -0.180653,
  "longitud": -78.467838,
  "orden": 1,
  "dia_inicio": 1,
  "dia_fin": 1,
  "tipo_ubicacion": "origen",
  "imagen_url": "/uploads/lugares/quito.jpg"
}
```

**Campos requeridos:** `nombre` (el `pais` se toma del tour si no se envia)

**Respuesta exitosa (201):**
```json
{
  "message": "Ubicacion creada exitosamente",
  "ubicacion": { ... }
}
```

---

#### Crear multiples ubicaciones (batch)
```
POST /admin/tours/{tour_id}/ubicaciones/batch
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "ubicaciones": [
    {
      "nombre": "Quito",
      "latitud": -0.180653,
      "longitud": -78.467838,
      "orden": 1,
      "tipo_ubicacion": "origen"
    },
    {
      "nombre": "Cotopaxi",
      "provincia": "Cotopaxi",
      "latitud": -0.683333,
      "longitud": -78.433333,
      "orden": 2,
      "dia_inicio": 2,
      "dia_fin": 2,
      "tipo_ubicacion": "destino"
    },
    {
      "nombre": "Cuenca",
      "provincia": "Azuay",
      "latitud": -2.900556,
      "longitud": -79.005556,
      "orden": 3,
      "tipo_ubicacion": "destino"
    }
  ]
}
```

**Respuesta exitosa (201):**
```json
{
  "message": "3 ubicaciones creadas",
  "ubicaciones": [ ... ]
}
```

---

#### Actualizar ubicacion
```
PUT /admin/ubicaciones/{ubicacion_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Body (solo campos a actualizar):**
```json
{
  "nombre": "Quito - Centro Historico",
  "descripcion": "Nueva descripcion...",
  "latitud": -0.180653
}
```

---

#### Eliminar ubicacion
```
DELETE /admin/ubicaciones/{ubicacion_id}
Authorization: Bearer {token}
```

---

#### Reordenar ubicaciones
```
POST /admin/ubicaciones/reorder
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "orden": [3, 1, 2, 5, 4]
}
```
(Los IDs en el orden deseado)

---

### 2.2 Endpoint PUBLICO (sin autenticacion)

#### Obtener ubicaciones de un tour (para el mapa)
```
GET /tours/{slug}/ubicaciones
```

**Ejemplo:** `GET /tours/ecuador-aventura/ubicaciones`

**Respuesta:**
```json
{
  "tour": {
    "id": 1,
    "nombre": "Ecuador Aventura",
    "slug": "ecuador-aventura",
    "pais": "Ecuador"
  },
  "centro": {
    "lat": -1.234567,
    "lng": -78.567890
  },
  "zoom_sugerido": 7,
  "ubicaciones": [
    {
      "id": 1,
      "nombre": "Quito",
      "pais": "Ecuador",
      "provincia": "Pichincha",
      "ciudad": "Quito",
      "descripcion": "Capital de Ecuador...",
      "latitud": -0.180653,
      "longitud": -78.467838,
      "orden": 1,
      "dia_inicio": 1,
      "dia_fin": 1,
      "tipo_ubicacion": "origen",
      "imagen_url": "/uploads/lugares/quito.jpg",
      "activo": true
    }
  ],
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "id": 1,
          "nombre": "Quito",
          "descripcion": "Capital de Ecuador...",
          "orden": 1,
          "tipo": "origen",
          "dia_inicio": 1,
          "dia_fin": 1,
          "imagen_url": "/uploads/lugares/quito.jpg"
        },
        "geometry": {
          "type": "Point",
          "coordinates": [-78.467838, -0.180653]
        }
      }
    ]
  }
}
```

**Nota:** El `geojson` esta en formato estandar GeoJSON para usar directamente con librerias de mapas.

---

## 3. Ubicaciones incluidas en detalle del tour

Al obtener el detalle de un tour (`GET /tours/{slug}`), las ubicaciones ya vienen incluidas:

```json
{
  "tour": {
    "id": 1,
    "nombre": "Ecuador Aventura",
    "slug": "ecuador-aventura",
    ...
    "ubicaciones": [
      {
        "id": 1,
        "nombre": "Quito",
        "latitud": -0.180653,
        "longitud": -78.467838,
        ...
      }
    ]
  }
}
```

---

## 4. Implementacion Frontend con Leaflet

### 4.1 Instalacion
```bash
npm install leaflet react-leaflet
# o
yarn add leaflet react-leaflet
```

### 4.2 Importar CSS de Leaflet
En tu `index.css` o `App.css`:
```css
@import 'leaflet/dist/leaflet.css';
```

### 4.3 Componente TourMap.jsx (React)

```jsx
import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix para iconos de Leaflet en React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Iconos personalizados por tipo
const iconos = {
  origen: new L.Icon({
    iconUrl: '/icons/marker-green.png', // Crear este icono
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  }),
  destino: new L.Icon({
    iconUrl: '/icons/marker-blue.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  }),
  parada: new L.Icon({
    iconUrl: '/icons/marker-yellow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  }),
};

export default function TourMap({ slug }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUbicaciones = async () => {
      try {
        const res = await fetch(`${API_URL}/tours/${slug}/ubicaciones`);
        const json = await res.json();
        setData(json);
      } catch (error) {
        console.error('Error cargando ubicaciones:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUbicaciones();
  }, [slug]);

  if (loading) return <div>Cargando mapa...</div>;
  if (!data || !data.ubicaciones.length) return <div>No hay ubicaciones para mostrar</div>;

  // Coordenadas para la linea de ruta
  const rutaCoordenadas = data.ubicaciones
    .filter(u => u.latitud && u.longitud)
    .map(u => [u.latitud, u.longitud]);

  return (
    <div className="tour-map-container" style={{ height: '500px', width: '100%' }}>
      <MapContainer
        center={[data.centro?.lat || -1.8312, data.centro?.lng || -78.1834]}
        zoom={data.zoom_sugerido || 7}
        style={{ height: '100%', width: '100%' }}
      >
        {/* Capa base del mapa */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Linea de ruta conectando los puntos */}
        {rutaCoordenadas.length > 1 && (
          <Polyline
            positions={rutaCoordenadas}
            color="#C1A919"
            weight={3}
            opacity={0.7}
            dashArray="10, 10"
          />
        )}

        {/* Marcadores de cada ubicacion */}
        {data.ubicaciones.map((ubicacion) => (
          ubicacion.latitud && ubicacion.longitud && (
            <Marker
              key={ubicacion.id}
              position={[ubicacion.latitud, ubicacion.longitud]}
              icon={iconos[ubicacion.tipo_ubicacion] || iconos.destino}
            >
              <Popup>
                <div className="popup-content">
                  <h4 style={{ margin: '0 0 8px 0' }}>
                    {ubicacion.orden}. {ubicacion.nombre}
                  </h4>
                  {ubicacion.provincia && (
                    <p style={{ margin: '4px 0', color: '#666', fontSize: '12px' }}>
                      {ubicacion.provincia}, {ubicacion.pais}
                    </p>
                  )}
                  {ubicacion.dia_inicio && (
                    <p style={{ margin: '4px 0', fontSize: '12px' }}>
                      <strong>Dia:</strong> {ubicacion.dia_inicio}
                      {ubicacion.dia_fin && ubicacion.dia_fin !== ubicacion.dia_inicio
                        ? ` - ${ubicacion.dia_fin}`
                        : ''}
                    </p>
                  )}
                  {ubicacion.descripcion && (
                    <p style={{ margin: '8px 0 0', fontSize: '13px' }}>
                      {ubicacion.descripcion}
                    </p>
                  )}
                  {ubicacion.imagen_url && (
                    <img
                      src={ubicacion.imagen_url}
                      alt={ubicacion.nombre}
                      style={{ width: '100%', marginTop: '8px', borderRadius: '4px' }}
                    />
                  )}
                </div>
              </Popup>
            </Marker>
          )
        ))}
      </MapContainer>
    </div>
  );
}
```

### 4.4 Uso del componente

```jsx
// En la pagina del tour
import TourMap from '../components/TourMap';

function TourDetailPage({ tour }) {
  return (
    <div>
      <h1>{tour.nombre}</h1>

      {/* Seccion del mapa */}
      <section className="tour-map-section">
        <h2>Ruta del Tour</h2>
        <TourMap slug={tour.slug} />
      </section>

      {/* Resto del contenido... */}
    </div>
  );
}
```

---

## 5. Implementacion Frontend ADMIN

### 5.1 Formulario para agregar ubicacion

```jsx
import { useState } from 'react';

export default function UbicacionForm({ tourId, onSuccess }) {
  const [formData, setFormData] = useState({
    nombre: '',
    provincia: '',
    ciudad: '',
    descripcion: '',
    latitud: '',
    longitud: '',
    orden: 1,
    dia_inicio: '',
    dia_fin: '',
    tipo_ubicacion: 'destino',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/admin/tours/${tourId}/ubicaciones`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...formData,
          latitud: formData.latitud ? parseFloat(formData.latitud) : null,
          longitud: formData.longitud ? parseFloat(formData.longitud) : null,
          orden: parseInt(formData.orden),
          dia_inicio: formData.dia_inicio ? parseInt(formData.dia_inicio) : null,
          dia_fin: formData.dia_fin ? parseInt(formData.dia_fin) : null,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        alert('Ubicacion creada!');
        onSuccess?.(data.ubicacion);
        // Limpiar formulario
        setFormData({
          nombre: '',
          provincia: '',
          ciudad: '',
          descripcion: '',
          latitud: '',
          longitud: '',
          orden: 1,
          dia_inicio: '',
          dia_fin: '',
          tipo_ubicacion: 'destino',
        });
      } else {
        const error = await res.json();
        alert(error.message || 'Error al crear ubicacion');
      }
    } catch (error) {
      console.error(error);
      alert('Error de conexion');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="ubicacion-form">
      <h3>Agregar Ubicacion al Tour</h3>

      <div className="form-row">
        <div className="form-group">
          <label>Nombre del lugar *</label>
          <input
            type="text"
            value={formData.nombre}
            onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
            placeholder="Ej: Quito, Cotopaxi, Galapagos..."
            required
          />
        </div>

        <div className="form-group">
          <label>Tipo</label>
          <select
            value={formData.tipo_ubicacion}
            onChange={(e) => setFormData({ ...formData, tipo_ubicacion: e.target.value })}
          >
            <option value="origen">Origen (punto de partida)</option>
            <option value="destino">Destino</option>
            <option value="parada">Parada</option>
            <option value="punto_interes">Punto de interes</option>
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Provincia/Estado</label>
          <input
            type="text"
            value={formData.provincia}
            onChange={(e) => setFormData({ ...formData, provincia: e.target.value })}
            placeholder="Ej: Pichincha"
          />
        </div>

        <div className="form-group">
          <label>Ciudad</label>
          <input
            type="text"
            value={formData.ciudad}
            onChange={(e) => setFormData({ ...formData, ciudad: e.target.value })}
            placeholder="Ej: Quito"
          />
        </div>
      </div>

      <div className="form-group">
        <label>Descripcion</label>
        <textarea
          value={formData.descripcion}
          onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
          placeholder="Breve descripcion del lugar..."
          rows={3}
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Latitud</label>
          <input
            type="number"
            step="any"
            value={formData.latitud}
            onChange={(e) => setFormData({ ...formData, latitud: e.target.value })}
            placeholder="Ej: -0.180653"
          />
        </div>

        <div className="form-group">
          <label>Longitud</label>
          <input
            type="number"
            step="any"
            value={formData.longitud}
            onChange={(e) => setFormData({ ...formData, longitud: e.target.value })}
            placeholder="Ej: -78.467838"
          />
        </div>
      </div>

      <p className="help-text">
        Tip: Busca las coordenadas en Google Maps, haz clic derecho en el lugar y copia las coordenadas.
      </p>

      <div className="form-row">
        <div className="form-group">
          <label>Orden de visita</label>
          <input
            type="number"
            min="1"
            value={formData.orden}
            onChange={(e) => setFormData({ ...formData, orden: e.target.value })}
          />
        </div>

        <div className="form-group">
          <label>Dia inicio</label>
          <input
            type="number"
            min="1"
            value={formData.dia_inicio}
            onChange={(e) => setFormData({ ...formData, dia_inicio: e.target.value })}
            placeholder="Ej: 1"
          />
        </div>

        <div className="form-group">
          <label>Dia fin</label>
          <input
            type="number"
            min="1"
            value={formData.dia_fin}
            onChange={(e) => setFormData({ ...formData, dia_fin: e.target.value })}
            placeholder="Ej: 2"
          />
        </div>
      </div>

      <button type="submit" disabled={loading}>
        {loading ? 'Guardando...' : 'Agregar Ubicacion'}
      </button>
    </form>
  );
}
```

---

## 6. Coordenadas de lugares comunes en Ecuador

Para facilitar el trabajo, aqui hay coordenadas de lugares turisticos comunes:

| Lugar | Latitud | Longitud |
|-------|---------|----------|
| Quito (Centro) | -0.180653 | -78.467838 |
| Quito (Mitad del Mundo) | -0.002217 | -78.455833 |
| Guayaquil | -2.189444 | -79.889167 |
| Cuenca | -2.900556 | -79.005556 |
| Cotopaxi (Volcan) | -0.683333 | -78.433333 |
| Banos de Agua Santa | -1.396667 | -78.424722 |
| Otavalo | 0.234167 | -78.261944 |
| Mindo | -0.050000 | -78.783333 |
| Galapagos (Santa Cruz) | -0.741667 | -90.303611 |
| Galapagos (San Cristobal) | -0.900000 | -89.600000 |
| Montanita | -1.833333 | -80.750000 |
| Tena | -0.983333 | -77.816667 |
| Puyo | -1.483333 | -78.000000 |
| Riobamba | -1.666667 | -78.650000 |
| Chimborazo | -1.468889 | -78.816667 |
| Quilotoa | -0.858611 | -78.903056 |
| Papallacta | -0.366667 | -78.133333 |
| Yasuni | -0.833333 | -76.166667 |

---

## 7. Ejemplo completo: Agregar ruta a un tour

### Desde Postman o codigo:

```javascript
// Crear todas las ubicaciones del tour "Ecuador Clasico" de una vez
const ubicaciones = [
  {
    nombre: "Quito",
    provincia: "Pichincha",
    descripcion: "Llegada al aeropuerto, traslado al hotel en el centro historico",
    latitud: -0.180653,
    longitud: -78.467838,
    orden: 1,
    dia_inicio: 1,
    dia_fin: 1,
    tipo_ubicacion: "origen"
  },
  {
    nombre: "Otavalo",
    provincia: "Imbabura",
    descripcion: "Visita al mercado indigena mas grande de Sudamerica",
    latitud: 0.234167,
    longitud: -78.261944,
    orden: 2,
    dia_inicio: 2,
    dia_fin: 2,
    tipo_ubicacion: "destino"
  },
  {
    nombre: "Cotopaxi",
    provincia: "Cotopaxi",
    descripcion: "Ascenso al refugio del volcan activo mas alto del mundo",
    latitud: -0.683333,
    longitud: -78.433333,
    orden: 3,
    dia_inicio: 3,
    dia_fin: 3,
    tipo_ubicacion: "destino"
  },
  {
    nombre: "Banos",
    provincia: "Tungurahua",
    descripcion: "Ciudad de las cascadas, aventura y aguas termales",
    latitud: -1.396667,
    longitud: -78.424722,
    orden: 4,
    dia_inicio: 4,
    dia_fin: 4,
    tipo_ubicacion: "destino"
  },
  {
    nombre: "Cuenca",
    provincia: "Azuay",
    descripcion: "Ciudad colonial patrimonio UNESCO",
    latitud: -2.900556,
    longitud: -79.005556,
    orden: 5,
    dia_inicio: 5,
    dia_fin: 6,
    tipo_ubicacion: "destino"
  },
  {
    nombre: "Guayaquil",
    provincia: "Guayas",
    descripcion: "Visita al Malecon 2000, vuelo de regreso",
    latitud: -2.189444,
    longitud: -79.889167,
    orden: 6,
    dia_inicio: 7,
    dia_fin: 7,
    tipo_ubicacion: "destino"
  }
];

// POST /admin/tours/1/ubicaciones/batch
fetch('/admin/tours/1/ubicaciones/batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  },
  body: JSON.stringify({ ubicaciones })
});
```

---

## 8. Actualizacion de Galeria (descripcion de fotos)

Ahora se puede actualizar la descripcion de las fotos de la galeria:

```
PUT /admin/galeria/{item_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "descripcion": "Vista panoramica del volcan Cotopaxi al amanecer",
  "categoria": "paisajes",
  "orden": 1
}
```

---

## 9. Resumen de cambios en el Backend

### Archivos modificados:
1. `models.py` - Nuevo modelo `TourUbicacion`
2. `routes/admin_routes.py` - Endpoints CRUD para ubicaciones + actualizar galeria
3. `routes/tour_routes.py` - Endpoint publico para ubicaciones

### Script SQL a ejecutar:
- `migrations_ubicaciones.sql` - Crear tabla `travel.tour_ubicaciones`

---

## 10. Checklist de implementacion Frontend

- [ ] Ejecutar script SQL en la base de datos
- [ ] Reiniciar el backend
- [ ] Instalar Leaflet (`npm install leaflet react-leaflet`)
- [ ] Importar CSS de Leaflet
- [ ] Crear componente `TourMap` para mostrar el mapa
- [ ] Agregar seccion de mapa en la pagina de detalle del tour
- [ ] Crear formulario en admin para agregar ubicaciones
- [ ] Crear lista de ubicaciones con opciones de editar/eliminar
- [ ] Agregar funcionalidad de reordenar (drag & drop opcional)

---

**Cualquier duda, revisar los endpoints en Postman o consultar este documento.**
