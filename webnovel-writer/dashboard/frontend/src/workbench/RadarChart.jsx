/**
 * 六维雷达图。纯 SVG 实现，无外部依赖。
 *
 * Props:
 *   dimensions: { [name: string]: number } — 维度名→分数(0-10)
 *   size: number — 图表尺寸（默认 250）
 */
export default function RadarChart({ dimensions, size = 250 }) {
  const entries = Object.entries(dimensions || {})
  const count = entries.length
  if (count < 3) return null

  const center = size / 2
  const radius = size / 2 - 30
  const angleStep = (2 * Math.PI) / count

  const getPoint = (index, value) => {
    const angle = angleStep * index - Math.PI / 2
    const r = (value / 10) * radius
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    }
  }

  const gridLevels = [2, 4, 6, 8, 10]
  const gridPaths = gridLevels.map(level => {
    const points = entries.map((_, i) => getPoint(i, level))
    return points.map(p => `${p.x},${p.y}`).join(' ')
  })

  const dataPoints = entries.map(([_, score], i) => getPoint(i, score))
  const dataPath = dataPoints.map(p => `${p.x},${p.y}`).join(' ')

  const axes = entries.map(([name, score], i) => {
    const outerPoint = getPoint(i, 10)
    const labelPoint = getPoint(i, 12)
    return { name, score, outerPoint, labelPoint }
  })

  return (
    <svg width={size} height={size} className="radar-chart">
      {gridPaths.map((points, i) => (
        <polygon key={i} points={points} fill="none" stroke="#e0e0e0" strokeWidth="1" />
      ))}

      {axes.map((axis, i) => (
        <line key={i} x1={center} y1={center} x2={axis.outerPoint.x} y2={axis.outerPoint.y} stroke="#e0e0e0" strokeWidth="1" />
      ))}

      <polygon points={dataPath} fill="rgba(59, 130, 246, 0.2)" stroke="#3b82f6" strokeWidth="2" />

      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4" fill="#3b82f6" />
      ))}

      {axes.map((axis, i) => (
        <text key={i} x={axis.labelPoint.x} y={axis.labelPoint.y} textAnchor="middle" dominantBaseline="middle" fontSize="12" fill="#666">
          {axis.name} ({axis.score})
        </text>
      ))}
    </svg>
  )
}
