# Documentacion: Sistema de Comentarios y Resenas de Tours

## Resumen

Sistema para que los usuarios dejen comentarios/resenas sobre los tours que han realizado. Los comentarios requieren aprobacion del admin antes de mostrarse publicamente.

**Flujo:**
1. Usuario logueado deja un comentario con calificacion (1-5 estrellas)
2. El comentario queda en estado "pendiente"
3. Admin aprueba o rechaza el comentario
4. Si es aprobado, se muestra en la pagina publica del tour

---

## 1. Estructura de Datos

### Tabla: `travel.comentarios`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `id` | BIGINT | ID unico |
| `usuario_id` | BIGINT | FK al usuario que comento |
| `tour_id` | BIGINT | FK al tour comentado |
| `calificacion` | INTEGER | Puntuacion de 1 a 5 (estrellas) |
| `comentario` | TEXT | Texto del comentario |
| `estado` | ENUM | "pendiente", "aprobado", "rechazado" |
| `respuesta_admin` | TEXT | Respuesta opcional del admin |
| `created_at` | TIMESTAMP | Fecha de creacion |
| `updated_at` | TIMESTAMP | Fecha de actualizacion |

### Estados posibles:
- `pendiente` - Recien creado, esperando moderacion
- `aprobado` - Visible en la pagina publica del tour
- `rechazado` - No se muestra, el admin puede dejar una razon

---

## 2. Endpoints del API

### 2.1 Endpoints PUBLICOS

#### Obtener detalle del tour CON sus comentarios aprobados
```
GET /tours/{slug}
```

**Ejemplo:** `GET /tours/ecuador-aventura`

**Respuesta:**
```json
{
  "tour": {
    "id": 1,
    "nombre": "Ecuador Aventura",
    "slug": "ecuador-aventura",
    "pais": "Ecuador",
    "duracion_dias": 7,
    "precio_pp": 1500.00,
    "descripcion_corta": "...",
    "descripcion_larga": "...",
    "itinerarios": [...],
    "galeria": [...],
    "ubicaciones": [...],
    ...
  },
  "comentarios": [
    {
      "id": 1,
      "usuario": "Juan Perez",
      "calificacion": 5,
      "comentario": "Excelente tour! Los guias fueron muy profesionales y los paisajes increibles.",
      "created_at": "2024-12-15T10:30:00"
    },
    {
      "id": 2,
      "usuario": "Maria Garcia",
      "calificacion": 4,
      "comentario": "Muy buena experiencia, solo que el clima no ayudo un dia.",
      "created_at": "2024-12-10T14:20:00"
    }
  ]
}
```

**Nota:** Solo se devuelven comentarios con estado `aprobado`.

---

### 2.2 Endpoint para CREAR comentario (Usuario logueado)

#### Crear un comentario/resena
```
POST /tours/{tour_id}/comentarios
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "comentario": "Fue una experiencia increible! Los guias super atentos y los lugares hermosos. 100% recomendado.",
  "calificacion": 5
}
```

**Campos requeridos:**
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `comentario` | string | Texto del comentario (requerido) |
| `calificacion` | integer | Puntuacion de 1 a 5 (requerido) |

**Respuesta exitosa (201):**
```json
{
  "message": "Comentario enviado y pendiente de aprobacion",
  "comentario": {
    "id": 15,
    "usuario": "Carlos Lopez",
    "calificacion": 5,
    "comentario": "Fue una experiencia increible!...",
    "created_at": "2024-12-29T15:45:00"
  }
}
```

**Errores posibles:**
| Codigo | Mensaje |
|--------|---------|
| 400 | "Faltan campos obligatorios" |
| 400 | "La calificacion debe ser un numero entero" |
| 400 | "La calificacion debe estar entre 1 y 5" |
| 401 | No autorizado (sin token) |
| 404 | "Usuario no encontrado" |
| 404 | "Tour no encontrado o inactivo" |

---

### 2.3 Endpoints ADMIN (Moderacion)

#### Listar todos los comentarios
```
GET /admin/comentarios
```

**Query params opcionales:**
| Param | Valores | Descripcion |
|-------|---------|-------------|
| `estado` | pendiente, aprobado, rechazado | Filtrar por estado |

