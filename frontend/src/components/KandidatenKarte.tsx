import { useEffect } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { Kandidat } from '../api'

function farbe(k: Kandidat) {
  const s = k.recherche_status === 'fertig' ? k.score : null
  if (s == null) return '#bac1b5'
  if (s >= 70) return '#2f6b3f'
  if (s >= 45) return '#f2c12e'
  return '#8e978b'
}

function Ausschnitt({ punkte }: { punkte: [number, number][] }) {
  const karte = useMap()
  useEffect(() => {
    if (punkte.length > 1) karte.fitBounds(punkte, { padding: [30, 30], maxZoom: 15 })
    else if (punkte.length === 1) karte.setView(punkte[0], 14)
  }, [karte, punkte])
  return null
}

export default function KandidatenKarte({
  zentrum,
  kandidaten,
  markiert,
  onMarkieren,
  onOeffnen,
}: {
  zentrum: [number, number]
  kandidaten: Kandidat[]
  markiert: number | null
  onMarkieren: (id: number | null) => void
  onOeffnen: (id: number) => void
}) {
  const punkte: [number, number][] = [zentrum, ...kandidaten.map((k) => [k.unternehmen.lat, k.unternehmen.lon] as [number, number])]
  return (
    <MapContainer center={zentrum} zoom={13} scrollWheelZoom={false} className="h-full min-h-[320px] w-full rounded-xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Ausschnitt punkte={punkte} />
      <CircleMarker center={zentrum} radius={9} pathOptions={{ color: '#f2c12e', weight: 3, fillColor: '#173b26', fillOpacity: 1 }}>
        <Tooltip>Verein</Tooltip>
      </CircleMarker>
      {kandidaten.map((k) => {
        const aktiv = markiert === k.id
        if (k.gesperrt) {
          // Gesperrt: nur grob verortet (Server rundet), grau, ohne Namen
          return (
            <CircleMarker key={k.id} center={[k.unternehmen.lat, k.unternehmen.lon]} radius={6}
              pathOptions={{ color: '#fff', weight: 1, fillColor: '#bac1b5', fillOpacity: 0.7, dashArray: '2 2' }}>
              <Tooltip direction="top">{k.unternehmen.branche}, mit Abo sichtbar</Tooltip>
            </CircleMarker>
          )
        }
        return (
          <CircleMarker
            key={k.id}
            center={[k.unternehmen.lat, k.unternehmen.lon]}
            radius={aktiv ? 11 : 7}
            pathOptions={{ color: '#fff', weight: 2, fillColor: farbe(k), fillOpacity: aktiv ? 1 : 0.85 }}
            eventHandlers={{
              click: () => onOeffnen(k.id),
              mouseover: () => onMarkieren(k.id),
              mouseout: () => onMarkieren(null),
            }}
          >
            <Tooltip direction="top">
              <strong>{k.unternehmen.name}</strong>
              <br />
              {k.unternehmen.branche}, {k.recherche_status === 'fertig' ? `Score ${k.score}` : 'noch nicht recherchiert'}
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
