import React, { useState } from 'react';

export default function DecaForm({ authToken }) {
  const [formData, setFormData] = useState({
    cargador_nombre: '',
    cargador_nif: '',
    cargador_domicilio: '',
    transportista_nombre: '',
    transportista_nif: '',
    transportista_domicilio: '',
    origen_lugar: '',
    destino_lugar: '',
    mercancia_descripcion: '',
    peso_kg: '',
    matricula: '',
    remolque: '',
    observaciones: ''
  });

  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResultado(null);

    try {
      const response = await fetch('/api/v1/deca', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) throw new Error('Error al emitir el documento');

      const data = await response.json();
      setResultado(data);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-md rounded-lg">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Emitir Nuevo Documento Control (DeCA)</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Bloque Cargador */}
        <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
          <h3 className="font-semibold text-gray-700 mb-3">1. Cargador Contractual</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="cargador_nombre" placeholder="Nombre / Razón Social" onChange={handleChange} required className="p-2 border rounded" />
            <input name="cargador_nif" placeholder="NIF / CIF" onChange={handleChange} required className="p-2 border rounded" />
            <input name="cargador_domicilio" placeholder="Domicilio Fiscal" onChange={handleChange} required className="p-2 border rounded" />
          </div>
        </div>

        {/* Bloque Transportista */}
        <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
          <h3 className="font-semibold text-gray-700 mb-3">2. Transportista Efectivo</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="transportista_nombre" placeholder="Nombre / Razón Social" onChange={handleChange} required className="p-2 border rounded" />
            <input name="transportista_nif" placeholder="NIF / CIF" onChange={handleChange} required className="p-2 border rounded" />
            <input name="transportista_domicilio" placeholder="Domicilio Fiscal" onChange={handleChange} required className="p-2 border rounded" />
          </div>
        </div>

        {/* Datos del Viaje */}
        <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
          <h3 className="font-semibold text-gray-700 mb-3">3. Datos del Transporte</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <input name="origen_lugar" placeholder="Origen / Carga" onChange={handleChange} required className="p-2 border rounded" />
            <input name="destino_lugar" placeholder="Destino / Descarga" onChange={handleChange} required className="p-2 border rounded" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input name="mercancia_descripcion" placeholder="Mercancía" onChange={handleChange} required className="p-2 border rounded" />
            <input name="peso_kg" placeholder="Peso (kg)" type="number" onChange={handleChange} required className="p-2 border rounded" />
            <input name="matricula" placeholder="Matrícula Tractora" onChange={handleChange} required className="p-2 border rounded" />
            <input name="remolque" placeholder="Remolque (Opcional)" onChange={handleChange} className="p-2 border rounded" />
          </div>
        </div>

        <button 
          type="submit" 
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-md font-bold hover:bg-blue-700 transition"
        >
          {loading ? 'Generando y Firmando...' : 'Emitir DeCA Inalterable'}
        </button>
      </form>

      {resultado && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md text-green-800">
          <p className="font-bold">¡DeCA Emitido Correctamente!</p>
          <p>Código: <span className="font-mono">{resultado.codigo_deca}</span></p>
          <p className="text-sm">Hash SHA-256: <span className="font-mono text-xs">{resultado.hash_sha256}</span></p>
        </div>
      )}
    </div>
  );
}