**Ejemplos:**
- `GET /admin/comentarios` - Todos los comentarios
- `GET /admin/comentarios?estado=pendiente` - Solo pendientes (para moderar)
- `GET /admin/comentarios?estado=aprobado` - Solo aprobados

**Respuesta:**
```json
[
  {
    "id": 15,
    "tour_id": 1,
    "usuario_id": 5,
    "calificacion": 5,
    "comentario": "Fue una experiencia increible!...",
    "estado": "pendiente",
    "respuesta_admin": null,
    "created_at": "2024-12-29T15:45:00"
  },
  {
    "id": 14,
    "tour_id": 2,
    "usuario_id": 3,
    "calificacion": 4,
    "comentario": "Muy buen tour, lo recomiendo.",
    "estado": "aprobado",
    "respuesta_admin": null,
    "created_at": "2024-12-28T10:20:00"
  }
]
```

---

#### Aprobar un comentario
```
PATCH /admin/comentarios/{comentario_id}/aprobar
Authorization: Bearer {token_admin}
```

**Respuesta exitosa:**
```json
{
  "message": "Comentario aprobado"
}
```

Despues de aprobar, el comentario aparecera en la pagina publica del tour.

---

#### Rechazar un comentario
```
PATCH /admin/comentarios/{comentario_id}/rechazar
Authorization: Bearer {token_admin}
Content-Type: application/json
```

**Body (opcional):**
```json
{
  "respuesta_admin": "El comentario contiene lenguaje inapropiado"
}
```

**Respuesta exitosa:**
```json
{
  "message": "Comentario rechazado"
}
```

---

## 3. Implementacion Frontend

### 3.1 Componente para mostrar comentarios (Pagina publica del tour)

```jsx
// components/ComentariosList.jsx
export default function ComentariosList({ comentarios }) {
  if (!comentarios || comentarios.length === 0) {
    return (
      <div className="no-comentarios">
        <p>Aun no hay resenas para este tour. Se el primero en comentar!</p>
      </div>
    );
  }

  // Calcular promedio de calificaciones
  const promedio = comentarios.reduce((acc, c) => acc + c.calificacion, 0) / comentarios.length;

  return (
    <div className="comentarios-section">
      <div className="comentarios-header">
        <h3>Resenas de viajeros</h3>
        <div className="rating-summary">
          <span className="rating-number">{promedio.toFixed(1)}</span>
          <div className="stars">
            {[1, 2, 3, 4, 5].map(star => (
              <span key={star} className={star <= Math.round(promedio) ? 'star filled' : 'star'}>
                ★
              </span>
            ))}
          </div>
          <span className="total-reviews">({comentarios.length} resenas)</span>
        </div>
      </div>

      <div className="comentarios-list">
        {comentarios.map(comentario => (
          <div key={comentario.id} className="comentario-card">
            <div className="comentario-header">
              <span className="usuario-nombre">{comentario.usuario}</span>
              <div className="stars">
                {[1, 2, 3, 4, 5].map(star => (
                  <span key={star} className={star <= comentario.calificacion ? 'star filled' : 'star'}>
                    ★
                  </span>
                ))}
              </div>
            </div>
            <p className="comentario-texto">{comentario.comentario}</p>
            <span className="comentario-fecha">
              {new Date(comentario.created_at).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3.2 CSS para comentarios

```css
.comentarios-section {
  margin-top: 40px;
  padding: 30px;
  background: #f9f9f9;
  border-radius: 12px;
}

.comentarios-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.rating-summary {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rating-number {
  font-size: 28px;
  font-weight: bold;
  color: #C1A919;
}

.stars {
  display: flex;
  gap: 2px;
}

.star {
  color: #ddd;
  font-size: 18px;
}

.star.filled {
  color: #C1A919;
}

.total-reviews {
  color: #666;
  font-size: 14px;
}

.comentario-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.comentario-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.usuario-nombre {
  font-weight: 600;
  color: #333;
}

.comentario-texto {
  color: #555;
  line-height: 1.6;
  margin-bottom: 12px;
}

.comentario-fecha {
  font-size: 12px;
  color: #999;
}
```

### 3.3 Formulario para dejar comentario (Usuario logueado)

```jsx
// components/ComentarioForm.jsx
import { useState } from 'react';

export default function ComentarioForm({ tourId, onSuccess }) {
  const [formData, setFormData] = useState({
    comentario: '',
    calificacion: 5
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('token');

      if (!token) {
        setError('Debes iniciar sesion para dejar un comentario');
        setLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/tours/${tourId}/comentarios`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });

      const data = await res.json();

      if (res.ok) {
        setSuccess(true);
        setFormData({ comentario: '', calificacion: 5 });
        onSuccess?.();
      } else {
        setError(data.message || 'Error al enviar comentario');
      }
    } catch (err) {
      setError('Error de conexion');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="comentario-success">
        <h4>Gracias por tu resena!</h4>
        <p>Tu comentario ha sido enviado y esta pendiente de aprobacion. Aparecera en la pagina una vez sea revisado.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="comentario-form">
      <h4>Deja tu resena</h4>

      {error && <div className="error-message">{error}</div>}

      <div className="form-group">
        <label>Calificacion</label>
        <div className="star-rating-input">
          {[1, 2, 3, 4, 5].map(star => (
            <button
              key={star}
              type="button"
              className={`star-btn ${star <= formData.calificacion ? 'active' : ''}`}
              onClick={() => setFormData({ ...formData, calificacion: star })}
            >
              ★
            </button>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label>Tu comentario</label>
        <textarea
          value={formData.comentario}
          onChange={(e) => setFormData({ ...formData, comentario: e.target.value })}
          placeholder="Cuentanos tu experiencia en este tour..."
          rows={4}
          required
          minLength={10}
        />
      </div>

      <button type="submit" disabled={loading} className="btn-submit">
        {loading ? 'Enviando...' : 'Enviar resena'}
      </button>
    </form>
  );
}
```

### 3.4 CSS para el formulario

```css
.comentario-form {
  background: white;
  padding: 24px;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  margin-top: 24px;
}

.comentario-form h4 {
  margin-bottom: 20px;
  color: #333;
}

.star-rating-input {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.star-btn {
  background: none;
  border: none;
  font-size: 32px;
  color: #ddd;
  cursor: pointer;
  transition: color 0.2s;
}

.star-btn:hover,
.star-btn.active {
  color: #C1A919;
}

.comentario-form textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  resize: vertical;
  font-family: inherit;
}

.comentario-form textarea:focus {
  outline: none;
  border-color: #C1A919;
}

.btn-submit {
  background: #C1A919;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 16px;
}

.btn-submit:hover {
  background: #a08915;
}

.btn-submit:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.comentario-success {
  background: #e8f5e9;
  padding: 24px;
  border-radius: 12px;
  text-align: center;
}

.comentario-success h4 {
  color: #2e7d32;
  margin-bottom: 8px;
}

.error-message {
  background: #ffebee;
  color: #c62828;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}
```

---

### 3.5 Uso en la pagina del tour

```jsx
// pages/TourDetailPage.jsx
import { useEffect, useState } from 'react';
import ComentariosList from '../components/ComentariosList';
import ComentarioForm from '../components/ComentarioForm';

export default function TourDetailPage({ slug }) {
  const [tour, setTour] = useState(null);
  const [comentarios, setComentarios] = useState([]);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // Verificar si hay usuario logueado
    const token = localStorage.getItem('token');
    setIsLoggedIn(!!token);

    // Cargar datos del tour
    const fetchTour = async () => {
      const res = await fetch(`${API_URL}/tours/${slug}`);
      const data = await res.json();
      setTour(data.tour);
      setComentarios(data.comentarios);
    };

    fetchTour();
  }, [slug]);

  if (!tour) return <div>Cargando...</div>;

  return (
    <div className="tour-detail-page">
      {/* ... otros datos del tour ... */}

      {/* Seccion de comentarios */}
      <section className="comentarios-section-wrapper">
        <ComentariosList comentarios={comentarios} />

        {isLoggedIn ? (
          <ComentarioForm
            tourId={tour.id}
            onSuccess={() => {
              // Opcional: recargar comentarios (aunque el nuevo estara pendiente)
            }}
          />
        ) : (
          <div className="login-prompt">
            <p>Inicia sesion para dejar tu resena</p>
            <a href="/login" className="btn-login">Iniciar sesion</a>
          </div>
        )}
      </section>
    </div>
  );
}
```

---

## 4. Panel Admin - Moderacion de comentarios

### 4.1 Lista de comentarios pendientes

```jsx
// admin/pages/ComentariosModeracion.jsx
import { useEffect, useState } from 'react';

export default function ComentariosModeracion() {
  const [comentarios, setComentarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState('pendiente');

  const fetchComentarios = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}/admin/comentarios?estado=${filtro}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    setComentarios(data);
    setLoading(false);
  };

  useEffect(() => {
    fetchComentarios();
  }, [filtro]);

  const aprobar = async (id) => {
    const token = localStorage.getItem('token');
    await fetch(`${API_URL}/admin/comentarios/${id}/aprobar`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    fetchComentarios();
  };

  const rechazar = async (id, motivo) => {
    const token = localStorage.getItem('token');
    await fetch(`${API_URL}/admin/comentarios/${id}/rechazar`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ respuesta_admin: motivo })
    });
    fetchComentarios();
  };

  return (
    <div className="admin-comentarios">
      <h2>Moderacion de Comentarios</h2>

      <div className="filtros">
        <button
          className={filtro === 'pendiente' ? 'active' : ''}
          onClick={() => setFiltro('pendiente')}
        >
          Pendientes
        </button>
        <button
          className={filtro === 'aprobado' ? 'active' : ''}
          onClick={() => setFiltro('aprobado')}
        >
          Aprobados
        </button>
        <button
          className={filtro === 'rechazado' ? 'active' : ''}
          onClick={() => setFiltro('rechazado')}
        >
          Rechazados
        </button>
      </div>

      {loading ? (
        <p>Cargando...</p>
      ) : comentarios.length === 0 ? (
        <p>No hay comentarios {filtro}s</p>
      ) : (
        <div className="comentarios-list">
          {comentarios.map(c => (
            <div key={c.id} className="comentario-admin-card">
              <div className="comentario-info">
                <div className="meta">
                  <span className="tour">Tour ID: {c.tour_id}</span>
                  <span className="usuario">Usuario ID: {c.usuario_id}</span>
                  <span className="fecha">{new Date(c.created_at).toLocaleDateString()}</span>
                </div>
                <div className="stars">
                  {[1, 2, 3, 4, 5].map(star => (
                    <span key={star} className={star <= c.calificacion ? 'star filled' : 'star'}>
                      ★
                    </span>
                  ))}
                </div>
                <p className="texto">{c.comentario}</p>
                <span className={`estado estado-${c.estado}`}>{c.estado}</span>
              </div>

              {filtro === 'pendiente' && (
                <div className="acciones">
                  <button className="btn-aprobar" onClick={() => aprobar(c.id)}>
                    Aprobar
                  </button>
                  <button
                    className="btn-rechazar"
                    onClick={() => {
                      const motivo = prompt('Motivo del rechazo (opcional):');
                      rechazar(c.id, motivo);
                    }}
                  >
                    Rechazar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 5. Resumen de Endpoints

| Metodo | Endpoint | Auth | Descripcion |
|--------|----------|------|-------------|
| GET | `/tours/{slug}` | No | Detalle tour + comentarios aprobados |
| POST | `/tours/{tour_id}/comentarios` | Usuario | Crear comentario (queda pendiente) |
| GET | `/admin/comentarios` | No* | Listar comentarios (filtrar por estado) |
| PATCH | `/admin/comentarios/{id}/aprobar` | Admin | Aprobar comentario |
| PATCH | `/admin/comentarios/{id}/rechazar` | Admin | Rechazar comentario |

*El endpoint `/admin/comentarios` actualmente no requiere auth, pero se recomienda agregarlo.

---

## 6. Checklist de implementacion Frontend

### Pagina publica del tour:
- [ ] Mostrar lista de comentarios aprobados
- [ ] Mostrar promedio de calificaciones (estrellas)
- [ ] Mostrar cantidad total de resenas
- [ ] Formulario para dejar comentario (solo si esta logueado)
- [ ] Mostrar mensaje de exito despues de enviar
- [ ] Mostrar mensaje si no hay comentarios

### Panel Admin:
- [ ] Pagina de moderacion de comentarios
- [ ] Filtros por estado (pendiente/aprobado/rechazado)
- [ ] Botones de aprobar/rechazar
- [ ] Input para motivo de rechazo (opcional)
- [ ] Contador de comentarios pendientes en dashboard

---

**Cualquier duda, revisar los endpoints en Postman o consultar este documento.**
